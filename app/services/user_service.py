from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.user import User, UserRole
from app.models.organization import Organization
from app.schemas.auth import UserCreate, UserUpdate
from app.auth import get_password_hash, verify_password
from datetime import datetime, timezone
import uuid

class UserService:
    def __init__(self, db: Session):
        self.db = db
    
    def list_users(
        self, 
        current_user: User,
        limit: int = 100, 
        offset: int = 0,
        is_active: Optional[bool] = None,
        role: Optional[str] = None
    ) -> List[User]:
        """List users based on current user's permissions"""
        
        query = self.db.query(User).filter(
            User.organization_id == current_user.organization_id
        )
        
        # Apply role-based filtering
        if current_user.role == UserRole.SUPERADMIN:
            # SuperAdmin can see all users
            pass
        elif current_user.role == UserRole.ADMIN:
            # Admin can only see members (not other admins/superadmins)
            query = query.filter(User.role == UserRole.MEMBER)
        else:
            # Members cannot list users
            return []
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        if role:
            query = query.filter(User.role == role)
        
        return query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    
    def create_user(
        self, 
        current_user: User,
        user_data: UserCreate
    ) -> Optional[User]:
        """Create user with permission check"""
        
        # Check if current user can create users
        if current_user.role == UserRole.MEMBER:
            return None  # Members cannot create users
        
        # Check if trying to create admin/superadmin
        if user_data.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            if current_user.role != UserRole.SUPERADMIN:
                return None  # Only superadmin can create admin/superadmin
        
        # Check if user with email already exists
        existing_user = self.db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            return None
        
        # Hash password
        hashed_password = get_password_hash(user_data.password)
        
        user = User(
            organization_id=current_user.organization_id,
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            role=user_data.role
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def get_user(
        self, 
        user_id: uuid.UUID, 
        current_user: User
    ) -> Optional[User]:
        """Get user with permission check"""
        
        target_user = self.db.query(User).filter(
            User.id == user_id,
            User.organization_id == current_user.organization_id
        ).first()
        
        if not target_user:
            return None
        
        # Check if current user can view this user
        if current_user.id == user_id:
            return target_user  # Can always view own profile
        
        if current_user.role == UserRole.SUPERADMIN:
            return target_user  # SuperAdmin can view all
        
        if current_user.role == UserRole.ADMIN and target_user.role == UserRole.MEMBER:
            return target_user  # Admin can view members
        
        return None
    
    def update_user(
        self,
        user_id: uuid.UUID,
        current_user: User,
        user_data: UserUpdate
    ) -> Optional[User]:
        """Update user with permission check"""
        
        target_user = self.db.query(User).filter(
            User.id == user_id,
            User.organization_id == current_user.organization_id
        ).first()
        
        if not target_user:
            return None
        
        # Check permissions
        if not current_user.can_manage_user(target_user) and current_user.id != user_id:
            return None
        
        # Role change restrictions
        if user_data.role and user_data.role != target_user.role:
            # Only superadmin can change roles to/from admin/superadmin
            if current_user.role != UserRole.SUPERADMIN:
                if user_data.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
                    return None
                if target_user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
                    return None
        
        # Update fields
        update_data = user_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(target_user, field):
                setattr(target_user, field, value)
        
        target_user.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(target_user)
        
        return target_user
    
    def delete_user(
        self, 
        user_id: uuid.UUID, 
        current_user: User
    ) -> bool:
        """Delete user with permission check"""
        
        target_user = self.db.query(User).filter(
            User.id == user_id,
            User.organization_id == current_user.organization_id
        ).first()
        
        if not target_user:
            return False
        
        # Cannot delete yourself
        if current_user.id == user_id:
            return False
        
        # Check permissions
        if not current_user.can_manage_user(target_user):
            return False
        
        # Soft delete - just deactivate
        target_user.is_active = False
        target_user.updated_at = datetime.utcnow()
        
        self.db.commit()
        return True
    
    def create_superadmin(
        self,
        organization_id: uuid.UUID,
        user_data: UserCreate
    ) -> Optional[User]:
        """Create superadmin - only for initial setup"""
        
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
            role=UserRole.SUPERADMIN
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        user = self.get_user_by_email(email)
        
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            return None
        
        # Update last login
        # user.last_login = datetime.utcnow()
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