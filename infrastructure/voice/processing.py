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

    Args:
        audio_bytes: Raw audio payload (typically WAV from audio-recorder-streamlit).
        target_sample_rate: Output sample rate in Hz (default 16k for speech).
        bitrate: Target bitrate (default 64kbps to keep ~28MB/hour).
        output_format: Desired output format (default MP3).

    Returns:
        Compressed audio data as bytes.

    Raises:
        AudioCompressionError: When FFmpeg fails or temporary files cannot be processed.
    """
    ffmpeg_path = ensure_ffmpeg_available()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as input_file:
        input_file.write(audio_bytes)
        input_file_path = input_file.name

    output_file_path = None
    try:
        suffix = ".mp3" if output_format == "mp3" else ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as output_file:
            output_file_path = output_file.name

        ffmpeg_cmd = [
            ffmpeg_path,
            "-i",
            input_file_path,
            "-ar",
            str(target_sample_rate),
            "-ac",
            "1",
            "-b:a",
            bitrate,
            "-y",
            output_file_path,
        ]

        try:
            subprocess.run(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else ""
            raise AudioCompressionError(f"FFmpeg compression failed: {stderr}") from exc

        try:
            with open(output_file_path, "rb") as handle:
                return handle.read()
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

