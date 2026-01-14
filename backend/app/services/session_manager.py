import json
import redis.asyncio as redis
from typing import Optional
from datetime import datetime
import uuid

from app.config import get_settings
from app.models.schemas import CallSession, Language, AuthenticationData, HealthAssessmentAnswers


class SessionManager:
    """Manages call sessions using Redis for persistence."""

    def __init__(self):
        self.settings = get_settings()
        self._redis: Optional[redis.Redis] = None

    async def get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(
                self.settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis

    async def create_session(
        self,
        first_name: str,
        phone_number: str,
        language: Language = Language.ENGLISH
    ) -> CallSession:
        """Create a new call session."""
        session_id = str(uuid.uuid4())
        session = CallSession(
            session_id=session_id,
            first_name=first_name,
            phone_number=phone_number,
            language=language,
        )

        r = await self.get_redis()
        await r.setex(
            f"session:{session_id}",
            86400,  # 24 hour TTL
            session.model_dump_json()
        )

        return session

    async def get_session(self, session_id: str) -> Optional[CallSession]:
        """Retrieve a session by ID."""
        r = await self.get_redis()
        data = await r.get(f"session:{session_id}")

        if data is None:
            return None

        return CallSession.model_validate_json(data)

    async def update_session(self, session: CallSession) -> CallSession:
        """Update an existing session."""
        session.updated_at = datetime.utcnow()

        r = await self.get_redis()
        await r.setex(
            f"session:{session.session_id}",
            86400,
            session.model_dump_json()
        )

        return session

    async def update_authentication(
        self,
        session_id: str,
        date_of_birth: Optional[str] = None,
        zip_code: Optional[str] = None,
        last_four_ssn: Optional[str] = None
    ) -> Optional[CallSession]:
        """Update authentication data for a session."""
        session = await self.get_session(session_id)
        if session is None:
            return None

        if date_of_birth:
            session.authentication.date_of_birth = date_of_birth
        if zip_code:
            session.authentication.zip_code = zip_code
        if last_four_ssn:
            session.authentication.last_four_ssn = last_four_ssn

        # Check if authenticated (2 out of 3)
        auth_fields = [
            session.authentication.date_of_birth,
            session.authentication.zip_code,
            session.authentication.last_four_ssn
        ]
        provided_count = sum(1 for f in auth_fields if f is not None)
        session.authentication.authenticated = provided_count >= 2

        return await self.update_session(session)

    async def update_answers(
        self,
        session_id: str,
        general_health: Optional[str] = None,
        moderate_activities: Optional[str] = None,
        climbing_stairs: Optional[str] = None
    ) -> Optional[CallSession]:
        """Update health assessment answers for a session."""
        session = await self.get_session(session_id)
        if session is None:
            return None

        if general_health:
            session.answers.general_health = general_health
        if moderate_activities:
            session.answers.moderate_activities_limitation = moderate_activities
        if climbing_stairs:
            session.answers.climbing_stairs_limitation = climbing_stairs

        return await self.update_session(session)

    async def set_sms_opt_in(
        self,
        session_id: str,
        cell_phone: str
    ) -> Optional[CallSession]:
        """Set SMS opt-in and phone number."""
        session = await self.get_session(session_id)
        if session is None:
            return None

        session.opted_in_for_sms = True
        session.cell_phone_for_sms = cell_phone

        return await self.update_session(session)

    async def mark_call_completed(self, session_id: str) -> Optional[CallSession]:
        """Mark the call as completed."""
        session = await self.get_session(session_id)
        if session is None:
            return None

        session.call_completed = True
        return await self.update_session(session)

    async def mark_form_submitted(self, session_id: str) -> Optional[CallSession]:
        """Mark the form as submitted."""
        session = await self.get_session(session_id)
        if session is None:
            return None

        session.form_submitted = True
        return await self.update_session(session)

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()


# Singleton instance
session_manager = SessionManager()

