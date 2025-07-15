from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.assistant import Assistant, AssistantTool
from app.models.tool import Tool
from app.schemas.assistant import AssistantCreate, AssistantUpdate, AssistantToolCreate
from datetime import datetime, timezone
import uuid

class AssistantService:
    def __init__(self, db: Session):
        self.db = db
    
    def list_assistants(
        self, 
        organization_id: uuid.UUID, 
        limit: int = 100, 
        offset: int = 0,
        is_active: Optional[bool] = None
    ) -> List[Assistant]:
        query = self.db.query(Assistant).filter(
            Assistant.organization_id == organization_id
        )
        
        if is_active is not None:
            query = query.filter(Assistant.is_active == is_active)
        
        return query.offset(offset).limit(limit).all()
    
    def create_assistant(
        self, 
        organization_id: uuid.UUID, 
        assistant_data: AssistantCreate
    ) -> Assistant:
        assistant = Assistant(
            organization_id=organization_id,
            **assistant_data.model_dump()
        )
        
        self.db.add(assistant)
        self.db.commit()
        self.db.refresh(assistant)
        
        return assistant
    
    def get_assistant(
        self, 
        assistant_id: uuid.UUID, 
        organization_id: uuid.UUID
    ) -> Optional[Assistant]:
        return self.db.query(Assistant).filter(
            Assistant.id == assistant_id,
            Assistant.organization_id == organization_id
        ).first()
    
    def update_assistant(
        self,
        assistant_id: uuid.UUID,
        organization_id: uuid.UUID,
        assistant_data: AssistantUpdate
    ) -> Optional[Assistant]:
        assistant = self.get_assistant(assistant_id, organization_id)
        
        if not assistant:
            return None
        
        update_data = assistant_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(assistant, field, value)
        
        assistant.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(assistant)
        
        return assistant
    
    def delete_assistant(
        self, 
        assistant_id: uuid.UUID, 
        organization_id: uuid.UUID
    ) -> bool:
        assistant = self.get_assistant(assistant_id, organization_id)
        
        if not assistant:
            return False
        
        self.db.delete(assistant)
        self.db.commit()
        
        return True
    
    def add_tool_to_assistant(
        self,
        assistant_id: uuid.UUID,
        organization_id: uuid.UUID,
        tool_data: AssistantToolCreate
    ) -> Optional[AssistantTool]:
        # Verify assistant exists and belongs to organization
        assistant = self.get_assistant(assistant_id, organization_id)
        if not assistant:
            return None
        
        # Verify tool exists and belongs to organization
        tool = self.db.query(Tool).filter(
            Tool.id == tool_data.tool_id,
            Tool.organization_id == organization_id
        ).first()
        
        if not tool:
            return None
        
        # Check if tool is already added
        existing = self.db.query(AssistantTool).filter(
            AssistantTool.assistant_id == assistant_id,
            AssistantTool.tool_id == tool_data.tool_id
        ).first()
        
        if existing:
            return existing
        
        assistant_tool = AssistantTool(
            assistant_id=assistant_id,
            tool_id=tool_data.tool_id,
            is_enabled=tool_data.is_enabled
        )
        
        self.db.add(assistant_tool)
        self.db.commit()
        self.db.refresh(assistant_tool)
        
        return assistant_tool
    
    def remove_tool_from_assistant(
        self,
        assistant_id: uuid.UUID,
        tool_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> bool:
        # Verify assistant belongs to organization
        assistant = self.get_assistant(assistant_id, organization_id)
        if not assistant:
            return False
        
        assistant_tool = self.db.query(AssistantTool).filter(
            AssistantTool.assistant_id == assistant_id,
            AssistantTool.tool_id == tool_id
        ).first()
        
        if not assistant_tool:
            return False
        
        self.db.delete(assistant_tool)
        self.db.commit()
        
        return True
    
    def list_assistant_tools(
        self,
        assistant_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> List[AssistantTool]:
        # Verify assistant belongs to organization
        assistant = self.get_assistant(assistant_id, organization_id)
        if not assistant:
            return []
        
        return self.db.query(AssistantTool).filter(
            AssistantTool.assistant_id == assistant_id
        ).all()