import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api_schemas import (
    BatchCreate,
    BatchOut,
    StatsOut,
    TicketCreate,
    TicketListOut,
    TicketOut,
)
from app.database import get_db
from app.models import TicketRecord
from app.workflow import process_ticket

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["tickets"])


def _new_ticket_id() -> str:
    return f"TKT-{uuid.uuid4().hex[:8].upper()}"


def _ticket_exists(db: Session, ticket_id: str) -> bool:
    stmt = select(TicketRecord.id).where(TicketRecord.ticket_id == ticket_id)
    return db.execute(stmt).first() is not None


async def _run_and_save(payload: TicketCreate, workflow: dict, db: Session) -> TicketRecord:
    """Process one ticket with the LLM workflow and store the outcome.

    A failed run is stored with status='failed' so it shows up in history.
    """
    ticket_id = payload.ticket_id or _new_ticket_id()

    if _ticket_exists(db, ticket_id):
        raise HTTPException(
            status_code=409,
            detail=f"Ticket ID '{ticket_id}' already exists.",
        )

    record = TicketRecord(
        ticket_id=ticket_id,
        customer_name=payload.customer_name,
        ticket_text=payload.ticket,
    )

    try:
        result = await process_ticket(
            {
                "ticket_id": ticket_id,
                "customer_name": payload.customer_name,
                "ticket": payload.ticket,
            },
            workflow,
        )
        record.status = "completed"
        for key, value in result.items():
            setattr(record, key, value)
    except Exception as exc:  # noqa: BLE001 - we want to record any failure
        logger.exception("Processing failed for %s", ticket_id)
        record.status = "failed"
        record.error = f"{type(exc).__name__}: {exc}"

    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/tickets", response_model=TicketOut, status_code=201)
async def create_ticket(
    payload: TicketCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    record = await _run_and_save(payload, request.app.state.workflow, db)
    if record.status == "failed":
        # Return 502 so the frontend can show a friendly error state
        raise HTTPException(
            status_code=502,
            detail=f"The AI workflow failed: {record.error}",
        )
    return record


@router.post("/tickets/batch", response_model=BatchOut)
async def create_batch(
    payload: BatchCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    workflow = request.app.state.workflow
    items: list[TicketRecord] = []

    # Sequential on purpose: free LLM tiers are rate limited
    for ticket in payload.tickets:
        try:
            items.append(await _run_and_save(ticket, workflow, db))
        except HTTPException as exc:
            # Duplicate IDs in a batch should not stop the other tickets
            logger.warning("Skipped ticket: %s", exc.detail)

    completed = sum(1 for item in items if item.status == "completed")
    return BatchOut(
        total=len(payload.tickets),
        completed=completed,
        failed=len(items) - completed,
        items=items,
    )


@router.get("/tickets", response_model=TicketListOut)
def list_tickets(
    db: Session = Depends(get_db),
    category: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    stmt = select(TicketRecord)

    if category:
        stmt = stmt.where(TicketRecord.category == category)
    if priority:
        stmt = stmt.where(TicketRecord.priority == priority)
    if status:
        stmt = stmt.where(TicketRecord.status == status)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                TicketRecord.ticket_id.ilike(like),
                TicketRecord.customer_name.ilike(like),
                TicketRecord.ticket_text.ilike(like),
            )
        )

    total = db.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar_one()

    items = (
        db.execute(
            stmt.order_by(TicketRecord.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )

    return TicketListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/stats", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)):
    total = db.execute(select(func.count(TicketRecord.id))).scalar_one()

    def count_where(*conditions) -> int:
        return db.execute(
            select(func.count(TicketRecord.id)).where(*conditions)
        ).scalar_one()

    completed = count_where(TicketRecord.status == "completed")
    failed = count_where(TicketRecord.status == "failed")
    human = count_where(TicketRecord.requires_human.is_(True))
    critical = count_where(TicketRecord.priority == "critical")

    avg_ms = db.execute(
        select(func.avg(TicketRecord.processing_ms)).where(
            TicketRecord.status == "completed"
        )
    ).scalar()

    def group_by(column) -> dict[str, int]:
        rows = db.execute(
            select(column, func.count(TicketRecord.id))
            .where(column.is_not(None))
            .group_by(column)
        ).all()
        return {key: count for key, count in rows}

    return StatsOut(
        total=total,
        completed=completed,
        failed=failed,
        human_required=human,
        human_required_pct=round(human / completed * 100, 1) if completed else 0.0,
        critical=critical,
        avg_processing_ms=int(avg_ms or 0),
        by_category=group_by(TicketRecord.category),
        by_priority=group_by(TicketRecord.priority),
        by_resolution=group_by(TicketRecord.resolution_type),
    )


@router.get("/tickets/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)):
    record = db.execute(
        select(TicketRecord).where(TicketRecord.ticket_id == ticket_id)
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Ticket not found.")
    return record


@router.delete("/tickets/{ticket_id}", status_code=204)
def delete_ticket(ticket_id: str, db: Session = Depends(get_db)):
    record = db.execute(
        select(TicketRecord).where(TicketRecord.ticket_id == ticket_id)
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Ticket not found.")
    db.delete(record)
    db.commit()
