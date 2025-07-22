from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.schemas.assistant import (
    AgentCreate, AgentUpdate, AgentsListResponse, 
    AgentSingleResponse, ToolAttachRequest, ToolDetachRequest
)
from app.services.assistant_service import AssistantService
from app.integrations.llm import LLMIntegration

router = APIRouter()

@router.get("/", response_model=AgentsListResponse)
async def list_agents(
    limit: int = Query(100, le=1000, ge=1),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, pattern="^(active|inactive)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all agents in clean format"""
    
    service = AssistantService(db)
    result = service.list_agents(
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
        status=status
    )
    
    return AgentsListResponse(**result)

@router.get("/providers")
async def get_available_providers():
    """Get all available LLM providers"""
    llm_integration = LLMIntegration()
    return {
        "providers":llm_integration.get_supported_providers()
    }

@router.get("/providers/{provider}/models")
async def get_provider_models(provider: str):
    """Get available models for a specific provider"""
    llm_integration= LLMIntegration()
    
    providers = llm_integration.get_supported_providers()
    if provider not in providers:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider: {provider}. Available providers: {providers}"
        )
    models_map = llm_integration.get_provider_models(provider)
    return {
        "provider": provider,
        "models": models_map
    }

@router.get("/tools/available")
async def get_available_tools(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all available tools for the organization"""
    
    service = AssistantService(db)
    tools = service.get_available_tools(
        organization_id=current_user.organization_id
    )
    
    return {
        "available_tools": tools,
        "total_tools": len(tools)
    }

@router.post("/", response_model=AgentSingleResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new agent"""
    
    service = AssistantService(db)
    result = service.create_agent(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        agent_data=agent_data
    )
    
    return AgentSingleResponse(**result)

@router.get("/{agent_id}", response_model=AgentSingleResponse)
async def get_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific agent by ID"""
    
    service = AssistantService(db)
    result = service.get_agent(
        agent_id=agent_id,
        organization_id=current_user.organization_id
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found"
        )
    
    return AgentSingleResponse(**result)

@router.put("/{agent_id}", response_model=AgentSingleResponse)
async def update_agent(
    agent_id: str,
    agent_data: AgentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an agent"""
    
    service = AssistantService(db)
    result = service.update_agent(
        agent_id=agent_id,
        organization_id=current_user.organization_id,
        agent_data=agent_data
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found"
        )
    
    return AgentSingleResponse(**result)

@router.patch("/{agent_id}", response_model=AgentSingleResponse)
async def patch_agent(
    agent_id: str,
    agent_data: AgentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Partially update an agent"""
    
    service = AssistantService(db)
    result = service.update_agent(
        agent_id=agent_id,
        organization_id=current_user.organization_id,
        agent_data=agent_data
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found"
        )
    
    return AgentSingleResponse(**result)

@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an agent"""
    
    service = AssistantService(db)
    success = service.delete_agent(
        agent_id=agent_id,
        organization_id=current_user.organization_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found"
        )
    
    return {"message": f"Agent '{agent_id}' deleted successfully"}

@router.post("/{agent_id}/tools/attach")
async def attach_tools(
    agent_id: str,
    request: ToolAttachRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Attach tools to an agent"""
    
    service = AssistantService(db)
    success = service.attach_tools(
        agent_id=agent_id,
        organization_id=current_user.organization_id,
        tool_names=request.tool_names
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found"
        )
    
    return {
        "message": f"Tools {request.tool_names} attached to agent '{agent_id}' successfully",
        "attached_tools": request.tool_names
    }

@router.post("/{agent_id}/tools/detach")
async def detach_tools(
    agent_id: str,
    request: ToolDetachRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Detach tools from an agent"""
    
    service = AssistantService(db)
    success = service.detach_tools(
        agent_id=agent_id,
        organization_id=current_user.organization_id,
        tool_names=request.tool_names
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found"
        )
    
    return {
        "message": f"Tools {request.tool_names} detached from agent '{agent_id}' successfully",
        "detached_tools": request.tool_names
    }

@router.get("/{agent_id}/tools")
async def get_agent_tools(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about tools attached to an agent"""
    
    service = AssistantService(db)
    tools = service.get_agent_tools_details(
        agent_id=agent_id,
        organization_id=current_user.organization_id
    )
    
    if tools is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found"
        )
    
    return {
        "agent_id": agent_id,
        "tools": tools,
        "total_tools": len(tools)
    }
# @router.post("/{agent_id}/duplicate", response_model=AgentSingleResponse)
# async def duplicate_agent(
#     agent_id: str,
#     new_name: str = Query(..., min_length=1, max_length=255),
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Duplicate an existing agent"""
    
#     service = AssistantService(db)
    
#     # Get original agent
#     original = service.get_agent(
#         agent_id=agent_id,
#         organization_id=current_user.organization_id
#     )
    
#     if not original:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Agent '{agent_id}' not found"
#         )
    
#     # Create new agent with same settings
#     original_data = original["agent"]
    
#     new_agent_data = AgentCreate(
#         name=new_name,
#         description=original_data["description"],
#         llm_provider=original_data["llm_provider"],
#         llm_model=original_data["llm_model"],
#         stt_provider=original_data["stt_provider"],
#         stt_model=original_data["stt_model"],
#         tts_provider=original_data["tts_provider"],
#         voice_id=original_data["voice_id"],
#         language=original_data["language"],
#         prompt=original_data["prompt"],
#         first_message=original_data["first_message"],
#         tools=original_data["tools"],
#         settings=original_data["settings"]
#     )
    
#     result = service.create_agent(
#         organization_id=current_user.organization_id,
#         agent_data=new_agent_data
#     )
    
#     return AgentSingleResponse(**result)

# @router.get("/{agent_id}/test")
# async def test_agent(
#     agent_id: str,
#     test_message: str = Query("Hello, how are you?"),
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Test an agent with a sample message"""
    
#     service = AssistantService(db)
#     agent = service.get_agent(
#         agent_id=agent_id,
#         organization_id=current_user.organization_id
#     )
    
#     if not agent:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Agent '{agent_id}' not found"
#         )
    
#     # TODO: Implement actual LLM testing
#     # This would integrate with your LLM integration
    
#     return {
#         "agent_id": agent_id,
#         "test_message": test_message,
#         "response": "This is a test response. Implement actual LLM integration here.",
#         "status": "test_completed"
#     }

# @router.get("/{agent_id}/analytics")
# async def get_agent_analytics(
#     agent_id: str,
#     days: int = Query(30, ge=1, le=365),
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Get analytics for a specific agent"""
    
#     service = AssistantService(db)
#     agent = service.get_agent(
#         agent_id=agent_id,
#         organization_id=current_user.organization_id
#     )
    
#     if not agent:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Agent '{agent_id}' not found"
#         )
    
#     # TODO: Implement actual analytics
#     # This would query your calls and usage tables
    
#     return {
#         "agent_id": agent_id,
#         "period_days": days,
#         "total_calls": 0,
#         "total_duration": 0,
#         "average_call_duration": 0,
#         "total_cost": 0.0,
#         "success_rate": 0.0,
#         "most_used_tools": []
#     }