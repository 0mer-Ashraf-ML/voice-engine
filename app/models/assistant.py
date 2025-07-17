from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, JSON, Text, Float, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime, timezone

class Assistant(Base):
    __tablename__ = "assistants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # Basic Info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
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
    transcriber_model = Column(String(100), default="nova-2-general")
    transcriber_config = Column(JSON, nullable=True)
    
    # Agent Format Fields
    language = Column(String(20), default="english")  # english, spanish, french, etc.
    conversation_timeout = Column(Float, default=30.0)  # Seconds before timeout
    audio_sample_rate = Column(Integer, default=16000)  # Audio quality
    audio_channels = Column(Integer, default=1)  # Mono/Stereo
    
    # ✅ NEW TOOLS FIELD - Direct JSON storage for easier attach/detach
    tools = Column(JSON, nullable=True, default=list)  # ["tool1", "tool2", "tool3"]
    
    # Settings
    interruptions_enabled = Column(Boolean, default=True)
    background_sound = Column(String(50), default="office")
    voicemail_detection = Column(Boolean, default=True)
    
    # Webhook settings
    server_url = Column(String(500), nullable=True)
    server_url_secret = Column(String(255), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    organization = relationship("Organization", back_populates="assistants")
    calls = relationship("Call", back_populates="assistant")
    squad_assistants = relationship("SquadAssistant", back_populates="assistant")
    # ✅ Keep assistant_tools relationship for backward compatibility if needed
    assistant_tools = relationship("AssistantTool", back_populates="assistant")
    
    # ✅ Helper methods for tools management
    def add_tool(self, tool_name: str):
        """Add a tool to the assistant"""
        if self.tools is None:
            self.tools = []
        if tool_name not in self.tools:
            self.tools.append(tool_name)
    
    def remove_tool(self, tool_name: str):
        """Remove a tool from the assistant"""
        if self.tools and tool_name in self.tools:
            self.tools.remove(tool_name)
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if assistant has a specific tool"""
        return self.tools and tool_name in self.tools
    
    def get_tools(self) -> list:
        """Get all tools as a list"""
        return self.tools or []
    
    def set_tools(self, tool_names: list):
        """Set all tools at once"""
        self.tools = tool_names or []

class AssistantTool(Base):
    __tablename__ = "assistant_tools"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assistant_id = Column(UUID(as_uuid=True), ForeignKey("assistants.id"), nullable=False)
    tool_id = Column(UUID(as_uuid=True), ForeignKey("tools.id"), nullable=False)
    
    is_enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    assistant = relationship("Assistant", back_populates="assistant_tools")
    tool = relationship("Tool", back_populates="assistant_tools")