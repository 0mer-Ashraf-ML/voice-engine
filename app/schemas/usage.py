from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class UsageRecordResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    call_id: Optional[uuid.UUID] = None
    usage_type: str
    quantity: float
    unit: str
    unit_cost: float
    total_cost: float
    provider: Optional[str] = None
    model_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    billing_period: str
    is_billed: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class UsageSummaryResponse(BaseModel):
    organization_id: uuid.UUID
    billing_period: str
    total_cost: float
    breakdown: Dict[str, float]  # {llm: 10.50, tts: 5.25, stt: 2.10}
    total_calls: int
    total_minutes: float
    
class UsageStatsResponse(BaseModel):
    today: UsageSummaryResponse
    this_month: UsageSummaryResponse
    last_month: UsageSummaryResponse