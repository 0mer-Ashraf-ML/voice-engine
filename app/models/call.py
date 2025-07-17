from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, JSON, Text, Float, Integer
from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy.dialects.sqlite import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime, timezone

class Call(Base):
    __tablename__ = "calls"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    assistant_id = Column(UUID(as_uuid=True), ForeignKey("assistants.id"), nullable=True)
    phone_number_id = Column(UUID(as_uuid=True), ForeignKey("phone_numbers.id"), nullable=True)
    
    # Call details
    type = Column(String(50), nullable=False)  # inbound, outbound, web
    status = Column(String(50), default="queued")  # queued, ringing, in-progress, completed, failed
    direction = Column(String(20), nullable=True)  # inbound, outbound
    
    # Phone call specific
    from_number = Column(String(20), nullable=True)
    to_number = Column(String(20), nullable=True)
    provider_call_id = Column(String(255), nullable=True)  # Twilio SID, etc.
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Call content
    transcript = Column(Text, nullable=True)
    recording_url = Column(String(500), nullable=True)
    summary = Column(Text, nullable=True)
    
    # Call results
    end_reason = Column(String(100), nullable=True)  # hangup, completed, error, etc.
    transfer_destination = Column(String(255), nullable=True)
    
    # Costs and usage
    cost_usd = Column(Float, default=0.0)
    cost_breakdown = Column(JSON, nullable=True)  # {llm: 0.01, tts: 0.02, stt: 0.01}
    
    # Metadata
    metadataa = Column(JSON, nullable=True)
    customer_info = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    organization = relationship("Organization", back_populates="calls")
    assistant = relationship("Assistant", back_populates="calls")
    phone_number = relationship("PhoneNumber", back_populates="calls")