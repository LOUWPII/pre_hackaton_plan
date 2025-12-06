import tempfile
from fastapi import UploadFile
import os

_whisper_model = None

def _load_whisper_model(model_name: str = "small"):
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper
        except Exception as e:
            raise ImportError("Whisper no está instalado. Instala 'openai-whisper' y sus dependencias (torch).")
        _whisper_model = whisper.load_model(model_name)
    return _whisper_model

async def transcribe_audiofile(upload_file: UploadFile, model_name: str = "small", language: str = "es") -> str:
    """
    Transcribe an uploaded audio file using OpenAI Whisper (local).
    Returns the transcribed text.
    Raises informative errors if whisper/torch are not available.
    """
    # Save to a temporary file
    suffix = os.path.splitext(upload_file.filename or "")[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await upload_file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        model = _load_whisper_model(model_name)
        result = model.transcribe(tmp_path, language=language)
        text = result.get("text", "").strip()
        return text
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
