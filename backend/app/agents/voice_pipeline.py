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
from app.services.zappix_service import zappix_service
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
        """Start the voice pipeline (full initialization including greeting)."""
        await self.start_without_greeting()
        await self.speak_greeting()

    async def start_without_greeting(self):
        """Start the voice pipeline without speaking the greeting yet."""
        logger.info(f"Starting voice pipeline for session {self.session.session_id}")

        # Initialize agent
        self.agent = create_health_assessment_agent()
        await self.agent.initialize(self.session)

        # Initialize STT (allow failure - we can still do TTS)
        try:
            self.stt_session = await deepgram_stt.create_streaming_connection(
                language=self.session.language,
                detect_language=True,
                on_transcript=self._on_transcript
            )
            await self.stt_session.connect()
            logger.info("STT session initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize STT (continuing without it): {e}")
            self.stt_session = None

        self._running = True

    async def speak_greeting(self):
        """Generate and speak the initial greeting."""
        try:
            greeting = await self.agent.get_initial_greeting()
            logger.info(f"Speaking greeting: {greeting[:50]}...")
            await self._speak(greeting)
        except Exception as e:
            logger.error(f"Failed to speak greeting: {e}")

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

        # Send raw mulaw audio directly to Deepgram (it expects mulaw at 8kHz)
        if self.stt_session:
            await self.stt_session.send_audio(audio_data)

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
            logger.info(f"TTS returned {len(audio_bytes)} bytes of audio")

            # Convert from 24kHz PCM to 8kHz mulaw for Twilio
            mulaw_audio = self._convert_for_twilio(audio_bytes)
            logger.info(f"Converted to {len(mulaw_audio)} bytes of mulaw audio")

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
        self._stream_ready = asyncio.Event()

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
            # Start pipeline initialization (STT, agent) but don't speak yet
            await self.pipeline.start_without_greeting()
            
            # Start processing messages in background
            message_task = asyncio.create_task(self._process_messages(websocket))
            
            # Wait for stream to be ready (with timeout)
            try:
                await asyncio.wait_for(self._stream_ready.wait(), timeout=10.0)
                logger.info("Stream ready, speaking greeting")
                await self.pipeline.speak_greeting()
            except asyncio.TimeoutError:
                logger.error("Timeout waiting for stream to start")
            
            # Wait for message processing to complete
            await message_task

        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            if self.pipeline:
                await self.pipeline.stop()

    async def _process_messages(self, websocket):
        """Process incoming WebSocket messages from Twilio."""
        async for message in websocket.iter_text():
            await self._handle_message(message)

    async def _handle_message(self, message: str):
        """Handle incoming WebSocket message from Twilio."""
        try:
            data = json.loads(message)
            event_type = data.get("event")

            if event_type == "start":
                self.stream_sid = data.get("streamSid")
                logger.info(f"Media stream started: {self.stream_sid}")
                self._stream_ready.set()  # Signal that stream is ready

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
            logger.warning(f"Cannot send audio: ws={bool(self._ws)}, stream_sid={self.stream_sid}")
            return

        logger.info(f"Sending {len(audio_data)} bytes of audio to Twilio stream {self.stream_sid}")

        # Twilio expects base64-encoded audio in chunks
        chunk_size = 640  # 40ms of 8kHz mulaw audio
        chunks_sent = 0

        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i + chunk_size]
            message = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {
                    "payload": base64.b64encode(chunk).decode("utf-8")
                }
            }
            try:
                await self._ws.send_text(json.dumps(message))
                chunks_sent += 1
            except Exception as e:
                logger.error(f"Error sending audio chunk {chunks_sent}: {e}")
                break
            # Small delay to control playback speed
            await asyncio.sleep(0.04)
        
        logger.info(f"Sent {chunks_sent} audio chunks to Twilio")

    async def _on_call_complete(self):
        """Handle call completion and trigger Zappix flow."""
        logger.info(f"Call complete for session {self.session_id}")

        # Get the latest session data
        session = await session_manager.get_session(self.session_id)
        if session:
            # Mark call as completed
            await session_manager.mark_call_completed(self.session_id)

            # Create Zappix session and send SMS if user opted in
            if session.opted_in_for_sms and session.cell_phone_for_sms:
                try:
                    success = await zappix_service.create_session_and_send_sms(session)
                    if success:
                        logger.info(f"Zappix session created and SMS sent for session {self.session_id}")
                    else:
                        logger.error(f"Zappix flow failed for session {self.session_id}")
                except Exception as e:
                    logger.error(f"Failed to process Zappix flow: {e}")

        if self._ws:
            # Send clear message to stop any pending audio
            if self.stream_sid:
                await self._ws.send_text(json.dumps({
                    "event": "clear",
                    "streamSid": self.stream_sid
                }))

