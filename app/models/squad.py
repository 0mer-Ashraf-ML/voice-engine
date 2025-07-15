from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, JSON, Text, Integer
# from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.sqlite import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime, timezone

class Squad(Base):
    __tablename__ = "squads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Squad configuration
    routing_strategy = Column(String(50), default="round_robin")  # round_robin, priority, skill_based
    max_concurrent_calls = Column(Integer, default=10)
    overflow_strategy = Column(String(50), default="queue")  # queue, voicemail, transfer
    
    # Settings
    is_active = Column(Boolean, default=True)
    working_hours = Column(JSON, nullable=True)  # Business hours configuration
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    organization = relationship("Organization", back_populates="squads")
    squad_assistants = relationship("SquadAssistant", back_populates="squad")

class SquadAssistant(Base):
    __tablename__ = "squad_assistants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    squad_id = Column(UUID(as_uuid=True), ForeignKey("squads.id"), nullable=False)
    assistant_id = Column(UUID(as_uuid=True), ForeignKey("assistants.id"), nullable=False)
    
    priority = Column(Integer, default=1)  # Lower number = higher priority
    is_active = Column(Boolean, default=True)
    max_concurrent_calls = Column(Integer, default=5)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    squad = relationship("Squad", back_populates="squad_assistants")
    assistant = relationship("Assistant", back_populates="squad_assistants")