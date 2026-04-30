"""End-to-end async pipeline: audio -> transcript -> SOAP note.

Run as a FastAPI BackgroundTask so the API returns immediately and the client
polls /visits/{id}/status until status == READY.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from ..db import session_scope
from ..models.note import Note, NoteStatus
from ..models.visit import Visit, VisitStatus
from .asr import transcribe_audio
from .summarizer import summarize_to_soap

logger = logging.getLogger(__name__)


def _set_status(db: Session, visit: Visit, status: VisitStatus, error: Optional[str] = None) -> None:
    visit.status = status
    visit.error_message = error
    db.add(visit)
    db.commit()


def process_visit_async(visit_id: str) -> None:
    """Run ASR + summarization for a visit. Idempotent on retries."""
    logger.info("[pipeline] starting visit=%s", visit_id)
    with session_scope() as db:
        visit = db.get(Visit, visit_id)
        if visit is None:
            logger.error("[pipeline] visit not found: %s", visit_id)
            return
        if not visit.audio_path:
            _set_status(db, visit, VisitStatus.ERROR, "No audio uploaded")
            return

        # ---- ASR ----
        try:
            _set_status(db, visit, VisitStatus.TRANSCRIBING)
            transcript = transcribe_audio(Path(visit.audio_path))
            visit.transcript = transcript
            db.add(visit)
            db.commit()
            logger.info("[pipeline] transcript ok visit=%s len=%d", visit_id, len(transcript))
        except Exception as e:
            logger.exception("[pipeline] ASR failed visit=%s", visit_id)
            _set_status(db, visit, VisitStatus.ERROR, f"ASR failed: {e}")
            return

        # ---- Summarization ----
        try:
            _set_status(db, visit, VisitStatus.SUMMARIZING)
            draft = summarize_to_soap(visit.transcript, visit.chief_complaint)
        except Exception as e:
            logger.exception("[pipeline] LLM failed visit=%s", visit_id)
            _set_status(db, visit, VisitStatus.ERROR, f"Summarization failed: {e}")
            return

        # ---- Persist note ----
        existing = visit.note
        if existing is None:
            note = Note(visit_id=visit.id)
            db.add(note)
        else:
            note = existing

        note.subjective = draft.subjective
        note.objective = draft.objective
        note.assessment = draft.assessment
        note.plan = draft.plan
        note.chief_complaint = draft.chief_complaint or visit.chief_complaint
        note.icd10_codes = ",".join(draft.icd10_codes) if draft.icd10_codes else None
        note.medications = "\n".join(draft.medications) if draft.medications else None
        note.status = NoteStatus.DRAFT

        visit.status = VisitStatus.READY
        visit.error_message = None
        db.add(visit)
        db.commit()
        logger.info("[pipeline] visit READY id=%s", visit_id)
