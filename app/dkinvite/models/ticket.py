import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dkinvite.extensions import db


class TicketStatus(str, enum.Enum):
    active = "active"
    used = "used"
    cancelled = "cancelled"
    blocked = "blocked"


class Ticket(db.Model):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    seat: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        SQLEnum(TicketStatus, name="ticket_statuses", native_enum=False, validate_strings=True),
        default=TicketStatus.active,
        nullable=False,
        index=True,
    )
    qr_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    event = relationship("Event", back_populates="tickets")
    audit_logs = relationship("AuditLog", back_populates="ticket")

    __table_args__ = (
        UniqueConstraint("event_id", "seat", name="uix_event_seat"),
        Index("ix_tickets_event_status", "event_id", "status"),
    )
