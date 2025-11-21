"""
Voice recording and transcription sidebar component.

Responsibilities:
- Render the microphone icon button (audio_recorder) inside the sidebar
- Persist each recording inside a session-scoped temp directory so users
  can download the file while the session stays open
- Send fresh recordings to the external transcription API and surface
  the resulting text inside the chat experience automatically
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from datetime import datetime

import streamlit as st

try:
    from audio_recorder_streamlit import audio_recorder

    AUDIO_RECORDER_AVAILABLE = True
except ModuleNotFoundError:
    AUDIO_RECORDER_AVAILABLE = False

from infrastructure.voice import (
    MAX_AUDIO_FILE_SIZE_BYTES,
    MAX_AUDIO_FILE_SIZE_MB,
    AudioCompressionError,
    VoiceTranscriptionError,
    compress_audio,
    transcribe_audio_bytes,
)

VOICE_MODEL_ID = "base"
VOICE_TEMPERATURE = 0.1
DEFAULT_LANGUAGE_HINT = ""
COMPRESSED_SAMPLE_RATE = 16000
COMPRESSED_BITRATE = "64k"
COMPRESSED_EXTENSION = ".mp3"


def _init_voice_state() -> None:
    """Ensure every state variable we rely on exists."""
    defaults = {
        "voice_temp_dir": None,
        "voice_temp_dir_path": None,
        "voice_recording_bytes": None,
        "voice_recording_filename": None,
        "voice_recording_path": None,
        "voice_last_audio_hash": None,
        "voice_last_transcription": None,
        "voice_last_transcription_model": None,
        "voice_last_transcription_language": None,
        "voice_transcription_error": None,
        "voice_is_transcribing": False,
        "pending_voice_message": None,
        "voice_status": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Lazily create a session-scoped temp directory. The TemporaryDirectory
    # object cleans itself up when the Streamlit session goes away.
    if st.session_state.voice_temp_dir is None:
        temp_dir = tempfile.TemporaryDirectory(prefix="reqvibe_voice_")
        st.session_state.voice_temp_dir = temp_dir
        st.session_state.voice_temp_dir_path = temp_dir.name


def _persist_recording(audio_bytes: bytes, extension: str) -> None:
    """Write the latest recording to disk so the user can download it."""
    previous_path = st.session_state.voice_recording_path
    if previous_path and os.path.exists(previous_path):
        try:
            os.remove(previous_path)
        except OSError:
            pass

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_extension = extension if extension.startswith(".") else f".{extension}"
    filename = f"voice_recording_{timestamp}{safe_extension}"
    temp_dir = st.session_state.voice_temp_dir_path or tempfile.gettempdir()
    file_path = os.path.join(temp_dir, filename)
    with open(file_path, "wb") as handle:
        handle.write(audio_bytes)

    st.session_state.voice_recording_bytes = audio_bytes
    st.session_state.voice_recording_filename = filename
    st.session_state.voice_recording_path = file_path


def _auto_transcribe_current_recording() -> None:
    """Send the most recent recording to the transcription API."""
    audio_bytes = st.session_state.voice_recording_bytes
    filename = st.session_state.voice_recording_filename
    if not audio_bytes or not filename:
        return

    st.session_state.voice_is_transcribing = True
    st.session_state.voice_transcription_error = None
    st.session_state.voice_status = "Transcribing latest recording..."

    try:
        with st.spinner("Transcribing voice input..."):
            result = transcribe_audio_bytes(
                audio_bytes,
                filename,
                model=VOICE_MODEL_ID,
                language=DEFAULT_LANGUAGE_HINT or None,
                temperature=VOICE_TEMPERATURE,
            )
    except VoiceTranscriptionError as exc:
        st.session_state.voice_transcription_error = str(exc)
        st.session_state.voice_status = "Transcription failed"
    else:
        st.session_state.voice_last_transcription = result.text
        st.session_state.voice_last_transcription_model = result.model_used
        st.session_state.voice_last_transcription_language = result.language
        st.session_state.pending_voice_message = result.text.strip() or None
        st.session_state.voice_status = "Transcription ready"
    finally:
        st.session_state.voice_is_transcribing = False


def _handle_new_audio(audio_bytes: bytes) -> None:
    """Validate, persist, and process a newly captured audio clip."""
    if not audio_bytes:
        return

    byte_count = len(audio_bytes)
    if byte_count > MAX_AUDIO_FILE_SIZE_BYTES:
        size_mb = byte_count / (1024 * 1024)
        st.session_state.voice_transcription_error = (
            f"Recording size {size_mb:.2f}MB exceeds the {MAX_AUDIO_FILE_SIZE_MB}MB limit."
        )
        st.session_state.voice_status = "Recording rejected (too large)"
        return

    audio_hash = hashlib.sha1(audio_bytes).hexdigest()
    if audio_hash == st.session_state.voice_last_audio_hash:
        # Ignore duplicates caused by Streamlit reruns after state updates.
        return

    st.session_state.voice_last_audio_hash = audio_hash

    compressed_bytes = audio_bytes
    extension = ".wav"
    compression_successful = False
    
    try:
        with st.spinner("Compressing voice input for faster processing..."):
            compressed_bytes = compress_audio(
                audio_bytes,
                target_sample_rate=COMPRESSED_SAMPLE_RATE,
                bitrate=COMPRESSED_BITRATE,
                output_format="mp3",
            )
            extension = COMPRESSED_EXTENSION
            compression_successful = True
            st.session_state.voice_status = "Recording compressed and captured"
    except AudioCompressionError as exc:
        # If MP3 compression fails, try WAV as fallback (better compatibility)
        try:
            with st.spinner("Compressing to WAV format (better compatibility)..."):
                compressed_bytes = compress_audio(
                    audio_bytes,
                    target_sample_rate=COMPRESSED_SAMPLE_RATE,
                    bitrate=COMPRESSED_BITRATE,
                    output_format="wav",
                )
                extension = ".wav"
                compression_successful = True
                st.session_state.voice_status = "Recording compressed (WAV format)"
        except AudioCompressionError:
            # If both fail, use original audio (Whisper can handle various formats)
            st.session_state.voice_transcription_error = None
            st.session_state.voice_status = (
                "Compression unavailable. Using original audio format."
            )
            # Keep original audio bytes and extension
            extension = ".wav"  # Default extension for audio-recorder-streamlit output

    _persist_recording(compressed_bytes, extension)
    _auto_transcribe_current_recording()


def _render_download_controls() -> None:
    """Provide download/reset options once a recording exists."""
    if not st.session_state.voice_recording_bytes:
        return

    filename = st.session_state.voice_recording_filename or "recording.wav"
    mime_type = "audio/mp3" if filename.endswith(".mp3") else "audio/wav"

    st.download_button(
        "Download last recording",
        data=st.session_state.voice_recording_bytes,
        file_name=filename,
        mime=mime_type,
        use_container_width=True,
        key="voice_download_button",
    )

    if st.button("Discard recording", use_container_width=True, key="voice_discard_button"):
        st.session_state.voice_recording_bytes = None
        st.session_state.voice_recording_filename = None
        st.session_state.voice_recording_path = None
        st.session_state.voice_last_transcription = None
        st.session_state.voice_status = "Recording discarded"


def _render_transcription_result() -> None:
    """Display transcription output or any encountered errors."""
    if st.session_state.voice_transcription_error:
        st.error(st.session_state.voice_transcription_error)
        return

    if not st.session_state.voice_last_transcription:
        return

    st.success("Latest voice input was transcribed and inserted into the chat box.")

    if st.session_state.voice_last_transcription_model or st.session_state.voice_last_transcription_language:
        meta_parts = []
        if st.session_state.voice_last_transcription_model:
            meta_parts.append(f"Model: {st.session_state.voice_last_transcription_model}")
        if st.session_state.voice_last_transcription_language:
            meta_parts.append(
                f"Language: {st.session_state.voice_last_transcription_language}"
            )
        st.caption(" | ".join(meta_parts))


def render_voice_input() -> None:
    """Public entry point used by the sidebar module."""
    _init_voice_state()

    st.markdown(
        "<div style='margin-top: 1.5rem; margin-bottom: 1rem;'>"
        "<h3 style='color: #8e8ea0; font-size: 0.9rem; font-weight: 600; "
        "text-transform: uppercase; letter-spacing: 0.5px;'>Voice Input</h3>"
        "</div>",
        unsafe_allow_html=True,
    )

    if not st.session_state.authenticated:
        st.info("Please log in to record voice messages.")
        return

    if not AUDIO_RECORDER_AVAILABLE:
        st.warning(
            "audio-recorder-streamlit is not installed. "
            "Add `audio-recorder-streamlit>=0.0.8` to requirements.txt."
        )
        return

    st.caption(
        "Click the microphone once to start recording and click again to stop. "
        "The clip is automatically compressed and transcribed locally (max 100MB)."
    )

    audio_bytes = audio_recorder(
        text="Tap to record",
        recording_color="#e74c3c",
        neutral_color="#343541",
        icon_name="microphone",
        icon_size="2x",
        pause_threshold=120.0,
    )

    if audio_bytes:
        _handle_new_audio(audio_bytes)

    if st.session_state.voice_status:
        st.info(st.session_state.voice_status)

    _render_download_controls()
    _render_transcription_result()

