from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.phone_number import PhoneNumber
from app.schemas.phone_number import PhoneNumberCreate, PhoneNumberUpdate, PhoneNumberResponse
from app.services.phone_service import PhoneService
import uuid

router = APIRouter()

@router.get("/", response_model=List[PhoneNumberResponse])
async def list_phone_numbers(
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    provider: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PhoneService(db)
    phone_numbers = service.list_phone_numbers(
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
        provider=provider,
        is_active=is_active
    )
    return [PhoneNumberResponse.model_validate(phone) for phone in phone_numbers]

@router.post("/", response_model=PhoneNumberResponse, status_code=status.HTTP_201_CREATED)
async def create_phone_number(
    phone_data: PhoneNumberCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PhoneService(db)
    phone_number = service.create_phone_number(
        organization_id=current_user.organization_id,
        phone_data=phone_data
    )
    return PhoneNumberResponse.model_validate(phone_number)

@router.get("/{phone_number_id}", response_model=PhoneNumberResponse)
async def get_phone_number(
    phone_number_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PhoneService(db)
    phone_number = service.get_phone_number(
        phone_number_id=phone_number_id,
        organization_id=current_user.organization_id
    )
    
    if not phone_number:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not found"
        )
    
    return PhoneNumberResponse.model_validate(phone_number)

@router.patch("/{phone_number_id}", response_model=PhoneNumberResponse)
async def update_phone_number(
    phone_number_id: uuid.UUID,
    phone_data: PhoneNumberUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PhoneService(db)
    phone_number = service.update_phone_number(
        phone_number_id=phone_number_id,
        organization_id=current_user.organization_id,
        phone_data=phone_data
    )
    
    if not phone_number:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not found"
        )
    
    return PhoneNumberResponse.model_validate(phone_number)

@router.delete("/{phone_number_id}")
async def delete_phone_number(
    phone_number_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PhoneService(db)
    success = service.delete_phone_number(
        phone_number_id=phone_number_id,
        organization_id=current_user.organization_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not found"
        )
    
    return {"message": "Phone number deleted successfully"}

@router.post("/purchase")
async def purchase_phone_number(
    area_code: str = Query(...),
    provider: str = Query("twilio"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PhoneService(db)
    phone_number = service.purchase_phone_number(
        organization_id=current_user.organization_id,
        area_code=area_code,
        provider=provider
    )
    
    if not phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to purchase phone number"
        )
    
    return PhoneNumberResponse.model_validate(phone_number)