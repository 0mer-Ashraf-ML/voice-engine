from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy.dialects.sqlite import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime, timezone

class Tool(Base):
    __tablename__ = "tools"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # Tool details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(50), nullable=False)  # webhook, function, api
    
    # Configuration
    webhook_url = Column(String(500), nullable=True)
    webhook_method = Column(String(10), default="POST")  # GET, POST, PUT, etc.
    webhook_headers = Column(JSON, nullable=True)
    webhook_timeout = Column(Integer, default=30)  # seconds
    
    # Function definition (for function calling)
    function_schema = Column(JSON, nullable=True)  # OpenAI function schema
    
    # Settings
    is_active = Column(Boolean, default=True)
    retry_attempts = Column(Integer, default=3)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    organization = relationship("Organization", back_populates="tools")
    assistant_tools = relationship("AssistantTool", back_populates="tool")