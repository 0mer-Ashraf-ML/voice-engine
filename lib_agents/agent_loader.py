import json
from typing import Dict, Any, Optional
from dataclasses import dataclass

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
    def __init__(self, config_file: str = "agents_config.json"):
        self.config_file = config_file
        self.agents_config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load agents configuration from JSON file"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: {self.config_file} not found. Using empty config.")
            return {"agents": {}}
        except json.JSONDecodeError as e:
            print(f"Error parsing {self.config_file}: {e}")
            return {"agents": {}}
    
    def get_agent_config(self, agent_id: str) -> Optional[AgentConfig]:
        """Get configuration for a specific agent"""
        agent_data = self.agents_config.get("agents", {}).get(agent_id)
        if not agent_data:
            return None
        
        return AgentConfig(
            id=agent_data.get("id", agent_id),
            name=agent_data.get("name", "Unknown Agent"),
            description=agent_data.get("description", ""),
            status=agent_data.get("status", "inactive"),
            llm_provider=agent_data.get("llm_provider", "openai"),
            llm_model=agent_data.get("llm_model", "4o-mini"),
            stt_provider=agent_data.get("stt_provider", "deepgram"),
            stt_model=agent_data.get("stt_model", "nova-2-general"),
            tts_provider=agent_data.get("tts_provider", "elevenlabs"),
            voice_id=agent_data.get("voice_id", "21m00Tcm4TlvDq8ikWAM"),
            language=agent_data.get("language", "english"),
            prompt=agent_data.get("prompt", "You are a helpful AI assistant."),
            tools=agent_data.get("tools", []),
            settings=agent_data.get("settings", {})
        )
    
    def get_all_agents(self) -> Dict[str, AgentConfig]:
        """Get all agent configurations"""
        agents = {}
        for agent_id in self.agents_config.get("agents", {}):
            agent_config = self.get_agent_config(agent_id)
            if agent_config:
                agents[agent_id] = agent_config
        return agents
    
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