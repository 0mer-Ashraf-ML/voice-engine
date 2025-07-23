from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

class AssistantSettings(BaseModel):
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=150, ge=1, le=4000)
    conversation_timeout: float = Field(default=30.0, ge=5.0, le=300.0)
    audio_sample_rate: int = Field(default=16000, ge=8000, le=48000)
    audio_channels: int = Field(default=1, ge=1, le=2)
    interruptions_enabled: bool = True
    voicemail_detection: bool = True
    background_sound: str = Field(default="office")

class AgentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: str = "active"
    llm_provider: str
    llm_model: str
    stt_provider: str
    stt_model: str
    tts_provider: str
    voice_id: Optional[str] = None
    language: str = "english"
    prompt: Optional[str] = None
    first_message: Optional[str] = None
    tools: List[str] = []
    settings: AssistantSettings
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class AgentsListResponse(BaseModel):
    agents: Dict[str, AgentResponse]
    total: int
    page: int
    per_page: int

class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    llm_provider: str = Field(default="openai", pattern="^(openai|anthropic|groq)$")
    llm_model: str = Field(default="gpt-4o-mini")
    stt_provider: str = Field(default="deepgram")
    stt_model: str = Field(default="nova-2-general")
    tts_provider: str = Field(default="elevenlabs")
    voice_id: Optional[str] = Field(None, description="Voice ID from the TTS provider")
    language: str = Field(default="english")
    prompt: Optional[str] = Field(None, max_length=10000, description="System prompt for the AI assistant")
    first_message: Optional[str] = Field(None, max_length=500, description="Initial greeting message")
    tools: List[str] = Field(default_factory=list, description="List of tool names to attach")
    settings: Optional[AssistantSettings] = Field(default_factory=AssistantSettings)
    
    # Additional fields for webhook integration
    server_url: Optional[str] = Field(None, description="Webhook URL for the assistant")
    server_url_secret: Optional[str] = Field(None, description="Secret for webhook authentication")

class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    llm_provider: Optional[str] = Field(None, pattern="^(openai|anthropic|groq)$")
    llm_model: Optional[str] = None
    stt_provider: Optional[str] = None
    stt_model: Optional[str] = None
    tts_provider: Optional[str] = None
    voice_id: Optional[str] = None
    language: Optional[str] = None
    prompt: Optional[str] = Field(None, max_length=10000)
    first_message: Optional[str] = Field(None, max_length=500)
    tools: Optional[List[str]] = None
    settings: Optional[AssistantSettings] = None
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")
    
    # Additional fields
    server_url: Optional[str] = None
    server_url_secret: Optional[str] = None

class AgentSingleResponse(BaseModel):
    agent: AgentResponse

class ToolAttachRequest(BaseModel):
    tool_names: List[str] = Field(..., min_items=1, description="List of tool names to attach")

class ToolDetachRequest(BaseModel):
    tool_names: List[str] = Field(..., min_items=1, description="List of tool names to detach")

# ✅ NEW: Tool detail response for agent tools endpoint
class ToolDetail(BaseModel):
    name: str
    description: Optional[str] = None
    type: str
    webhook_url: Optional[str] = None
    function_schema: Optional[Dict[str, Any]] = None
    id: str

class AgentToolsResponse(BaseModel):
    agent_id: str
    tools: List[ToolDetail]
    total_tools: int

# ✅ NEW: Available tools response
class AvailableToolsResponse(BaseModel):
    available_tools: List[ToolDetail]
    total_tools: int

# ✅ NEW: Analytics response
class AgentAnalytics(BaseModel):
    agent_id: str
    period_days: int
    total_calls: int = 0
    total_duration: float = 0.0  # in seconds
    average_call_duration: float = 0.0
    total_cost: float = 0.0
    success_rate: float = 0.0  # percentage
    most_used_tools: List[str] = []
    cost_breakdown: Dict[str, float] = Field(default_factory=dict)  # {"llm": 10.50, "tts": 5.25}

# ✅ NEW: Test response
class AgentTestResponse(BaseModel):
    agent_id: str
    test_message: str
    response: str
    status: str
    response_time: Optional[float] = None  # in seconds
    cost: Optional[float] = None  # in USD
    
# ✅ NEW: Duplication response
class AgentDuplicateResponse(BaseModel):
    original_agent_id: str
    new_agent: AgentResponse
    message: str

# ✅ NEW: Bulk operations
class BulkAgentUpdate(BaseModel):
    agent_ids: List[str] = Field(..., min_items=1)
    update_data: AgentUpdate

class BulkAgentResponse(BaseModel):
    updated_agents: List[str]
    failed_agents: List[str]
    total_processed: int

# ✅ NEW: Agent configuration export/import
class AgentExport(BaseModel):
    agent: AgentResponse
    tools_details: List[ToolDetail]
    export_timestamp: datetime
    version: str = "1.0"

class AgentImport(BaseModel):
    name: str
    agent_config: AgentCreate
    import_tools: bool = True

# ✅ LEGACY: Keep old schemas for backward compatibility (commented)
"""
Legacy schemas - kept for reference/backward compatibility

class AssistantCreate(BaseModel):
    name: str
    first_message: Optional[str] = None
    system_prompt: Optional[str] = None
    
    # Model Configuration
    model_provider: str = "openai"
    model_name: str = "gpt-4o"
    model_temperature: float = 0.7
    model_max_tokens: int = 250
    assistant_config: Optional[Dict[str, Any]] = None
    
    # Voice Configuration
    voice_provider: str = "elevenlabs"
    voice_id: Optional[str] = None
    voice_settings: Optional[Dict[str, Any]] = None
    
    # Transcriber Configuration
    transcriber_provider: str = "deepgram"
    transcriber_model: str = "nova-3"
    transcriber_config: Optional[Dict[str, Any]] = None
    
    # Settings
    interruptions_enabled: bool = True
    background_sound: str = "office"
    voicemail_detection: bool = True
    
    # Webhook settings
    server_url: Optional[str] = None
    server_url_secret: Optional[str] = None

class AssistantUpdate(BaseModel):
    name: Optional[str] = None
    first_message: Optional[str] = None
    system_prompt: Optional[str] = None
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    model_temperature: Optional[float] = None
    model_max_tokens: Optional[int] = None
    assistant_config: Optional[Dict[str, Any]] = None
    voice_provider: Optional[str] = None
    voice_id: Optional[str] = None
    voice_settings: Optional[Dict[str, Any]] = None
    transcriber_provider: Optional[str] = None
    transcriber_model: Optional[str] = None
    transcriber_config: Optional[Dict[str, Any]] = None
    interruptions_enabled: Optional[bool] = None
    background_sound: Optional[str] = None
    voicemail_detection: Optional[bool] = None
    server_url: Optional[str] = None
    server_url_secret: Optional[str] = None
    is_active: Optional[bool] = None

class AssistantResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    first_message: Optional[str] = None
    system_prompt: Optional[str] = None
    model_provider: str
    model_name: str
    model_temperature: float
    model_max_tokens: int
    assistant_config: Optional[Dict[str, Any]] = None
    voice_provider: str
    voice_id: Optional[str] = None
    voice_settings: Optional[Dict[str, Any]] = None
    transcriber_provider: str
    transcriber_model: str
    transcriber_config: Optional[Dict[str, Any]] = None
    interruptions_enabled: bool
    background_sound: str
    voicemail_detection: bool
    server_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AssistantToolCreate(BaseModel):
    tool_id: uuid.UUID
    is_enabled: bool = True
"""

# ✅ Helper schemas for validation
class ModelProviderConfig(BaseModel):
    openai: List[str] = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
    anthropic: List[str] = ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]
    groq: List[str] = ["mixtral-8x7b", "llama2-70b", "gemma-7b"]

class VoiceProviderConfig(BaseModel):
    elevenlabs: List[str] = ["21m00Tcm4TlvDq8ikWAM", "EXAVITQu4vr4xnSDxMaL", "pNInz6obpgDQGcFmaJgB"]
    deepgram: List[str] = ["aura-asteria-en", "aura-luna-en", "aura-stella-en"]

class STTProviderConfig(BaseModel):
    deepgram: List[str] = ["nova-2-general", "nova-2-meeting", "nova-2-phonecall", "nova-2-voicemail"]
    
# ✅ Configuration response for frontend
class AgentConfigOptions(BaseModel):
    model_providers: ModelProviderConfig
    voice_providers: VoiceProviderConfig
    stt_providers: STTProviderConfig
    languages: List[str] = ["english", "spanish", "french", "german", "italian"]
    background_sounds: List[str] = ["office", "cafe", "nature", "silent"]