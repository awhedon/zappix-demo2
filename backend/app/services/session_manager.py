import json
import redis.asyncio as redis
from typing import Optional, Dict
from datetime import datetime
import uuid
import logging

from app.config import get_settings
from app.models.schemas import CallSession, Language, AuthenticationData, HealthAssessmentAnswers

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages call sessions using Redis for persistence, with in-memory fallback."""

    def __init__(self):
        self.settings = get_settings()
        self._redis: Optional[redis.Redis] = None
        self._redis_available: Optional[bool] = None
        self._memory_store: Dict[str, str] = {}  # In-memory fallback

    async def _check_redis_available(self) -> bool:
        """Check if Redis is available."""
        if self._redis_available is not None:
            return self._redis_available
        
        try:
            client = redis.from_url(
                self.settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await client.ping()
            self._redis = client
            self._redis_available = True
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis unavailable ({e}), using in-memory session storage")
            self._redis_available = False
        
        return self._redis_available

    async def get_redis(self) -> Optional[redis.Redis]:
        if not await self._check_redis_available():
            return None
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

        key = f"session:{session_id}"
        data = session.model_dump_json()
        
        r = await self.get_redis()
        if r:
            await r.setex(key, 86400, data)  # 24 hour TTL
        else:
            self._memory_store[key] = data

        return session

    async def get_session(self, session_id: str) -> Optional[CallSession]:
        """Retrieve a session by ID."""
        key = f"session:{session_id}"
        
        r = await self.get_redis()
        if r:
            data = await r.get(key)
        else:
            data = self._memory_store.get(key)

        if data is None:
            return None

        return CallSession.model_validate_json(data)

    async def update_session(self, session: CallSession) -> CallSession:
        """Update an existing session."""
        session.updated_at = datetime.utcnow()

        key = f"session:{session.session_id}"
        data = session.model_dump_json()
        
        r = await self.get_redis()
        if r:
            await r.setex(key, 86400, data)
        else:
            self._memory_store[key] = data

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

