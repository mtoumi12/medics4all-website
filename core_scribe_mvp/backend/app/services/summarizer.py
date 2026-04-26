"""Transcript -> structured SOAP note summarizer.

Strategy:
  1. Provider-abstracted: ``openai`` (cloud) | ``ollama`` (local) | ``mock``.
  2. Returns a strictly-typed ``SOAPDraft`` — never raw markdown.
  3. Uses JSON-mode response_format when available; falls back to a permissive
     extractor for older / smaller models that occasionally wrap JSON in prose.
  4. Light constraint: medications must come from the spoken transcript, not
     invented. (Real RAG-grounded version comes in v1.5.)
"""
from __future__ import annotations

import json
import logging
import re

from ..config import get_settings, using_mock_pipeline
from ..schemas.note import SOAPDraft

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a licensed medical scribe assistant. Convert the supplied
clinician-patient encounter transcript into a structured SOAP note.

Strict rules:
- Output ONLY a JSON object matching this schema (no prose, no markdown, no code fences):
  {
    "chief_complaint": string,
    "subjective": string,         // patient-reported symptoms, history, ROS
    "objective": string,          // exam findings, vitals spoken in the visit
    "assessment": string,         // clinical impression / differential
    "plan": string,               // workup, prescriptions, follow-up, patient education
    "icd10_codes": [string],      // a SHORT-list (1-4) of plausible ICD-10 codes
    "medications": [string]       // drugs explicitly mentioned (name + dose if spoken)
  }
- Never invent labs, vitals, medications, or doses that were not spoken.
- Use clinical brevity (bullet phrases, not full sentences) for Objective and Plan.
- If a section has no information, return an empty string (not null).
- Do not include any disclaimer, signature block, or commentary.
"""


# ---------------------------------------------------------------------------
# Robust JSON extraction (helps with smaller local models that wander)
# ---------------------------------------------------------------------------
_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")


def _coerce_json(content: str) -> dict:
    content = content.strip()
    # 1) Direct parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 2) Strip markdown code fences if present
    fenced = re.match(r"^```(?:json)?\s*([\s\S]+?)\s*```$", content, flags=re.IGNORECASE)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass

    # 3) First-balanced-{...} extraction
    match = _JSON_BLOCK.search(content)
    if match:
        candidate = match.group(0)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract JSON from model output: {content[:300]!r}")


# ---------------------------------------------------------------------------
# OpenAI (cloud) and Ollama (local) — both speak the OpenAI API protocol
# ---------------------------------------------------------------------------
def _summarize_via_openai_compat(
    transcript: str,
    chief_complaint_hint: str | None,
    *,
    api_key: str,
    base_url: str | None,
    model: str,
    use_json_mode: bool,
) -> SOAPDraft:
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError("openai package is not installed; run `pip install openai`.") from e

    client = OpenAI(api_key=api_key, base_url=base_url)

    user_msg = f"TRANSCRIPT:\n\n{transcript.strip()}"
    if chief_complaint_hint:
        user_msg = (
            f"PRELIMINARY CHIEF COMPLAINT (clinician-supplied): {chief_complaint_hint}\n\n"
            + user_msg
        )

    kwargs: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.2,
    }
    if use_json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content or "{}"
    try:
        data = _coerce_json(content)
    except ValueError as e:
        logger.exception("LLM returned unparseable output: %s", content[:500])
        raise RuntimeError(f"LLM returned unparseable output: {e}") from e
    return SOAPDraft(**data)


def _summarize_openai(transcript: str, hint: str | None) -> SOAPDraft:
    s = get_settings()
    return _summarize_via_openai_compat(
        transcript, hint,
        api_key=s.openai_api_key,
        base_url=s.openai_base_url,
        model=s.llm_model,
        use_json_mode=True,
    )


def _summarize_ollama(transcript: str, hint: str | None) -> SOAPDraft:
    """Use Ollama via its OpenAI-compatible endpoint at /v1.

    Ollama supports JSON mode for most recent models, but smaller models can
    still occasionally wander; the ``_coerce_json`` extractor smooths over that.
    The dummy api_key is required by the OpenAI client but not validated.
    """
    s = get_settings()
    return _summarize_via_openai_compat(
        transcript, hint,
        api_key="ollama-local-noop",
        base_url=s.ollama_base_url,
        model=s.ollama_model,
        use_json_mode=True,
    )


# ---------------------------------------------------------------------------
# Mock
# ---------------------------------------------------------------------------
def _summarize_mock(transcript: str, hint: str | None) -> SOAPDraft:
    logger.warning("[LLM] mock pipeline active — returning canned SOAP draft")
    return SOAPDraft(
        chief_complaint=hint or "Persistent dry cough x10 days with mild dyspnea on exertion.",
        subjective=(
            "10-day history of dry cough, worse at night. Low-grade fever (~38°C) on days 1-3, "
            "now resolved. Mild dyspnea on exertion (climbing stairs). No chest pain. "
            "Self-medicating with paracetamol 500 mg BID. Past medical history of childhood asthma, "
            "no inhaler use for ~15 years. Sick contact: partner had similar symptoms 2 weeks ago, "
            "now resolved. No recent travel."
        ),
        objective=(
            "Vitals: BP 124/78, HR 88, SpO2 96% RA, Temp 37.4°C.\n"
            "Resp: mild bilateral expiratory wheeze, no focal consolidation, no accessory muscle use.\n"
            "General: alert, well-appearing, no acute distress."
        ),
        assessment=(
            "1. Post-viral bronchitis with reactive airway component, likely viral in origin.\n"
            "2. Childhood asthma — possible mild reactivation given wheeze on exam.\n"
            "Pneumonia not yet excluded; imaging recommended."
        ),
        plan=(
            "• Chest X-ray PA/lateral to rule out pneumonia or other consolidation.\n"
            "• Albuterol HFA 90 mcg, 2 puffs q4-6h PRN wheeze x 7 days.\n"
            "• Dextromethorphan 30 mg PO q6-8h PRN cough.\n"
            "• Continue paracetamol PRN; counsel on hydration and rest.\n"
            "• Return precautions: high fever, hemoptysis, worsening dyspnea, chest pain.\n"
            "• Follow-up in 7-10 days; sooner if symptoms worsen."
        ),
        icd10_codes=["J20.9", "J45.20", "R05.9"],
        medications=[
            "Albuterol HFA 90 mcg, 2 puffs q4-6h PRN x 7 days",
            "Dextromethorphan 30 mg PO q6-8h PRN cough",
            "Paracetamol 500 mg PO BID PRN (already taking)",
        ],
    )


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------
def summarize_to_soap(transcript: str, chief_complaint_hint: str | None = None) -> SOAPDraft:
    if using_mock_pipeline():
        return _summarize_mock(transcript, chief_complaint_hint)

    s = get_settings()
    if s.llm_provider == "openai":
        return _summarize_openai(transcript, chief_complaint_hint)
    if s.llm_provider == "ollama":
        return _summarize_ollama(transcript, chief_complaint_hint)

    raise NotImplementedError(f"LLM provider not implemented: {s.llm_provider}")
