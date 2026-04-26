from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..models.note import NoteStatus


class SOAPDraft(BaseModel):
    """The structured payload returned by the LLM."""

    subjective: str = ""
    objective: str = ""
    assessment: str = ""
    plan: str = ""
    chief_complaint: str | None = None
    icd10_codes: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)


class NoteUpdate(BaseModel):
    subjective: str | None = None
    objective: str | None = None
    assessment: str | None = None
    plan: str | None = None
    chief_complaint: str | None = None


class SignNoteIn(BaseModel):
    signed_by: str = Field(min_length=2, max_length=120)


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    visit_id: str
    subjective: str
    objective: str
    assessment: str
    plan: str
    chief_complaint: str | None
    icd10_codes: str | None
    medications: str | None
    status: NoteStatus
    signed_by: str | None
    signed_at: datetime | None
    created_at: datetime
    updated_at: datetime
