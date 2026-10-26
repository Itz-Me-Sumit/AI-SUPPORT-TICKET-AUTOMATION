import hmac
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
