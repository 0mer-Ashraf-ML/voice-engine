from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.squad import Squad, SquadAssistant
from app.models.assistant import Assistant
from app.schemas.squad import SquadCreate, SquadUpdate, SquadAssistantCreate
from datetime import datetime, timezone
import uuid

class SquadService:
    def __init__(self, db: Session):
        self.db = db
    
    def list_squads(
        self, 
        organization_id: uuid.UUID, 
        limit: int = 100, 
        offset: int = 0,
        is_active: Optional[bool] = None
    ) -> List[Squad]:
        query = self.db.query(Squad).filter(
            Squad.organization_id == organization_id
        )
        
        if is_active is not None:
            query = query.filter(Squad.is_active == is_active)
        
        return query.offset(offset).limit(limit).all()
    
    def create_squad(
        self, 
        organization_id: uuid.UUID, 
        squad_data: SquadCreate
    ) -> Squad:
        squad = Squad(
            organization_id=organization_id,
            **squad_data.model_dump()
        )
        
        self.db.add(squad)
        self.db.commit()
        self.db.refresh(squad)
        
        return squad
    
    def get_squad(
        self, 
        squad_id: uuid.UUID, 
        organization_id: uuid.UUID
    ) -> Optional[Squad]:
        return self.db.query(Squad).filter(
            Squad.id == squad_id,
            Squad.organization_id == organization_id
        ).first()
    
    def update_squad(
        self,
        squad_id: uuid.UUID,
        organization_id: uuid.UUID,
        squad_data: SquadUpdate
    ) -> Optional[Squad]:
        squad = self.get_squad(squad_id, organization_id)
        
        if not squad:
            return None
        
        update_data = squad_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(squad, field, value)
        
        squad.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(squad)
        
        return squad
    
    def delete_squad(
        self, 
        squad_id: uuid.UUID, 
        organization_id: uuid.UUID
    ) -> bool:
        squad = self.get_squad(squad_id, organization_id)
        
        if not squad:
            return False
        
        self.db.delete(squad)
        self.db.commit()
        
        return True
    
    def list_squad_assistants(
        self,
        squad_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> List[SquadAssistant]:
        # Verify squad belongs to organization
        squad = self.get_squad(squad_id, organization_id)
        if not squad:
            return []
        
        return self.db.query(SquadAssistant).filter(
            SquadAssistant.squad_id == squad_id,
            SquadAssistant.is_active == True
        ).order_by(SquadAssistant.priority).all()
    
    def add_assistant_to_squad(
        self,
        squad_id: uuid.UUID,
        organization_id: uuid.UUID,
        assistant_data: SquadAssistantCreate
    ) -> Optional[SquadAssistant]:
        # Verify squad exists and belongs to organization
        squad = self.get_squad(squad_id, organization_id)
        if not squad:
            return None
        
        # Verify assistant exists and belongs to organization
        assistant = self.db.query(Assistant).filter(
            Assistant.id == assistant_data.assistant_id,
            Assistant.organization_id == organization_id
        ).first()
        
        if not assistant:
            return None
        
        # Check if assistant is already in squad
        existing = self.db.query(SquadAssistant).filter(
            SquadAssistant.squad_id == squad_id,
            SquadAssistant.assistant_id == assistant_data.assistant_id
        ).first()
        
        if existing:
            return existing
        
        squad_assistant = SquadAssistant(
            squad_id=squad_id,
            **assistant_data.model_dump()
        )
        
        self.db.add(squad_assistant)
        self.db.commit()
        self.db.refresh(squad_assistant)
        
        return squad_assistant
    
    def remove_assistant_from_squad(
        self,
        squad_id: uuid.UUID,
        assistant_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> bool:
        # Verify squad belongs to organization
        squad = self.get_squad(squad_id, organization_id)
        if not squad:
            return False
        
        squad_assistant = self.db.query(SquadAssistant).filter(
            SquadAssistant.squad_id == squad_id,
            SquadAssistant.assistant_id == assistant_id
        ).first()
        
        if not squad_assistant:
            return False
        
        self.db.delete(squad_assistant)
        self.db.commit()
        
        return True
    
    def get_next_available_assistant(
        self,
        squad_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> Optional[Assistant]:
        # Verify squad belongs to organization
        squad = self.get_squad(squad_id, organization_id)
        if not squad:
            return None
        
        # Get squad assistants ordered by priority
        squad_assistants = self.list_squad_assistants(squad_id, organization_id)
        
        for squad_assistant in squad_assistants:
            # Check if assistant is available (not at max concurrent calls)
            # This is a simplified check - in production you'd track active calls
            assistant = self.db.query(Assistant).filter(
                Assistant.id == squad_assistant.assistant_id,
                Assistant.is_active == True
            ).first()
            
            if assistant:
                return assistant
        
        return None
    
    def get_squad_stats(
        self,
        squad_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> dict:
        squad = self.get_squad(squad_id, organization_id)
        if not squad:
            return {}
        
        squad_assistants = self.list_squad_assistants(squad_id, organization_id)
        
        return {
            "squad_id": str(squad_id),
            "squad_name": squad.name,
            "total_assistants": len(squad_assistants),
            "active_assistants": len([sa for sa in squad_assistants if sa.is_active]),
            "routing_strategy": squad.routing_strategy,
            "max_concurrent_calls": squad.max_concurrent_calls
        }