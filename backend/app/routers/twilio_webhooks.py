import logging
from fastapi import APIRouter, Request, WebSocket, Form
from fastapi.responses import Response

from app.config import get_settings
from app.services.twilio_service import twilio_service
from app.services.session_manager import session_manager
from app.agents.voice_pipeline import TwilioMediaStreamHandler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/twilio", tags=["twilio"])


@router.post("/voice/{session_id}")
async def handle_voice_webhook(session_id: str, request: Request):
    """
    Handle incoming Twilio voice webhook.
    Returns TwiML to start a media stream for real-time conversation.
    """
    logger.info(f"Voice webhook called for session {session_id}")

    # Get session to verify it exists
    session = await session_manager.get_session(session_id)
    if not session:
        logger.error(f"Session not found: {session_id}")
        return Response(
            content="<Response><Say>Sorry, there was an error. Goodbye.</Say></Response>",
            media_type="application/xml"
        )

    # Generate TwiML to start media stream
    twiml = twilio_service.generate_media_stream_twiml(session_id)

    logger.info(f"Returning TwiML for session {session_id}")
    return Response(content=twiml, media_type="application/xml")


@router.post("/status/{session_id}")
async def handle_status_callback(
    session_id: str,
    CallSid: str = Form(None),
    CallStatus: str = Form(None),
    CallDuration: str = Form(None)
):
    """
    Handle Twilio call status callbacks.
    """
    logger.info(f"Status callback for session {session_id}: {CallStatus}")

    if CallStatus == "completed":
        session = await session_manager.get_session(session_id)
        if session:
            await session_manager.mark_call_completed(session_id)

            # Send SMS if user opted in
            if session.opted_in_for_sms and session.cell_phone_for_sms:
                try:
                    await twilio_service.send_sms(
                        to_number=session.cell_phone_for_sms,
                        session_id=session_id,
                        language=session.language
                    )
                    logger.info(f"Sent SMS for completed session {session_id}")
                except Exception as e:
                    logger.error(f"Failed to send SMS: {e}")

    return {"status": "ok"}


@router.websocket("/media-stream/{session_id}")
async def handle_media_stream(websocket: WebSocket, session_id: str):
    """
    Handle Twilio Media Stream WebSocket connection.
    This is where the real-time audio conversation happens.
    """
    await websocket.accept()
    logger.info(f"Media stream WebSocket connected for session {session_id}")

    handler = TwilioMediaStreamHandler(session_id)
    await handler.handle_websocket(websocket)

    logger.info(f"Media stream WebSocket closed for session {session_id}")

