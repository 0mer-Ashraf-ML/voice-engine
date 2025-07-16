from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    

    # DATABASE_URL: str = "postgresql://postgres:password@localhost:5433/voice_db"
    DATABASE_URL: str = "postgresql://voicebot:mindmeta123%40@voicebot.postgres.database.azure.com:5432/postgres?sslmode=require"

    # DATABASE_URL: str = "sqlite:///./vapi_voice.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # JWT Settings
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # API Keys
    API_KEY_PREFIX: str = "mindmeta_"
    
    # Integration Keys
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
    
    class Config:
        env_file = ".env"

settings = Settings()