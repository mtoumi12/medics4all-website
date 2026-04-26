"""Visit = a single doctor-patient encounter."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Enum, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


class VisitStatus(str, enum.Enum):
    CREATED = "created"
    UPLOADING = "uploading"
    TRANSCRIBING = "transcribing"
    SUMMARIZING = "summarizing"
    READY = "ready"
    ERROR = "error"


def _new_id() -> str:
    return uuid.uuid4().hex


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    clinician_name: Mapped[str] = mapped_column(String(120), default="Dr. Demo")
    patient_label: Mapped[str] = mapped_column(String(120), default="Patient")
    chief_complaint: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    audio_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    audio_duration_sec: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[VisitStatus] = mapped_column(
        Enum(VisitStatus), default=VisitStatus.CREATED, index=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    note: Mapped[Optional["Note"]] = relationship(
        "Note", back_populates="visit", uselist=False, cascade="all, delete-orphan"
    )
