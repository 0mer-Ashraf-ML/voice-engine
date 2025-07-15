from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

class AssistantCreate(BaseModel):
    name: str
    first_message: Optional[str] = None
    system_prompt: Optional[str] = None
    
    # Model Configuration
    model_provider: str = "openai"
    model_name: str = "gpt-4o"
    model_temperature: float = 0.7
    model_max_tokens: int = 1000
    model_config: Optional[Dict[str, Any]] = None
    
    # Voice Configuration
    voice_provider: str = "elevenlabs"
    voice_id: Optional[str] = None
    voice_settings: Optional[Dict[str, Any]] = None
    
    # Transcriber Configuration
    transcriber_provider: str = "deepgram"
    transcriber_model: str = "nova-3"
    transcriber_config: Optional[Dict[str, Any]] = None
    
    # Settings
    interruptions_enabled: bool = True
    background_sound: str = "office"
    voicemail_detection: bool = True
    
    # Webhook settings
    server_url: Optional[str] = None
    server_url_secret: Optional[str] = None

class AssistantUpdate(BaseModel):
    name: Optional[str] = None
    first_message: Optional[str] = None
    system_prompt: Optional[str] = None
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    model_temperature: Optional[float] = None
    model_max_tokens: Optional[int] = None
    model_config: Optional[Dict[str, Any]] = None
    voice_provider: Optional[str] = None
    voice_id: Optional[str] = None
    voice_settings: Optional[Dict[str, Any]] = None
    transcriber_provider: Optional[str] = None
    transcriber_model: Optional[str] = None
    transcriber_config: Optional[Dict[str, Any]] = None
    interruptions_enabled: Optional[bool] = None
    background_sound: Optional[str] = None
    voicemail_detection: Optional[bool] = None
    server_url: Optional[str] = None
    server_url_secret: Optional[str] = None
    is_active: Optional[bool] = None

class AssistantResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    first_message: Optional[str] = None
    system_prompt: Optional[str] = None
    model_provider: str
    model_name: str
    model_temperature: float
    model_max_tokens: int
    model_config: Optional[Dict[str, Any]] = None
    voice_provider: str
    voice_id: Optional[str] = None
    voice_settings: Optional[Dict[str, Any]] = None
    transcriber_provider: str
    transcriber_model: str
    transcriber_config: Optional[Dict[str, Any]] = None
    interruptions_enabled: bool
    background_sound: str
    voicemail_detection: bool
    server_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AssistantToolCreate(BaseModel):
    tool_id: uuid.UUID
    is_enabled: bool = True