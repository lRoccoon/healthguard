"""
Speech-to-Text Transcription Service using OpenAI Whisper API.
"""

import io
from typing import Optional
import openai
from openai import AsyncOpenAI

from ..config import settings


class TranscriptionService:
    """
    Service for transcribing audio files to text using OpenAI Whisper API.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize transcription service.

        Args:
            api_key: OpenAI API key. If not provided, uses settings.openai_api_key
        """
        self.api_key = api_key or settings.openai_api_key
        if self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key)
        else:
            self.client = None

    async def transcribe_audio(
        self,
        audio_data: bytes,
        filename: str = "audio.m4a",
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> dict:
        """
        Transcribe audio file to text using OpenAI Whisper.

        Args:
            audio_data: Raw audio file bytes
            filename: Original filename (helps Whisper detect format)
            language: ISO 639-1 language code (e.g., 'en', 'zh', 'es')
                     If not provided, Whisper will auto-detect
            prompt: Optional text to guide the model's style or continue a previous segment

        Returns:
            dict with:
                - text: Transcribed text
                - language: Detected language (if auto-detected)
                - duration: Audio duration (if available)

        Raises:
            RuntimeError: If OpenAI API key is not configured
            Exception: If transcription fails
        """
        if not self.client:
            raise RuntimeError(
                "OpenAI API key not configured. Please set OPENAI_API_KEY in environment variables."
            )

        try:
            # Create file-like object from bytes
            audio_file = io.BytesIO(audio_data)
            audio_file.name = filename

            # Call Whisper API
            transcription_params = {
                "model": "whisper-1",
                "file": audio_file,
                "response_format": "verbose_json"  # Get more detailed response
            }

            if language:
                transcription_params["language"] = language

            if prompt:
                transcription_params["prompt"] = prompt

            response = await self.client.audio.transcriptions.create(**transcription_params)

            # Extract response data
            result = {
                "text": response.text,
                "language": getattr(response, 'language', None),
                "duration": getattr(response, 'duration', None)
            }

            return result

        except Exception as e:
            raise Exception(f"Transcription failed: {str(e)}")

    def is_configured(self) -> bool:
        """
        Check if the transcription service is properly configured.

        Returns:
            bool: True if API key is set, False otherwise
        """
        return self.client is not None


# Global transcription service instance
_transcription_service: Optional[TranscriptionService] = None


def get_transcription_service() -> TranscriptionService:
    """
    Get the global transcription service instance.

    Returns:
        TranscriptionService: Global transcription service
    """
    global _transcription_service
    if _transcription_service is None:
        _transcription_service = TranscriptionService()
    return _transcription_service
