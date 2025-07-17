from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.call import Call
from app.models.assistant import Assistant
from app.models.phone_number import PhoneNumber
from app.schemas.call import CallCreate, CallUpdate
from app.websocket import manager
from datetime import datetime, timezone
import uuid
import asyncio

class CallService:
    def __init__(self, db: Session):
        self.db = db
    
    def list_calls(
        self, 
        organization_id: uuid.UUID, 
        limit: int = 100, 
        offset: int = 0,
        assistant_id: Optional[uuid.UUID] = None,
        phone_number_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None
    ) -> List[Call]:
        query = self.db.query(Call).filter(
            Call.organization_id == organization_id
        )
        
        if assistant_id:
            query = query.filter(Call.assistant_id == assistant_id)
        
        if phone_number_id:
            query = query.filter(Call.phone_number_id == phone_number_id)
        
        if status:
            query = query.filter(Call.status == status)
        
        return query.order_by(Call.created_at.desc()).offset(offset).limit(limit).all()
    
    def create_call(
        self, 
        organization_id: uuid.UUID, 
        call_data: CallCreate
    ) -> Call:
        # Validate assistant belongs to organization
        if call_data.assistant_id:
            assistant = self.db.query(Assistant).filter(
                Assistant.id == call_data.assistant_id,
                Assistant.organization_id == organization_id
            ).first()
            
            if not assistant:
                raise ValueError("Assistant not found")
        
        # Validate phone number belongs to organization
        if call_data.phone_number_id:
            phone_number = self.db.query(PhoneNumber).filter(
                PhoneNumber.id == call_data.phone_number_id,
                PhoneNumber.organization_id == organization_id
            ).first()
            
            if not phone_number:
                raise ValueError("Phone number not found")
        
        call = Call(
            organization_id=organization_id,
            **call_data.model_dump()
        )
        
        self.db.add(call)
        self.db.commit()
        self.db.refresh(call)
        
        return call
    
    def get_call(
        self, 
        call_id: uuid.UUID, 
        organization_id: uuid.UUID
    ) -> Optional[Call]:
        return self.db.query(Call).filter(
            Call.id == call_id,
            Call.organization_id == organization_id
        ).first()
    
    def update_call(
        self,
        call_id: uuid.UUID,
        organization_id: uuid.UUID,
        call_data: CallUpdate
    ) -> Optional[Call]:
        call = self.get_call(call_id, organization_id)
        
        if not call:
            return None
        
        update_data = call_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(call, field, value)
        
        call.updated_at = datetime.now(timezone.utc)
        
        # Calculate duration if call ended
        if call_data.status == "completed" and call.started_at and not call.ended_at:
            call.ended_at = datetime.now(timezone.utc)
            duration = (call.ended_at - call.started_at).total_seconds()
            call.duration_seconds = int(duration)
        
        self.db.commit()
        self.db.refresh(call)
        
        # Broadcast status update via WebSocket
        if call_data.status:
            asyncio.create_task(
                manager.broadcast_call_status(str(call_id), call_data.status)
            )
        
        return call
    
    def delete_call(
        self, 
        call_id: uuid.UUID, 
        organization_id: uuid.UUID
    ) -> bool:
        call = self.get_call(call_id, organization_id)
        
        if not call:
            return False
        
        self.db.delete(call)
        self.db.commit()
        
        return True
    
    def start_call(
        self,
        call_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> Optional[Call]:
        call = self.get_call(call_id, organization_id)
        
        if not call:
            return None
        
        call.status = "in-progress"
        call.started_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(call)
        
        return call
    
    def end_call(
        self,
        call_id: uuid.UUID,
        organization_id: uuid.UUID,
        end_reason: str = "completed"
    ) -> Optional[Call]:
        call = self.get_call(call_id, organization_id)
        
        if not call:
            return None
        
        call.status = "completed"
        call.ended_at = datetime.now(timezone.utc)
        call.end_reason = end_reason
        
        if call.started_at:
            duration = (call.ended_at - call.started_at).total_seconds()
            call.duration_seconds = int(duration)
        
        self.db.commit()
        self.db.refresh(call)
        
        return call
    
    def get_call_analytics(
        self,
        organization_id: uuid.UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        query = self.db.query(Call).filter(
            Call.organization_id == organization_id
        )
        
        if start_date:
            query = query.filter(Call.created_at >= start_date)
        
        if end_date:
            query = query.filter(Call.created_at <= end_date)
        
        calls = query.all()
        
        total_calls = len(calls)
        completed_calls = len([c for c in calls if c.status == "completed"])
        total_duration = sum([c.duration_seconds or 0 for c in calls])
        total_cost = sum([c.cost_usd for c in calls])
        
        avg_duration = total_duration / total_calls if total_calls > 0 else 0
        completion_rate = (completed_calls / total_calls * 100) if total_calls > 0 else 0
        
        return {
            "total_calls": total_calls,
            "completed_calls": completed_calls,
            "total_duration_seconds": total_duration,
            "average_duration_seconds": avg_duration,
            "completion_rate_percent": completion_rate,
            "total_cost_usd": total_cost
        }