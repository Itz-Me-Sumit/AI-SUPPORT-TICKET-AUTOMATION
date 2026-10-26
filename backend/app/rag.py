import asyncio
import logging
import re
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

NOT_FOUND_ANSWER = (
    "I do not have that information in our knowledge base."
)

ANSWER_PROMPT = """You are a phone support agent. Answer the customer's question using ONLY the context below.

Rules:
- Reply in at most two short sentences, in plain spoken English.
- Do not use lists, markdown, or symbols. The answer will be read aloud.
- If the context does not contain the answer, say you do not have that information.
- Never invent prices, dates, or policies.

Context:
{context}

Customer question: {question}

Answer:"""


@dataclass
class Chunk:
    source: str
    heading: str
    text: str


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


class KnowledgeBase:
    """In-memory vector index over the knowledge files."""

    def __init__(self, chunks: list[Chunk], matrix: np.ndarray, model: TextEmbedding):
        self.chunks = chunks
        self._matrix = matrix
        self._model = model

    def search(self, query: str, top_k: int) -> list[tuple[Chunk, float]]:
        vector = np.array(list(self._model.embed([query])), dtype=np.float32)[0]
        vector = vector / (np.linalg.norm(vector) + 1e-12)
        scores = self._matrix @ vector
        order = np.argsort(-scores)[:top_k]
        return [(self.chunks[i], float(scores[i])) for i in order]


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
    logger.info("Knowledge base ready: %d chunks from %d files", len(chunks), len(files))
    return KnowledgeBase(chunks, matrix, model)


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


async def answer_question(kb: KnowledgeBase, question: str) -> dict:
    """Retrieve context and write a short spoken-style answer."""
    hits = await asyncio.to_thread(kb.search, question, settings.rag_top_k)
    relevant = [(chunk, score) for chunk, score in hits if score >= settings.rag_min_score]

    if not relevant:
        return {"found": False, "answer": NOT_FOUND_ANSWER, "sources": []}

    context = "\n\n".join(
        f"[{chunk.heading or chunk.source}]\n{chunk.text}" for chunk, _ in relevant
    )
    response = await _get_voice_llm().ainvoke(
        ANSWER_PROMPT.format(context=context, question=question)
    )
    answer = str(getattr(response, "content", response)).strip()

    return {
        "found": True,
        "answer": answer or NOT_FOUND_ANSWER,
        "sources": [
            {"source": chunk.source, "heading": chunk.heading, "score": round(score, 3)}
            for chunk, score in relevant
        ],
    }
