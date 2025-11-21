"""
Local Whisper transcription service.

This module provides local speech-to-text transcription using OpenAI Whisper models.
It replaces the external HTTP API with on-device processing, matching the
implementation pattern from StreamlitaudioTest/streamlit_app/app.py.

The service uses Streamlit's resource cache to load Whisper models once per session,
reducing memory overhead and startup time for subsequent transcriptions.

Models are first checked in the project's models/whisper/ directory. If found,
they are used directly without downloading. Otherwise, Whisper will download
the model to the default cache location.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

import streamlit as st

try:
    import whisper

    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    whisper = None


class WhisperServiceError(RuntimeError):
    """Raised when Whisper transcription fails."""


def _get_project_root() -> Path:
    """
    Find the project root directory by looking for app.py or requirements.txt.

    Returns:
        Path to the project root directory.
    """
    current = Path(__file__).resolve()
    
    # Look for project root markers (app.py or requirements.txt)
    for _ in range(6):  # Max 6 levels up
        if (current / "app.py").exists() or (current / "requirements.txt").exists():
            # Verify it has the infrastructure package
            if (current / "infrastructure").exists():
                return current
        current = current.parent
    
    # Fallback: use directory containing this file, go up to project root
    return Path(__file__).resolve().parent.parent.parent


def _get_local_models_dir() -> Path:
    """
    Get the path to the local Whisper models directory.

    Returns:
        Path to models/whisper/ directory in the project root.
    """
    project_root = _get_project_root()
    return project_root / "models" / "whisper"


def ensure_ffmpeg_available() -> str:
    """
    Verify that FFmpeg is installed and reachable via PATH.

    Returns:
        Absolute path to the FFmpeg executable.

    Raises:
        WhisperServiceError: If FFmpeg cannot be located.
    """
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise WhisperServiceError(
            "FFmpeg executable not found. Install FFmpeg and ensure it is on PATH."
        )
    return ffmpeg_path


@st.cache_resource(show_spinner=False)
def _load_whisper_model(model_name: str):
    """
    Load a Whisper model using Streamlit's resource cache.

    This function first checks for a local model file in models/whisper/
    directory. If found, it uses that model directly. Otherwise, it falls
    back to Whisper's default behavior (downloads to cache).

    Models are loaded once per session, then reused for subsequent
    transcriptions. This significantly reduces memory usage and startup time.

    Args:
        model_name: Name of the Whisper model (tiny, base, small, medium, large-v2).

    Returns:
        Loaded Whisper model instance.

    Raises:
        WhisperServiceError: If Whisper is not installed or model loading fails.
    """
    if not WHISPER_AVAILABLE:
        raise WhisperServiceError(
            "Whisper is not installed. Add 'openai-whisper>=20231117' to requirements.txt."
        )

    try:
        # Check for local model in project directory
        local_models_dir = _get_local_models_dir()
        local_model_path = local_models_dir / f"{model_name}.pt"
        
        # Use local model if it exists, otherwise let Whisper download
        if local_model_path.exists():
            # Load from local directory
            return whisper.load_model(model_name, download_root=str(local_models_dir))
        else:
            # Fall back to default behavior (downloads to ~/.cache/whisper/)
            return whisper.load_model(model_name)
            
    except Exception as exc:
        raise WhisperServiceError(
            f"Failed to load Whisper model '{model_name}': {exc}"
        ) from exc


def transcribe_audio_file(
    audio_file_path: str,
    model_name: str = "base",
    language: Optional[str] = None,
    temperature: float = 0.1,
) -> str:
    """
    Transcribe an audio file using a local Whisper model.

    This function processes audio files locally without requiring
    an external API. It uses FFmpeg (via Whisper) to handle various
    audio formats and sample rates.

    Args:
        audio_file_path: Path to the audio file to transcribe.
        model_name: Whisper model to use (default: "base").
        language: Optional ISO-639-1 language code (e.g., "en", "zh").
                  If None, Whisper will auto-detect the language.
        temperature: Sampling temperature between 0 and 1 (default: 0.1).

    Returns:
        Transcribed text as a string.

    Raises:
        WhisperServiceError: If transcription fails for any reason.
    """
    if not os.path.exists(audio_file_path):
        raise WhisperServiceError(f"Audio file not found: {audio_file_path}")

    try:
        # Ensure FFmpeg is available (Whisper requires it)
        ensure_ffmpeg_available()

        # Load the model (cached per session)
        model = _load_whisper_model(model_name)

        # Configure transcription options
        transcription_options = {
            "temperature": temperature,
            "fp16": False,  # Improves compatibility on CPUs without CUDA
        }
        if language:
            transcription_options["language"] = language

        # Perform transcription
        result = model.transcribe(audio_file_path, **transcription_options)
        transcribed_text = result.get("text", "").strip()

        if not transcribed_text:
            raise WhisperServiceError(
                "Transcription returned empty result. The audio might be silent or unclear."
            )

        return transcribed_text

    except WhisperServiceError:
        raise
    except Exception as exc:
        raise WhisperServiceError(f"Transcription failed: {str(exc)}") from exc

