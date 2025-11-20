"""
Voice transcription HTTP client.

This module encapsulates the logic for sending recorded audio to the
external transcription API documented in
`StreamlitaudioTest/api_service/docs/API_USAGE.md`.

Keeping this logic in the infrastructure layer helps us:
- Reuse the same request/validation flow from different UI surfaces
- Swap or reconfigure the transcription backend via environment variables
- Centralize size validation so the UI stays lean
"""

from __future__ import annotations

import io
import mimetypes
import os
from dataclasses import dataclass
from typing import Optional

import requests

# API contract caps uploads at 100MB
MAX_AUDIO_FILE_SIZE_MB = 100
MAX_AUDIO_FILE_SIZE_BYTES = MAX_AUDIO_FILE_SIZE_MB * 1024 * 1024


class VoiceTranscriptionError(RuntimeError):
    """Raised when the transcription service cannot process the request."""


@dataclass
class TranscriptionResponse:
    """Lightweight container for transcription metadata."""

    text: str
    model_used: str
    language: Optional[str]


def _get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Helper to fetch trimmed environment variables with default fallback."""
    value = os.getenv(key)
    if value is None:
        return default
    trimmed = value.strip()
    return trimmed or default


def get_transcription_api_base_url() -> str:
    """
    Return the base URL that hosts the `/api/transcribe` endpoint.

    Defaults to the local FastAPI service if no env var is set.
    """
    base_url = _get_env("VOICE_TRANSCRIBE_API_BASE_URL", "http://192.168.31.200:8000")
    return base_url.rstrip("/")


def get_default_model() -> str:
    """Return the Whisper model name to request."""
    return _get_env("VOICE_TRANSCRIBE_MODEL", "medium") or "medium"


def get_default_language() -> str:
    """
    Return the ISO-639-1 language code hint.

    The API accepts an empty string / None to auto-detect, so we keep the
    default empty.
    """
    return _get_env("VOICE_TRANSCRIBE_LANGUAGE", "") or ""


def get_default_temperature() -> float:
    """Return the sampling temperature to send to the transcription API."""
    raw = _get_env("VOICE_TRANSCRIBE_TEMPERATURE", "0.1")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = 0.0
    return max(0.0, min(1.0, value))


def _guess_mime_type(filename: str) -> str:
    """Guess content type for the multipart request."""
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type is None:
        # Fall back to audio/wav which is the default output format from
        # audio-recorder-streamlit.
        return "audio/wav"
    return mime_type


def _safe_filename(filename: Optional[str]) -> str:
    """Prevent directory traversal and provide a deterministic fallback."""
    if not filename:
        return "recording.wav"
    return os.path.basename(filename)


def transcribe_audio_bytes(
    file_bytes: bytes,
    filename: str,
    *,
    model: Optional[str] = None,
    language: Optional[str] = None,
    temperature: Optional[float] = None,
    timeout: int = 120,
) -> TranscriptionResponse:
    """
    Send audio bytes to the transcription backend and return the parsed text.

    Args:
        file_bytes: Raw audio payload captured from the recorder.
        filename: Suggested filename (only used for metadata/MIME detection).
        model: Optional Whisper model. Defaults to env-configured value.
        language: Optional ISO-639-1 language hint.
        temperature: Optional sampling temperature.
        timeout: HTTP timeout in seconds for the outbound request.
    """
    if not file_bytes:
        raise VoiceTranscriptionError("No audio payload provided for transcription.")

    if len(file_bytes) > MAX_AUDIO_FILE_SIZE_BYTES:
        size_mb = len(file_bytes) / (1024 * 1024)
        raise VoiceTranscriptionError(
            f"Recording is {size_mb:.2f}MB which exceeds the "
            f"{MAX_AUDIO_FILE_SIZE_MB}MB limit enforced by the transcription API."
        )

    base_url = get_transcription_api_base_url()
    url = f"{base_url}/api/transcribe"

    payload_model = model or get_default_model()
    payload_language = language or get_default_language()
    payload_temperature = (
        get_default_temperature() if temperature is None else float(temperature)
    )

    files = {
        "file": (
            _safe_filename(filename),
            io.BytesIO(file_bytes),
            _guess_mime_type(filename),
        )
    }

    data = {
        "model": payload_model,
        "temperature": str(payload_temperature),
    }

    if payload_language:
        data["language"] = payload_language

    try:
        response = requests.post(url, files=files, data=data, timeout=timeout)
    except requests.RequestException as exc:
        raise VoiceTranscriptionError(
            f"Failed to reach transcription service at {url}: {exc}"
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise VoiceTranscriptionError(
            "Transcription service returned a non-JSON response."
        ) from exc

    if response.status_code != 200 or not payload.get("success"):
        error_msg = payload.get("error") if isinstance(payload, dict) else str(payload)
        raise VoiceTranscriptionError(
            f"Transcription request failed ({response.status_code}): {error_msg}"
        )

    return TranscriptionResponse(
        text=payload.get("transcription", ""),
        model_used=payload.get("model_used", payload_model),
        language=payload.get("language", payload_language or None),
    )

