from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # Application
    app_env: str = "development"
    app_debug: bool = False
    app_secret_key: str = "change-me-in-production"
    backend_url: str = "https://zappix2-backend.aldea.ai"
    frontend_url: str = "https://zappix2.aldea.ai"

    # LiveKit
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo-preview"

    # Deepgram (STT)
    deepgram_api_key: str = ""
    deepgram_base_url: str = "https://api.deepgram.com"

    # Cartesia (TTS)
    cartesia_api_key: str = ""
    cartesia_base_url: str = "http://132.145.196.127:5555"
    cartesia_voice_id: str = "a0e99841-438c-4a64-b679-ae501e7d6091"
    cartesia_voice_id_spanish: str = "5619d38c-cf51-4d8e-9575-48f61a280571"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/zappix_demo"

    # AWS
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "zappix-demo-forms"

    # Email
    smtp_host: str = "smtp.sendgrid.net"
    smtp_port: int = 587
    smtp_user: str = "apikey"
    smtp_password: str = ""
    notification_email: str = "sales@zappix.com"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()

