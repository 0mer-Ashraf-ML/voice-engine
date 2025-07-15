import uuid
import re
import hashlib
import secrets
import string
from typing import Optional, Any, Dict
from datetime import datetime, timezone
import phonenumbers
from phonenumbers import NumberParseException

def generate_uuid() -> str:
    """Generate a new UUID string"""
    return str(uuid.uuid4())

def generate_api_key(prefix: str = "vapi") -> str:
    """Generate a secure API key"""
    suffix = secrets.token_urlsafe(32)
    return f"{prefix}_{suffix}"

def hash_string(value: str, salt: str = None) -> str:
    """Hash a string with optional salt"""
    if salt:
        value = f"{value}{salt}"
    return hashlib.sha256(value.encode()).hexdigest()

def format_phone_number(phone_number: str, country_code: str = "US") -> Optional[str]:
    """Format phone number to international format"""
    try:
        parsed = phonenumbers.parse(phone_number, country_code)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        return None
    except NumberParseException:
        return None

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def sanitize_string(value: str, max_length: int = None) -> str:
    """Sanitize string input"""
    if not isinstance(value, str):
        value = str(value)
    
    # Remove potentially dangerous characters
    value = re.sub(r'[<>"\']', '', value)
    
    # Trim whitespace
    value = value.strip()
    
    # Limit length
    if max_length and len(value) > max_length:
        value = value[:max_length]
    
    return value

def convert_to_utc(dt: datetime) -> datetime:
    """Convert datetime to UTC"""
    if dt.tzinfo is None:
        # Assume local timezone if none specified
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def calculate_duration(start_time: datetime, end_time: datetime = None) -> int:
    """Calculate duration in seconds"""
    if end_time is None:
        end_time = datetime.utcnow()
    
    duration = end_time - start_time
    return int(duration.total_seconds())

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def parse_duration_string(duration_str: str) -> int:
    """Parse duration string (e.g., '1h30m', '45s') to seconds"""
    if not duration_str:
        return 0
    
    # Remove spaces
    duration_str = duration_str.replace(" ", "").lower()
    
    # Parse different units
    total_seconds = 0
    
    # Hours
    if 'h' in duration_str:
        hours_match = re.search(r'(\d+)h', duration_str)
        if hours_match:
            total_seconds += int(hours_match.group(1)) * 3600
    
    # Minutes
    if 'm' in duration_str:
        minutes_match = re.search(r'(\d+)m', duration_str)
        if minutes_match:
            total_seconds += int(minutes_match.group(1)) * 60
    
    # Seconds
    if 's' in duration_str:
        seconds_match = re.search(r'(\d+)s', duration_str)
        if seconds_match:
            total_seconds += int(seconds_match.group(1))
    
    # If no units found, assume seconds
    if total_seconds == 0 and duration_str.isdigit():
        total_seconds = int(duration_str)
    
    return total_seconds

def format_duration(seconds: int) -> str:
    """Format seconds to human-readable duration"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        if remaining_seconds > 0:
            return f"{minutes}m {remaining_seconds}s"
        return f"{minutes}m"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        if remaining_minutes > 0:
            return f"{hours}h {remaining_minutes}m"
        return f"{hours}h"

def format_currency(amount: float, currency: str = "USD") -> str:
    """Format currency amount"""
    if currency.upper() == "USD":
        return f"${amount:.2f}"
    else:
        return f"{amount:.2f} {currency}"

def extract_domain_from_url(url: str) -> Optional[str]:
    """Extract domain from URL"""
    try:
        # Remove protocol
        if url.startswith(('http://', 'https://')):
            url = url.split('://', 1)[1]
        
        # Extract domain (remove path, query, fragment)
        domain = url.split('/')[0].split('?')[0].split('#')[0]
        
        return domain.lower()
    except Exception:
        return None

def generate_random_string(length: int = 10, include_digits: bool = True) -> str:
    """Generate random string"""
    chars = string.ascii_letters
    if include_digits:
        chars += string.digits
    
    return ''.join(secrets.choice(chars) for _ in range(length))

def is_valid_uuid(uuid_string: str) -> bool:
    """Check if string is valid UUID"""
    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False

def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """Mask sensitive data showing only first/last characters"""
    if len(data) <= visible_chars * 2:
        return "*" * len(data)
    
    return data[:visible_chars] + "*" * (len(data) - visible_chars * 2) + data[-visible_chars:]

def parse_boolean(value: Any) -> bool:
    """Parse various inputs to boolean"""
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
    
    if isinstance(value, int):
        return value != 0
    
    return False

def deep_merge_dict(dict1: dict, dict2: dict) -> dict:
    """Deep merge two dictionaries"""
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dict(result[key], value)
        else:
            result[key] = value
    
    return result