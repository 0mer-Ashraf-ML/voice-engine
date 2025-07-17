# external imports
import os , uuid , asyncio
from dotenv import load_dotenv
from api_request_schemas import (SourceEnum , LanguageEnum)
from fastapi import FastAPI, WebSocket , Request, HTTPException
from fastapi.websockets import WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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

# loading .env configs
load_dotenv()
PORT = int(os.getenv("PORT"))
OUTPUT_MP3_FILES = "output.mp3"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Initialize agent loader
agent_loader = AgentLoader()

# app initalization & setup
app = FastAPI()
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
@app.get("/agents")
async def list_agents_page(request: Request):
    """Display all available agents"""
    agents = agent_loader.get_all_agents()
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

# New agent-specific route
@app.get("/agent/{agent_id}")
async def agent_voice_chat_page(agent_id: str, request: Request):
    """Serve voice chat page for specific agent"""
    # Get agent configuration
    agent_config = agent_loader.get_agent_config(agent_id)
    if not agent_config:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    
    if agent_config.status != "active":
        raise HTTPException(status_code=403, detail=f"Agent '{agent_id}' is not active")
    
    # Agent configuration for the frontend
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
    source: SourceEnum,
    language: LanguageEnum | None = None 
):
    # Default to assistant-001 for backward compatibility
    await websocket_agent_endpoint(websocket, source, "assistant-001", language)

# New agent-specific websocket endpoint - matches your JS URL structure
@app.websocket("/ws/{source}/agent/{agent_id}")
async def websocket_agent_endpoint(
    websocket: WebSocket,
    source: SourceEnum,
    agent_id: str,
    language: LanguageEnum | None = None
):
    guid = str(uuid.uuid4())
    
    # Get agent configuration
    agent_config = agent_loader.get_agent_config(agent_id)
    if not agent_config:
        await websocket.close(code=4404, reason=f"Agent '{agent_id}' not found")
        return
    
    if agent_config.status != "active":
        await websocket.close(code=4403, reason=f"Agent '{agent_id}' is not active")
        return
    
    # Override language if specified in agent config
    if language is None:
        language = LanguageEnum(agent_config.language)
    
    print(f"WebSocket connection established for agent '{agent_id}' via {source.value} with UID {guid} & language {language.value}")

    # Use agent-specific prompt generator
    prompt_generator = AgentPromptGenerator(agent_config)
    
    # Initialize LLM with agent-specific model
    modelInstance = LLM(guid, prompt_generator, OPENAI_API_KEY, model=agent_config.llm_model)

    global_logger = GlobalLoggerAsync(
        guid,
        dispatcher,
        pubsub_events={
            MessageType.CALL_WEBSOCKET_PUT: True,
            MessageType.LLM_GENERATED_TEXT: True,
            MessageType.TRANSCRIPTION_CREATED: True,
            MessageType.FINAL_TRANSCRIPTION_CREATED : True,
            MessageType.LLM_GENERATED_FULL_TEXT : True,
            MessageType.CALL_WEBSOCKET_GET : False
        },
        # events whose output needs to be ignored, we just need to capture the time they are fired
        ignore_msg_events = {  
            MessageType.CALL_WEBSOCKET_PUT: True,
            MessageType.CALL_WEBSOCKET_GET : True
        }
    )

    websocket_manager = WebsocketManager(guid, modelInstance, dispatcher, websocket, source)
    speech_to_text = SpeechToTextDeepgram(guid, dispatcher, websocket, DEEPGRAM_API_KEY)
    large_language_model = LargeLanguageModel(guid, modelInstance, dispatcher, source.value)
    
    # Choose TTS provider based on agent configuration
    if agent_config.tts_provider == "elevenlabs":
        text_to_speech = TextToSpeechElevenLabs(guid, dispatcher, ELEVENLABS_API_KEY, agent_config.voice_id)
    else:  # Default to deepgram
        text_to_speech = TextToSpeechDeepgram(guid, dispatcher, DEEPGRAM_API_KEY)

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
            guid, Message(MessageHeader(MessageType.CALL_ENDED), "Call ended") 
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
    print(f"Server Up At : http://localhost:{PORT}/")