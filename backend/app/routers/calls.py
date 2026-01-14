import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.models.schemas import (
    OutboundCallRequest,
    OutboundCallResponse,
    SMSRequest,
    SMSResponse,
    Language
)
from app.services.session_manager import session_manager
from app.services.twilio_service import twilio_service
from app.services.zappix_service import zappix_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/calls", tags=["calls"])


@router.post("/outbound", response_model=OutboundCallResponse)
async def initiate_outbound_call(
    request: OutboundCallRequest,
    background_tasks: BackgroundTasks
):
    """
    Initiate an outbound call to conduct a health assessment.
    This is the main entry point for the Zappix Intelligent Outreach flow.
    """
    try:
        # Create a new session
        session = await session_manager.create_session(
            first_name=request.first_name,
            phone_number=request.phone_number,
            language=request.language
        )

        logger.info(f"Created session {session.session_id} for {request.first_name}")

        # Initiate the outbound call via Twilio
        call_sid = await twilio_service.initiate_outbound_call(
            to_number=request.phone_number,
            session_id=session.session_id,
            first_name=request.first_name,
            language=request.language
        )

        logger.info(f"Initiated call {call_sid} for session {session.session_id}")

        return OutboundCallResponse(
            success=True,
            session_id=session.session_id,
            message=f"Call initiated successfully. Call SID: {call_sid}"
        )

    except Exception as e:
        logger.error(f"Failed to initiate outbound call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/zappix/{session_id}", response_model=SMSResponse)
async def trigger_zappix_flow(session_id: str):
    """
    Manually trigger the Zappix flow for a session.
    Creates a Zappix session with user answers and sends SMS with form link.

    This is typically called automatically when the call completes,
    but can be triggered manually for testing.
    """
    try:
        # Get session
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Allow manual trigger even if not opted in (for testing)
        phone_number = session.cell_phone_for_sms or session.phone_number

        # Create Zappix session and send SMS
        success = await zappix_service.create_session_and_send_sms(session)

        if success:
            logger.info(f"Zappix flow triggered successfully for session {session_id}")
            return SMSResponse(
                success=True,
                message="Zappix session created and SMS sent successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Zappix flow failed")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger Zappix flow for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sms/{session_id}", response_model=SMSResponse)
async def send_form_sms(session_id: str):
    """
    Send SMS with form link for a completed call session.
    DEPRECATED: Use /zappix/{session_id} instead for Zappix integration.
    This endpoint is kept for backwards compatibility.
    """
    try:
        # Get session
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if not session.opted_in_for_sms:
            raise HTTPException(status_code=400, detail="User has not opted in for SMS")

        if not session.cell_phone_for_sms:
            raise HTTPException(status_code=400, detail="No phone number provided for SMS")

        # Use Zappix flow instead
        success = await zappix_service.create_session_and_send_sms(session)

        if success:
            logger.info(f"Zappix SMS sent for session {session_id}")
            return SMSResponse(
                success=True,
                message="Zappix session created and SMS sent successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to send SMS via Zappix")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send SMS for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session details."""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

