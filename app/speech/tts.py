import os
import hashlib
import logging
import subprocess
from gtts import gTTS
from app.config import settings

logger = logging.getLogger("urfeast.tts")

def speak(text: str, lang: str = "en") -> str:
    """Generates speech MP3 for text in specified language, returning relative web URL path."""
    if not text or not text.strip():
        return ""

    # Hash text and lang for caching
    hash_str = hashlib.md5(f"{lang}:{text.strip()}".encode("utf-8")).hexdigest()
    filename = f"{hash_str}.mp3"
    filepath = os.path.join(settings.TTS_CACHE_DIR, filename)
    web_url = f"/tts_cache/{filename}"

    if os.path.exists(filepath):
        return web_url

    lang = "en" if lang not in ("en", None) else "en"

    # Check Piper local model availability first for English output
    piper_model_path = f"models/piper/{lang}.onnx"
    if os.path.exists(piper_model_path):
        try:
            wav_path = filepath.replace(".mp3", ".wav")
            cmd = ["piper", "--model", piper_model_path, "--output_file", wav_path]
            process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            process.communicate(input=text.encode("utf-8"))
            if os.path.exists(wav_path):
                return f"/tts_cache/{filename.replace('.mp3', '.wav')}"
        except Exception as e:
            logger.warning(f"Piper TTS execution failed ({e}). Falling back to gTTS.")

    # Fallback to gTTS
    try:
        tts = gTTS(text=text, lang="en", slow=False)
        tts.save(filepath)
        return web_url
    except Exception as e:
        logger.warning(f"gTTS error: {e}")
        return ""
