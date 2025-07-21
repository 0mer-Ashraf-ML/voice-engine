# External imports
import os
import uuid
import asyncio
import time
import json
from collections import defaultdict
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, Request, HTTPException, Depends, status
from fastapi.websockets import WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlalchemy.orm import Session

# Internal imports
from api_request_schemas import (SourceEnum, LanguageEnum)
from lib_socket_handler.web_socket_manager import WebsocketManager
from lib_stt.speech_to_text_deepgram import SpeechToTextDeepgram
from lib_llm.helpers.llm import LLM
from lib_llm.helpers.prompt_generator import PromptGenerator
from lib_llm.large_language_model import LargeLanguageModel
from lib_tts.text_to_speech_deepgram import TextToSpeechDeepgram
from lib_tts.text_to_speech_elevenlabs import TextToSpeechElevenLabs
from lib_infrastructure.dispatcher import (Dispatcher, Message, MessageHeader, MessageType)
from lib_infrastructure.helpers.global_event_logger import GlobalLoggerAsync
from lib_agents.agent_loader import AgentLoader

from app.database import get_db, Base, engine
from app.models.user import User
from app.auth import get_current_user
from app.config import settings
from app.api import api_router
from app.utils.logger import get_logger, api_logger, security_logger
from app.websocket import manager

# Load environment variables
load_dotenv()

# Configuration
PORT = settings.PORT  # Single port for both applications
OUTPUT_MP3_FILES = "output.mp3"

# API Keys from settings
OPENAI_API_KEY = settings.OPENAI_API_KEY
DEEPGRAM_API_KEY = settings.DEEPGRAM_API_KEY
ELEVENLABS_API_KEY = settings.ELEVENLABS_API_KEY

# Initialize logger
logger = get_logger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize dispatcher
dispatcher = Dispatcher()

# Custom Middleware Classes
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Log request
        api_logger.log_request(
            method=request.method,
            path=request.url.path,
            user_id=getattr(request.state, 'user_id', None),
            organization_id=getattr(request.state, 'organization_id', None)
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Log response
        api_logger.log_response(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            response_time=response_time
        )
        
        # Add response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{response_time:.3f}s"
        
        return response

class UserContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for public endpoints
        public_paths = [
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/register",
            "/auth/login",
            "/agents",
            "/agent",
            "/public"
        ]
        
        # Check if path starts with any public path
        is_public = any(request.url.path.startswith(path) for path in public_paths)
        
        if is_public:
            return await call_next(request)
        
        # Try to get user from authorization header
        try:
            if hasattr(request.state, 'user'):
                user = request.state.user
                request.state.user_id = str(user.id)
                request.state.organization_id = str(user.organization_id)
        except Exception:
            # User context not available, continue without it
            pass
        
        return await call_next(request)

# Rate limiting storage
rate_limit_storage = defaultdict(list)
error_counts = defaultdict(int)

# Custom prompt generator for agents
class AgentPromptGenerator:
    def __init__(self, agent_config):
        self.agent_config = agent_config
        self.prompt = agent_config.prompt
        self.serialize_prompt()

    def serialize_prompt(self):
        return self.prompt.strip()

    def __repr__(self):
        return self.prompt

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Use cautiously in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(UserContextMiddleware)

# Mount static files
app.mount("/public", StaticFiles(directory="public"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Record start time for uptime calculation
start_time = time.time()

# Event handlers
@app.on_event("startup")
async def startup():
    logger.info("Starting up merged Vapi Clone application...")
    print("Connecting to memory://")
    await dispatcher.connect()
    print("Connected to memory://")
    logger.info("Application started successfully")

@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down merged application...")
    print("Disconnecting from memory://")
    await dispatcher.disconnect()
    print("Disconnected from memory://")
    logger.info("Application shutdown completed")

# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Custom HTTP exception handler"""
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    
    # Log security-related errors
    if exc.status_code in [401, 403]:
        security_logger.log_auth_failure(
            email="unknown",
            reason=exc.detail,
            ip_address=request.client.host if request.client else None
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "request_id": getattr(request.state, 'request_id', None)
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom validation exception handler"""
    logger.error(f"Validation Error: {exc.errors()}")
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation failed",
            "details": exc.errors(),
            "status_code": 422,
            "request_id": getattr(request.state, 'request_id', None)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "request_id": getattr(request.state, 'request_id', None)
        }
    )

# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Basic rate limiting middleware"""
    # Skip rate limiting for certain paths
    if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)
    
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Rate limit: 100 requests per minute
    now = datetime.utcnow()
    minute_ago = now - timedelta(minutes=1)
    
    # Clean old requests
    rate_limit_storage[client_ip] = [
        req_time for req_time in rate_limit_storage[client_ip] 
        if req_time > minute_ago
    ]
    
    # Check rate limit
    if len(rate_limit_storage[client_ip]) >= 100:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please try again later.",
                "retry_after": 60
            }
        )
    
    # Add current request
    rate_limit_storage[client_ip].append(now)
    
    return await call_next(request)

# Error tracking middleware
@app.middleware("http")
async def error_tracking_middleware(request: Request, call_next):
    """Track errors for monitoring"""
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        error_type = type(e).__name__
        error_counts[error_type] += 1
        logger.error(f"Error tracked: {error_type} - Count: {error_counts[error_type]}")
        raise

# Include API routers from main.py
app.include_router(api_router, prefix="/api/v1")

# ROOT ENDPOINTS
@app.get("/")
async def get(request: Request):
    """Original UI route from app.py"""
    return templates.TemplateResponse("index.html", {"request": request})

# HEALTH CHECK ENDPOINTS
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0",
        "service": settings.APP_NAME
    }

# AGENT ENDPOINTS (from app.py)
@app.get("/agents/{user_id}")
async def list_agents_page(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    agent_loader = AgentLoader(db)
    agents = agent_loader.get_agent_by_user_id(user_id=user_id)
    print(f"Agents fetched for user {user_id}: {agents}")
    print(f"Total agents found: {len(agents)}")
    print(f"Agents data: {agents.values()}")

    agents_list = [
        {
            "id": config.id,
            "name": config.name,
            "description": config.description,
            "status": config.status,
            "llm_model": config.llm_model,
            "voice_provider": config.tts_provider,
            "voice_id": config.voice_id,
            "language": config.language
        }
        for config in agents.values()
    ]
    
    return templates.TemplateResponse("agents_list.html", {
        "request": request,
        "agents": agents_list
    })

@app.get("/agent/{agent_id}")
async def agent_voice_chat_page(
    agent_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    agent_loader = AgentLoader(db)
    agent_config = agent_loader.get_agent_config(agent_id, organization_id='e19eaf1c-924b-4c1f-b0df-9d09d296cacb')

    if not agent_config:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    
    # Convert boolean status to string
    agent_config.status = "active" if agent_config.status else "inactive"
    if agent_config.status != "active":
        raise HTTPException(status_code=403, detail=f"Agent '{agent_id}' is not active")
    
    agent_data = {
        "id": agent_config.id,
        "name": agent_config.name,
        "description": agent_config.description,
        "status": agent_config.status,
        "llm_model": agent_config.llm_model,
        "voice_provider": agent_config.tts_provider,
        "voice_id": agent_config.voice_id,
        "language": agent_config.language
    }
    
    return templates.TemplateResponse("agent_chat.html", {
        "request": request,
        "agent": agent_data,
        "agent_id": agent_id
    })

# API ENDPOINTS (from app.py)
@app.get("/api/agents")
async def list_agents(db: Session = Depends(get_db)):
    agent_loader = AgentLoader(db)
    agents = agent_loader.get_all_agents(organization_id='fa1c8ec9-67bc-495c-8526-f96fc2a5e3e0')
    print(f"Agents fetched for user : {agents}")
    print(f"Total agents found: {len(agents)}")
    print(f"Agents data: {agents.values()}")
    
    return {
        "agents": [
            {
                "id": config.id,
                "name": config.name,
                "description": config.description,
                "status": config.status,
                "llm_model": config.llm_model,
                "voice_provider": config.tts_provider
            }
            for config in agents.values()
        ]
    }

@app.get("/api/agent/{agent_id}")
async def get_agent_info(
    agent_id: str,
    db: Session = Depends(get_db)
):
    agent_loader = AgentLoader(db)
    agent_config = agent_loader.get_agent_config(agent_id, organization_id=1)

    if not agent_config:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    
    return {
        "id": agent_config.id,
        "name": agent_config.name,
        "description": agent_config.description,
        "status": agent_config.status,
        "llm_model": agent_config.llm_model,
        "voice_provider": agent_config.tts_provider,
        "voice_id": agent_config.voice_id,
        "language": agent_config.language,
        "tools": agent_config.tools
    }

# WEBSOCKET ENDPOINTS
@app.websocket("/invoke_llm")
async def chat_invoke(websocket: WebSocket):
    """Original LLM invoke endpoint from app.py"""
    guid = str(uuid.uuid4())
    prompt_generator = PromptGenerator()
    modelInstance = LLM(guid, prompt_generator, OPENAI_API_KEY)
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            if data: 
                user_msg = LLM.LLMMessage(role=LLM.Role.USER, content=data['user_msg'])
                llm_resp = modelInstance.interaction_langchain_synchronous(user_msg)
                print(llm_resp)
                await websocket.send_json(llm_resp)
    except Exception as e:
        print(f"Client disconnected >>> {e}")   

@app.websocket("/ws/{source}")
async def websocket_endpoint(
    websocket: WebSocket,
    source: str,
    user_id: str = "fa1c8ec9-67bc-495c-8526-f96fc2a5e3e0",
    agent_id: str = "assistant-ec87d3fbe4d9",
    language: str | None = None,
    db: Session = Depends(get_db)
):
    """Original websocket endpoint from app.py"""
    print("From WEBSOCKET_ENDPOINT >>>> /ws/source")
    print(f"WebSocket connection established from {source} with user_id: {user_id} and agent_id: {agent_id}")
    
    user = None
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await websocket.close(code=4404, reason="User not found")
            return
    else:
        print("No user_id provided, proceeding without user context.")
        if not user:
            await websocket.close(code=4404, reason="User not found")
            return

    # Convert source to SourceEnum
    try:
        source_enum = SourceEnum(source)
    except ValueError:
        await websocket.close(code=4400, reason=f"Invalid source: {source}")
        return
    
    await handle_websocket(
        websocket=websocket,
        source=source_enum,
        agent_id=agent_id,
        language=language,
        current_user=user,
        db=db
    )

@app.websocket("/ws/{source}/agent/{agent_id}")
async def websocket_agent_endpoint(
    websocket: WebSocket,
    source: SourceEnum,
    agent_id: str = "assistant-ec87d3fbe4d9",
    user_id: str = "fa1c8ec9-67bc-495c-8526-f96fc2a5e3e0",
    language: LanguageEnum | None = None,
    db: Session = Depends(get_db)
):
    """Agent-specific websocket endpoint from app.py"""
    print("From WEBSOCKET_ENDPOINT >>>> /ws/source/agent/agent_id")
    print(f"WebSocket connection established from {source} with user_id: {user_id} and agent_id: {agent_id}")
    
    user = db.query(User).filter(User.id == user_id).first()
    print(f"User fetched: {user}")
    if not user:
        await websocket.close(code=4404, reason="User not found")
        return
    
    await handle_websocket(
        websocket,
        source,
        agent_id,
        language,
        user,
        db
    )

@app.websocket("/ws/calls/{call_id}")
async def websocket_call_endpoint(websocket, call_id: str):
    """WebSocket endpoint for real-time call communication from main.py"""
    connection_id = str(uuid.uuid4())
    await manager.connect(websocket, connection_id)
    manager.register_call(call_id, connection_id)
    
    try:
        await manager.broadcast_call_status(call_id, "connected")
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "start_call":
                await manager.broadcast_call_status(call_id, "in-progress")
            elif message.get("type") == "end_call":
                await manager.broadcast_call_status(call_id, "completed")
                break
            elif message.get("type") == "transcript":
                await manager.broadcast_transcript(
                    call_id, 
                    message.get("text", ""), 
                    message.get("is_user", True)
                )
    
    except Exception as e:
        logger.error(f"WebSocket error for call {call_id}: {e}")
        await manager.broadcast_call_status(call_id, "error")
    
    finally:
        manager.disconnect(connection_id)

# WebSocket handler function (from app.py)
async def handle_websocket(
    websocket: WebSocket,
    source: SourceEnum,
    agent_id: str,
    language: LanguageEnum | None,
    current_user: User | None,
    db: Session
):
    agent_loader = AgentLoader(db)
    org_id = current_user.organization_id if current_user else 1

    # Load agent config using org_id
    agent_config = agent_loader.get_agent_config(agent_id, org_id)
    if not agent_config:
        await websocket.close(code=4404, reason=f"Agent '{agent_id}' not found in organization {org_id}")
        return

    # Convert boolean status to string
    agent_config.status = "active" if agent_config.status else "inactive"
    if agent_config.status != "active":
        await websocket.close(code=4403, reason=f"Agent '{agent_id}' is not active")
        return

    # Initialize services
    guid = str(uuid.uuid4())
    language = language or LanguageEnum(agent_config.language)
    prompt_generator = AgentPromptGenerator(agent_config)
    modelInstance = LLM(
        guid,
        prompt_generator,
        OPENAI_API_KEY,
        model=agent_config.llm_model
    )

    global_logger = GlobalLoggerAsync(
        guid,
        dispatcher,
        pubsub_events={
            MessageType.CALL_WEBSOCKET_PUT: True,
            MessageType.LLM_GENERATED_TEXT: True,
            MessageType.TRANSCRIPTION_CREATED: True,
            MessageType.FINAL_TRANSCRIPTION_CREATED: True,
            MessageType.LLM_GENERATED_FULL_TEXT: True,
            MessageType.CALL_WEBSOCKET_GET: False
        },
        ignore_msg_events={
            MessageType.CALL_WEBSOCKET_PUT: True,
            MessageType.CALL_WEBSOCKET_GET: True
        }
    )

    websocket_manager = WebsocketManager(
        guid,
        modelInstance,
        dispatcher,
        websocket,
        source
    )

    speech_to_text = SpeechToTextDeepgram(
        guid,
        dispatcher,
        websocket,
        DEEPGRAM_API_KEY
    )

    large_language_model = LargeLanguageModel(
        guid,
        modelInstance,
        dispatcher,
        source.value
    )

    if agent_config.tts_provider == "elevenlabs":
        text_to_speech = TextToSpeechElevenLabs(
            guid,
            dispatcher,
            ELEVENLABS_API_KEY,
            agent_config.voice_id
        )
    else:
        text_to_speech = TextToSpeechDeepgram(
            guid,
            dispatcher,
            DEEPGRAM_API_KEY
        )

    try:
        tasks = [
            asyncio.create_task(global_logger.run_async()),
            asyncio.create_task(speech_to_text.run_async()),
            asyncio.create_task(large_language_model.run_async()),
            asyncio.create_task(text_to_speech.run_async()),
            asyncio.create_task(websocket_manager.run_async()),
        ]

        await asyncio.gather(*tasks)

    except asyncio.CancelledError:
        await websocket_manager.dispose()
    except Exception as e:
        await websocket_manager.dispose()
        raise e
    finally:
        await dispatcher.broadcast(
            guid,
            Message(MessageHeader(MessageType.CALL_ENDED), "Call ended")
        )

# METRICS AND MONITORING ENDPOINTS
@app.get("/metrics")
async def metrics():
    """Basic metrics endpoint"""
    return {
        "requests_total": len(rate_limit_storage),
        "active_connections": len(manager.active_connections),
        "uptime": time.time() - start_time
    }

@app.get("/admin/health")
async def admin_health_check(current_user: User = Depends(get_current_user)):
    """Admin health check with detailed information"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return {
        "status": "healthy",
        "database": "connected",
        "integrations": {
            "elevenlabs": "configured" if settings.ELEVENLABS_API_KEY else "not configured",
            "deepgram": "configured" if settings.DEEPGRAM_API_KEY else "not configured",
            "openai": "configured" if settings.OPENAI_API_KEY else "not configured",
            "twilio": "configured" if settings.TWILIO_ACCOUNT_SID else "not configured",
            "stripe": "configured" if settings.STRIPE_SECRET_KEY else "not configured"
        },
        "environment": "debug" if settings.DEBUG else "production",
        "timestamp": datetime.utcnow().isoformat()
    }

# DEVELOPMENT ENDPOINTS
if settings.DEBUG:
    @app.get("/api/docs")
    async def api_documentation():
        """API documentation endpoint"""
        return {
            "message": "API Documentation",
            "endpoints": {
                "authentication": "/api/v1/auth/",
                "assistants": "/api/v1/assistants/",
                "calls": "/api/v1/calls/",
                "phone_numbers": "/api/v1/phone-numbers/",
                "squads": "/api/v1/squads/",
                "tools": "/api/v1/tools/",
                "users": "/api/v1/users/",
                "usage": "/api/v1/usage/"
            },
            "websocket": "/ws/calls/{call_id}",
            "swagger_ui": "/docs",
            "redoc": "/redoc"
        }

    @app.get("/debug/errors")
    async def debug_errors():
        """Debug endpoint to view error counts"""
        return dict(error_counts)
    
    @app.get("/debug/rate-limits")
    async def debug_rate_limits():
        """Debug endpoint to view rate limit status"""
        return {
            "rate_limits": {
                ip: len(requests) for ip, requests in rate_limit_storage.items()
            }
        }

# MAIN EXECUTION
if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting merged Vapi Clone application on port {PORT}...")
    print(f"Server Up At: http://localhost:{PORT}/")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        reload=settings.DEBUG,
    )