import hmac
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import settings
from app.api_schemas import TicketCreate
from app.database import SessionLocal
from app.rag import answer_question
from app.routers.tickets import _run_and_save

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


# ---------------------------------------------------------------------------
# Post-call webhook: turn a finished phone call into a ticket
# ---------------------------------------------------------------------------
MAX_TICKET_CHARS = 5000


def _call_ticket_id(execution_id: str) -> str:
    return f"CALL-{execution_id.replace('-', '')[:8].upper()}"


def _has_caller_speech(transcript: str) -> bool:
    """True if the customer said at least one line during the call."""
    return any(line.strip().lower().startswith("user:") for line in transcript.splitlines())


async def _process_call(execution_id: str, transcript: str, workflow: dict) -> None:
    """Run the full ticket pipeline for one finished call (runs in the background)."""
    text = "Phone call transcript (assistant = support agent, user = customer):\n" + transcript
    payload = TicketCreate(
        customer_name="Valued customer",
        ticket=text[:MAX_TICKET_CHARS],
        ticket_id=_call_ticket_id(execution_id),
    )

    db = SessionLocal()
    try:
        record = await _run_and_save(payload, workflow, db)
        if record.status == "completed":
            logger.info("Ticket %s created from call %s", payload.ticket_id, execution_id)
        else:
            logger.warning("Ticket %s was saved as failed: %s", payload.ticket_id, record.error)
    except HTTPException as exc:
        # Most likely a duplicate delivery for a call we already handled
        logger.info("Call %s skipped: %s", execution_id, exc.detail)
    except Exception:  # noqa: BLE001 - never crash the background task silently
        logger.exception("Could not create a ticket for call %s", execution_id)
    finally:
        db.close()


@router.post("/webhook", dependencies=[Depends(verify_secret)])
async def call_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receives call updates from the voice platform. Only finished calls create tickets."""
    try:
        execution = await request.json()
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Body must be valid JSON.")

    if not isinstance(execution, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object.")

    status = str(execution.get("status", ""))
    execution_id = str(execution.get("id", ""))

    # A single call sends several updates; only the final one carries the transcript.
    if status != "completed" or not execution_id:
        return {"ok": True, "ignored": status or "no-status"}

    transcript = execution.get("transcript") or ""
    if not isinstance(transcript, str) or not _has_caller_speech(transcript):
        return {"ok": True, "ignored": "no caller speech"}

    background_tasks.add_task(
        _process_call, execution_id, transcript, request.app.state.workflow
    )
    return {"ok": True, "accepted": _call_ticket_id(execution_id)}
