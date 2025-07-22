from __future__ import annotations
import json
import os
from enum import Enum
from openai import AsyncOpenAI
from typing import AsyncGenerator, Union, Dict

class LLM:
    # Multi-Provider Models Dictionary
    models = {
        # OpenAI Models
        "4": "gpt-4-turbo", 
        "35": "gpt-3.5-turbo", 
        "4+": "gpt-4-1106-preview",
        "36" : "gpt-3.5-turbo-1106",
        "37" : "gpt-3.5-turbo-16k",
        "4++" : "gpt-4-0125-preview",
        "35++" : "gpt-3.5-turbo-0125",
        "4o-mini" : "gpt-4o-mini",
        "4o" : "gpt-4o",
        
        # Anthropic Models (Claude) - Short keys map to full names
        "claude-3-5-sonnet-20241022": "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022": "claude-3-5-haiku-20241022", 
        "claude-3-opus-20240229": "claude-3-opus-20240229",
        "3-5-sonnet-20241022": "claude-3-5-sonnet-20241022",
        "3-5-haiku-20241022": "claude-3-5-haiku-20241022",
        "3-opus-20240229": "claude-3-opus-20240229",
        
        # Groq Models
        "llama3-70b-8192": "llama3-70b-8192",
        "mixtral-8x7b-32768": "mixtral-8x7b-32768",
        "gemma-7b-it": "gemma-7b-it",
        "llama3-8b-8192": "llama3-8b-8192",
    }

    # Provider detection based on model names
    @staticmethod
    def get_provider_for_model(model_name: str) -> str:
        """Determine the provider based on the model name"""
        if model_name.startswith("gpt-") or model_name in ["4", "35", "4+", "36", "37", "4++", "35++", "4o-mini", "4o"]:
            return "openai"
        elif "claude" in model_name or model_name.startswith("3-"):
            return "anthropic"
        elif model_name in ["llama3-70b-8192", "mixtral-8x7b-32768", "gemma-7b-it", "llama3-8b-8192"]:
            return "groq"
        else:
            return "openai"  # Default fallback

    class Role(Enum):
        USER = "user"
        TOOL = "tool"
        SYSTEM = "system"
        ASSISTANT = "assistant"

    class LLMMessage:
        def __init__(self, role: LLM.Role, content: str, tool_call_id: str = None) -> None:
            self.role = role
            self.content = content
            self.tool_call_id = tool_call_id
            
        def __str__(self) -> str:
            return f"{self.role.value}: {self.content}"

    def __init__(self, guid, prompt_generator, api_key, model="4o-mini", custom_functions=None):
        self.guid = guid
        self.prompt_generator = prompt_generator
        self.custom_functions = custom_functions or []
        self.function_responses = []
        
        # Check if model exists in dictionary
        if model not in LLM.models:
            raise KeyError(f"Model '{model}' not found in supported models. Available models: {list(LLM.models.keys())}")
            
        self.model_key = model
        self.model = LLM.models[model]
        self.provider = LLM.get_provider_for_model(self.model)
        
        # Initialize the correct client based on provider
        if self.provider == "openai":
            self.client = AsyncOpenAI(api_key=api_key)
        elif self.provider == "anthropic":
            try:
                from anthropic import AsyncAnthropic
                anthropic_key = os.getenv("ANTHROPIC_API_KEY") or api_key
                self.client = AsyncAnthropic(api_key=anthropic_key)
            except ImportError:
                raise ImportError("Please install: pip install anthropic")
        elif self.provider == "groq":
            groq_key = os.getenv("GROQ_API_KEY") or api_key
            self.client = AsyncOpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=groq_key
            )
        
        # Set tools for the instance - filter out None/empty tools for Groq
        if self.provider == "groq":
            # Groq is stricter about tools, so only set valid tools
            self.tools = [tool for tool in custom_functions if tool and isinstance(tool, dict)] if custom_functions else []
        else:
            self.tools = custom_functions or []
        
        print(f"LLM_Provider: {self.provider} | Model: {self.model} | Tools: {len(self.tools)}")
        
        self.reset()

    def reset(self):
        self.messages = []
        self.add_message(
            message=LLM.LLMMessage(LLM.Role.SYSTEM, str(self.prompt_generator))
        )

    def add_message(self, message: LLMMessage) -> None:
        if message.role == LLM.Role.TOOL: 
            self.messages.append(
                {"role": message.role.value, "content": message.content, "tool_call_id": message.tool_call_id}
            )
        else: 
            self.messages.append(
                {"role": message.role.value, "content": message.content}
            )

    async def create_completion(self, message: LLMMessage) -> AsyncGenerator[Union[str, Dict], None]:
        """Create a completion using the appropriate provider"""
        if message.content != "":
            self.add_message(message)

        if self.provider == "anthropic":
            async for result in self._create_anthropic_completion():
                yield result
        else:
            # OpenAI-compatible (OpenAI, Groq)
            async for result in self._create_openai_completion():
                yield result

    async def _create_anthropic_completion(self) -> AsyncGenerator[Union[str, Dict], None]:
        """Handle Anthropic Claude completions"""
        
        # Convert messages to Anthropic format
        anthropic_messages = []
        system_message = None
        
        for msg in self.messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            elif msg["role"] in ["user", "assistant"]:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        # Prepare request parameters
        kwargs = {
            "model": self.model,
            "max_tokens": 1000,
            "messages": anthropic_messages,
            "temperature": 0.3
        }
        
        if system_message:
            kwargs["system"] = system_message
            
        # Convert tools if present
        if self.tools:
            anthropic_tools = []
            for tool in self.tools:
                if "function" in tool:
                    anthropic_tools.append({
                        "name": tool["function"]["name"],
                        "description": tool["function"]["description"],
                        "input_schema": tool["function"]["parameters"]
                    })
            if anthropic_tools:
                kwargs["tools"] = anthropic_tools

        try:
            # Stream the response
            words = []
            async with self.client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    words.append(text)
                    yield text
                    
                # Handle tool calls if any
                message = await stream.get_final_message()
                if hasattr(message, 'content'):
                    for content in message.content:
                        if hasattr(content, 'type') and content.type == 'tool_use':
                            yield {
                                "type": "function_call",
                                "name": content.name,
                                "id": content.id,
                                "args": json.dumps(content.input) if hasattr(content, 'input') else "{}"
                            }
            
            # Add assistant message to history
            assistant_content = "".join(words).strip()
            if assistant_content:
                assistant_message = LLM.LLMMessage(
                    role=LLM.Role.ASSISTANT,
                    content=assistant_content
                )
                self.add_message(assistant_message)
                
        except Exception as e:
            print(f"Anthropic completion error: {e}")
            yield f"Error: {str(e)}"

    async def _create_openai_completion(self) -> AsyncGenerator[Union[str, Dict], None]:
        """Handle OpenAI-compatible completions (OpenAI, Groq)"""
        
    async def _create_openai_completion(self) -> AsyncGenerator[Union[str, Dict], None]:
        """Handle OpenAI-compatible completions (OpenAI, Groq)"""
        
        # Prepare request parameters
        kwargs = {
            "model": self.model,
            "messages": self.messages,
            "stream": True,
            "temperature": 0.3
        }
        
        # Handle tools - only add if we have valid tools
        if self.tools and len(self.tools) > 0:
            # Validate tools format
            valid_tools = []
            for tool in self.tools:
                if isinstance(tool, dict) and "function" in tool:
                    valid_tools.append(tool)
            
            if valid_tools:
                kwargs["tools"] = valid_tools
                
                # For Groq, be explicit about tool_choice
                if self.provider == "groq":
                    kwargs["tool_choice"] = "auto"
                else:
                    kwargs["tool_choice"] = "auto"
        
        try:
            stream = await self.client.chat.completions.create(**kwargs)
        except Exception as e:
            print(f"Error creating completion for {self.provider}: {e}")
            # If tools cause issues, retry without tools
            if "tools" in kwargs:
                print(f"Retrying without tools for {self.provider}")
                kwargs_no_tools = {k: v for k, v in kwargs.items() if k not in ["tools", "tool_choice"]}
                stream = await self.client.chat.completions.create(**kwargs_no_tools)
            else:
                raise e

        words = []
        tool_calls_buffer = {}

        async for part in stream:
            choice = part.choices[0]
            delta = choice.delta

            # Collect normal content (assistant message)
            if delta.content:
                words.append(delta.content)
                yield delta.content

            # Collect streaming tool calls
            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    idx = tool_call.index
                    # Initialize if first time seeing this tool call
                    if idx not in tool_calls_buffer:
                        tool_calls_buffer[idx] = {
                            "id": tool_call.id or "",
                            "type": "function",
                            "function": {
                                "name": "",
                                "arguments": ""
                            }
                        }
                    
                    # Update the function name if provided
                    if tool_call.function and tool_call.function.name:
                        tool_calls_buffer[idx]["function"]["name"] = tool_call.function.name
                    
                    # Append to arguments if provided
                    if tool_call.function and tool_call.function.arguments:
                        tool_calls_buffer[idx]["function"]["arguments"] += tool_call.function.arguments

        # Yield any collected tool calls
        for tool_call in tool_calls_buffer.values():
            if tool_call["function"]["name"]:  # Only yield if we have a function name
                yield {
                    "type": "function_call",
                    "name": tool_call["function"]["name"],
                    "id": tool_call["id"],
                    "args": tool_call["function"]["arguments"]
                }

        # Add assistant message to history if we have content
        if words:
            assistant_message = LLM.LLMMessage(
                role=LLM.Role.ASSISTANT,
                content="".join(words).strip().replace("\n", " ")
            )
            self.add_message(assistant_message)

    async def interaction(self, message: LLMMessage) -> str:
        """Legacy method for backward compatibility"""
        words = []
        async for word in self.create_completion(message):
            if isinstance(word, str):
                words.append(word)
        return "".join(words)