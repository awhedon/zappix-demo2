from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum


class Language(str, Enum):
    ENGLISH = "en"
    SPANISH = "es"


class HealthRating(str, Enum):
    EXCELLENT = "excellent"
    VERY_GOOD = "very_good"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class LimitationLevel(str, Enum):
    LIMITED_A_LOT = "limited_a_lot"
    LIMITED_A_LITTLE = "limited_a_little"
    NOT_LIMITED = "not_limited"


class AuthenticationData(BaseModel):
    date_of_birth: Optional[str] = None
    zip_code: Optional[str] = None
    last_four_ssn: Optional[str] = None
    authenticated: bool = False


class HealthAssessmentAnswers(BaseModel):
    general_health: Optional[HealthRating] = None
    moderate_activities_limitation: Optional[LimitationLevel] = None
    climbing_stairs_limitation: Optional[LimitationLevel] = None


class CallSession(BaseModel):
    session_id: str
    first_name: str
    phone_number: str
    language: Language = Language.ENGLISH
    authentication: AuthenticationData = Field(default_factory=AuthenticationData)
    answers: HealthAssessmentAnswers = Field(default_factory=HealthAssessmentAnswers)
    cell_phone_for_sms: Optional[str] = None
    opted_in_for_sms: bool = False
    call_completed: bool = False
    form_submitted: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class OutboundCallRequest(BaseModel):
    first_name: str
    phone_number: str
    language: Language = Language.ENGLISH


class OutboundCallResponse(BaseModel):
    success: bool
    session_id: str
    message: str


class ZappixFormData(BaseModel):
    session_id: str
    first_name: str
    language: Language
    date_of_birth: Optional[str] = None
    zip_code: Optional[str] = None
    general_health: Optional[str] = None
    moderate_activities_limitation: Optional[str] = None
    climbing_stairs_limitation: Optional[str] = None
    signature: Optional[str] = None
    submitted_at: Optional[datetime] = None


class SMSRequest(BaseModel):
    session_id: str
    phone_number: str


class SMSResponse(BaseModel):
    success: bool
    message: str


class FormSubmission(BaseModel):
    session_id: str
    signature: str
    submitted_at: datetime = Field(default_factory=datetime.utcnow)


class WebhookEvent(BaseModel):
    event_type: str
    session_id: str
    data: dict

