from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.user import User
from app.models.organization import Organization
from app.schemas.auth import UserCreate
from app.auth import get_password_hash, verify_password
from datetime import datetime, timezone
import uuid

class UserService:
    def __init__(self, db: Session):
        self.db = db
    
    def list_users(
        self, 
        organization_id: uuid.UUID, 
        limit: int = 100, 
        offset: int = 0,
        is_active: Optional[bool] = None,
        role: Optional[str] = None
    ) -> List[User]:
        query = self.db.query(User).filter(
            User.organization_id == organization_id
        )
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        if role:
            query = query.filter(User.role == role)
        
        return query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    
    def create_user(
        self, 
        organization_id: uuid.UUID, 
        user_data: UserCreate
    ) -> Optional[User]:
        # Check if user with email already exists
        existing_user = self.db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            return None
        
        # Hash password
        hashed_password = get_password_hash(user_data.password)
        
        user = User(
            organization_id=organization_id,
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            role=user_data.role,
            is_admin=True if user_data.role == "admin" else False
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def get_user(
        self, 
        user_id: uuid.UUID, 
        organization_id: uuid.UUID
    ) -> Optional[User]:
        return self.db.query(User).filter(
            User.id == user_id,
            User.organization_id == organization_id
        ).first()
    
    def update_user(
        self,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_data: dict
    ) -> Optional[User]:
        user = self.get_user(user_id, organization_id)
        
        if not user:
            return None
        
        # Handle password update separately
        if "password" in user_data:
            user_data["hashed_password"] = get_password_hash(user_data.pop("password"))
        
        # Update role and admin status
        if "role" in user_data:
            user.is_admin = user_data["role"] == "admin"
        
        for field, value in user_data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        user.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def delete_user(
        self, 
        user_id: uuid.UUID, 
        organization_id: uuid.UUID
    ) -> bool:
        user = self.get_user(user_id, organization_id)
        
        if not user:
            return False
        
        # Soft delete - just deactivate the user
        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        
        return True
    
    def authenticate_user(
        self,
        email: str,
        password: str
    ) -> Optional[User]:
        user = self.db.query(User).filter(User.email == email).first()
        
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            return None
        
        # Update last login
        user.last_login = datetime.now(timezone.utc)
        self.db.commit()
        
        return user
    
    def change_password(
        self,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        current_password: str,
        new_password: str
    ) -> bool:
        user = self.get_user(user_id, organization_id)
        
        if not user:
            return False
        
        # Verify current password
        if not verify_password(current_password, user.hashed_password):
            return False
        
        # Update password
        user.hashed_password = get_password_hash(new_password)
        user.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        
        return True
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()
    
    def activate_user(
        self,
        user_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> bool:
        user = self.get_user(user_id, organization_id)
        
        if not user:
            return False
        
        user.is_active = True
        user.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        
        return True
    
    def deactivate_user(
        self,
        user_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> bool:
        user = self.get_user(user_id, organization_id)
        
        if not user:
            return False
        
        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        
        return True
    
    def get_organization_stats(self, organization_id: uuid.UUID) -> dict:
        users = self.list_users(organization_id, limit=1000)
        
        total_users = len(users)
        active_users = len([u for u in users if u.is_active])
        admin_users = len([u for u in users if u.is_admin])
        
        # Get role distribution
        roles = {}
        for user in users:
            role = user.role
            if role not in roles:
                roles[role] = 0
            roles[role] += 1
        
        return {
            "organization_id": str(organization_id),
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "admin_users": admin_users,
            "role_distribution": roles
        }