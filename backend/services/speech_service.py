"""
Speech-to-Text service for citizen voice complaints.
Uses Google Cloud Speech-to-Text with multilingual Indian language support.
Falls back to mock transcription when credentials are unavailable.
"""

import io
import logging
from typing import Optional

from backend.config import get_settings

logger = logging.getLogger(__name__)


def transcribe_audio(
    audio_bytes: bytes,
    language_code: str = "hi-IN",
    sample_rate_hertz: int = 16000,
) -> str:
    """
    Transcribe audio bytes to text using Google Speech-to-Text.

    Supported languages:
    - hi-IN (Hindi), en-IN (English), mr-IN (Marathi),
      gu-IN (Gujarati), ta-IN (Tamil), te-IN (Telugu),
      kn-IN (Kannada), bn-IN (Bengali)

    Args:
        audio_bytes: Raw audio file bytes (WAV, MP3, OGG, FLAC)
        language_code: BCP-47 language code
        sample_rate_hertz: Audio sample rate

    Returns:
        Transcribed text string. Returns mock text if STT is unavailable.
    """
    # Attempt real Speech-to-Text first
    try:
        return _transcribe_google_stt(audio_bytes, language_code, sample_rate_hertz)
    except ImportError:
        logger.warning("google-cloud-speech not installed. Using Gemini fallback.")
        return _transcribe_gemini_fallback(audio_bytes, language_code)
    except Exception as e:
        logger.warning("Speech-to-Text failed (%s). Using mock transcription.", e)
        return _get_mock_transcription(language_code)


def _transcribe_google_stt(
    audio_bytes: bytes,
    language_code: str,
    sample_rate_hertz: int,
) -> str:
    """Real Google Cloud Speech-to-Text transcription."""
    from google.cloud import speech

    client = speech.SpeechClient()

    audio = speech.RecognitionAudio(content=audio_bytes)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=sample_rate_hertz,
        language_code=language_code,
        alternative_language_codes=["en-IN", "hi-IN"],
        enable_automatic_punctuation=True,
        model="latest_long",
    )

    response = client.recognize(config=config, audio=audio)

    if not response.results:
        return ""

    # Concatenate all recognized segments
    transcript = " ".join(
        result.alternatives[0].transcript
        for result in response.results
        if result.alternatives
    )
    return transcript.strip()


def _transcribe_gemini_fallback(
    audio_bytes: bytes,
    language_code: str,
) -> str:
    """
    Use Gemini multimodal as fallback for audio transcription.
    Gemini can process audio files directly.
    """
    try:
        from google import genai
        settings = get_settings()
        client = genai.Client()

        lang_name = _LANGUAGE_NAMES.get(language_code, "Hindi/English")

        response = client.models.generate_content(
            model=settings.gemini_model_name,
            contents=[
                f"Transcribe this audio file. The speaker is likely speaking {lang_name}. "
                f"Return ONLY the transcribed text, no explanation.",
                {"mime_type": "audio/wav", "data": audio_bytes},
            ],
        )
        return response.text.strip()
    except Exception as e:
        logger.warning("Gemini audio transcription failed: %s", e)
        return _get_mock_transcription(language_code)


def _get_mock_transcription(language_code: str) -> str:
    """Mock transcriptions for demo when STT APIs are unavailable."""
    mocks = {
        "hi-IN": "यहाँ बहुत धुआं है, कोई कूड़ा जला रहा है। बच्चों को साँस लेने में तकलीफ हो रही है।",
        "en-IN": "There is heavy smoke coming from the garbage dump near sector 15. Children are having breathing difficulty.",
        "mr-IN": "इथे खूप धूर आहे, कोणीतरी कचरा जाळत आहे. मुलांना श्वास घेण्यास त्रास होत आहे.",
        "gu-IN": "અહીં ખૂબ ધુમાડો છે, કોઈ કચરો બાળી રહ્યું છે. બાળકોને શ્વાસ લેવામાં તકલીફ થઈ રહી છે.",
        "ta-IN": "இங்கே நிறைய புகை வருகிறது, யாரோ குப்பையை எரிக்கிறார்கள். குழந்தைகளுக்கு சுவாசிக்க சிரமம்.",
    }
    return mocks.get(language_code, mocks["en-IN"])


_LANGUAGE_NAMES = {
    "hi-IN": "Hindi",
    "en-IN": "English",
    "mr-IN": "Marathi",
    "gu-IN": "Gujarati",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
    "kn-IN": "Kannada",
    "bn-IN": "Bengali",
}


def get_supported_languages() -> list[dict]:
    """Returns list of supported languages with display names."""
    return [
        {"code": code, "name": name}
        for code, name in _LANGUAGE_NAMES.items()
    ]
