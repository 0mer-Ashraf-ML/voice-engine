from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.call import Call
from app.schemas.call import CallCreate, CallUpdate, CallResponse
from app.services.call_service import CallService
from app.websocket import manager
import uuid
import json

router = APIRouter()

@router.get("/", response_model=List[CallResponse])
async def list_calls(
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    assistant_id: Optional[uuid.UUID] = Query(None),
    phone_number_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = CallService(db)
    calls = service.list_calls(
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
        assistant_id=assistant_id,
        phone_number_id=phone_number_id,
        status=status
    )
    return [CallResponse.model_validate(call) for call in calls]

@router.post("/", response_model=CallResponse, status_code=status.HTTP_201_CREATED)
async def create_call(
    call_data: CallCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = CallService(db)
    call = service.create_call(
        organization_id=current_user.organization_id,
        call_data=call_data
    )
    return CallResponse.model_validate(call)

@router.get("/{call_id}", response_model=CallResponse)
async def get_call(
    call_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = CallService(db)
    call = service.get_call(
        call_id=call_id,
        organization_id=current_user.organization_id
    )
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    return CallResponse.model_validate(call)

@router.patch("/{call_id}", response_model=CallResponse)
async def update_call(
    call_id: uuid.UUID,
    call_data: CallUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = CallService(db)
    call = service.update_call(
        call_id=call_id,
        organization_id=current_user.organization_id,
        call_data=call_data
    )
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    return CallResponse.model_validate(call)

@router.delete("/{call_id}")
async def delete_call(
    call_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = CallService(db)
    success = service.delete_call(
        call_id=call_id,
        organization_id=current_user.organization_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    return {"message": "Call deleted successfully"}

@router.websocket("/ws/{call_id}")
async def websocket_endpoint(websocket: WebSocket, call_id: str):
    connection_id = str(uuid.uuid4())
    await manager.connect(websocket, connection_id)
    manager.register_call(call_id, connection_id)
    
    try:
        await manager.broadcast_call_status(call_id, "connected")
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "start_call":
                await manager.broadcast_call_status(call_id, "in-progress")
            elif message.get("type") == "end_call":
                await manager.broadcast_call_status(call_id, "completed")
                break
            elif message.get("type") == "transcript":
                await manager.broadcast_transcript(
                    call_id, 
                    message.get("text", ""), 
                    message.get("is_user", True)
                )
    
    except WebSocketDisconnect:
        manager.disconnect(connection_id)
        await manager.broadcast_call_status(call_id, "disconnected")