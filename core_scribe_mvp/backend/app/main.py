"""Medics4ALL Core Scribe — FastAPI application factory."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .api import api_router
from .config import active_profile, get_settings
from .db import init_db


def _configure_logging(debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    _configure_logging(settings.debug)
    init_db()
    log = logging.getLogger("medics4all")
    log.info("Medics4ALL Core Scribe v%s starting", __version__)
    profile = active_profile()
    log.info(
        "Active profile: ASR=%s (ready=%s) · LLM=%s (ready=%s) · mock=%s",
        profile["asr_provider"], profile["asr_ready"],
        profile["llm_provider"], profile["llm_ready"],
        profile["mock_pipeline"],
    )
    yield
    log.info("Medics4ALL Core Scribe shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Tier 1 — Core English AI Medical Scribe. "
            "Captures audio, transcribes with Whisper, generates a SOAP note via GPT-4o, "
            "and provides edit/sign/export endpoints for clinician review."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/api/v1/health", tags=["meta"])
    def health() -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "version": __version__,
                **active_profile(),
            }
        )

    # ----- Serve the static frontend (zero build step) -----
    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
    if frontend_dir.exists():
        app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

        @app.get("/", response_class=HTMLResponse, tags=["meta"])
        def index() -> HTMLResponse:
            html = (frontend_dir / "index.html").read_text(encoding="utf-8")
            return HTMLResponse(html)

    return app


app = create_app()
