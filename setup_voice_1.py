from pathlib import Path

ROOT = Path(__file__).resolve().parent

NEW_FILES = {}

# ---------------------------------------------------------------------------
# backend/app/rag.py
# ---------------------------------------------------------------------------
NEW_FILES["backend/app/rag.py"] = r'''import asyncio
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
'''

# ---------------------------------------------------------------------------
# backend/app/routers/voice.py
# ---------------------------------------------------------------------------
NEW_FILES["backend/app/routers/voice.py"] = r'''import hmac
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import settings
from app.rag import answer_question

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])


class AskRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)


class AskResponse(BaseModel):
    found: bool
    answer: str
    sources: list[dict]


def verify_secret(x_voice_secret: str | None = Header(default=None)) -> None:
    """Only the voice platform (which knows the shared secret) may call these endpoints."""
    expected = settings.voice_api_secret
    if not expected:
        raise HTTPException(status_code=503, detail="Voice API is not configured.")
    if not x_voice_secret or not hmac.compare_digest(x_voice_secret, expected):
        raise HTTPException(status_code=401, detail="Invalid voice API secret.")


@router.post("/ask", response_model=AskResponse, dependencies=[Depends(verify_secret)])
async def ask(payload: AskRequest, request: Request):
    knowledge_base = getattr(request.app.state, "knowledge_base", None)
    if knowledge_base is None:
        raise HTTPException(status_code=503, detail="Knowledge base is not available.")

    logger.info("Voice question: %s", payload.query)
    return await answer_question(knowledge_base, payload.query)
'''

# ---------------------------------------------------------------------------
# backend/knowledge/sample_faq.md (only used until you add your real documents)
# ---------------------------------------------------------------------------
NEW_FILES["backend/knowledge/sample_faq.md"] = r'''# Sample Support FAQ

This is a sample file so the voice helpdesk works on day one.
Replace it with your real company documents (Markdown or text files).

## Plans

### Basic plan
The Basic plan costs 9 dollars per month and supports one user.

### Pro plan
The Pro plan costs 29 dollars per month, supports up to 10 users, and includes priority support.

## Refunds

### Refund policy
Customers can request a full refund within 14 days of purchase.
After 14 days, refunds are given only for unused months of an annual plan.

### How long refunds take
Approved refunds reach the original payment method in 5 to 7 business days.

## Account

### Resetting a password
Open the login page, choose Forgot password, and follow the link sent to your email.
If the email does not arrive, check the spam folder and try again after 10 minutes.

### Locked account
An account is locked after five wrong password attempts.
It unlocks automatically after 30 minutes, or immediately after a password reset.
'''

# ---------------------------------------------------------------------------
# Patches for existing files
# ---------------------------------------------------------------------------
def patch_file(rel_path, marker, replacements):
    path = ROOT / rel_path
    if not path.exists():
        print(f"MISSING {rel_path}")
        return
    text = path.read_text(encoding="utf-8")
    if marker in text:
        print(f"SKIP    {rel_path} (already patched)")
        return
    for old, new in replacements:
        if old not in text:
            print(f"WARNING {rel_path}: could not find text to patch: {old.strip()[:50]!r}")
            return
    for old, new in replacements:
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"PATCHED {rel_path}")


def main():
    print(f"Project root: {ROOT}\n")

    for rel_path, content in NEW_FILES.items():
        path = ROOT / rel_path
        if path.exists():
            print(f"SKIP    {rel_path} (already exists)")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        print(f"CREATED {rel_path}")

    patch_file(
        "backend/app/config.py",
        "voice_api_secret",
        [(
            "    llm_max_retries: int = 3\n",
            "    llm_max_retries: int = 3\n"
            "\n"
            "    # Voice helpdesk and RAG\n"
            "    voice_api_secret: str = \"\"\n"
            "    voice_llm_model: str = \"\"\n"
            "    knowledge_dir: str = \"knowledge\"\n"
            "    embedding_model: str = \"BAAI/bge-small-en-v1.5\"\n"
            "    embedding_cache_dir: str = \"./data/fastembed_cache\"\n"
            "    rag_top_k: int = 3\n"
            "    rag_min_score: float = 0.35\n",
        )],
    )

    patch_file(
        "backend/app/main.py",
        "voice.router",
        [
            ("import logging\n", "import asyncio\nimport logging\n"),
            (
                "from app.routers import tickets\n",
                "from app.rag import load_knowledge_base\nfrom app.routers import tickets, voice\n",
            ),
            (
                "    app.state.workflow = build_workflow(get_llm())\n",
                "    app.state.workflow = build_workflow(get_llm())\n"
                "    app.state.knowledge_base = await asyncio.to_thread(load_knowledge_base)\n",
            ),
            (
                "app.include_router(tickets.router)\n",
                "app.include_router(tickets.router)\napp.include_router(voice.router)\n",
            ),
        ],
    )

    patch_file(
        "backend/Dockerfile",
        "COPY knowledge",
        [("COPY prompts ./prompts\n", "COPY prompts ./prompts\nCOPY knowledge ./knowledge\n")],
    )

    # requirements.txt and .env.example: append only what is missing
    req_path = ROOT / "backend/requirements.txt"
    if req_path.exists():
        req_text = req_path.read_text(encoding="utf-8")
        added = [pkg for pkg in ("fastembed>=0.4", "numpy>=1.26") if pkg.split(">=")[0] not in req_text]
        if added:
            req_path.write_text(req_text.rstrip("\n") + "\n" + "\n".join(added) + "\n", encoding="utf-8", newline="\n")
            print(f"PATCHED backend/requirements.txt (added {', '.join(added)})")
        else:
            print("SKIP    backend/requirements.txt (already patched)")

    env_path = ROOT / ".env.example"
    if env_path.exists():
        env_text = env_path.read_text(encoding="utf-8")
        if "VOICE_API_SECRET" not in env_text:
            env_path.write_text(
                env_text.rstrip("\n")
                + "\n\n# Voice helpdesk\n"
                "# Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\"\n"
                "VOICE_API_SECRET=change_me\n"
                "# Optional: a faster model for live calls (empty = same as LLM_MODEL)\n"
                "VOICE_LLM_MODEL=\n",
                encoding="utf-8",
                newline="\n",
            )
            print("PATCHED .env.example")
        else:
            print("SKIP    .env.example (already patched)")

    print("\nDone! Next: add VOICE_API_SECRET to your real .env, then pip install -r backend/requirements.txt")


if __name__ == "__main__":
    main()