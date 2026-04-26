"""Visit lifecycle endpoints.

Flow:
  1. POST   /visits                         -> creates a Visit shell, returns id
  2. POST   /visits/{id}/audio              -> uploads recorded audio (multipart)
  3. GET    /visits/{id}/status             -> poll the pipeline state
  4. GET    /visits/{id}                    -> full visit + transcript
  5. GET    /visits                         -> list recent visits
"""
from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models.visit import Visit, VisitStatus
from ..schemas.visit import VisitCreate, VisitOut, VisitStatusOut
from ..services.pipeline import process_visit_async

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/visits", tags=["visits"])


_ALLOWED_AUDIO_SUFFIXES = {".webm", ".wav", ".mp3", ".m4a", ".ogg", ".mp4"}
_MAX_AUDIO_BYTES = 100 * 1024 * 1024  # 100 MB safety cap (~ 90-min visit)


@router.post("", response_model=VisitOut, status_code=status.HTTP_201_CREATED)
def create_visit(payload: VisitCreate, db: Session = Depends(get_db)) -> Visit:
    visit = Visit(
        clinician_name=payload.clinician_name,
        patient_label=payload.patient_label,
        chief_complaint=payload.chief_complaint,
        status=VisitStatus.CREATED,
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return visit


@router.post("/{visit_id}/audio", response_model=VisitStatusOut)
async def upload_audio(
    visit_id: str,
    background: BackgroundTasks,
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> VisitStatusOut:
    settings = get_settings()
    visit = db.get(Visit, visit_id)
    if visit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Visit {visit_id} not found")

    suffix = Path(audio.filename or "").suffix.lower() or ".webm"
    if suffix not in _ALLOWED_AUDIO_SUFFIXES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Unsupported audio format '{suffix}'. Allowed: {sorted(_ALLOWED_AUDIO_SUFFIXES)}",
        )

    file_id = uuid.uuid4().hex
    target = settings.audio_storage_dir / f"{visit_id}_{file_id}{suffix}"

    bytes_written = 0
    with target.open("wb") as out_fh:
        while chunk := await audio.read(1024 * 1024):
            bytes_written += len(chunk)
            if bytes_written > _MAX_AUDIO_BYTES:
                out_fh.close()
                target.unlink(missing_ok=True)
                raise HTTPException(
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    f"Audio exceeds {_MAX_AUDIO_BYTES // (1024 * 1024)} MB cap",
                )
            out_fh.write(chunk)

    visit.audio_path = str(target)
    visit.status = VisitStatus.UPLOADING
    db.add(visit)
    db.commit()
    db.refresh(visit)

    background.add_task(process_visit_async, visit.id)

    logger.info(
        "uploaded audio visit=%s bytes=%s -> %s; pipeline scheduled",
        visit.id,
        bytes_written,
        target.name,
    )

    return VisitStatusOut(
        id=visit.id,
        status=visit.status,
        error_message=visit.error_message,
        has_note=visit.note is not None,
    )


@router.get("/{visit_id}/status", response_model=VisitStatusOut)
def get_visit_status(visit_id: str, db: Session = Depends(get_db)) -> VisitStatusOut:
    visit = db.get(Visit, visit_id)
    if visit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Visit {visit_id} not found")
    return VisitStatusOut(
        id=visit.id,
        status=visit.status,
        error_message=visit.error_message,
        has_note=visit.note is not None,
    )


@router.get("/{visit_id}", response_model=VisitOut)
def get_visit(visit_id: str, db: Session = Depends(get_db)) -> Visit:
    visit = db.get(Visit, visit_id)
    if visit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Visit {visit_id} not found")
    return visit


@router.get("", response_model=list[VisitOut])
def list_visits(limit: int = 25, db: Session = Depends(get_db)) -> list[Visit]:
    limit = max(1, min(limit, 100))
    stmt = select(Visit).order_by(Visit.created_at.desc()).limit(limit)
    return list(db.scalars(stmt))
