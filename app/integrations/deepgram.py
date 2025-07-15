import httpx
import base64
import asyncio
from typing import Dict, Any, List, Optional
from app.config import settings

class DeepgramIntegration:
    def __init__(self):
        self.api_key = settings.DEEPGRAM_API_KEY
        self.base_url = "https://api.deepgram.com/v1"
    
    async def speech_to_text(
        self,
        audio_data: bytes,
        model: str = "nova-2",
        language: str = "en-US",
        encoding: str = "linear16",
        sample_rate: int = 16000,
        channels: int = 1,
        **kwargs
    ) -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "Deepgram API key not configured"}
        
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": f"audio/{encoding}"
        }
        
        params = {
            "model": model,
            "language": language,
            "punctuate": True,
            "diarize": False,
            "smart_format": True,
            "utterances": True,
            **kwargs
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/listen",
                    headers=headers,
                    params=params,
                    content=audio_data
                )
                
                if response.status_code != 200:
                    return {
                        "error": f"Deepgram API error: {response.status_code} - {response.text}"
                    }
                
                result = response.json()
                
                # Extract transcript
                transcript = ""
                if result.get("results") and result["results"].get("channels"):
                    alternatives = result["results"]["channels"][0].get("alternatives", [])
                    if alternatives:
                        transcript = alternatives[0].get("transcript", "")
                
                return {
                    "success": True,
                    "transcript": transcript,
                    "confidence": alternatives[0].get("confidence", 0) if alternatives else 0,
                    "metadata": result.get("metadata", {}),
                    "model": model,
                    "provider": "deepgram",
                    "raw_response": result
                }
                
        except Exception as e:
            return {"error": f"Deepgram STT failed: {str(e)}"}
    
    async def speech_to_text_streaming(
        self,
        audio_stream,
        model: str = "nova-2",
        language: str = "en-US",
        callback=None
    ) -> Dict[str, Any]:
        """Real-time streaming speech-to-text"""
        if not self.api_key:
            return {"error": "Deepgram API key not configured"}
        
        # WebSocket streaming implementation would go here
        # This is a simplified version
        return {"error": "Streaming STT not implemented in this example"}
    
    async def get_models(self) -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "Deepgram API key not configured"}
        
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/projects/models",
                    headers=headers
                )
                
                if response.status_code != 200:
                    return {
                        "error": f"Deepgram API error: {response.status_code} - {response.text}"
                    }
                
                return {
                    "success": True,
                    "models": response.json()
                }
                
        except Exception as e:
            return {"error": f"Failed to get models: {str(e)}"}
    
    def get_available_models(self) -> List[str]:
        return [
            "nova-2",
            "nova",
            "enhanced",
            "base",
            "whisper-large",
            "whisper-medium",
            "whisper-small"
        ]
    
    def get_supported_languages(self) -> List[str]:
        return [
            "en-US", "en-GB", "en-AU", "en-NZ", "en-IN",
            "es-ES", "es-MX", "es-419",
            "fr-FR", "fr-CA",
            "de-DE",
            "it-IT",
            "pt-BR", "pt-PT",
            "nl-NL",
            "pl-PL",
            "ru-RU",
            "zh-CN", "zh-TW",
            "ja-JP",
            "ko-KR",
            "hi-IN",
            "ar-SA"
        ]
    
    def calculate_cost(self, audio_duration_seconds: float, model: str = "nova-2") -> float:
        # Deepgram pricing (approximate)
        rates = {
            "nova-2": 0.0059 / 60,  # $0.0059 per minute
            "nova": 0.0044 / 60,    # $0.0044 per minute
            "enhanced": 0.0025 / 60, # $0.0025 per minute
            "base": 0.0015 / 60,    # $0.0015 per minute
            "whisper-large": 0.0048 / 60,  # $0.0048 per minute
            "whisper-medium": 0.0036 / 60, # $0.0036 per minute
            "whisper-small": 0.0024 / 60,  # $0.0024 per minute
        }
        
        rate = rates.get(model, 0.0059 / 60)
        return audio_duration_seconds * rate