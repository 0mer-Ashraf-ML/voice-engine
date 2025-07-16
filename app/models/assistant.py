from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, JSON, Text, Float, Integer
from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy.dialects.sqlite import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime, timezone

class Assistant(Base):
    __tablename__ = "assistants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    first_message = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=True)
    
    # Model Configuration
    model_provider = Column(String(50), default="openai")  # openai, anthropic, groq
    model_name = Column(String(100), default="gpt-4o")
    model_temperature = Column(Float, default=0.7)
    model_max_tokens = Column(Integer, default=1000)
    assistant_config = Column(JSON, nullable=True)  # Additional model settings
    
    # Voice Configuration
    voice_provider = Column(String(50), default="elevenlabs")
    voice_id = Column(String(255), nullable=True)
    voice_settings = Column(JSON, nullable=True)
    
    # Transcriber Configuration
    transcriber_provider = Column(String(50), default="deepgram")
    transcriber_model = Column(String(100), default="nova-3")
    transcriber_config = Column(JSON, nullable=True)
    
    # Settings
    interruptions_enabled = Column(Boolean, default=True)
    background_sound = Column(String(50), default="office")
    voicemail_detection = Column(Boolean, default=True)
    
    # Webhook settings
    server_url = Column(String(500), nullable=True)
    server_url_secret = Column(String(255), nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    organization = relationship("Organization", back_populates="assistants")
    calls = relationship("Call", back_populates="assistant")
    squad_assistants = relationship("SquadAssistant", back_populates="assistant")
    assistant_tools = relationship("AssistantTool", back_populates="assistant")

class AssistantTool(Base):
    __tablename__ = "assistant_tools"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assistant_id = Column(UUID(as_uuid=True), ForeignKey("assistants.id"), nullable=False)
    tool_id = Column(UUID(as_uuid=True), ForeignKey("tools.id"), nullable=False)
    
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    assistant = relationship("Assistant", back_populates="assistant_tools")
    tool = relationship("Tool", back_populates="assistant_tools")