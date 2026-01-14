import logging
import asyncio
import base64
import json
from typing import Optional, Callable, Awaitable
from dataclasses import dataclass

from app.config import get_settings
from app.models.schemas import Language, CallSession
from app.services.cartesia_tts import cartesia_tts
from app.services.deepgram_stt import deepgram_stt, DeepgramStreamingSession
from app.agents.health_assessment_agent import HealthAssessmentAgent, create_health_assessment_agent
from app.services.session_manager import session_manager

logger = logging.getLogger(__name__)


@dataclass
class AudioConfig:
    """Audio configuration for the voice pipeline."""
    sample_rate: int = 8000  # Twilio uses 8kHz
    channels: int = 1
    sample_width: int = 2  # 16-bit audio


class VoicePipeline:
    """
    Manages the full voice conversation pipeline.
    Integrates STT (Deepgram), LLM (OpenAI via HealthAssessmentAgent), and TTS (Cartesia).
    """

    def __init__(
        self,
        session: CallSession,
        on_audio_output: Callable[[bytes], Awaitable[None]],
        on_call_complete: Optional[Callable[[], Awaitable[None]]] = None
    ):
        self.settings = get_settings()
        self.session = session
        self.on_audio_output = on_audio_output
        self.on_call_complete = on_call_complete

        self.agent: Optional[HealthAssessmentAgent] = None
        self.stt_session: Optional[DeepgramStreamingSession] = None
        self.audio_config = AudioConfig()

        self._running = False
        self._speaking = False
        self._current_transcript = ""
        self._silence_frames = 0
        self._speech_detected = False

        # Audio buffer for Deepgram (needs 24kHz, but Twilio sends 8kHz)
        self._audio_buffer = bytearray()

    async def start(self):
        """Start the voice pipeline."""
        logger.info(f"Starting voice pipeline for session {self.session.session_id}")

        # Initialize agent
        self.agent = create_health_assessment_agent()
        await self.agent.initialize(self.session)

        # Initialize STT
        self.stt_session = await deepgram_stt.create_streaming_connection(
            language=self.session.language,
            detect_language=True,
            on_transcript=self._on_transcript
        )
        await self.stt_session.connect()

        self._running = True

        # Generate and speak initial greeting
        greeting = await self.agent.get_initial_greeting()
        await self._speak(greeting)

    async def stop(self):
        """Stop the voice pipeline."""
        logger.info(f"Stopping voice pipeline for session {self.session.session_id}")
        self._running = False

        if self.stt_session:
            await self.stt_session.close()

        if self.on_call_complete:
            await self.on_call_complete()

    async def process_audio_input(self, audio_data: bytes):
        """
        Process incoming audio from Twilio.
        Audio is expected to be 8kHz mulaw.
        """
        if not self._running or self._speaking:
            return

        # Convert mulaw to linear PCM if needed
        pcm_data = self._mulaw_to_linear(audio_data)

        # Upsample from 8kHz to 16kHz for Deepgram
        upsampled = self._upsample_audio(pcm_data, 8000, 16000)

        # Send to Deepgram for transcription
        if self.stt_session:
            await self.stt_session.send_audio(upsampled)

    def _on_transcript(self, text: str, is_final: bool, detected_language: Optional[str]):
        """Callback for Deepgram transcripts."""
        if not text.strip():
            return

        logger.debug(f"Transcript ({'final' if is_final else 'interim'}): {text}")

        if is_final:
            self._current_transcript = text
            # Process final transcript
            asyncio.create_task(self._process_transcript(text, detected_language))
        else:
            self._speech_detected = True

    async def _process_transcript(self, text: str, detected_language: Optional[str]):
        """Process a final transcript and generate response."""
        if not self.agent:
            return

        try:
            # Process through agent
            response, is_complete = await self.agent.process_user_input(
                text,
                detected_language
            )

            # Speak the response
            await self._speak(response)

            # Check if call is complete
            if is_complete:
                await asyncio.sleep(1)  # Brief pause after final message
                await self.stop()

        except Exception as e:
            logger.error(f"Error processing transcript: {e}")
            # Speak error message
            error_msg = (
                "Lo siento, tuve un problema. ¿Podría repetir eso?"
                if self.session.language == Language.SPANISH
                else "I'm sorry, I had a moment. Could you please repeat that?"
            )
            await self._speak(error_msg)

    async def _speak(self, text: str):
        """Convert text to speech and send to Twilio."""
        if not text:
            return

        self._speaking = True
        logger.info(f"Speaking: {text[:50]}...")

        try:
            # Get TTS audio from Cartesia
            audio_bytes = await cartesia_tts.synthesize(
                text,
                language=self.session.language
            )

            # Convert from 24kHz PCM to 8kHz mulaw for Twilio
            mulaw_audio = self._convert_for_twilio(audio_bytes)

            # Send audio to Twilio
            await self.on_audio_output(mulaw_audio)

        except Exception as e:
            logger.error(f"Error in TTS: {e}")
        finally:
            self._speaking = False

    def _mulaw_to_linear(self, mulaw_data: bytes) -> bytes:
        """Convert mulaw audio to linear PCM."""
        import audioop
        return audioop.ulaw2lin(mulaw_data, 2)

    def _linear_to_mulaw(self, linear_data: bytes) -> bytes:
        """Convert linear PCM to mulaw."""
        import audioop
        return audioop.lin2ulaw(linear_data, 2)

    def _upsample_audio(self, audio: bytes, from_rate: int, to_rate: int) -> bytes:
        """Upsample audio from one sample rate to another."""
        import audioop
        return audioop.ratecv(audio, 2, 1, from_rate, to_rate, None)[0]

    def _downsample_audio(self, audio: bytes, from_rate: int, to_rate: int) -> bytes:
        """Downsample audio from one sample rate to another."""
        import audioop
        return audioop.ratecv(audio, 2, 1, from_rate, to_rate, None)[0]

    def _convert_for_twilio(self, audio_24khz: bytes) -> bytes:
        """Convert 24kHz PCM audio to 8kHz mulaw for Twilio."""
        # Downsample from 24kHz to 8kHz
        audio_8khz = self._downsample_audio(audio_24khz, 24000, 8000)
        # Convert to mulaw
        return self._linear_to_mulaw(audio_8khz)


class TwilioMediaStreamHandler:
    """
    Handles WebSocket connection for Twilio Media Streams.
    Manages bidirectional audio streaming between Twilio and the voice pipeline.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.pipeline: Optional[VoicePipeline] = None
        self.stream_sid: Optional[str] = None
        self._ws = None

    async def handle_websocket(self, websocket):
        """Handle the WebSocket connection from Twilio."""
        self._ws = websocket

        # Get session
        session = await session_manager.get_session(self.session_id)
        if not session:
            logger.error(f"Session not found: {self.session_id}")
            return

        # Create voice pipeline
        self.pipeline = VoicePipeline(
            session=session,
            on_audio_output=self._send_audio,
            on_call_complete=self._on_call_complete
        )

        try:
            await self.pipeline.start()

            async for message in websocket.iter_text():
                await self._handle_message(message)

        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            if self.pipeline:
                await self.pipeline.stop()

    async def _handle_message(self, message: str):
        """Handle incoming WebSocket message from Twilio."""
        try:
            data = json.loads(message)
            event_type = data.get("event")

            if event_type == "start":
                self.stream_sid = data.get("streamSid")
                logger.info(f"Media stream started: {self.stream_sid}")

            elif event_type == "media":
                # Incoming audio from caller
                payload = data.get("media", {}).get("payload", "")
                if payload:
                    audio_data = base64.b64decode(payload)
                    if self.pipeline:
                        await self.pipeline.process_audio_input(audio_data)

            elif event_type == "stop":
                logger.info(f"Media stream stopped: {self.stream_sid}")
                if self.pipeline:
                    await self.pipeline.stop()

            elif event_type == "dtmf":
                # Handle DTMF tones (keypress)
                digit = data.get("dtmf", {}).get("digit")
                if digit and self.pipeline and self.pipeline.agent:
                    # Process DTMF as text input
                    response, is_complete = await self.pipeline.agent.process_user_input(digit)
                    await self.pipeline._speak(response)
                    if is_complete:
                        await self.pipeline.stop()

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def _send_audio(self, audio_data: bytes):
        """Send audio to Twilio via WebSocket."""
        if not self._ws or not self.stream_sid:
            return

        # Twilio expects base64-encoded audio in chunks
        chunk_size = 640  # 40ms of 8kHz mulaw audio

        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i + chunk_size]
            message = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {
                    "payload": base64.b64encode(chunk).decode("utf-8")
                }
            }
            await self._ws.send_text(json.dumps(message))
            # Small delay to control playback speed
            await asyncio.sleep(0.04)

    async def _on_call_complete(self):
        """Handle call completion."""
        logger.info(f"Call complete for session {self.session_id}")
        if self._ws:
            # Send clear message to stop any pending audio
            if self.stream_sid:
                await self._ws.send_text(json.dumps({
                    "event": "clear",
                    "streamSid": self.stream_sid
                }))

