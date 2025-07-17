from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy.dialects.sqlite import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime, timezone

class PhoneNumber(Base):
    __tablename__ = "phone_numbers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # Phone number details
    phone_number = Column(String(20), unique=True, nullable=False)
    country_code = Column(String(5), nullable=False)
    area_code = Column(String(10), nullable=True)
    formatted_number = Column(String(30), nullable=False)  # +1 (555) 123-4567
    
    # Provider details
    provider = Column(String(50), nullable=False)  # twilio, vonage, telnyx
    provider_id = Column(String(255), nullable=False)  # Provider's ID for this number
    provider_config = Column(JSON, nullable=True)
    
    # Configuration
    name = Column(String(255), nullable=True)  # User-friendly name
    is_active = Column(Boolean, default=True)
    
    # Webhook URLs
    inbound_webhook_url = Column(String(500), nullable=True)
    status_webhook_url = Column(String(500), nullable=True)
    
    # Capabilities
    voice_enabled = Column(Boolean, default=True)
    sms_enabled = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    organization = relationship("Organization", back_populates="phone_numbers")
    calls = relationship("Call", back_populates="phone_number")