import httpx
import logging
import asyncio
from typing import AsyncGenerator, Optional
import base64
import json

from app.config import get_settings
from app.models.schemas import Language

logger = logging.getLogger(__name__)


class CartesiaTTS:
    """Text-to-Speech service using Cartesia API."""

    def __init__(self):
        # Don't cache settings at init time - read them lazily
        pass
    
    @property
    def base_url(self) -> str:
        return get_settings().cartesia_base_url
    
    @property
    def api_key(self) -> str:
        return get_settings().cartesia_api_key

    def get_voice_id(self, language: Language) -> str:
        """Get the appropriate voice ID based on language."""
        settings = get_settings()
        if language == Language.SPANISH:
            return settings.cartesia_voice_id_spanish
        return settings.cartesia_voice_id

    async def synthesize(
        self,
        text: str,
        language: Language = Language.ENGLISH
    ) -> bytes:
        """
        Synthesize text to speech using Cartesia.
        Returns raw audio bytes (PCM 16-bit, 24kHz).
        """
        voice_id = self.get_voice_id(language)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/tts/bytes",
                headers={
                    "X-API-Key": self.api_key,
                    "Cartesia-Version": "2025-04-16",
                    "Content-Type": "application/json"
                },
                json={
                    "model_id": "sonic-english" if language == Language.ENGLISH else "sonic-multilingual",
                    "transcript": text,
                    "voice": {
                        "mode": "id",
                        "id": voice_id
                    },
                    "output_format": {
                        "container": "raw",
                        "encoding": "pcm_s16le",
                        "sample_rate": 24000
                    }
                },
                timeout=30.0
            )

            if response.status_code != 200:
                logger.error(f"Cartesia TTS error: {response.status_code} - {response.text}")
                raise Exception(f"Cartesia TTS failed: {response.status_code}")

            return response.content

    async def synthesize_stream(
        self,
        text: str,
        language: Language = Language.ENGLISH
    ) -> AsyncGenerator[bytes, None]:
        """
        Synthesize text to speech with streaming output.
        Yields audio chunks as they become available.
        """
        voice_id = self.get_voice_id(language)

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/tts/sse",
                headers={
                    "X-API-Key": self.api_key,
                    "Cartesia-Version": "2025-04-16",
                    "Content-Type": "application/json"
                },
                json={
                    "model_id": "sonic-english" if language == Language.ENGLISH else "sonic-multilingual",
                    "transcript": text,
                    "voice": {
                        "mode": "id",
                        "id": voice_id
                    },
                    "output_format": {
                        "container": "raw",
                        "encoding": "pcm_s16le",
                        "sample_rate": 24000
                    }
                },
                timeout=60.0
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(f"Cartesia TTS stream error: {response.status_code} - {error_text}")
                    raise Exception(f"Cartesia TTS stream failed: {response.status_code}")

                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        try:
                            data = json.loads(line[5:].strip())
                            if "audio" in data:
                                yield base64.b64decode(data["audio"])
                        except json.JSONDecodeError:
                            continue

    async def synthesize_websocket(
        self,
        text: str,
        language: Language = Language.ENGLISH,
        context_id: Optional[str] = None
    ) -> AsyncGenerator[bytes, None]:
        """
        Synthesize using WebSocket for lowest latency streaming.
        """
        import websockets

        voice_id = self.get_voice_id(language)
        ws_url = self.base_url.replace("https://", "wss://").replace("http://", "ws://")

        async with websockets.connect(
            f"{ws_url}/tts/websocket",
            additional_headers={
                "X-API-Key": self.api_key,
                "Cartesia-Version": "2025-04-16"
            }
        ) as ws:
            # Send synthesis request
            await ws.send(json.dumps({
                "model_id": "sonic-english" if language == Language.ENGLISH else "sonic-multilingual",
                "transcript": text,
                "voice": {
                    "mode": "id",
                    "id": voice_id
                },
                "output_format": {
                    "container": "raw",
                    "encoding": "pcm_s16le",
                    "sample_rate": 24000
                },
                "context_id": context_id
            }))

            # Receive audio chunks
            while True:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=30.0)
                    data = json.loads(message)

                    if data.get("type") == "audio":
                        yield base64.b64decode(data["data"])
                    elif data.get("type") == "done":
                        break
                except asyncio.TimeoutError:
                    break


# Singleton instance
cartesia_tts = CartesiaTTS()

