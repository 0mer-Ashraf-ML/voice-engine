from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

class SquadCreate(BaseModel):
    name: str
    description: Optional[str] = None
    routing_strategy: str = "round_robin"
    max_concurrent_calls: int = 10
    overflow_strategy: str = "queue"
    working_hours: Optional[Dict[str, Any]] = None

class SquadUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    routing_strategy: Optional[str] = None
    max_concurrent_calls: Optional[int] = None
    overflow_strategy: Optional[str] = None
    working_hours: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class SquadResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: Optional[str] = None
    routing_strategy: str
    max_concurrent_calls: int
    overflow_strategy: str
    working_hours: Optional[Dict[str, Any]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class SquadAssistantCreate(BaseModel):
    assistant_id: uuid.UUID
    priority: int = 1
    max_concurrent_calls: int = 5
    is_active: bool = True

class SquadAssistantResponse(BaseModel):
    id: uuid.UUID
    squad_id: uuid.UUID
    assistant_id: uuid.UUID
    priority: int
    is_active: bool
    max_concurrent_calls: int
    created_at: datetime
    
    class Config:
        from_attributes = True