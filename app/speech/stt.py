import os
import logging
from typing import Dict, Any

logger = logging.getLogger("urfeast.stt")

_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        try:
            print("🎙️ Loading faster-whisper (small, int8 CPU)...")
            from faster_whisper import WhisperModel
            _whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
            print("✅ faster-whisper loaded successfully!")
        except Exception as e:
            logger.warning(f"Could not load faster-whisper model: {e}")
            _whisper_model = None
    return _whisper_model

def transcribe_audio(audio_path: str) -> Dict[str, Any]:
    """Transcribes audio file using faster-whisper, auto-detecting language."""
    model = get_whisper_model()
    if not model or not os.path.exists(audio_path):
        return {
            "text": "Could not process voice recording. Please type your question.",
            "language": "en"
        }

    try:
        segments, info = model.transcribe(audio_path, vad_filter=True, beam_size=5)
        text_parts = [segment.text for segment in segments]
        full_text = " ".join(text_parts).strip()
        
        detected_lang = info.language or "en"
        return {
            "text": full_text or "Voice question recorded.",
            "language": detected_lang
        }
    except Exception as e:
        logger.warning(f"Error during whisper transcription: {e}")
        return {
            "text": "Error processing voice audio. Please try typing instead.",
            "language": "en"
        }
