from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy.dialects.sqlite import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Billing info
    stripe_customer_id = Column(String(255), nullable=True)
    subscription_plan = Column(String(50), default="free")  # free, pro, enterprise
    
    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    assistants = relationship("Assistant", back_populates="organization", cascade="all, delete-orphan")
    calls = relationship("Call", back_populates="organization", cascade="all, delete-orphan")
    phone_numbers = relationship("PhoneNumber", back_populates="organization", cascade="all, delete-orphan")
    squads = relationship("Squad", back_populates="organization", cascade="all, delete-orphan")
    tools = relationship("Tool", back_populates="organization", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="organization", cascade="all, delete-orphan")