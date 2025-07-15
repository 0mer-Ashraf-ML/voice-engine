from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import httpx
import json
from app.config import settings

class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        pass

class OpenAIProvider(BaseLLMProvider):
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = "https://api.openai.com/v1"
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                return {
                    "error": f"OpenAI API error: {response.status_code} - {response.text}"
                }
            
            result = response.json()
            
            return {
                "success": True,
                "response": result["choices"][0]["message"]["content"],
                "tool_calls": result["choices"][0]["message"].get("tool_calls"),
                "usage": result.get("usage", {}),
                "model": result.get("model"),
                "provider": "openai"
            }

class AnthropicProvider(BaseLLMProvider):
    def __init__(self):
        self.api_key = settings.ANTHROPIC_API_KEY
        self.base_url = "https://api.anthropic.com/v1"
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        model: str = "claude-3-sonnet-20240229",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> Dict[str, Any]:
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        # Convert OpenAI format to Anthropic format
        system_message = ""
        claude_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                claude_messages.append(msg)
        
        payload = {
            "model": model,
            "messages": claude_messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        if system_message:
            payload["system"] = system_message
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                return {
                    "error": f"Anthropic API error: {response.status_code} - {response.text}"
                }
            
            result = response.json()
            
            return {
                "success": True,
                "response": result["content"][0]["text"],
                "usage": result.get("usage", {}),
                "model": result.get("model"),
                "provider": "anthropic"
            }

class GroqProvider(BaseLLMProvider):
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.base_url = "https://api.groq.com/openai/v1"
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        model: str = "mixtral-8x7b-32768",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                return {
                    "error": f"Groq API error: {response.status_code} - {response.text}"
                }
            
            result = response.json()
            
            return {
                "success": True,
                "response": result["choices"][0]["message"]["content"],
                "usage": result.get("usage", {}),
                "model": result.get("model"),
                "provider": "groq"
            }

class LLMIntegration:
    def __init__(self):
        self.providers = {
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "groq": GroqProvider()
        }
    
    async def generate_response(
        self,
        provider: str,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        if provider not in self.providers:
            return {"error": f"Unsupported LLM provider: {provider}"}
        
        try:
            return await self.providers[provider].generate_response(
                messages=messages,
                model=model,
                **kwargs
            )
        except Exception as e:
            return {"error": f"LLM generation failed: {str(e)}"}
    
    def get_available_models(self, provider: str) -> List[str]:
        models = {
            "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
            "anthropic": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
            "groq": ["mixtral-8x7b-32768", "llama2-70b-4096", "gemma-7b-it"]
        }
        return models.get(provider, [])