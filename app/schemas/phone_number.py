from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class PhoneNumberCreate(BaseModel):
    phone_number: str
    country_code: str
    area_code: Optional[str] = None
    provider: str
    name: Optional[str] = None
    inbound_webhook_url: Optional[str] = None
    status_webhook_url: Optional[str] = None
    voice_enabled: bool = True
    sms_enabled: bool = False

class PhoneNumberUpdate(BaseModel):
    name: Optional[str] = None
    inbound_webhook_url: Optional[str] = None
    status_webhook_url: Optional[str] = None
    voice_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    is_active: Optional[bool] = None

class PhoneNumberResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    phone_number: str
    country_code: str
    area_code: Optional[str] = None
    formatted_number: str
    provider: str
    provider_id: str
    provider_config: Optional[Dict[str, Any]] = None
    name: Optional[str] = None
    is_active: bool
    inbound_webhook_url: Optional[str] = None
    status_webhook_url: Optional[str] = None
    voice_enabled: bool
    sms_enabled: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True