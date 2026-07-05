import logging
from fastapi import APIRouter, File, UploadFile, Form, Response, HTTPException
from google.cloud import texttospeech
from google.cloud import speech

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/accessibility/tts")
async def text_to_speech(
    text: str = Form(...)
):
    """Converts a text alert into an MP3 audio stream for visually impaired users."""
    try:
        client = texttospeech.TextToSpeechClient()
        
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-IN",
            name="en-IN-Standard-A"  # Using a neutral standard Indian English voice
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        
        return Response(content=response.audio_content, media_type="audio/mpeg")
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate audio from text.")

@router.post("/accessibility/stt")
async def speech_to_text(
    audio: UploadFile = File(...)
):
    """Transcribes uploaded voice recordings for hard-of-hearing operators."""
    try:
        audio_bytes = await audio.read()
        
        client = speech.SpeechClient()
        
        audio_request = speech.RecognitionAudio(content=audio_bytes)
        
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16, # Assuming LINEAR16, client must send valid format
            language_code="en-IN",
            enable_automatic_punctuation=True
        )
        
        # Depending on the actual file type uploaded from mobile, we might need to handle other encodings 
        # (like OGG_OPUS or MP3), but typically mobile clients can send LINEAR16. We'll stick to a robust default.
        # Alternatively, we can let Google auto-detect if the format is supported, but LINEAR16 is standard.
        # Note: If it's WEBM/AMR, it needs specific config. Assuming standard PCM/WAV for now.
        
        response = client.recognize(config=config, audio=audio_request)
        
        transcription = " ".join([result.alternatives[0].transcript for result in response.results])
        
        return {"transcription": transcription}
    except Exception as e:
        logger.error(f"STT processing failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to transcribe audio.")
