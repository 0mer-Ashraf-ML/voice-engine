import os
import json
from typing import Dict, List, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class LLMIntegration:
    def __init__(self):
        self.clients = {}  # Cache clients
    
    def _get_client(self, provider: str):
        """Get or create a client for the specified provider"""
        if provider in self.clients:
            return self.clients[provider]
        
        provider = provider.lower()
        
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")
            client = OpenAI(api_key=api_key)
            
        elif provider == "anthropic":
            try:
                from anthropic import Anthropic
            except ImportError:
                raise ImportError("Please install: pip install anthropic")
            
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            client = Anthropic(api_key=api_key)
            
        elif provider == "groq":
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY not set")
            client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=api_key
            )
            
        elif provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not set")
            client = OpenAI(
                base_url="https://generativelanguage.googleapis.com/v1beta/openai",
                api_key=api_key
            )
            
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        self.clients[provider] = client
        return client
    
    async def generate_response(
        self,
        provider: str,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 250,
        tools: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Generate response using specified provider"""
        
        try:
            client = self._get_client(provider)
            provider = provider.lower()
            
            # Handle Anthropic separately due to different API
            if provider == "anthropic":
                return await self._generate_anthropic_response(
                    client, messages, model, temperature, max_tokens, tools
                )
            else:
                return await self._generate_openai_compatible_response(
                    client, messages, model, temperature, max_tokens, tools
                )
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": provider,
                "model": model
            }
    
    async def _generate_anthropic_response(
        self, client, messages, model, temperature, max_tokens, tools
    ) -> Dict[str, Any]:
        """Handle Anthropic API calls"""
        
        # Convert OpenAI format to Anthropic format
        anthropic_messages = []
        system_message = None
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": anthropic_messages,
            "temperature": temperature
        }
        
        if system_message:
            kwargs["system"] = system_message
        
        if tools:
            # Convert OpenAI tools format to Anthropic format
            anthropic_tools = []
            for tool in tools:
                anthropic_tools.append({
                    "name": tool["function"]["name"],
                    "description": tool["function"]["description"],
                    "input_schema": tool["function"]["parameters"]
                })
            kwargs["tools"] = anthropic_tools
        
        response = client.messages.create(**kwargs)
        
        # Handle tool calls
        tool_calls = []
        if hasattr(response, 'content'):
            for content in response.content:
                if hasattr(content, 'type') and content.type == 'tool_use':
                    tool_calls.append({
                        "id": content.id,
                        "type": "function",
                        "function": {
                            "name": content.name,
                            "arguments": json.dumps(content.input)
                        }
                    })
        
        return {
            "success": True,
            "response": response.content[0].text if response.content else "",
            "tool_calls": tool_calls,
            "usage": {
                "prompt_tokens": response.usage.input_tokens if hasattr(response, 'usage') else 0,
                "completion_tokens": response.usage.output_tokens if hasattr(response, 'usage') else 0,
                "total_tokens": (response.usage.input_tokens + response.usage.output_tokens) if hasattr(response, 'usage') else 0
            }
        }
    
    async def _generate_openai_compatible_response(
        self, client, messages, model, temperature, max_tokens, tools
    ) -> Dict[str, Any]:
        """Handle OpenAI-compatible API calls"""
        
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        
        response = client.chat.completions.create(**kwargs)
        
        # Extract tool calls
        tool_calls = []
        if response.choices[0].message.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                tool_calls.append({
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                })
        
        return {
            "success": True,
            "response": response.choices[0].message.content or "",
            "tool_calls": tool_calls,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
    
    def get_supported_providers(self) -> List[str]:
        """Get list of supported providers"""
        return ["openai", "anthropic", "groq"]
    
    def get_provider_models(self, provider: str) -> List[str]:
        """Get available models for a provider"""
        models = {
            "openai": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini"],
            "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-7-sonnet-20250219","claude-sonnet-4-20250514"],
            "groq": ["llama3-70b-8192", "mixtral-8x7b-32768", "gemma-7b-it", "llama3-8b-8192"],
        }
        return models.get(provider.lower(), [])