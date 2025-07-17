from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://voicebot:mindmeta123%40@voicebot.postgres.database.azure.com:5432/postgres?sslmode=require"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT Settings
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # API Keys
    API_KEY_PREFIX: str = "mindmeta_"
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    ELEVENLABS_API_KEY: Optional[str] = None
    DEEPGRAM_API_KEY: Optional[str] = None

    # Telephony
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None

    # Payment
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None

    # App Settings
    APP_NAME: str = "Voice API"
    DEBUG: bool = False

    # Add PORT field
    PORT: int = 8000  # Default port value

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False  # Allow case-insensitive env var matching [[4]]

settings = Settings()