import httpx
import base64
import io
from typing import Dict, Any, List, Optional
from app.config import settings

class ElevenLabsIntegration:
    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        self.base_url = "https://api.elevenlabs.io/v1"
    
    async def text_to_speech(
        self,
        text: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # Default voice
        model_id: str = "eleven_turbo_v2",
        voice_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "ElevenLabs API key not configured"}
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        default_settings = {
            "stability": 0.5,
            "similarity_boost": 0.5,
            "style": 0.0,
            "use_speaker_boost": True
        }
        
        if voice_settings:
            default_settings.update(voice_settings)
        
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": default_settings
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/text-to-speech/{voice_id}",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    return {
                        "error": f"ElevenLabs API error: {response.status_code} - {response.text}"
                    }
                
                # Convert audio to base64 for easy transport
                audio_content = response.content
                audio_base64 = base64.b64encode(audio_content).decode('utf-8')
                
                return {
                    "success": True,
                    "audio_base64": audio_base64,
                    "audio_format": "mp3",
                    "voice_id": voice_id,
                    "model_id": model_id,
                    "character_count": len(text),
                    "provider": "elevenlabs"
                }
                
        except Exception as e:
            return {"error": f"ElevenLabs TTS failed: {str(e)}"}
    
    async def get_voices(self) -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "ElevenLabs API key not configured"}
        
        headers = {
            "Accept": "application/json",
            "xi-api-key": self.api_key
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/voices",
                    headers=headers
                )
                
                if response.status_code != 200:
                    return {
                        "error": f"ElevenLabs API error: {response.status_code} - {response.text}"
                    }
                
                return {
                    "success": True,
                    "voices": response.json()["voices"]
                }
                
        except Exception as e:
            return {"error": f"Failed to get voices: {str(e)}"}
    
    async def get_voice_settings(self, voice_id: str) -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "ElevenLabs API key not configured"}
        
        headers = {
            "Accept": "application/json",
            "xi-api-key": self.api_key
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/voices/{voice_id}/settings",
                    headers=headers
                )
                
                if response.status_code != 200:
                    return {
                        "error": f"ElevenLabs API error: {response.status_code} - {response.text}"
                    }
                
                return {
                    "success": True,
                    "settings": response.json()
                }
                
        except Exception as e:
            return {"error": f"Failed to get voice settings: {str(e)}"}
    
    async def clone_voice(
        self,
        name: str,
        files: List[bytes],
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "ElevenLabs API key not configured"}
        
        headers = {
            "Accept": "application/json",
            "xi-api-key": self.api_key
        }
        
        # Prepare multipart form data
        files_data = []
        for i, file_content in enumerate(files):
            files_data.append(
                ("files", (f"audio_{i}.wav", io.BytesIO(file_content), "audio/wav"))
            )
        
        data = {"name": name}
        if description:
            data["description"] = description
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/voices/add",
                    headers=headers,
                    data=data,
                    files=files_data
                )
                
                if response.status_code != 200:
                    return {
                        "error": f"ElevenLabs API error: {response.status_code} - {response.text}"
                    }
                
                return {
                    "success": True,
                    "voice": response.json()
                }
                
        except Exception as e:
            return {"error": f"Voice cloning failed: {str(e)}"}
    
    def get_available_models(self) -> List[str]:
        return [
            "eleven_turbo_v2",
            "eleven_multilingual_v2", 
            "eleven_monolingual_v1",
            "eleven_turbo_v2_5"
        ]
    
    def calculate_cost(self, character_count: int, model_id: str = "eleven_turbo_v2") -> float:
        # ElevenLabs pricing (approximate)
        rates = {
            "eleven_turbo_v2": 0.18 / 1000,  # $0.18 per 1K characters
            "eleven_multilingual_v2": 0.24 / 1000,  # $0.24 per 1K characters
            "eleven_monolingual_v1": 0.22 / 1000,  # $0.22 per 1K characters
            "eleven_turbo_v2_5": 0.20 / 1000,  # $0.20 per 1K characters
        }
        
        rate = rates.get(model_id, 0.18 / 1000)
        return character_count * rate