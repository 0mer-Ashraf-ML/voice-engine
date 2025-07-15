from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.squad import Squad, SquadAssistant
from app.schemas.squad import SquadCreate, SquadUpdate, SquadResponse, SquadAssistantCreate, SquadAssistantResponse
from app.services.squad_service import SquadService
import uuid

router = APIRouter()

@router.get("/", response_model=List[SquadResponse])
async def list_squads(
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = SquadService(db)
    squads = service.list_squads(
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
        is_active=is_active
    )
    return [SquadResponse.model_validate(squad) for squad in squads]

@router.post("/", response_model=SquadResponse, status_code=status.HTTP_201_CREATED)
async def create_squad(
    squad_data: SquadCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = SquadService(db)
    squad = service.create_squad(
        organization_id=current_user.organization_id,
        squad_data=squad_data
    )
    return SquadResponse.model_validate(squad)

@router.get("/{squad_id}", response_model=SquadResponse)
async def get_squad(
    squad_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = SquadService(db)
    squad = service.get_squad(
        squad_id=squad_id,
        organization_id=current_user.organization_id
    )
    
    if not squad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Squad not found"
        )
    
    return SquadResponse.model_validate(squad)

@router.patch("/{squad_id}", response_model=SquadResponse)
async def update_squad(
    squad_id: uuid.UUID,
    squad_data: SquadUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = SquadService(db)
    squad = service.update_squad(
        squad_id=squad_id,
        organization_id=current_user.organization_id,
        squad_data=squad_data
    )
    
    if not squad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Squad not found"
        )
    
    return SquadResponse.model_validate(squad)

@router.delete("/{squad_id}")
async def delete_squad(
    squad_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = SquadService(db)
    success = service.delete_squad(
        squad_id=squad_id,
        organization_id=current_user.organization_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Squad not found"
        )
    
    return {"message": "Squad deleted successfully"}

@router.get("/{squad_id}/assistants", response_model=List[SquadAssistantResponse])
async def list_squad_assistants(
    squad_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = SquadService(db)
    assistants = service.list_squad_assistants(
        squad_id=squad_id,
        organization_id=current_user.organization_id
    )
    return [SquadAssistantResponse.model_validate(assistant) for assistant in assistants]

@router.post("/{squad_id}/assistants")
async def add_assistant_to_squad(
    squad_id: uuid.UUID,
    assistant_data: SquadAssistantCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = SquadService(db)
    squad_assistant = service.add_assistant_to_squad(
        squad_id=squad_id,
        organization_id=current_user.organization_id,
        assistant_data=assistant_data
    )
    
    if not squad_assistant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Squad or assistant not found"
        )
    
    return {"message": "Assistant added to squad successfully"}

@router.delete("/{squad_id}/assistants/{assistant_id}")
async def remove_assistant_from_squad(
    squad_id: uuid.UUID,
    assistant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = SquadService(db)
    success = service.remove_assistant_from_squad(
        squad_id=squad_id,
        assistant_id=assistant_id,
        organization_id=current_user.organization_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Squad assistant not found"
        )
    
    return {"message": "Assistant removed from squad successfully"}