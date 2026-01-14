import logging
import base64
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.models.schemas import ZappixFormData, FormSubmission
from app.services.session_manager import session_manager
from app.services.email_service import email_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/forms", tags=["forms"])


class FormDataResponse(BaseModel):
    """Response containing pre-populated form data."""
    session_id: str
    first_name: str
    language: str
    date_of_birth: Optional[str] = None
    zip_code: Optional[str] = None
    general_health: Optional[str] = None
    general_health_display: Optional[str] = None
    moderate_activities_limitation: Optional[str] = None
    moderate_activities_display: Optional[str] = None
    climbing_stairs_limitation: Optional[str] = None
    climbing_stairs_display: Optional[str] = None
    call_completed: bool = False


class FormSubmissionRequest(BaseModel):
    """Request to submit a signed form."""
    signature: str  # Base64 encoded signature image


def _get_display_value(value: Optional[str], value_type: str, language: str) -> Optional[str]:
    """Convert internal value to display string."""
    if not value:
        return None

    if value_type == "health":
        display_map_en = {
            "excellent": "Excellent",
            "very_good": "Very Good",
            "good": "Good",
            "fair": "Fair",
            "poor": "Poor"
        }
        display_map_es = {
            "excellent": "Excelente",
            "very_good": "Muy Buena",
            "good": "Buena",
            "fair": "Regular",
            "poor": "Mala"
        }
        return display_map_es.get(value, value) if language == "es" else display_map_en.get(value, value)

    elif value_type == "limitation":
        display_map_en = {
            "limited_a_lot": "Limited a Lot",
            "limited_a_little": "Limited a Little",
            "not_limited": "Not Limited at All"
        }
        display_map_es = {
            "limited_a_lot": "Muy Limitado",
            "limited_a_little": "Poco Limitado",
            "not_limited": "Sin Limitación"
        }
        return display_map_es.get(value, value) if language == "es" else display_map_en.get(value, value)

    return value


@router.get("/{session_id}", response_model=FormDataResponse)
async def get_form_data(session_id: str):
    """
    Get pre-populated form data for a session.
    This is called when the user clicks the SMS link.
    """
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    language = session.language.value

    return FormDataResponse(
        session_id=session.session_id,
        first_name=session.first_name,
        language=language,
        date_of_birth=session.authentication.date_of_birth,
        zip_code=session.authentication.zip_code,
        general_health=session.answers.general_health,
        general_health_display=_get_display_value(
            session.answers.general_health, "health", language
        ),
        moderate_activities_limitation=session.answers.moderate_activities_limitation,
        moderate_activities_display=_get_display_value(
            session.answers.moderate_activities_limitation, "limitation", language
        ),
        climbing_stairs_limitation=session.answers.climbing_stairs_limitation,
        climbing_stairs_display=_get_display_value(
            session.answers.climbing_stairs_limitation, "limitation", language
        ),
        call_completed=session.call_completed
    )


@router.post("/{session_id}/submit")
async def submit_form(
    session_id: str,
    request: FormSubmissionRequest,
    background_tasks: BackgroundTasks
):
    """
    Submit the signed form.
    This sends the completed form to the notification email.
    """
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.form_submitted:
        raise HTTPException(status_code=400, detail="Form already submitted")

    # Decode signature
    try:
        signature_bytes = base64.b64decode(request.signature.split(",")[-1])
    except Exception:
        signature_bytes = None

    # Mark form as submitted
    await session_manager.mark_form_submitted(session_id)

    # Send email in background
    background_tasks.add_task(
        email_service.send_completed_form,
        session,
        signature_bytes
    )

    logger.info(f"Form submitted for session {session_id}")

    return {
        "success": True,
        "message": "Form submitted successfully",
        "session_id": session_id
    }


@router.get("/{session_id}/status")
async def get_form_status(session_id: str):
    """Get the current status of a form submission."""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "call_completed": session.call_completed,
        "form_submitted": session.form_submitted,
        "opted_in_for_sms": session.opted_in_for_sms
    }

