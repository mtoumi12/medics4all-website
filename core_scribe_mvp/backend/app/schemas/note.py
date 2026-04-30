from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.note import NoteStatus


class SOAPDraft(BaseModel):
    """The structured payload returned by the LLM.

    Local LLMs sometimes return lists instead of strings for text fields;
    validators automatically convert lists → strings for robustness.
    """

    subjective: str = ""
    objective: str = ""
    assessment: str = ""
    plan: str = ""
    chief_complaint: Optional[str] = None
    icd10_codes: list = Field(default_factory=list)
    medications: list = Field(default_factory=list)

    @field_validator("subjective", "objective", "assessment", "plan", mode="before")
    @classmethod
    def _coerce_text_fields(cls, v):
        """Convert lists to strings for LLMs that return arrays instead of text."""
        if isinstance(v, list):
            if not v:
                return ""
            return "\n".join(
                f"• {item}" if not item.startswith(("•", "-", "*")) else item
                for item in v
            )
        return v or ""

    @field_validator("chief_complaint", mode="before")
    @classmethod
    def _coerce_chief_complaint(cls, v):
        """Convert lists to strings for chief complaint."""
        if isinstance(v, list):
            return " ".join(str(item) for item in v) if v else None
        return v

    @field_validator("icd10_codes", "medications", mode="before")
    @classmethod
    def _coerce_list_fields(cls, v):
        """Convert strings to lists for codes/medications, or ensure lists."""
        if isinstance(v, str):
            if not v.strip():
                return []
            items = [item.strip() for item in v.replace(";", ",").split(",") if item.strip()]
            if not items:
                items = [item.strip() for item in v.split("\n") if item.strip()]
            return items
        elif isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        return v or []


class NoteUpdate(BaseModel):
    subjective: Optional[str] = None
    objective: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    chief_complaint: Optional[str] = None


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
    chief_complaint: Optional[str]
    icd10_codes: Optional[str]
    medications: Optional[str]
    status: NoteStatus
    signed_by: Optional[str]
    signed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
