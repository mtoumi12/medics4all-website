"""Note = the SOAP-format clinical note generated for a visit."""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


class NoteStatus(str, enum.Enum):
    DRAFT = "draft"
    EDITED = "edited"
    SIGNED = "signed"
    EXPORTED = "exported"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    visit_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("visits.id", ondelete="CASCADE"), unique=True, index=True
    )

    subjective: Mapped[str] = mapped_column(Text, default="")
    objective: Mapped[str] = mapped_column(Text, default="")
    assessment: Mapped[str] = mapped_column(Text, default="")
    plan: Mapped[str] = mapped_column(Text, default="")

    chief_complaint: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    icd10_codes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # CSV
    medications: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # CSV / json string

    status: Mapped[NoteStatus] = mapped_column(Enum(NoteStatus), default=NoteStatus.DRAFT)
    signed_by: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    signed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    visit = relationship("Visit", back_populates="note")
