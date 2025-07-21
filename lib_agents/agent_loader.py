import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from app.models.user import User  # Assuming User model is imported
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


# class AgentLoader:
#     def __init__(self, config_file: str = "agents_config.json"):
#         self.config_file = config_file
#         self.agents_config = self._load_config()
    
#     def _load_config(self) -> Dict[str, Any]:
#         """Load agents configuration from JSON file"""
#         try:
#             with open(self.config_file, 'r', encoding='utf-8') as f:
#                 return json.load(f)
#         except FileNotFoundError:
#             print(f"Warning: {self.config_file} not found. Using empty config.")
#             return {"agents": {}}
#         except json.JSONDecodeError as e:
#             print(f"Error parsing {self.config_file}: {e}")
#             return {"agents": {}}
    
#     def get_agent_config(self, agent_id: str) -> Optional[AgentConfig]:
#         """Get configuration for a specific agent"""
#         agent_data = self.agents_config.get("agents", {}).get(agent_id)
#         if not agent_data:
#             return None
        
#         return AgentConfig(
#             id=agent_data.get("id", agent_id),
#             name=agent_data.get("name", "Unknown Agent"),
#             description=agent_data.get("description", ""),
#             status=agent_data.get("status", "inactive"),
#             llm_provider=agent_data.get("llm_provider", "openai"),
#             llm_model=agent_data.get("llm_model", "4o-mini"),
#             stt_provider=agent_data.get("stt_provider", "deepgram"),
#             stt_model=agent_data.get("stt_model", "nova-2-general"),
#             tts_provider=agent_data.get("tts_provider", "elevenlabs"),
#             voice_id=agent_data.get("voice_id", "21m00Tcm4TlvDq8ikWAM"),
#             language=agent_data.get("language", "english"),
#             prompt=agent_data.get("prompt", "You are a helpful AI assistant."),
#             tools=agent_data.get("tools", []),
#             settings=agent_data.get("settings", {})
#         )
    
#     def get_all_agents(self) -> Dict[str, AgentConfig]:
#         """Get all agent configurations"""
#         agents = {}
#         for agent_id in self.agents_config.get("agents", {}):
#             agent_config = self.get_agent_config(agent_id)
#             if agent_config:
#                 agents[agent_id] = agent_config
#         return agents

class AgentLoader:
    def __init__(self, db: Session):
        self.db = db

    def get_agent_config(self, agent_id: str, organization_id: uuid.UUID) -> Optional[AgentConfig]:
        """Fetch agent configuration from the database using AssistantService"""
        service = AssistantService(self.db)
        result = service.get_agent(agent_id, organization_id)
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

    def get_all_agents(self, organization_id: uuid.UUID) -> Dict[str, AgentConfig]:
        """List all agents for the organization"""
        service = AssistantService(self.db)
        agents_result = service.list_agents(organization_id, limit=1000)
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
    
    def agent_exists(self, agent_id: str) -> bool:
        """Check if an agent exists"""
        return agent_id in self.agents_config.get("agents", {})
    
    def get_active_agents(self) -> Dict[str, AgentConfig]:
        """Get only active agents"""
        all_agents = self.get_all_agents()
        return {aid: config for aid, config in all_agents.items() if config.status == "active"}
    
    def reload_config(self) -> bool:
        """Reload configuration from file"""
        try:
            self.agents_config = self._load_config()
            return True
        except Exception as e:
            print(f"Error reloading config: {e}")
            return False