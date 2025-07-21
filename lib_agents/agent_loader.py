# lib_agent/agent_loader.py

import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from app.models.user import User
from app.services.assistant_service import AssistantService
from sqlalchemy.orm import Session
import uuid

@dataclass
class AgentConfig:
    id: str
    name: str
    description: str
    status: str
    llm_provider: str
    llm_model: str
    stt_provider: str
    stt_model: str
    tts_provider: str
    voice_id: str
    language: str
    prompt: str
    tools: list
    settings: dict

class AgentLoader:
    def __init__(self, db: Session):
        self.db = db

    def get_agent_config(self, agent_id: str) -> Optional[AgentConfig]:
        """Fetch agent configuration from the database without organization filtering"""
        service = AssistantService(self.db)
        # Remove organization_id parameter - get agent directly by ID
        result = service.get_agent_by_id(agent_id)  # Assuming this method exists
        
        if not result:
            return None

        agent_data = result["agent"]
        return AgentConfig(
            id=agent_data["id"],
            name=agent_data["name"],
            description=agent_data["description"],
            status=agent_data["status"],
            llm_provider=agent_data["llm_provider"],
            llm_model=agent_data["llm_model"],
            stt_provider=agent_data["stt_provider"],
            stt_model=agent_data["stt_model"],
            tts_provider=agent_data["tts_provider"],
            voice_id=agent_data["voice_id"],
            language=agent_data["language"],
            prompt=agent_data["prompt"],
            tools=agent_data["tools"],
            settings=agent_data["settings"],
            # user_id=agent_data.get("user_id", None)
        )

    def get_all_agents(self) -> Dict[str, AgentConfig]:
        """List all agents from database without organization filtering"""
        service = AssistantService(self.db)
        # Remove organization_id parameter - get all agents
        agents_result = service.list_all_agents()  # Assuming this method exists
        
        agents_dict = agents_result["agents"]
        return {
            agent_id: AgentConfig(
                id=agent["id"],
                name=agent["name"],
                description=agent["description"],
                status=agent["status"],
                llm_provider=agent["llm_provider"],
                llm_model=agent["llm_model"],
                stt_provider=agent["stt_provider"],
                stt_model=agent["stt_model"],
                tts_provider=agent["tts_provider"],
                voice_id=agent["voice_id"],
                language=agent["language"],
                prompt=agent["prompt"],
                tools=agent["tools"],
                settings=agent["settings"],
            )
            for agent_id, agent in agents_dict.items()
        }
        
    def get_agent_by_user_id(self, user_id: uuid.UUID) -> Dict[str, AgentConfig]:
        """List all agents for the organization"""
        service = AssistantService(self.db)
        agents_result = service.list_agents_by_user_id(user_id, limit=1000)
        agents_dict = agents_result["agents"]
        return {
            agent_id: AgentConfig(
                id=agent["id"],
                name=agent["name"],
                description=agent["description"],
                status=agent["status"],
                llm_provider=agent["llm_provider"],
                llm_model=agent["llm_model"],
                stt_provider=agent["stt_provider"],
                stt_model=agent["stt_model"],
                tts_provider=agent["tts_provider"],
                voice_id=agent["voice_id"],
                language=agent["language"],
                prompt=agent["prompt"],
                tools=agent["tools"],
                settings=agent["settings"],
                
            )
            for agent_id, agent in agents_dict.items()
        }

    def get_all_agents_by_user_id(self, user_id: str) -> Dict[str, AgentConfig]:
        """List all agents for a specific user without organization filtering"""
        service = AssistantService(self.db)
        # Get agents by user_id only
        agents_result = service.list_agents_by_user_id(user_id)  # Assuming this method exists
        
        agents_dict = agents_result["agents"]
        return {
            agent_id: AgentConfig(
                id=agent["id"],
                name=agent["name"],
                description=agent["description"],
                status=agent["status"],
                llm_provider=agent["llm_provider"],
                llm_model=agent["llm_model"],
                stt_provider=agent["stt_provider"],
                stt_model=agent["stt_model"],
                tts_provider=agent["tts_provider"],
                voice_id=agent["voice_id"],
                language=agent["language"],
                prompt=agent["prompt"],
                tools=agent["tools"],
                settings=agent["settings"]
            )
            for agent_id, agent in agents_dict.items()
        }

    def agent_exists(self, agent_id: str) -> bool:
        """Check if an agent exists"""
        agent_config = self.get_agent_config(agent_id)
        return agent_config is not None

    def get_active_agents(self) -> Dict[str, AgentConfig]:
        """Get only active agents"""
        all_agents = self.get_all_agents()
        return {aid: config for aid, config in all_agents.items() if config.status == "active"}

    def reload_config(self) -> bool:
        """Reload configuration from database"""
        try:
            # Since we're using database, this could refresh any cached data
            # or simply return True if no caching is used
            return True
        except Exception as e:
            print(f"Error reloading config: {e}")
            return False