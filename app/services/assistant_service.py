from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List, Dict, Any
from app.models.assistant import Assistant, AssistantTool
from app.models.tool import Tool
from app.schemas.assistant import AgentCreate, AgentUpdate, AssistantSettings
from datetime import datetime, timezone
import uuid

class AssistantService:
    def __init__(self, db: Session):
        self.db = db
    
    def _assistant_to_agent_format(self, assistant: Assistant) -> Dict[str, Any]:
        """Convert database Assistant to clean Agent format"""
        
        # Create clean agent ID
        agent_id = f"assistant-{str(assistant.id).replace('-', '')[:12]}"
        
        # Map model names to clean format
        model_name = assistant.model_name.replace("gpt-", "").replace("claude-", "")
        
        return {
            "id": agent_id,
            "name": assistant.name,
            "description": assistant.description or assistant.first_message or "AI Assistant",
            "status": "active" if assistant.is_active else "inactive",
            "llm_provider": assistant.model_provider,
            "llm_model": model_name,
            "stt_provider": assistant.transcriber_provider,
            "stt_model": assistant.transcriber_model,
            "tts_provider": assistant.voice_provider,
            "voice_id": assistant.voice_id,
            "language": assistant.language,
            "prompt": assistant.system_prompt,
            "first_message": assistant.first_message,
            "tools": assistant.get_tools(),  # ✅ Use the new tools field
            "settings": {
                "temperature": assistant.model_temperature,
                "max_tokens": assistant.model_max_tokens,
                "conversation_timeout": assistant.conversation_timeout,
                "audio_sample_rate": assistant.audio_sample_rate,
                "audio_channels": assistant.audio_channels,
                "interruptions_enabled": assistant.interruptions_enabled,
                "voicemail_detection": assistant.voicemail_detection
            },
            "created_at": assistant.created_at,
            "updated_at": assistant.updated_at
        }
    
    def _agent_id_to_uuid(self, agent_id: str) -> Optional[uuid.UUID]:
        """Convert agent ID back to UUID"""
        try:
            if agent_id.startswith("assistant-"):
                hex_part = agent_id[10:]  # Remove "assistant-" prefix
                # Find the assistant by matching the hex prefix
                assistants = self.db.query(Assistant).all()
                for assistant in assistants:
                    if str(assistant.id).replace('-', '')[:12] == hex_part:
                        return assistant.id
            return None
        except:
            return None
    
    def list_agents(
        self, 
        organization_id: uuid.UUID, 
        limit: int = 100, 
        offset: int = 0,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """List assistants in clean agent format"""
        
        query = self.db.query(Assistant).filter(
            Assistant.organization_id == organization_id
        )
        
        if status:
            is_active = status == "active"
            query = query.filter(Assistant.is_active == is_active)
        
        total = query.count()
        assistants = query.order_by(Assistant.created_at.desc()).offset(offset).limit(limit).all()
        
        agents_dict = {}
        for assistant in assistants:
            agent_data = self._assistant_to_agent_format(assistant)
            agents_dict[agent_data["id"]] = agent_data
        
        return {
            "agents": agents_dict,
            "total": total,
            "page": (offset // limit) + 1,
            "per_page": limit
        }
    
    def create_agent(
        self, 
        organization_id: uuid.UUID, 
        agent_data: AgentCreate
    ) -> Dict[str, Any]:
        """Create new assistant"""
        
        # Handle settings
        settings = agent_data.settings or AssistantSettings()
        
        assistant = Assistant(
            organization_id=organization_id,
            name=agent_data.name,
            description=agent_data.description,
            first_message=agent_data.first_message,
            system_prompt=agent_data.prompt,
            model_provider=agent_data.llm_provider,
            model_name=self._normalize_model_name(agent_data.llm_model, agent_data.llm_provider),
            model_temperature=settings.temperature,
            model_max_tokens=settings.max_tokens,
            voice_provider=agent_data.tts_provider,
            voice_id=agent_data.voice_id,
            transcriber_provider=agent_data.stt_provider,
            transcriber_model=agent_data.stt_model,
            language=agent_data.language,
            conversation_timeout=settings.conversation_timeout,
            audio_sample_rate=settings.audio_sample_rate,
            audio_channels=settings.audio_channels,
            interruptions_enabled=settings.interruptions_enabled,
            voicemail_detection=settings.voicemail_detection,
            tools=agent_data.tools or []  # ✅ Set tools directly
        )
        
        self.db.add(assistant)
        self.db.commit()
        self.db.refresh(assistant)
        
        return {"agent": self._assistant_to_agent_format(assistant)}
    
    def get_agent(
        self, 
        agent_id: str, 
        organization_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """Get single assistant by agent ID"""
        
        uuid_id = self._agent_id_to_uuid(agent_id)
        if not uuid_id:
            return None
        
        assistant = self.db.query(Assistant).filter(
            Assistant.id == uuid_id,
            Assistant.organization_id == organization_id
        ).first()
        
        if not assistant:
            return None
        
        return {"agent": self._assistant_to_agent_format(assistant)}
    
    def update_agent(
        self,
        agent_id: str,
        organization_id: uuid.UUID,
        agent_data: AgentUpdate
    ) -> Optional[Dict[str, Any]]:
        """Update assistant"""
        
        uuid_id = self._agent_id_to_uuid(agent_id)
        if not uuid_id:
            return None
        
        assistant = self.db.query(Assistant).filter(
            Assistant.id == uuid_id,
            Assistant.organization_id == organization_id
        ).first()
        
        if not assistant:
            return None
        
        # Update basic fields
        if agent_data.name is not None:
            assistant.name = agent_data.name
        if agent_data.description is not None:
            assistant.description = agent_data.description
        if agent_data.llm_provider is not None:
            assistant.model_provider = agent_data.llm_provider
        if agent_data.llm_model is not None:
            assistant.model_name = self._normalize_model_name(agent_data.llm_model, assistant.model_provider)
        if agent_data.stt_provider is not None:
            assistant.transcriber_provider = agent_data.stt_provider
        if agent_data.stt_model is not None:
            assistant.transcriber_model = agent_data.stt_model
        if agent_data.tts_provider is not None:
            assistant.voice_provider = agent_data.tts_provider
        if agent_data.voice_id is not None:
            assistant.voice_id = agent_data.voice_id
        if agent_data.language is not None:
            assistant.language = agent_data.language
        if agent_data.prompt is not None:
            assistant.system_prompt = agent_data.prompt
        if agent_data.first_message is not None:
            assistant.first_message = agent_data.first_message
        if agent_data.status is not None:
            assistant.is_active = agent_data.status == "active"
        
        # ✅ Update tools directly
        if agent_data.tools is not None:
            assistant.set_tools(agent_data.tools)
        
        # Update settings
        if agent_data.settings:
            assistant.model_temperature = agent_data.settings.temperature
            assistant.model_max_tokens = agent_data.settings.max_tokens
            assistant.conversation_timeout = agent_data.settings.conversation_timeout
            assistant.audio_sample_rate = agent_data.settings.audio_sample_rate
            assistant.audio_channels = agent_data.settings.audio_channels
            assistant.interruptions_enabled = agent_data.settings.interruptions_enabled
            assistant.voicemail_detection = agent_data.settings.voicemail_detection
        
        assistant.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(assistant)
        
        return {"agent": self._assistant_to_agent_format(assistant)}
    
    def delete_agent(
        self, 
        agent_id: str, 
        organization_id: uuid.UUID
    ) -> bool:
        """Delete assistant"""
        
        uuid_id = self._agent_id_to_uuid(agent_id)
        if not uuid_id:
            return False
        
        assistant = self.db.query(Assistant).filter(
            Assistant.id == uuid_id,
            Assistant.organization_id == organization_id
        ).first()
        
        if not assistant:
            return False
        
        # Remove tool associations first (if using relationship table)
        self.db.query(AssistantTool).filter(
            AssistantTool.assistant_id == assistant.id
        ).delete()
        
        # Delete assistant
        self.db.delete(assistant)
        self.db.commit()
        
        return True
    
    def attach_tools(
        self,
        agent_id: str,
        organization_id: uuid.UUID,
        tool_names: List[str]
    ) -> bool:
        """Attach tools to assistant"""
        
        uuid_id = self._agent_id_to_uuid(agent_id)
        if not uuid_id:
            return False
        
        assistant = self.db.query(Assistant).filter(
            Assistant.id == uuid_id,
            Assistant.organization_id == organization_id
        ).first()
        
        if not assistant:
            return False
        
        # ✅ Validate that tools exist in the organization
        existing_tools = self.db.query(Tool).filter(
            Tool.organization_id == organization_id,
            Tool.name.in_(tool_names),
            Tool.is_active == True
        ).all()
        
        existing_tool_names = [tool.name for tool in existing_tools]
        
        # ✅ Add tools directly to the JSON field
        current_tools = assistant.get_tools()
        
        for tool_name in existing_tool_names:
            if tool_name not in current_tools:
                assistant.add_tool(tool_name)
        
        assistant.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        
        return True
    
    def detach_tools(
        self,
        agent_id: str,
        organization_id: uuid.UUID,
        tool_names: List[str]
    ) -> bool:
        """Detach tools from assistant"""
        
        uuid_id = self._agent_id_to_uuid(agent_id)
        if not uuid_id:
            return False
        
        assistant = self.db.query(Assistant).filter(
            Assistant.id == uuid_id,
            Assistant.organization_id == organization_id
        ).first()
        
        if not assistant:
            return False
        
        # ✅ Remove tools directly from the JSON field
        for tool_name in tool_names:
            assistant.remove_tool(tool_name)
        
        assistant.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        
        return True
    
    def get_available_tools(
        self,
        organization_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """Get all available tools for the organization"""
        
        tools = self.db.query(Tool).filter(
            Tool.organization_id == organization_id,
            Tool.is_active == True
        ).all()
        
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "type": tool.type,
                "id": str(tool.id)
            }
            for tool in tools
        ]
    
    def get_agent_tools_details(
        self,
        agent_id: str,
        organization_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """Get detailed information about tools attached to an agent"""
        
        uuid_id = self._agent_id_to_uuid(agent_id)
        if not uuid_id:
            return []
        
        assistant = self.db.query(Assistant).filter(
            Assistant.id == uuid_id,
            Assistant.organization_id == organization_id
        ).first()
        
        if not assistant:
            return []
        
        tool_names = assistant.get_tools()
        
        if not tool_names:
            return []
        
        # Get detailed tool information
        tools = self.db.query(Tool).filter(
            Tool.organization_id == organization_id,
            Tool.name.in_(tool_names),
            Tool.is_active == True
        ).all()
        
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "type": tool.type,
                "webhook_url": tool.webhook_url,
                "function_schema": tool.function_schema,
                "id": str(tool.id)
            }
            for tool in tools
        ]
    
    def _normalize_model_name(self, model_name: str, provider: str) -> str:
        """Convert clean model name back to full name"""
        
        if provider == "openai":
            if model_name in ["4o", "4o-mini", "4-turbo"]:
                return f"gpt-{model_name}"
            return model_name
        elif provider == "anthropic":
            if model_name in ["opus", "sonnet", "haiku"]:
                return f"claude-3-{model_name}-20240229"
            return model_name
        
        return model_name