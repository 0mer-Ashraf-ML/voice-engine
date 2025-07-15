from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.assistant import Assistant, AssistantTool
from app.schemas.assistant import AssistantCreate, AssistantUpdate, AssistantResponse, AssistantToolCreate
from app.services.assistant_service import AssistantService
import uuid

router = APIRouter()

@router.get("/", response_model=List[AssistantResponse])
async def list_assistants(
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AssistantService(db)
    assistants = service.list_assistants(
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset
    )
    return [AssistantResponse.model_validate(assistant) for assistant in assistants]

@router.post("/", response_model=AssistantResponse, status_code=status.HTTP_201_CREATED)
async def create_assistant(
    assistant_data: AssistantCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AssistantService(db)
    assistant = service.create_assistant(
        organization_id=current_user.organization_id,
        assistant_data=assistant_data
    )
    return AssistantResponse.model_validate(assistant)

@router.get("/{assistant_id}", response_model=AssistantResponse)
async def get_assistant(
    assistant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AssistantService(db)
    assistant = service.get_assistant(
        assistant_id=assistant_id,
        organization_id=current_user.organization_id
    )
    
    if not assistant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assistant not found"
        )
    
    return AssistantResponse.model_validate(assistant)

@router.patch("/{assistant_id}", response_model=AssistantResponse)
async def update_assistant(
    assistant_id: uuid.UUID,
    assistant_data: AssistantUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AssistantService(db)
    assistant = service.update_assistant(
        assistant_id=assistant_id,
        organization_id=current_user.organization_id,
        assistant_data=assistant_data
    )
    
    if not assistant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assistant not found"
        )
    
    return AssistantResponse.model_validate(assistant)

@router.delete("/{assistant_id}")
async def delete_assistant(
    assistant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AssistantService(db)
    success = service.delete_assistant(
        assistant_id=assistant_id,
        organization_id=current_user.organization_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assistant not found"
        )
    
    return {"message": "Assistant deleted successfully"}

@router.post("/{assistant_id}/tools")
async def add_tool_to_assistant(
    assistant_id: uuid.UUID,
    tool_data: AssistantToolCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AssistantService(db)
    assistant_tool = service.add_tool_to_assistant(
        assistant_id=assistant_id,
        organization_id=current_user.organization_id,
        tool_data=tool_data
    )
    
    if not assistant_tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assistant or tool not found"
        )
    
    return {"message": "Tool added to assistant successfully"}

@router.delete("/{assistant_id}/tools/{tool_id}")
async def remove_tool_from_assistant(
    assistant_id: uuid.UUID,
    tool_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AssistantService(db)
    success = service.remove_tool_from_assistant(
        assistant_id=assistant_id,
        tool_id=tool_id,
        organization_id=current_user.organization_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assistant tool not found"
        )
    
    return {"message": "Tool removed from assistant successfully"}