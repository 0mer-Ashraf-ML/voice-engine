from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.auth import get_current_user
from app.models.user import User, UserRole
from app.schemas.auth import UserResponse, UserCreate, UserUpdate
from app.services.user_service import UserService
import uuid

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)

@router.get("/", response_model=List[UserResponse])
async def list_users(
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    is_active: Optional[bool] = Query(None),
    role: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check permissions
    if current_user.role == UserRole.MEMBER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Members cannot list users"
        )
    
    service = UserService(db)
    users = service.list_users(
        current_user=current_user,
        limit=limit,
        offset=offset,
        is_active=is_active,
        role=role.lower()
    )
    return [UserResponse.model_validate(user) for user in users]

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = UserService(db)
    user = service.create_user(
        current_user=current_user,
        user_data=user_data
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create user. Either email exists or insufficient permissions."
        )
    
    return UserResponse.model_validate(user)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = UserService(db)
    user = service.get_user(
        user_id=user_id,
        current_user=current_user
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or insufficient permissions"
        )
    
    return UserResponse.model_validate(user)

@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = UserService(db)
    user = service.update_user(
        user_id=user_id,
        current_user=current_user,
        user_data=user_data
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or insufficient permissions"
        )
    
    return UserResponse.model_validate(user)

@router.delete("/{user_id}")
async def delete_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = UserService(db)
    success = service.delete_user(
        user_id=user_id,
        current_user=current_user
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or insufficient permissions"
        )
    
    return {"message": "User deleted successfully"}