from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class ToolCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str  # webhook, function, api
    webhook_url: Optional[str] = None
    webhook_method: str = "POST"
    webhook_headers: Optional[Dict[str, Any]] = None
    webhook_timeout: int = 30
    function_schema: Optional[Dict[str, Any]] = None
    retry_attempts: int = 3

class ToolUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_method: Optional[str] = None
    webhook_headers: Optional[Dict[str, Any]] = None
    webhook_timeout: Optional[int] = None
    function_schema: Optional[Dict[str, Any]] = None
    retry_attempts: Optional[int] = None
    is_active: Optional[bool] = None

class ToolResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: Optional[str] = None
    type: str
    webhook_url: Optional[str] = None
    webhook_method: str
    webhook_headers: Optional[Dict[str, Any]] = None
    webhook_timeout: int
    function_schema: Optional[Dict[str, Any]] = None
    is_active: bool
    retry_attempts: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True