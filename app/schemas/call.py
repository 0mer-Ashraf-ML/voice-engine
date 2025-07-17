from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class CallCreate(BaseModel):
    type: str  # inbound, outbound, web
    assistant_id: Optional[uuid.UUID] = None
    phone_number_id: Optional[uuid.UUID] = None
    to_number: Optional[str] = None
    from_number: Optional[str] = None
    customer_info: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class CallUpdate(BaseModel):
    status: Optional[str] = None
    end_reason: Optional[str] = None
    transfer_destination: Optional[str] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    recording_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class CallResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    assistant_id: Optional[uuid.UUID] = None
    phone_number_id: Optional[uuid.UUID] = None
    type: str
    status: str
    direction: Optional[str] = None
    from_number: Optional[str] = None
    to_number: Optional[str] = None
    provider_call_id: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    transcript: Optional[str] = None
    recording_url: Optional[str] = None
    summary: Optional[str] = None
    end_reason: Optional[str] = None
    transfer_destination: Optional[str] = None
    cost_usd: float
    cost_breakdown: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    customer_info: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True