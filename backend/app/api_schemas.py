from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TicketCreate(BaseModel):
    """Request body for submitting one ticket."""

    customer_name: str = Field(min_length=1, max_length=120)
    ticket: str = Field(min_length=5, max_length=5000)
    ticket_id: Optional[str] = Field(default=None, max_length=64)

    @field_validator("customer_name", "ticket")
    @classmethod
    def strip_and_check(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty or only spaces.")
        return value

    @field_validator("ticket_id")
    @classmethod
    def clean_ticket_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


class BatchCreate(BaseModel):
    """Request body for submitting many tickets at once."""

    tickets: list[TicketCreate] = Field(min_length=1, max_length=50)


class TicketOut(BaseModel):
    """Ticket as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    ticket_id: str
    customer_name: str
    ticket_text: str
    status: str
    error: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    language: Optional[str] = None
    case_analysis: Optional[dict[str, Any]] = None
    resolution_type: Optional[str] = None
    recommended_action: Optional[str] = None
    requires_human: Optional[bool] = None
    resolution_reason: Optional[str] = None
    response: Optional[str] = None
    processing_ms: Optional[int] = None
    created_at: datetime


class TicketListOut(BaseModel):
    items: list[TicketOut]
    total: int
    page: int
    page_size: int


class BatchOut(BaseModel):
    total: int
    completed: int
    failed: int
    items: list[TicketOut]


class StatsOut(BaseModel):
    total: int
    completed: int
    failed: int
    human_required: int
    human_required_pct: float
    critical: int
    avg_processing_ms: int
    by_category: dict[str, int]
    by_priority: dict[str, int]
    by_resolution: dict[str, int]
