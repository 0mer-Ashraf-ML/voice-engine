# # external imports
# import os , uuid , asyncio
# from dotenv import load_dotenv
# from api_request_schemas import (SourceEnum , LanguageEnum)
# from fastapi import FastAPI, WebSocket , Request, HTTPException, Depends
# from fastapi.websockets import WebSocketDisconnect
# from fastapi.staticfiles import StaticFiles
# from fastapi.templating import Jinja2Templates
# from fastapi.middleware.cors import CORSMiddleware

# # internal imports
# from lib_socket_handler.web_socket_manager import WebsocketManager
# from lib_stt.speech_to_text_deepgram import SpeechToTextDeepgram
# from lib_llm.helpers.llm import LLM
# from lib_llm.helpers.prompt_generator import PromptGenerator
# from lib_llm.large_language_model import LargeLanguageModel
# from lib_tts.text_to_speech_deepgram import TextToSpeechDeepgram
# from lib_tts.text_to_speech_elevenlabs import TextToSpeechElevenLabs
# from lib_infrastructure.dispatcher import ( Dispatcher , Message , MessageHeader , MessageType )
# from lib_infrastructure.helpers.global_event_logger import GlobalLoggerAsync
# from lib_agents.agent_loader import AgentLoader

# from app.database import get_db
# from app.models.user import User
# from app.auth import get_current_user
# from sqlalchemy.orm import Session
# from app.config import settings

# # loading .env configs
# load_dotenv()
# # PORT = int(os.getenv("PORT"))
# PORT = 3000
# OUTPUT_MP3_FILES = "output.mp3"
# # OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# # DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
# # ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# OPENAI_API_KEY = settings.OPENAI_API_KEY
# DEEPGRAM_API_KEY = settings.DEEPGRAM_API_KEY
# ELEVENLABS_API_KEY = settings.ELEVENLABS_API_KEY

# # Initialize agent loader
# # agent_loader = AgentLoader()

# # app initalization & setup
# app = FastAPI()
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Allows all origins (use cautiously in production)
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# app.mount("/public", StaticFiles(directory="public"), name="static")
# templates = Jinja2Templates(directory="templates")
# dispatcher = Dispatcher()

# # managing dispatcher connect event on app startup
# @app.on_event("startup")
# async def startup():
#     print("Conneting to memory://")
#     await dispatcher.connect()
#     print("Connected to memory://")

# # managing dispatcher connect event on app shutdown
# @app.on_event("shutdown")
# async def shutdown():
#     print("Disconnecting from memory://")
#     await dispatcher.disconnect()
#     print("Disconnected from memory://")

# # Original UI route
# @app.get("/")
# async def get(request: Request):
#     return templates.TemplateResponse("index.html" ,  {"request": request})

# # Agents listing page
# @app.get("/agents/{user_id}")
# async def list_agents_page(
#     user_id: str,  # Extract user_id from URL
#     request: Request,
#     db: Session = Depends(get_db)
# ):
#     agent_loader = AgentLoader(db)
    
#     # Load agents by user_id without authentication
#     agents = agent_loader.get_all_agents_by_user_id(user_id)

#     agents_list = [
#         {
#             "id": config.id,
#             "name": config.name,
#             "description": config.description,
#             "status": config.status,
#             "llm_model": config.llm_model,
#             "voice_provider": config.tts_provider,
#             "voice_id": config.voice_id,
#             "language": config.language
#         }
#         for config in agents.values()
#     ]

#     # Return JSON if requested
#     if request.headers.get("accept") == "application/json":
#         return {"agents": agents_list}

#     # Otherwise, render HTML template
#     return templates.TemplateResponse("agents_list.html", {
#         "request": request,
#         "agents": agents_list
#     })

# # New agent-specific route
# @app.get("/agent/{agent_id}")
# async def agent_voice_chat_page(
#     agent_id: str,
#     request: Request,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     agent_loader = AgentLoader(db)
#     agent_config = agent_loader.get_agent_config(agent_id, current_user.organization_id)
#     if not agent_config:
#         raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
#     if agent_config.status != "active":
#         raise HTTPException(status_code=403, detail=f"Agent '{agent_id}' is not active")
    
#     agent_data = {
#         "id": agent_config.id,
#         "name": agent_config.name,
#         "description": agent_config.description,
#         "status": agent_config.status,
#         "llm_model": agent_config.llm_model,
#         "voice_provider": agent_config.tts_provider,
#         "voice_id": agent_config.voice_id,
#         "language": agent_config.language
#     }

#     # Check if the request accepts JSON
#     # if request.headers.get("accept") == "application/json":
#     #     return agent_data
    
#     return templates.TemplateResponse("agent_chat.html", {
#         "request": request,
#         "agent": agent_data,
#         "agent_id": agent_id
#     })

# # API endpoint to get agent info
# @app.get("/api/agent/{agent_id}")
# async def get_agent_info(
#     agent_id: str,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     agent_loader = AgentLoader(db)
#     agent_config = agent_loader.get_agent_config(agent_id, current_user.organization_id)
#     if not agent_config:
#         raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    
#     return {
#         "id": agent_config.id,
#         "name": agent_config.name,
#         "description": agent_config.description,
#         "status": agent_config.status,
#         "llm_model": agent_config.llm_model,
#         "voice_provider": agent_config.tts_provider,
#         "voice_id": agent_config.voice_id,
#         "language": agent_config.language,
#         "tools": agent_config.tools
#     }

# # API endpoint to list all agents
# @app.get("/api/agents")
# async def list_agents(
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     agent_loader = AgentLoader(db)
#     agents = agent_loader.get_all_agents(current_user.organization_id)
    
#     return {
#         "agents": [
#             {
#                 "id": config.id,
#                 "name": config.name,
#                 "description": config.description,
#                 "status": config.status,
#                 "llm_model": config.llm_model,
#                 "voice_provider": config.tts_provider
#             }
#             for config in agents.values()
#         ]
#     }

# # Custom prompt generator for agents
# class AgentPromptGenerator:
#     def __init__(self, agent_config):
#         self.agent_config = agent_config
#         self.prompt = agent_config.prompt
#         self.serialize_prompt()

#     def serialize_prompt(self):
#         return self.prompt.strip()

#     def __repr__(self):
#         return self.prompt

# # Original LLM invoke endpoint
# @app.websocket("/invoke_llm")
# async def chat_invoke(websocket: WebSocket):
#     guid = str(uuid.uuid4())
#     prompt_generator = PromptGenerator()
#     modelInstance = LLM(guid , prompt_generator, OPENAI_API_KEY)

#     await websocket.accept()
#     try:
#         while True:
#             data = await websocket.receive_json()
#             if data : 
#                 user_msg=LLM.LLMMessage(role=LLM.Role.USER, content=data['user_msg'])
#                 llm_resp = modelInstance.interaction_langchain_synchronous( user_msg )
#                 print(llm_resp)
#                 await websocket.send_json(llm_resp)
#     except Exception as e:
#         print(f"Client disconnected >>> {e}")   

# # Original websocket endpoint (for backward compatibility)
# @app.websocket("/ws/{source}")
# async def websocket_endpoint(
#     websocket: WebSocket,
#     source: str,
#     user_id: str = "fa1c8ec9-67bc-495c-8526-f96fc2a5e3e0",
#     agent_id: str = "assistant-ec87d3fbe4d9",
#     language: str | None = None,
#     db: Session = Depends(get_db)
# ):
#     print("From WEBSOCKET_ENDPOINT >>>> `/ws/source`")
#     print(f"WebSocket connection established from {source} with user_id: {user_id} and agent_id: {agent_id}")
#     user = None
#     if user_id:
#         user = db.query(User).filter(User.id == user_id).first()
#         if not user:
#             await websocket.close(code=4404, reason="User not found")
#             return
    
#     # Convert source to SourceEnum
#     try:
#         source_enum = SourceEnum(source)
#     except ValueError:
#         await websocket.close(code=4400, reason=f"Invalid source: {source}")
#         return
    
#     await handle_websocket(
#         websocket=websocket,
#         source=source_enum,
#         agent_id=agent_id,
#         language=language,
#         current_user=user,
#         db=db
#     )


# # New agent-specific websocket endpoint - matches your JS URL structure
# @app.websocket("/ws/{source}/agent/{agent_id}")
# async def websocket_agent_endpoint(
#     websocket: WebSocket,
#     source: SourceEnum,
#     agent_id: str = "assistant-ec87d3fbe4d9",
#     user_id: str = "fa1c8ec9-67bc-495c-8526-f96fc2a5e3e0",
#     language: LanguageEnum | None = None,
#     db: Session = Depends(get_db)
# ):
    
#     print("From WEBSOCKET_ENDPOINT >>>> `/ws/source/agent/agent_id`")
#     print(f"WebSocket connection established from {source} with user_id: {user_id} and agent_id: {agent_id}")
    
    
#     user = db.query(User).filter(User.id == user_id).first()
#     print(f"User fetched: {user}")
#     if not user:
#         await websocket.close(code=4404, reason="User not found")
#         return

#     # From the client side, connect like this:
#     # const ws = new WebSocket("ws://localhost:3000/ws/phone/agent/assistant-ec87d3fbe4d9?user_id=fa1c8ec9-67bc-495c-8526-f96fc2a5e3e0&language=english");

    
#     await handle_websocket(
#         websocket,
#         source,
#         agent_id,
#         language,
#         user,  # Pass the user object (or None)
#         db
#     )

# # Update the handle_websocket function to handle optional user
# async def handle_websocket(
#     websocket: WebSocket,
#     source: SourceEnum,
#     agent_id: str,
#     language: LanguageEnum | None,
#     current_user: User | None,  # Optional user object
#     db: Session
# ):
#     agent_loader = AgentLoader(db)

#     # Use user's organization_id if user exists, else fallback to 1
#     org_id = current_user.organization_id if current_user else 1

#     # Load agent config using org_id
#     agent_config = agent_loader.get_agent_config(agent_id, org_id)

#     if not agent_config:
#         await websocket.close(code=4404, reason=f"Agent '{agent_id}' not found in organization {org_id}")
#         return

#     if agent_config.status != "active":
#         await websocket.close(code=4403, reason=f"Agent '{agent_id}' is not active")
#         return

#     # Proceed with initializing services (LLM, TTS, STT, etc.)
#     guid = str(uuid.uuid4())
#     language = language or LanguageEnum(agent_config.language)
#     prompt_generator = AgentPromptGenerator(agent_config)

#     modelInstance = LLM(
#         guid,
#         prompt_generator,
#         OPENAI_API_KEY,
#         model=agent_config.llm_model
#     )

#     global_logger = GlobalLoggerAsync(
#         guid,
#         dispatcher,
#         pubsub_events={
#             MessageType.CALL_WEBSOCKET_PUT: True,
#             MessageType.LLM_GENERATED_TEXT: True,
#             MessageType.TRANSCRIPTION_CREATED: True,
#             MessageType.FINAL_TRANSCRIPTION_CREATED: True,
#             MessageType.LLM_GENERATED_FULL_TEXT: True,
#             MessageType.CALL_WEBSOCKET_GET: False
#         },
#         ignore_msg_events={
#             MessageType.CALL_WEBSOCKET_PUT: True,
#             MessageType.CALL_WEBSOCKET_GET: True
#         }
#     )

#     websocket_manager = WebsocketManager(
#         guid,
#         modelInstance,
#         dispatcher,
#         websocket,
#         source
#     )

#     speech_to_text = SpeechToTextDeepgram(
#         guid,
#         dispatcher,
#         websocket,
#         DEEPGRAM_API_KEY
#     )

#     large_language_model = LargeLanguageModel(
#         guid,
#         modelInstance,
#         dispatcher,
#         source.value
#     )

#     if agent_config.tts_provider == "elevenlabs":
#         text_to_speech = TextToSpeechElevenLabs(
#             guid,
#             dispatcher,
#             ELEVENLABS_API_KEY,
#             agent_config.voice_id
#         )
#     else:
#         text_to_speech = TextToSpeechDeepgram(
#             guid,
#             dispatcher,
#             DEEPGRAM_API_KEY
#         )

#     try:
#         tasks = [
#             asyncio.create_task(global_logger.run_async()),
#             asyncio.create_task(speech_to_text.run_async()),
#             asyncio.create_task(large_language_model.run_async()),
#             asyncio.create_task(text_to_speech.run_async()),
#             asyncio.create_task(websocket_manager.run_async()),
#         ]
#         await asyncio.gather(*tasks)
#     except asyncio.CancelledError:
#         await websocket_manager.dispose()
#     except Exception as e:
#         await websocket_manager.dispose()
#         raise e
#     finally:
#         await dispatcher.broadcast(
#             guid,
#             Message(MessageHeader(MessageType.CALL_ENDED), "Call ended")
#         )

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=PORT)
#     print(f"Server Up At : http://localhost:{PORT}/")







# external imports
import os , uuid , asyncio
from dotenv import load_dotenv
from api_request_schemas import (SourceEnum , LanguageEnum)
from fastapi import FastAPI, WebSocket , Request, HTTPException, Depends
from fastapi.websockets import WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# internal imports
from lib_socket_handler.web_socket_manager import WebsocketManager
from lib_stt.speech_to_text_deepgram import SpeechToTextDeepgram
from lib_llm.helpers.llm import LLM
from lib_llm.helpers.prompt_generator import PromptGenerator
from lib_llm.large_language_model import LargeLanguageModel
from lib_tts.text_to_speech_deepgram import TextToSpeechDeepgram
from lib_tts.text_to_speech_elevenlabs import TextToSpeechElevenLabs
from lib_infrastructure.dispatcher import ( Dispatcher , Message , MessageHeader , MessageType )
from lib_infrastructure.helpers.global_event_logger import GlobalLoggerAsync
from lib_agents.agent_loader import AgentLoader

from app.database import get_db
from app.models.user import User
from sqlalchemy.orm import Session
from app.config import settings

# loading .env configs
load_dotenv()
PORT = 3000
OUTPUT_MP3_FILES = "output.mp3"

OPENAI_API_KEY = settings.OPENAI_API_KEY
DEEPGRAM_API_KEY = settings.DEEPGRAM_API_KEY
ELEVENLABS_API_KEY = settings.ELEVENLABS_API_KEY

# app initalization & setup
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (use cautiously in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/public", StaticFiles(directory="public"), name="static")
templates = Jinja2Templates(directory="templates")
dispatcher = Dispatcher()

# managing dispatcher connect event on app startup
@app.on_event("startup")
async def startup():
    print("Conneting to memory://")
    await dispatcher.connect()
    print("Connected to memory://")

# managing dispatcher connect event on app shutdown
@app.on_event("shutdown")
async def shutdown():
    print("Disconnecting from memory://")
    await dispatcher.disconnect()
    print("Disconnected from memory://")

# Original UI route
@app.get("/")
async def get(request: Request):
    return templates.TemplateResponse("index.html" ,  {"request": request})

# Agents listing page
@app.get("/agents/{user_id}")
async def list_agents_page(
    user_id: str,  # Extract user_id from URL
    request: Request,
    db: Session = Depends(get_db)
):
    agent_loader = AgentLoader(db)
    # Using a default organization_id of 1 since we're removing auth
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

# Agent-specific route
@app.get("/agent/{agent_id}")
async def agent_voice_chat_page(
    agent_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    agent_loader = AgentLoader(db)
    # Using default organization_id of 1
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

# API endpoint to list all agents
@app.get("/api/agents")
async def list_agents(db: Session = Depends(get_db)):
    agent_loader = AgentLoader(db)
    # Using default organization_id of 1
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

# API endpoint to get agent info
@app.get("/api/agent/{agent_id}")
async def get_agent_info(
    agent_id: str,
    db: Session = Depends(get_db)
):
    agent_loader = AgentLoader(db)
    # Using default organization_id of 1
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

# Original LLM invoke endpoint
@app.websocket("/invoke_llm")
async def chat_invoke(websocket: WebSocket):
    guid = str(uuid.uuid4())
    prompt_generator = PromptGenerator()
    modelInstance = LLM(guid , prompt_generator, OPENAI_API_KEY)

    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            if data : 
                user_msg=LLM.LLMMessage(role=LLM.Role.USER, content=data['user_msg'])
                llm_resp = modelInstance.interaction_langchain_synchronous( user_msg )
                print(llm_resp)
                await websocket.send_json(llm_resp)
    except Exception as e:
        print(f"Client disconnected >>> {e}")   

# Original websocket endpoint (for backward compatibility)
@app.websocket("/ws/{source}")
async def websocket_endpoint(
    websocket: WebSocket,
    source: str,
    user_id: str = "fa1c8ec9-67bc-495c-8526-f96fc2a5e3e0",
    agent_id: str = "assistant-ec87d3fbe4d9",
    language: str | None = None,
    db: Session = Depends(get_db)
):
    print("From WEBSOCKET_ENDPOINT >>>> /ws/source")
    print(f"WebSocket connection established from {source} with user_id: {user_id} and agent_id: {agent_id}")
    user = None
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await websocket.close(code=4404, reason="User not found")
            return
    else:
        # If user_id is not provided, we can either set user to None or handle it as needed
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
        db=db
    )

# New agent-specific websocket endpoint
@app.websocket("/ws/{source}/agent/{agent_id}")
async def websocket_agent_endpoint(
    websocket: WebSocket,
    source: SourceEnum,
    agent_id: str = "assistant-ec87d3fbe4d9",
    user_id: str = "fa1c8ec9-67bc-495c-8526-f96fc2a5e3e0",
    language: LanguageEnum | None = None,
    db: Session = Depends(get_db)
):
    print("From WEBSOCKET_ENDPOINT >>>> /ws/source/agent/agent_id")
    print(f"WebSocket connection established from {source} with user_id: {user_id} and agent_id: {agent_id}")
    
    await handle_websocket(
        websocket,
        source,
        agent_id,
        language,
        db
    )

# Updated handle_websocket function without authentication
async def handle_websocket(
    websocket: WebSocket,
    source: SourceEnum,
    agent_id: str,
    language: LanguageEnum | None,
    db: Session
):
    agent_loader = AgentLoader(db)

    # Load agent config without organization filtering
    agent_config = agent_loader.get_agent_config(agent_id)

    if not agent_config:
        await websocket.close(code=4404, reason=f"Agent '{agent_id}' not found")
        return

    # Convert boolean status to string
    agent_config.status = "active" if agent_config.status else "inactive"

    if agent_config.status != "active":
        await websocket.close(code=4403, reason=f"Agent '{agent_id}' is not active")
        return

    # Proceed with initializing services (LLM, TTS, STT, etc.)
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
    print(f"Server Up At : http://localhost:{PORT}/")