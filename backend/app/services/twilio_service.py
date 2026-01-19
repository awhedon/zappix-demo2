import logging
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect

from app.config import get_settings
from app.models.schemas import Language

logger = logging.getLogger(__name__)


class TwilioService:
    """Service for Twilio voice calls and SMS."""

    def __init__(self):
        self.settings = get_settings()
        self.client = Client(
            self.settings.twilio_account_sid,
            self.settings.twilio_auth_token
        )

    async def initiate_outbound_call(
        self,
        to_number: str,
        session_id: str,
        first_name: str,
        language: Language = Language.ENGLISH
    ) -> str:
        """
        Initiate an outbound call using Twilio.
        Returns the call SID.
        """
        # The TwiML will connect to our LiveKit room for the conversation
        twiml_url = f"{self.settings.backend_url}/api/twilio/voice/{session_id}"

        call = self.client.calls.create(
            to=to_number,
            from_=self.settings.twilio_phone_number,
            url=twiml_url,
            method="POST",
            status_callback=f"{self.settings.backend_url}/api/twilio/status/{session_id}",
            status_callback_event=["initiated", "ringing", "answered", "completed"],
            status_callback_method="POST"
        )

        logger.info(f"Initiated outbound call {call.sid} to {to_number} for session {session_id}")
        return call.sid

    async def send_sms(
        self,
        to_number: str,
        session_id: str,
        language: Language = Language.ENGLISH
    ) -> str:
        """
        Send SMS with link to Zappix form.
        Returns the message SID.
        """
        form_url = f"{self.settings.frontend_url}/form/{session_id}"

        if language == Language.SPANISH:
            body = f"Por favor revise y firme su formulario de evaluación de salud: {form_url}"
        else:
            body = f"Please review and sign your health assessment form: {form_url}"

        message = self.client.messages.create(
            to=to_number,
            from_=self.settings.twilio_phone_number,
            body=body
        )

        logger.info(f"Sent SMS {message.sid} to {to_number} for session {session_id}")
        return message.sid

    def generate_livekit_connect_twiml(self, session_id: str, room_name: str) -> str:
        """
        Generate TwiML to connect Twilio call to LiveKit room via SIP.
        """
        response = VoiceResponse()

        # Connect to LiveKit via SIP trunk
        connect = Connect()
        connect.stream(
            url=f"wss://{self.settings.backend_url.replace('https://', '')}/api/twilio/media-stream/{session_id}",
            name=f"livekit-{session_id}"
        )
        response.append(connect)

        return str(response)

    def generate_media_stream_twiml(self, session_id: str) -> str:
        """
        Generate TwiML to start a bidirectional media stream for real-time audio processing.
        Uses <Connect><Stream> for bidirectional audio (sending audio back to caller).
        """
        response = VoiceResponse()

        # Use Connect for bidirectional media stream
        connect = Connect()
        connect.stream(
            url=f"wss://{self.settings.backend_url.replace('https://', '')}/api/twilio/media-stream/{session_id}"
        )
        response.append(connect)

        return str(response)


# Singleton instance
twilio_service = TwilioService()

