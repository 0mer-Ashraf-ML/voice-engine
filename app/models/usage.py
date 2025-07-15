from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, JSON, Float, Integer
# from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.sqlite import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime, timezone

class UsageRecord(Base):
    __tablename__ = "usage_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id"), nullable=True)
    
    # Usage type
    usage_type = Column(String(50), nullable=False)  # call, llm_tokens, tts_characters, stt_minutes
    
    # Quantities
    quantity = Column(Float, nullable=False)  # Minutes, tokens, characters, etc.
    unit = Column(String(20), nullable=False)  # minutes, tokens, characters, calls
    
    # Costs
    unit_cost = Column(Float, nullable=False)  # Cost per unit
    total_cost = Column(Float, nullable=False)  # Total cost in USD
    
    # Provider info
    provider = Column(String(50), nullable=True)  # openai, elevenlabs, deepgram, twilio
    model_name = Column(String(100), nullable=True)  # gpt-4, eleven_turbo_v2, nova-2
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Billing
    billing_period = Column(String(10), nullable=False)  # YYYY-MM format
    is_billed = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    organization = relationship("Organization", back_populates="usage_records")
    call = relationship("Call")