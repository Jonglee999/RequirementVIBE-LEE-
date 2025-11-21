"""
Local voice transcription client.

This module provides local speech-to-text transcription using OpenAI Whisper models.
It replaces the external HTTP API with on-device processing, matching the
implementation pattern from StreamlitaudioTest/streamlit_app/app.py.

The service uses Streamlit's resource cache to load Whisper models once per session,
reducing memory overhead and startup time for subsequent transcriptions.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from typing import Optional

from .whisper_service import (
    WhisperServiceError,
    transcribe_audio_file as _transcribe_audio_file,
)

# File size limit for recordings (100MB)
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
    Return a placeholder URL (not used for local transcription).

    Kept for backward compatibility with existing code that may reference this.
    """
    return "local://whisper"


def get_default_model() -> str:
    """Return the Whisper model name to use."""
    return _get_env("VOICE_TRANSCRIBE_MODEL", "medium") or "medium"


def get_default_language() -> str:
    """
    Return the ISO-639-1 language code hint.

    Empty string means auto-detect (Whisper default).
    """
    return _get_env("VOICE_TRANSCRIBE_LANGUAGE", "") or ""


def get_default_temperature() -> float:
    """Return the sampling temperature for Whisper transcription."""
    raw = _get_env("VOICE_TRANSCRIBE_TEMPERATURE", "0.1")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = 0.1
    return max(0.0, min(1.0, value))


def transcribe_audio_bytes(
    file_bytes: bytes,
    filename: str,
    *,
    model: Optional[str] = None,
    language: Optional[str] = None,
    temperature: Optional[float] = None,
    timeout: Optional[int] = None,  # Not used for local transcription, kept for compatibility
) -> TranscriptionResponse:
    """
    Transcribe audio bytes using local Whisper models.

    This function writes the audio bytes to a temporary file, then uses
    Whisper to transcribe it locally. The temporary file is automatically
    cleaned up after transcription.

    Args:
        file_bytes: Raw audio payload captured from the recorder.
        filename: Suggested filename (used to determine file extension).
        model: Optional Whisper model. Defaults to "medium".
        language: Optional ISO-639-1 language hint (empty string = auto-detect).
        temperature: Optional sampling temperature (default: 0.1).

    Returns:
        TranscriptionResponse containing the transcribed text and metadata.

    Raises:
        VoiceTranscriptionError: If transcription fails for any reason.
    """
    if not file_bytes:
        raise VoiceTranscriptionError("No audio payload provided for transcription.")

    if len(file_bytes) > MAX_AUDIO_FILE_SIZE_BYTES:
        size_mb = len(file_bytes) / (1024 * 1024)
        raise VoiceTranscriptionError(
            f"Recording is {size_mb:.2f}MB which exceeds the "
            f"{MAX_AUDIO_FILE_SIZE_MB}MB limit."
        )

    # Determine file extension from filename
    file_ext = os.path.splitext(filename)[1] if filename else ".wav"
    if not file_ext or file_ext == ".":
        file_ext = ".wav"

    # Use configured defaults
    model_name = model or get_default_model()
    language_hint = language if language is not None else get_default_language()
    temp_value = (
        get_default_temperature() if temperature is None else float(temperature)
    )

    # Write audio bytes to temporary file for Whisper processing
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=file_ext, delete=False
        ) as temp_file:
            temp_file.write(file_bytes)
            temp_file_path = temp_file.name

        # Perform local transcription
        try:
            transcribed_text = _transcribe_audio_file(
                audio_file_path=temp_file_path,
                model_name=model_name,
                language=language_hint if language_hint else None,
                temperature=temp_value,
            )
        except WhisperServiceError as exc:
            raise VoiceTranscriptionError(str(exc)) from exc

        # Return response in the same format as the HTTP API
        return TranscriptionResponse(
            text=transcribed_text,
            model_used=model_name,
            language=language_hint if language_hint else None,
        )

    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except OSError:
                # Ignore cleanup errors
                pass

