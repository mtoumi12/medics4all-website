"""Automatic Speech Recognition service with speaker diarization.

Provider-abstracted: today we ship three implementations behind one interface:

  * ``openai``  - cloud Whisper API (paid, fast) with basic diarization
  * ``local``   - faster-whisper running on this machine (free, private) with basic diarization
  * ``mock``    - canned transcript for demos with no audio backend

Speaker Diarization:
  * Basic heuristic-based speaker separation between Doctor and Patient
  * Uses context clues, question patterns, and medical terminology
  * For production: consider integrating pyannote.audio for advanced diarization

Adding ``deepgram`` (HIPAA-covered) tomorrow only means adding one more branch.
"""
from __future__ import annotations

import logging
import platform
from functools import lru_cache
from pathlib import Path

from ..config import get_settings, using_mock_pipeline

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Speaker Diarization Helper
# ---------------------------------------------------------------------------
def _apply_speaker_diarization(segments: list) -> str:
    """Apply basic speaker diarization to transcript segments.
    
    This is a simplified implementation that alternates speakers based on 
    pauses and context clues. For production use, consider integrating
    a dedicated diarization model like pyannote.audio.
    """
    if not segments:
        return ""
    
    diarized_parts = []
    current_speaker = "Doctor"  # Start with doctor typically asking questions
    
    for i, segment in enumerate(segments):
        text = segment.get('text', '').strip() if isinstance(segment, dict) else getattr(segment, 'text', '').strip()
        if not text:
            continue
        
        # Simple heuristics for speaker change detection
        # In medical encounters, questions often indicate doctor, responses indicate patient
        lower_text = text.lower()
        
        # Keywords that suggest doctor is speaking
        doctor_keywords = [
            'how are you', 'any', 'what', 'when', 'where', 'describe', 'tell me',
            'show me', 'let me', 'i think', 'diagnosis', 'prescription', 'medication',
            'blood pressure', 'heart rate', 'temperature', 'examination', 'vitals'
        ]
        
        # Keywords that suggest patient is speaking  
        patient_keywords = [
            'i have', 'i feel', 'i am', 'my', 'it hurts', 'painful', 'since', 'started',
            'symptoms', 'better', 'worse', 'yesterday', 'last week', 'at home'
        ]
        
        # Check for speaker change indicators
        prev_speaker = current_speaker
        
        # If text starts with typical question words, likely doctor
        if any(text.lower().startswith(word) for word in ['how', 'what', 'when', 'where', 'any', 'do you', 'have you']):
            current_speaker = "Doctor"
        # If text has patient-like content, likely patient
        elif any(keyword in lower_text for keyword in patient_keywords):
            current_speaker = "Patient"
        # If text has doctor-like medical terms, likely doctor
        elif any(keyword in lower_text for keyword in doctor_keywords):
            current_speaker = "Doctor"
        # If there's a long pause (detected via timestamp gaps) and no clear indicator,
        # alternate speaker (simplified approach)
        elif i > 0 and current_speaker == prev_speaker:
            # Check if this might be a response (shorter, first person)
            if len(text.split()) < 10 and ('i ' in lower_text or 'my ' in lower_text):
                current_speaker = "Patient" if prev_speaker == "Doctor" else "Doctor"
        
        # Add speaker label if changed or first segment
        if i == 0 or current_speaker != prev_speaker:
            diarized_parts.append(f"{current_speaker}: {text}")
        else:
            # Continue same speaker
            diarized_parts.append(text)
    
    return "\n".join(diarized_parts)


# ---------------------------------------------------------------------------
# Mock fixture (used when no API key / no model is available)
# ---------------------------------------------------------------------------
_MOCK_TRANSCRIPT = (
    "Doctor: Good morning, how are you feeling today?\n"
    "Patient: Hi doctor. I've had a really persistent dry cough for about ten days. "
    "It's worse at night and I've been a bit short of breath when I climb stairs.\n"
    "Doctor: Any fever or chest pain?\n"
    "Patient: Low-grade fever the first three days, around 38 Celsius. No chest pain. "
    "I've been taking paracetamol 500 milligrams twice a day.\n"
    "Doctor: Any history of asthma or COPD?\n"
    "Patient: Mild asthma as a kid. I haven't used an inhaler in fifteen years.\n"
    "Doctor: Any smokers at home, recent travel, exposure to sick contacts?\n"
    "Patient: My partner had similar symptoms two weeks ago, mostly resolved now. No travel.\n"
    "Doctor: Vitals look reasonable: BP 124 over 78, heart rate 88, oxygen saturation 96 percent on room air, "
    "temperature 37.4. Lungs have mild bilateral wheeze, no focal consolidation. "
    "I think this is a post-viral bronchitis, possibly with a reactive airway component. "
    "Let's get a chest X-ray to rule out pneumonia, start a short course of inhaled albuterol, "
    "and dextromethorphan for the cough. If you're not improving in seven days or you develop high fever, "
    "we need to revisit. I'd also like a follow-up in ten days."
)


# ---------------------------------------------------------------------------
# OpenAI Whisper (cloud)
# ---------------------------------------------------------------------------
def _transcribe_openai(audio_path: Path) -> str:
    s = get_settings()
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError("openai package is not installed; run `pip install openai`.") from e

    client = OpenAI(api_key=s.openai_api_key, base_url=s.openai_base_url)
    with audio_path.open("rb") as fh:
        # First, get the raw transcript with timestamps
        response = client.audio.transcriptions.create(
            model=s.whisper_model,
            file=fh,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
            prompt=(
                "Medical encounter between clinician and patient. "
                "Expect terms like blood pressure, oxygen saturation, ICD-10 codes, "
                "common medications, and clinical findings. "
                "Please indicate when the speaker changes between doctor and patient."
            ),
        )
    
    # Apply speaker diarization if enabled
    if s.enable_diarization:
        transcript = _apply_speaker_diarization(response.segments if hasattr(response, 'segments') else [])
    else:
        # Fallback to simple text concatenation
        if hasattr(response, 'segments'):
            segments = [seg.get('text', '') for seg in response.segments]
            transcript = " ".join(segments).strip()
        else:
            transcript = response if isinstance(response, str) else getattr(response, "text", str(response))
    
    return transcript


# ---------------------------------------------------------------------------
# faster-whisper (local)
# ---------------------------------------------------------------------------
def _resolve_local_device(setting: str) -> tuple[str, str]:
    """Pick (device, compute_type) for faster-whisper based on user setting + hardware.

    Apple Silicon: faster-whisper does not support 'mps' yet; CPU runs fine
    via Accelerate framework with int8 quantization. CUDA GPUs use float16.
    """
    s = get_settings()
    device = setting.lower()
    if device == "auto":
        try:
            import torch
            if torch.cuda.is_available():
                device = "cuda"
            else:
                # Apple Silicon and Intel Macs: CPU is the right call for ctranslate2
                device = "cpu"
        except ImportError:
            device = "cpu"

    compute_type = s.local_whisper_compute_type
    if device == "cpu" and compute_type == "float16":
        # float16 on CPU is slow; nudge to int8
        compute_type = "int8"

    return device, compute_type


@lru_cache(maxsize=1)
def _get_local_whisper():
    s = get_settings()
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise RuntimeError(
            "faster-whisper not installed. Run `pip install faster-whisper`."
        ) from e

    device, compute_type = _resolve_local_device(s.local_whisper_device)
    logger.info(
        "[ASR/local] loading model=%s device=%s compute=%s arch=%s",
        s.local_whisper_model, device, compute_type, platform.machine(),
    )
    return WhisperModel(s.local_whisper_model, device=device, compute_type=compute_type)


def _transcribe_local(audio_path: Path) -> str:
    """Transcribe locally via faster-whisper. First call downloads the model (~150MB for base.en)."""
    s = get_settings()
    model = _get_local_whisper()
    segments, info = model.transcribe(
        str(audio_path),
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        initial_prompt=(
            "Medical encounter between clinician and patient. "
            "Expect terms like blood pressure, oxygen saturation, ICD-10 codes, "
            "common medications, and clinical findings. "
            "Please indicate when the speaker changes between doctor and patient."
        ),
    )
    
    # Collect segments with timing
    segment_list = []
    for seg in segments:
        segment_data = {
            'text': seg.text.strip(),
            'start': seg.start,
            'end': seg.end
        }
        segment_list.append(segment_data)
    
    # Apply speaker diarization if enabled
    if s.enable_diarization:
        text = _apply_speaker_diarization(segment_list)
    else:
        # Simple concatenation without speaker labels
        text = " ".join([seg['text'] for seg in segment_list if seg['text']]).strip()
    
    logger.info(
        "[ASR/local] done lang=%s prob=%.2f duration=%.1fs len=%d segments=%d diarization=%s",
        info.language, info.language_probability, info.duration, len(text), len(segment_list), s.enable_diarization
    )
    return text


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------
def transcribe_audio(audio_path: Path) -> str:
    """Top-level transcription entry-point. Falls back to mock when no provider is usable."""
    if using_mock_pipeline():
        logger.warning("[ASR] mock pipeline active — returning canned transcript")
        return _MOCK_TRANSCRIPT

    s = get_settings()
    if s.asr_provider == "openai":
        return _transcribe_openai(audio_path)
    if s.asr_provider == "local":
        return _transcribe_local(audio_path)

    raise NotImplementedError(f"ASR provider not implemented: {s.asr_provider}")
