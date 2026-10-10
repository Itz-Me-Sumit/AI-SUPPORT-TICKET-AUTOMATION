from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TicketRecord(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(120))
    ticket_text: Mapped[str] = mapped_column(Text)

    # "completed" ya "failed"
    status: Mapped[str] = mapped_column(String(16), default="completed", index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    category: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    priority: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    language: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # case analysis ko JSON dict ki tarah store karte hain (frontend ko cards banane ke liye)
    case_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    resolution_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_human: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    resolution_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)

    processing_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
