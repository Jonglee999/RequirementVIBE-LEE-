"""
Voice infrastructure package.

This namespace groups helpers that communicate with external
speech-related services (e.g., transcription APIs). Keeping it
isolated under infrastructure allows presentation components to
stay framework-agnostic while still reusing the same HTTP client.
"""

from .client import (
    MAX_AUDIO_FILE_SIZE_BYTES,
    MAX_AUDIO_FILE_SIZE_MB,
    TranscriptionResponse,
    VoiceTranscriptionError,
    get_default_language,
    get_default_model,
    get_default_temperature,
    get_transcription_api_base_url,
    transcribe_audio_bytes,
)
from .processing import AudioCompressionError, compress_audio, ensure_ffmpeg_available

__all__ = [
    "MAX_AUDIO_FILE_SIZE_BYTES",
    "MAX_AUDIO_FILE_SIZE_MB",
    "TranscriptionResponse",
    "VoiceTranscriptionError",
    "AudioCompressionError",
    "get_default_language",
    "get_default_model",
    "get_default_temperature",
    "get_transcription_api_base_url",
    "transcribe_audio_bytes",
    "compress_audio",
    "ensure_ffmpeg_available",
]

