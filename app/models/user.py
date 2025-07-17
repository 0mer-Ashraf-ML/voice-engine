from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime
import enum

class UserRole(enum.Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    MEMBER = "member"

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    
    is_active = Column(Boolean, default=True)
    role = Column(String(20), default=UserRole.MEMBER.value)  # ✅ Use String instead of Enum to avoid DB issues
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # last_login = Column(DateTime, nullable=True)  # ✅ Uncommented and nullable
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    assistants = relationship("Assistant", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    
    @property
    def is_admin(self) -> bool:
        """Check if user is admin or superadmin"""
        # return self.role in ["admin", "superadmin"]  # ✅ Use string values
        return self.role in [UserRole.ADMIN.value, UserRole.SUPERADMIN.value]
    
    @property
    def is_superadmin(self) -> bool:
        """Check if user is superadmin"""
        # return self.role == "superadmin"  # ✅ Use string value
        return self.role == UserRole.SUPERADMIN.value
    
    def can_manage_user(self, target_user: 'User') -> bool:
        """Check if current user can manage target user"""
        if self.role == UserRole.SUPERADMIN.value:
            return True  # SuperAdmin can manage everyone
        
        if self.role == UserRole.ADMIN.value:
            # Admin can only manage members, not other admins/superadmins
            return target_user.role == UserRole.MEMBER.value
        
        return False  # Members cannot manage anyone

class ApiKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False)
    key_prefix = Column(String(20), nullable=False)
    
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")