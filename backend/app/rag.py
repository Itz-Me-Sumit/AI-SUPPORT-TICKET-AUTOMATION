import asyncio
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from fastembed import TextEmbedding
from langchain_openrouter import ChatOpenRouter

from app.config import settings

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_SUFFIXES = {".md", ".txt"}
MAX_CHUNK_CHARS = 900
RRF_K = 60  # standard constant for Reciprocal Rank Fusion
MODES = ("vector", "hybrid", "rerank")

NOT_FOUND_ANSWER = (
    "I do not have that information in our knowledge base."
)

ANSWER_PROMPT = """You are a phone support agent. Answer the customer's question using ONLY the context below.

Rules:
- Reply in at most two short sentences, in plain spoken English.
- Do not use lists, markdown, or symbols. The answer will be read aloud.
- If the context does not contain the answer, say you do not have that information.
- Never invent prices, dates, or policies.
- If the customer asks whether you are a person or an AI, say clearly that you are an AI assistant.

Context:
{context}

Customer question: {question}

Answer:"""


@dataclass
class Chunk:
    source: str
    heading: str
    text: str


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
def _pack_paragraphs(body: str) -> list[str]:
    """Group paragraphs into pieces that stay below MAX_CHUNK_CHARS."""
    pieces: list[str] = []
    current = ""

    for paragraph in re.split(r"\n\s*\n", body):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if current and len(current) + len(paragraph) + 2 > MAX_CHUNK_CHARS:
            pieces.append(current)
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}" if current else paragraph

    if current:
        pieces.append(current)
    return pieces


def split_markdown(text: str, source: str) -> list[Chunk]:
    """Split a document by headings and keep the heading path with every chunk."""
    chunks: list[Chunk] = []
    heading_path: list[str] = []
    buffer: list[str] = []

    def flush() -> None:
        body = "\n".join(buffer).strip()
        buffer.clear()
        if not body:
            return
        heading = " > ".join(heading_path)
        for piece in _pack_paragraphs(body):
            chunks.append(Chunk(source=source, heading=heading, text=piece))

    for line in text.splitlines():
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if match:
            flush()
            level = len(match.group(1))
            heading_path[:] = heading_path[: level - 1]
            heading_path.append(match.group(2).strip())
        else:
            buffer.append(line)

    flush()
    return chunks


def _chunk_text_for_embedding(chunk: Chunk) -> str:
    return f"{chunk.heading}\n{chunk.text}" if chunk.heading else chunk.text


# ---------------------------------------------------------------------------
# Keyword search (BM25)
# ---------------------------------------------------------------------------
TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = {
    "a", "an", "the", "is", "are", "to", "of", "and", "or", "in", "on", "for",
    "my", "i", "do", "does", "can", "you", "your", "it", "how", "what", "with",
    "be", "that", "this", "we", "at", "by", "so", "me", "if", "will",
}


def _stem(token: str) -> str:
    """Very small stemmer so that charge/charged/charges and price/pricing match."""
    for suffix in ("ing", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            token = token[: -len(suffix)]
            break
    if token.endswith("e") and len(token) > 4:
        token = token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    return [_stem(t) for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


class BM25:
    """Okapi BM25 over a small list of tokenized documents."""

    def __init__(self, documents: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.term_freqs = [Counter(doc) for doc in documents]
        self.doc_len = np.array([len(doc) for doc in documents], dtype=np.float32)
        self.avg_len = float(self.doc_len.mean()) if len(documents) else 1.0

        document_freq: Counter = Counter()
        for doc in documents:
            document_freq.update(set(doc))
        total = len(documents)
        self.idf = {
            term: math.log(1 + (total - count + 0.5) / (count + 0.5))
            for term, count in document_freq.items()
        }

    def scores(self, query_tokens: list[str]) -> np.ndarray:
        result = np.zeros(len(self.term_freqs), dtype=np.float32)
        for token in set(query_tokens):
            idf = self.idf.get(token)
            if idf is None:
                continue
            for index, freqs in enumerate(self.term_freqs):
                frequency = freqs.get(token, 0)
                if not frequency:
                    continue
                norm = 1 - self.b + self.b * self.doc_len[index] / self.avg_len
                result[index] += idf * frequency * (self.k1 + 1) / (frequency + self.k1 * norm)
        return result


# ---------------------------------------------------------------------------
# Knowledge base with three retrieval modes
# ---------------------------------------------------------------------------
def gate_threshold(mode: str) -> float:
    """Minimum score for 'found'. Cosine scores and reranker scores use different scales."""
    return settings.rerank_min_score if mode == "rerank" else settings.rag_min_score


class KnowledgeBase:
    """In-memory index: vector search, hybrid search (vector + BM25) and reranking."""

    def __init__(self, chunks: list[Chunk], matrix: np.ndarray, model: TextEmbedding):
        self.chunks = chunks
        self._matrix = matrix
        self._model = model
        self._bm25 = BM25([tokenize(_chunk_text_for_embedding(c)) for c in chunks])
        self._reranker = None
        self._reranker_failed = False

    def warm_up(self) -> None:
        """Load the reranker once at startup so the first call is not slow."""
        self._get_reranker()

    def _get_reranker(self):
        if self._reranker is None and not self._reranker_failed:
            try:
                from fastembed.rerank.cross_encoder import TextCrossEncoder

                self._reranker = TextCrossEncoder(
                    model_name=settings.rerank_model,
                    cache_dir=settings.embedding_cache_dir,
                )
            except Exception:  # noqa: BLE001 - fall back to hybrid search
                logger.exception("Could not load the reranker, falling back to hybrid search")
                self._reranker_failed = True
        return self._reranker

    def _cosine_scores(self, query: str) -> np.ndarray:
        vector = np.array(list(self._model.embed([query])), dtype=np.float32)[0]
        vector = vector / (np.linalg.norm(vector) + 1e-12)
        return self._matrix @ vector

    def search_with_mode(self, query: str, top_k: int, mode: str | None = None):
        """Return (hits, mode_used). hits is a list of (chunk, score)."""
        mode = mode or settings.rag_mode
        cosine = self._cosine_scores(query)

        if mode not in ("hybrid", "rerank"):
            order = np.argsort(-cosine)[:top_k]
            return [(self.chunks[i], float(cosine[i])) for i in order], "vector"

        # Hybrid: fuse the vector ranking and the keyword ranking
        size = max(settings.rag_candidates, top_k)
        vector_order = np.argsort(-cosine)[:size]
        keyword_scores = self._bm25.scores(tokenize(query))
        keyword_order = [i for i in np.argsort(-keyword_scores)[:size] if keyword_scores[i] > 0]

        fused: dict[int, float] = {}
        for rank, index in enumerate(vector_order):
            fused[int(index)] = fused.get(int(index), 0.0) + 1.0 / (RRF_K + rank + 1)
        for rank, index in enumerate(keyword_order):
            fused[int(index)] = fused.get(int(index), 0.0) + 1.0 / (RRF_K + rank + 1)
        candidates = sorted(fused, key=fused.get, reverse=True)[:size]

        reranker = self._get_reranker() if mode == "rerank" else None
        if reranker is None:
            hits = [(self.chunks[i], float(cosine[i])) for i in candidates[:top_k]]
            return hits, "hybrid"

        texts = [_chunk_text_for_embedding(self.chunks[i]) for i in candidates]
        scores = [float(s) for s in reranker.rerank(query, texts)]
        ranked = sorted(zip(candidates, scores), key=lambda pair: pair[1], reverse=True)[:top_k]
        return [(self.chunks[i], score) for i, score in ranked], "rerank"

    def search(self, query: str, top_k: int, mode: str | None = None):
        return self.search_with_mode(query, top_k, mode)[0]


def load_knowledge_base() -> "KnowledgeBase | None":
    """Read the knowledge files, embed them, and return a ready index.

    Returns None (and logs why) instead of crashing the whole app.
    """
    folder = BACKEND_ROOT / settings.knowledge_dir
    files = (
        sorted(p for p in folder.rglob("*") if p.suffix.lower() in SUPPORTED_SUFFIXES)
        if folder.exists()
        else []
    )

    chunks: list[Chunk] = []
    for path in files:
        chunks.extend(split_markdown(path.read_text(encoding="utf-8"), path.name))

    if not chunks:
        logger.warning("No knowledge files found in %s", folder)
        return None

    try:
        model = TextEmbedding(
            model_name=settings.embedding_model,
            cache_dir=settings.embedding_cache_dir,
        )
        texts = [_chunk_text_for_embedding(chunk) for chunk in chunks]
        matrix = np.array(list(model.embed(texts)), dtype=np.float32)
    except Exception:  # noqa: BLE001 - the app should still start without RAG
        logger.exception("Could not build the knowledge base index")
        return None

    matrix = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-12)
    knowledge_base = KnowledgeBase(chunks, matrix, model)
    if settings.rag_mode == "rerank":
        knowledge_base.warm_up()

    logger.info(
        "Knowledge base ready: %d chunks from %d files (mode: %s)",
        len(chunks), len(files), settings.rag_mode,
    )
    return knowledge_base


# ---------------------------------------------------------------------------
# Answer generation
# ---------------------------------------------------------------------------
_voice_llm = None


def _get_voice_llm() -> ChatOpenRouter:
    """A separate LLM client so the voice path can use a faster model."""
    global _voice_llm
    if _voice_llm is None:
        _voice_llm = ChatOpenRouter(
            model=settings.voice_llm_model or settings.llm_model,
            temperature=0.1,
            max_retries=2,
        )
    return _voice_llm


TROUBLE_ANSWER = "Sorry, I am having a technical problem right now. Please try again in a moment."

_fallback_llm = None


def _get_fallback_llm():
    """Optional second model, used only if the main voice model keeps failing."""
    global _fallback_llm
    if _fallback_llm is None and settings.voice_fallback_model:
        _fallback_llm = ChatOpenRouter(
            model=settings.voice_fallback_model, temperature=0.1, max_retries=1
        )
    return _fallback_llm


async def _generate_answer(prompt: str) -> "str | None":
    """Ask the LLM. Retry temporary errors (such as rate limits), then try the fallback model."""
    attempts = [
        (_get_voice_llm, 0.0),
        (_get_voice_llm, 0.8),
        (_get_voice_llm, 1.6),
        (_get_fallback_llm, 0.0),
    ]
    for get_llm, wait in attempts:
        llm = get_llm()
        if llm is None:
            continue
        if wait:
            await asyncio.sleep(wait)
        try:
            response = await llm.ainvoke(prompt)
            return str(getattr(response, "content", response)).strip()
        except Exception as exc:  # noqa: BLE001 - try the next attempt
            logger.warning("LLM call failed (%s): %s", type(exc).__name__, exc)
    return None


async def answer_question(kb: KnowledgeBase, question: str) -> dict:
    """Retrieve context and write a short spoken-style answer."""
    hits, mode_used = await asyncio.to_thread(kb.search_with_mode, question, settings.rag_top_k)
    threshold = gate_threshold(mode_used)
    relevant = [(chunk, score) for chunk, score in hits if score >= threshold]

    if not relevant:
        return {"found": False, "answer": NOT_FOUND_ANSWER, "sources": []}

    context = "\n\n".join(
        f"[{chunk.heading or chunk.source}]\n{chunk.text}" for chunk, _ in relevant
    )
    prompt = ANSWER_PROMPT.format(context=context, question=question)
    answer = await _generate_answer(prompt)
    if answer is None:
        return {"found": False, "answer": TROUBLE_ANSWER, "sources": []}

    return {
        "found": True,
        "answer": answer or NOT_FOUND_ANSWER,
        "sources": [
            {"source": chunk.source, "heading": chunk.heading, "score": round(score, 3)}
            for chunk, score in relevant
        ],
    }
