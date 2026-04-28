"""Centralized application configuration loaded from environment variables.

Provider selection
==================
The MVP supports three deployment profiles, configured via env vars:

  * ``cloud``  -> OpenAI Whisper + OpenAI GPT-4o (paid, fast, needs API key)
  * ``local``  -> faster-whisper + Ollama (free, private, runs on your laptop)
  * ``hybrid`` -> e.g. local Whisper + cloud LLM (mixes privacy with quality)

Two independent knobs (``ASR_PROVIDER`` and ``LLM_PROVIDER``) make the
configuration completely flexible — see ``.env.example`` for ready-made presets.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings — backed by ``.env`` at the project root."""

    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_name: str = "Medics4ALL Core Scribe"
    debug: bool = Field(default=True)
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000"
    )

    # --- Storage ---
    # In Docker, set MEDICS4ALL_DATA=/data and mount a named volume there so SQLite
    # and upload audio survive container restarts. Otherwise paths live under the
    # project root (../.. from this file).
    data_dir: Optional[Path] = Field(
        default=None,
        validation_alias=AliasChoices("MEDICS4ALL_DATA", "DATA_DIR"),
    )
    database_url: str = Field(default=f"sqlite:///{ROOT / 'medics4all.db'}")
    audio_storage_dir: Path = Field(default=ROOT / "storage" / "audio")

    # --- ASR provider: openai | local | mock ---
    asr_provider: str = Field(default="openai")
    # Enable speaker diarization (Doctor/Patient separation)
    enable_diarization: bool = Field(default=True)

    # OpenAI Whisper (cloud)
    openai_api_key: str = Field(default="")
    openai_base_url: Optional[str] = Field(default=None)  # set for Azure / proxies
    whisper_model: str = Field(default="whisper-1")

    # Local Whisper (faster-whisper / CTranslate2)
    # tiny | base | small | medium | large-v3 (and -en variants for English-only)
    local_whisper_model: str = Field(default="base.en")
    # auto | cpu | cuda | mps  (mps = Apple Silicon)
    local_whisper_device: str = Field(default="auto")
    # int8 = lowest memory; float16 = better quality on GPU
    local_whisper_compute_type: str = Field(default="int8")

    # Deepgram (planned, BAA-covered)
    deepgram_api_key: str = Field(default="")

    # --- LLM provider: openai | ollama | mock ---
    llm_provider: str = Field(default="openai")
    llm_model: str = Field(default="gpt-4o-mini")

    # Ollama (local LLM)
    ollama_base_url: str = Field(default="http://localhost:11434/v1")
    ollama_model: str = Field(default="llama3.1:8b")

    # --- Security (placeholder — wire real auth before any pilot) ---
    api_key_header: str = Field(default="X-API-Key")
    dev_api_key: str = Field(default="dev-medics4all-changeme")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _with_data_dir(self) -> "Settings":
        if self.data_dir is None:
            return self
        b = self.data_dir.resolve()
        return self.model_copy(
            update={
                "database_url": f"sqlite:///{b / 'medics4all.db'}",
                "audio_storage_dir": b / "storage" / "audio",
            }
        )

    # ------- runtime checks -------

    def asr_ready(self) -> bool:
        """True if the configured ASR provider is usable right now.

        For ``local`` we use ``find_spec`` rather than ``import`` so the heavy
        ctranslate2 OpenMP runtime is not loaded just to answer /health.
        """
        if self.asr_provider == "openai":
            return bool(self.openai_api_key)
        if self.asr_provider == "local":
            from importlib.util import find_spec
            return find_spec("faster_whisper") is not None
        return self.asr_provider == "mock"

    def llm_ready(self) -> bool:
        if self.llm_provider == "openai":
            return bool(self.openai_api_key)
        if self.llm_provider == "ollama":
            return True  # availability check happens in summarizer
        return self.llm_provider == "mock"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    s = Settings()
    s.audio_storage_dir.mkdir(parents=True, exist_ok=True)
    return s


def using_mock_pipeline() -> bool:
    """True when no usable provider is configured — pipeline returns canned data."""
    s = get_settings()
    return (
        s.asr_provider == "mock"
        or s.llm_provider == "mock"
        or not s.asr_ready()
        or not s.llm_ready()
    )


def active_profile() -> dict:
    """Surface the current provider config — used by /health for debugging."""
    s = get_settings()
    return {
        "asr_provider": s.asr_provider,
        "asr_ready": s.asr_ready(),
        "asr_model": (
            s.whisper_model if s.asr_provider == "openai" else
            s.local_whisper_model if s.asr_provider == "local" else
            s.asr_provider
        ),
        "llm_provider": s.llm_provider,
        "llm_ready": s.llm_ready(),
        "llm_model": (
            s.llm_model if s.llm_provider == "openai" else
            s.ollama_model if s.llm_provider == "ollama" else
            s.llm_provider
        ),
        "mock_pipeline": using_mock_pipeline(),
    }
