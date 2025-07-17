from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.tool import Tool
from app.schemas.tool import ToolCreate, ToolUpdate, ToolResponse
from app.services.tool_service import ToolService
import uuid

router = APIRouter()

@router.get("/", response_model=List[ToolResponse])
async def list_tools(
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    tool_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ToolService(db)
    tools = service.list_tools(
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
        tool_type=tool_type,
        is_active=is_active
    )
    return [ToolResponse.model_validate(tool) for tool in tools]

@router.post("/", response_model=ToolResponse, status_code=status.HTTP_201_CREATED)
async def create_tool(
    tool_data: ToolCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ToolService(db)
    tool = service.create_tool(
        organization_id=current_user.organization_id,
        tool_data=tool_data
    )
    return ToolResponse.model_validate(tool)

@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ToolService(db)
    tool = service.get_tool(
        tool_id=tool_id,
        organization_id=current_user.organization_id
    )
    
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found"
        )
    
    return ToolResponse.model_validate(tool)

@router.patch("/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: uuid.UUID,
    tool_data: ToolUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ToolService(db)
    tool = service.update_tool(
        tool_id=tool_id,
        organization_id=current_user.organization_id,
        tool_data=tool_data
    )
    
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found"
        )
    
    return ToolResponse.model_validate(tool)

@router.delete("/{tool_id}")
async def delete_tool(
    tool_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ToolService(db)
    success = service.delete_tool(
        tool_id=tool_id,
        organization_id=current_user.organization_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found"
        )
    
    return {"message": "Tool deleted successfully"}

@router.post("/{tool_id}/test")
async def test_tool(
    tool_id: uuid.UUID,
    test_data: dict = {},
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ToolService(db)
    result = await service.test_tool(
        tool_id=tool_id,
        organization_id=current_user.organization_id,
        test_data=test_data
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found"
        )
    
    return result