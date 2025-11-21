"""
Voice infrastructure package.

This namespace groups helpers for local speech transcription using
OpenAI Whisper models. The transcription runs entirely on-device,
matching the implementation pattern from StreamlitaudioTest.
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

