"""
Audio processing helpers for voice recordings.

These functions are used to shrink raw recordings before they are
uploaded to the transcription API. We rely on FFmpeg (must be
installed on the host) to downsample the audio to a 16kHz mono MP3
at 64kbps, matching the reference implementation in
`StreamlitaudioTest/streamlit_app/app.py`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Literal

AudioFormat = Literal["mp3", "wav"]


class AudioCompressionError(RuntimeError):
    """Raised when FFmpeg fails to compress a recording."""


def ensure_ffmpeg_available() -> str:
    """
    Verify that FFmpeg is installed and reachable via PATH.

    Returns:
        Absolute path to the FFmpeg executable.

    Raises:
        AudioCompressionError: If FFmpeg cannot be located.
    """
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise AudioCompressionError(
            "FFmpeg executable not found. Install FFmpeg and ensure it is on PATH."
        )
    return ffmpeg_path


def compress_audio(
    audio_bytes: bytes,
    target_sample_rate: int = 16000,
    bitrate: str = "64k",
    output_format: AudioFormat = "mp3",
) -> bytes:
    """
    Compress audio bytes to a smaller format suitable for speech transcription.

    This function handles various input formats (WAV, WebM, OGG) from different
    browsers and devices. Mobile browsers often record in WebM/OGG format, which
    requires special handling.

    Args:
        audio_bytes: Raw audio payload (WAV, WebM, or OGG from audio-recorder-streamlit).
        target_sample_rate: Output sample rate in Hz (default 16k for speech).
        bitrate: Target bitrate (default 64kbps to keep ~28MB/hour).
        output_format: Desired output format (default MP3, falls back to WAV on error).

    Returns:
        Compressed audio data as bytes.

    Raises:
        AudioCompressionError: When FFmpeg fails or temporary files cannot be processed.
    """
    ffmpeg_path = ensure_ffmpeg_available()

    # Use a generic input file extension - FFmpeg will auto-detect the format
    # This handles WAV (desktop), WebM/OGG (mobile) formats
    with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as input_file:
        input_file.write(audio_bytes)
        input_file_path = input_file.name

    output_file_path = None
    try:
        suffix = ".mp3" if output_format == "mp3" else ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as output_file:
            output_file_path = output_file.name

        # Build FFmpeg command with better format handling
        # -f auto: Let FFmpeg auto-detect input format (handles WAV, WebM, OGG)
        # -ignore_unknown: Ignore unknown input streams
        # -fflags +genpts: Generate presentation timestamps (helps with some formats)
        ffmpeg_cmd = [
            ffmpeg_path,
            "-f", "auto",  # Auto-detect input format
            "-ignore_unknown",  # Ignore unknown streams
            "-fflags", "+genpts",  # Generate timestamps for better compatibility
            "-i", input_file_path,
            "-ar", str(target_sample_rate),  # Sample rate
            "-ac", "1",  # Mono channel
            "-b:a", bitrate,  # Audio bitrate
            "-y",  # Overwrite output
            output_file_path,
        ]

        try:
            result = subprocess.run(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=30,  # 30 second timeout
            )
        except subprocess.TimeoutExpired:
            raise AudioCompressionError("FFmpeg compression timed out after 30 seconds")
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else ""
            
            # If MP3 compression fails, try WAV as fallback
            if output_format == "mp3":
                try:
                    # Retry with WAV format (more compatible)
                    return compress_audio(
                        audio_bytes,
                        target_sample_rate=target_sample_rate,
                        bitrate=bitrate,
                        output_format="wav",
                    )
                except AudioCompressionError:
                    # If WAV also fails, raise the original MP3 error
                    pass
            
            raise AudioCompressionError(f"FFmpeg compression failed: {stderr}") from exc

        try:
            with open(output_file_path, "rb") as handle:
                compressed_data = handle.read()
            
            # Verify output file is not empty
            if len(compressed_data) == 0:
                raise AudioCompressionError("FFmpeg produced empty output file")
            
            return compressed_data
        except OSError as exc:
            raise AudioCompressionError(
                "Failed to read compressed audio output."
            ) from exc
    finally:
        for path in (input_file_path, output_file_path):
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    # Ignore cleanup errors to avoid masking the original error.
                    pass

