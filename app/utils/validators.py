import re
import json
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

def validate_webhook_url(url: str) -> bool:
    """Validate webhook URL format"""
    if not url:
        return False
    
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ('http', 'https')
    except Exception:
        return False

def validate_model_config(config: Dict[str, Any], provider: str) -> tuple[bool, Optional[str]]:
    """Validate model configuration"""
    if not isinstance(config, dict):
        return False, "Configuration must be a dictionary"
    
    # Provider-specific validation
    if provider == "openai":
        return _validate_openai_config(config)
    elif provider == "anthropic":
        return _validate_anthropic_config(config)
    elif provider == "groq":
        return _validate_groq_config(config)
    else:
        return False, f"Unsupported provider: {provider}"

def _validate_openai_config(config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Validate OpenAI model configuration"""
    required_fields = ["model"]
    
    for field in required_fields:
        if field not in config:
            return False, f"Missing required field: {field}"
    
    # Validate model name
    valid_models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
    if config["model"] not in valid_models:
        return False, f"Invalid model: {config['model']}"
    
    # Validate temperature
    if "temperature" in config:
        temp = config["temperature"]
        if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
            return False, "Temperature must be between 0 and 2"
    
    # Validate max_tokens
    if "max_tokens" in config:
        tokens = config["max_tokens"]
        if not isinstance(tokens, int) or tokens < 1 or tokens > 8192:
            return False, "max_tokens must be between 1 and 8192"
    
    return True, None

def _validate_anthropic_config(config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Validate Anthropic model configuration"""
    required_fields = ["model"]
    
    for field in required_fields:
        if field not in config:
            return False, f"Missing required field: {field}"
    
    # Validate model name
    valid_models = ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]
    if config["model"] not in valid_models:
        return False, f"Invalid model: {config['model']}"
    
    # Validate temperature
    if "temperature" in config:
        temp = config["temperature"]
        if not isinstance(temp, (int, float)) or temp < 0 or temp > 1:
            return False, "Temperature must be between 0 and 1"
    
    # Validate max_tokens
    if "max_tokens" in config:
        tokens = config["max_tokens"]
        if not isinstance(tokens, int) or tokens < 1 or tokens > 4096:
            return False, "max_tokens must be between 1 and 4096"
    
    return True, None

def _validate_groq_config(config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Validate Groq model configuration"""
    required_fields = ["model"]
    
    for field in required_fields:
        if field not in config:
            return False, f"Missing required field: {field}"
    
    # Validate model name
    valid_models = ["mixtral-8x7b-32768", "llama2-70b-4096", "gemma-7b-it"]
    if config["model"] not in valid_models:
        return False, f"Invalid model: {config['model']}"
    
    return True, None

def validate_voice_settings(settings: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Validate ElevenLabs voice settings"""
    if not isinstance(settings, dict):
        return False, "Voice settings must be a dictionary"
    
    # Validate stability
    if "stability" in settings:
        stability = settings["stability"]
        if not isinstance(stability, (int, float)) or stability < 0 or stability > 1:
            return False, "Stability must be between 0 and 1"
    
    # Validate similarity_boost
    if "similarity_boost" in settings:
        similarity = settings["similarity_boost"]
        if not isinstance(similarity, (int, float)) or similarity < 0 or similarity > 1:
            return False, "Similarity boost must be between 0 and 1"
    
    # Validate style
    if "style" in settings:
        style = settings["style"]
        if not isinstance(style, (int, float)) or style < 0 or style > 1:
            return False, "Style must be between 0 and 1"
    
    return True, None

def validate_phone_number_format(phone_number: str) -> bool:
    """Validate phone number format"""
    # Basic phone number validation
    pattern = r'^\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})$'
    return bool(re.match(pattern, phone_number))

def validate_json_schema(data: Any, schema: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Basic JSON schema validation"""
    try:
        # This is a simplified validator - in production you'd use jsonschema library
        if "type" in schema:
            expected_type = schema["type"]
            
            if expected_type == "object" and not isinstance(data, dict):
                return False, "Expected object"
            elif expected_type == "array" and not isinstance(data, list):
                return False, "Expected array"
            elif expected_type == "string" and not isinstance(data, str):
                return False, "Expected string"
            elif expected_type == "number" and not isinstance(data, (int, float)):
                return False, "Expected number"
            elif expected_type == "boolean" and not isinstance(data, bool):
                return False, "Expected boolean"
        
        # Validate required fields for objects
        if isinstance(data, dict) and "required" in schema:
            for field in schema["required"]:
                if field not in data:
                    return False, f"Missing required field: {field}"
        
        return True, None
        
    except Exception as e:
        return False, str(e)

def validate_webhook_signature_format(signature: str) -> bool:
    """Validate webhook signature format"""
    # Should be in format: sha256=<hex_string>
    pattern = r'^sha256=[a-f0-9]{64}$'
    return bool(re.match(pattern, signature))

def validate_assistant_name(name: str) -> tuple[bool, Optional[str]]:
    """Validate assistant name"""
    if not name or not name.strip():
        return False, "Assistant name cannot be empty"
    
    if len(name) < 2:
        return False, "Assistant name must be at least 2 characters"
    
    if len(name) > 100:
        return False, "Assistant name cannot exceed 100 characters"
    
    # Allow letters, numbers, spaces, hyphens, underscores
    if not re.match(r'^[a-zA-Z0-9\s\-_]+$', name):
        return False, "Assistant name contains invalid characters"
    
    return True, None

def validate_system_prompt(prompt: str) -> tuple[bool, Optional[str]]:
    """Validate system prompt"""
    if not prompt:
        return True, None  # System prompt is optional
    
    if len(prompt) > 10000:
        return False, "System prompt cannot exceed 10,000 characters"
    
    # Check for potentially harmful content (basic check)
    harmful_patterns = [
        r'<script[^>]*>',
        r'javascript:',
        r'data:text/html'
    ]
    
    for pattern in harmful_patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            return False, "System prompt contains potentially harmful content"
    
    return True, None

def validate_call_metadata(metadata: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Validate call metadata"""
    if not isinstance(metadata, dict):
        return False, "Metadata must be a dictionary"
    
    # Check size limit (1MB when serialized)
    try:
        serialized = json.dumps(metadata)
        if len(serialized.encode('utf-8')) > 1024 * 1024:  # 1MB
            return False, "Metadata size exceeds 1MB limit"
    except Exception:
        return False, "Metadata is not JSON serializable"
    
    # Check for valid keys (no special characters that could cause issues)
    for key in metadata.keys():
        if not isinstance(key, str):
            return False, "All metadata keys must be strings"
        
        if not re.match(r'^[a-zA-Z0-9_\-\.]+$', key):
            return False, f"Invalid metadata key: {key}"
    
    return True, None