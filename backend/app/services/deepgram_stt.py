import httpx
import logging
import asyncio
from typing import AsyncGenerator, Optional, Callable
import json
import websockets

from app.config import get_settings
from app.models.schemas import Language

logger = logging.getLogger(__name__)


class DeepgramSTT:
    """Speech-to-Text service using Deepgram API."""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.deepgram_base_url
        self.api_key = self.settings.deepgram_api_key

    def get_language_code(self, language: Language) -> str:
        """Get Deepgram language code."""
        if language == Language.SPANISH:
            return "es"
        return "en-US"

    async def transcribe(
        self,
        audio_data: bytes,
        language: Language = Language.ENGLISH,
        detect_language: bool = False
    ) -> dict:
        """
        Transcribe audio using Deepgram.
        Returns transcription result with text and metadata.
        """
        params = {
            "model": "nova-2",
            "smart_format": "true",
            "punctuate": "true",
        }

        if detect_language:
            params["detect_language"] = "true"
        else:
            params["language"] = self.get_language_code(language)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/listen",
                headers={
                    "Authorization": f"Token {self.api_key}",
                    "Content-Type": "audio/raw"
                },
                params=params,
                content=audio_data,
                timeout=30.0
            )

            if response.status_code != 200:
                logger.error(f"Deepgram STT error: {response.status_code} - {response.text}")
                raise Exception(f"Deepgram STT failed: {response.status_code}")

            return response.json()

    async def create_streaming_connection(
        self,
        language: Language = Language.ENGLISH,
        detect_language: bool = False,
        on_transcript: Optional[Callable[[str, bool, Optional[str]], None]] = None
    ):
        """
        Create a streaming WebSocket connection to Deepgram.

        Args:
            language: The language to transcribe
            detect_language: Whether to auto-detect language
            on_transcript: Callback function(text, is_final, detected_language)

        Returns:
            DeepgramStreamingSession
        """
        return DeepgramStreamingSession(
            api_key=self.api_key,
            base_url=self.base_url,
            language=language,
            detect_language=detect_language,
            on_transcript=on_transcript
        )


class DeepgramStreamingSession:
    """Manages a streaming transcription session with Deepgram."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        language: Language,
        detect_language: bool,
        on_transcript: Optional[Callable[[str, bool, Optional[str]], None]]
    ):
        self.api_key = api_key
        self.base_url = base_url.replace("https://", "wss://").replace("http://", "ws://")
        self.language = language
        self.detect_language = detect_language
        self.on_transcript = on_transcript
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        self._receive_task: Optional[asyncio.Task] = None

    async def connect(self):
        """Establish WebSocket connection to Deepgram."""
        params = [
            "model=nova-2",
            "smart_format=true",
            "punctuate=true",
            "interim_results=true",
            "endpointing=300",
            "vad_events=true",
        ]

        if self.detect_language:
            params.append("detect_language=true")
        else:
            lang_code = "es" if self.language == Language.SPANISH else "en-US"
            params.append(f"language={lang_code}")

        url = f"{self.base_url}/v1/listen?{'&'.join(params)}"

        self.ws = await websockets.connect(
            url,
            additional_headers={"Authorization": f"Token {self.api_key}"}
        )

        self._running = True
        self._receive_task = asyncio.create_task(self._receive_loop())

        logger.info("Connected to Deepgram streaming")

    async def _receive_loop(self):
        """Background task to receive transcripts from Deepgram."""
        while self._running and self.ws:
            try:
                message = await asyncio.wait_for(self.ws.recv(), timeout=30.0)
                data = json.loads(message)

                if data.get("type") == "Results":
                    channel = data.get("channel", {})
                    alternatives = channel.get("alternatives", [])

                    if alternatives:
                        transcript = alternatives[0].get("transcript", "")
                        is_final = data.get("is_final", False)
                        detected_lang = data.get("detected_language")

                        if transcript and self.on_transcript:
                            self.on_transcript(transcript, is_final, detected_lang)

            except asyncio.TimeoutError:
                # Send keepalive
                if self.ws:
                    await self.ws.send(json.dumps({"type": "KeepAlive"}))
            except websockets.exceptions.ConnectionClosed:
                logger.info("Deepgram connection closed")
                break
            except Exception as e:
                logger.error(f"Error in Deepgram receive loop: {e}")
                break

    async def send_audio(self, audio_data: bytes):
        """Send audio data to Deepgram for transcription."""
        if self.ws:
            await self.ws.send(audio_data)

    async def close(self):
        """Close the Deepgram connection."""
        self._running = False

        if self.ws:
            # Send close message
            await self.ws.send(json.dumps({"type": "CloseStream"}))
            await self.ws.close()
            self.ws = None

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        logger.info("Closed Deepgram streaming session")


# Singleton instance
deepgram_stt = DeepgramSTT()

