from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from ..models.visit import VisitStatus


class VisitCreate(BaseModel):
    clinician_name: str = Field(default="Dr. Demo", max_length=120)
    patient_label: str = Field(default="Patient", max_length=120)
    chief_complaint: Optional[str] = Field(default=None, max_length=500)


class VisitStatusOut(BaseModel):
    id: str
    status: VisitStatus
    error_message: Optional[str] = None
    has_note: bool = False


class VisitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    clinician_name: str
    patient_label: str
    chief_complaint: Optional[str]
    status: VisitStatus
    error_message: Optional[str]
    audio_duration_sec: Optional[float]
    transcript: Optional[str]
    created_at: datetime
    updated_at: datetime
