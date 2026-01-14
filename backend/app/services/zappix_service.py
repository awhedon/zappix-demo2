import logging
import httpx
from typing import Optional
from urllib.parse import urlencode

from app.config import get_settings
from app.models.schemas import Language, CallSession

logger = logging.getLogger(__name__)


class ZappixService:
    """Service for interacting with Zappix APIs."""

    # Zappix API endpoints
    CREATE_SESSION_URL = "https://248ukb6dyi.execute-api.us-east-1.amazonaws.com/qa/api/v1/create-session"
    SEND_SMS_URL = "https://qastudio.zappix.com/mobile_api/v7/send-sms"

    # Zappix client IDs
    CREATE_SESSION_CLIENT_ID = "ugIAhM3dquTJS7L5y35CyZChiV9eO1arqgDMzdFfUKDdoLcRS9is0ltmKLkyhriM"
    SEND_SMS_CLIENT_ID = "qMso8TcCURFXE8k9AVMyV0JIkiADK9"

    # Zappix app base URL for the form link
    ZAPPIX_APP_BASE_URL = "https://qa.zappix.com/app/3606/session/"

    def __init__(self):
        self.settings = get_settings()

    def _format_health_answer(self, value: Optional[str]) -> str:
        """Convert internal health rating to Zappix format."""
        if not value:
            return ""

        mapping = {
            "excellent": "Excellent",
            "very_good": "Very Good",
            "good": "Good",
            "fair": "Fair",
            "poor": "Poor"
        }
        return mapping.get(value, value)

    def _format_limitation_answer(self, value: Optional[str]) -> str:
        """Convert internal limitation level to Zappix format."""
        if not value:
            return ""

        mapping = {
            "limited_a_lot": "Limited a lot",
            "limited_a_little": "Limited a bit",
            "not_limited": "Not limited at all"
        }
        return mapping.get(value, value)

    async def create_session(
        self,
        session: CallSession,
        additional_comments: str = ""
    ) -> Optional[dict]:
        """
        Create a Zappix session with user answers.

        Returns:
            dict with 'zappixSid' and 'optIn' on success, None on failure
        """
        # Build the user answers payload
        user_answers = {
            "GeneralHealth": self._format_health_answer(session.answers.general_health),
            "ModerateActivities": self._format_limitation_answer(session.answers.moderate_activities_limitation),
            "ClimbingStairs": self._format_limitation_answer(session.answers.climbing_stairs_limitation),
            "AdditionalComments": additional_comments,
            "OptInToReviewAndSign": "Yes" if session.opted_in_for_sms else "No"
        }

        # Determine locale based on language
        locale = "es" if session.language == Language.SPANISH else "en"

        # Build the request payload
        payload = {
            "locale": locale,
            "customerPhoneNumber": session.cell_phone_for_sms or session.phone_number,
            "customerFirstName": session.first_name,
            "customerLastName": "",  # We don't collect last name in the current flow
            "userAnswers": user_answers
        }

        logger.info(f"Creating Zappix session for {session.session_id}")
        logger.debug(f"Zappix payload: {payload}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.CREATE_SESSION_URL,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "clientId": self.CREATE_SESSION_CLIENT_ID
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Zappix session created: {result}")
                    return result
                else:
                    logger.error(f"Zappix create session failed: {response.status_code} - {response.text}")
                    return None

        except Exception as e:
            logger.error(f"Error creating Zappix session: {e}")
            return None

    async def send_sms(
        self,
        phone_number: str,
        zappix_sid: int,
        language: Language = Language.ENGLISH
    ) -> bool:
        """
        Send SMS with Zappix form link.

        Args:
            phone_number: User's phone number
            zappix_sid: Zappix session ID from create_session response
            language: User's preferred language

        Returns:
            True on success, False on failure
        """
        # Build the form link
        form_link = f"{self.ZAPPIX_APP_BASE_URL}?sid={zappix_sid}"

        # Build the SMS message based on language
        if language == Language.SPANISH:
            sms_message = f"Hola, Revise y firme su encuesta de salud usando este enlace seguro: {form_link}"
        else:
            sms_message = f"Hello, Review & sign your health survey using this secure link: {form_link}"

        # URL encode the message (& becomes %26, etc.)
        # The Zappix API expects form-urlencoded parameters
        params = {
            "includeLink": "n",
            "mobilePhoneNumber": phone_number,
            "smsMessage": sms_message
        }

        logger.info(f"Sending Zappix SMS to {phone_number} with SID {zappix_sid}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.SEND_SMS_URL,
                    params=params,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "clientId": self.SEND_SMS_CLIENT_ID
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        logger.info(f"Zappix SMS sent successfully to {phone_number}")
                        return True
                    else:
                        logger.error(f"Zappix SMS failed: {result.get('error')}")
                        return False
                else:
                    logger.error(f"Zappix send SMS failed: {response.status_code} - {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Error sending Zappix SMS: {e}")
            return False

    async def create_session_and_send_sms(
        self,
        session: CallSession,
        additional_comments: str = ""
    ) -> bool:
        """
        Combined flow: Create Zappix session and send SMS.

        This is the main method to call when the call is complete and
        the user has opted in to receive the form.

        Returns:
            True if both operations succeed, False otherwise
        """
        # Step 1: Create Zappix session
        result = await self.create_session(session, additional_comments)

        if not result:
            logger.error(f"Failed to create Zappix session for {session.session_id}")
            return False

        zappix_sid = result.get("zappixSid")
        if not zappix_sid:
            logger.error(f"No zappixSid in response for {session.session_id}")
            return False

        # Step 2: Send SMS with form link
        phone_number = session.cell_phone_for_sms or session.phone_number
        success = await self.send_sms(
            phone_number=phone_number,
            zappix_sid=zappix_sid,
            language=session.language
        )

        if success:
            logger.info(f"Zappix flow complete for session {session.session_id}, SID: {zappix_sid}")
        else:
            logger.error(f"Failed to send Zappix SMS for session {session.session_id}")

        return success


# Singleton instance
zappix_service = ZappixService()

