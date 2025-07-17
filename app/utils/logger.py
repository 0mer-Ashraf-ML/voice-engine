import logging
import sys
from datetime import datetime
from pathlib import Path
from app.config import settings

def setup_logger(name: str = "vapi_clone", level: str = "INFO") -> logging.Logger:
    """Setup application logger with file and console handlers"""
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
    
    simple_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler (if not in debug mode)
    if not settings.DEBUG:
        # Create logs directory
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(
            log_dir / f"vapi_clone_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
        
        # Error file handler
        error_handler = logging.FileHandler(
            log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        logger.addHandler(error_handler)
    
    return logger

def get_logger(name: str = "vapi_clone") -> logging.Logger:
    """Get logger instance"""
    return logging.getLogger(name)

# Custom log levels
def add_custom_log_level(level_name: str, level_num: int, method_name: str = None):
    """Add a custom log level"""
    if not method_name:
        method_name = level_name.lower()
    
    if hasattr(logging, level_name):
        raise AttributeError(f'{level_name} already defined in logging module')
    
    if hasattr(logging, method_name):
        raise AttributeError(f'{method_name} already defined in logging module')
    
    if hasattr(logging.getLoggerClass(), method_name):
        raise AttributeError(f'{method_name} already defined in logger class')
    
    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(level_num):
            self._log(level_num, message, args, **kwargs)
    
    def logToRoot(message, *args, **kwargs):
        logging.log(level_num, message, *args, **kwargs)
    
    logging.addLevelName(level_num, level_name)
    setattr(logging, level_name, level_num)
    setattr(logging.getLoggerClass(), method_name, logForLevel)
    setattr(logging, method_name, logToRoot)

# API request logging
class APIRequestLogger:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_request(self, method: str, path: str, user_id: str = None, organization_id: str = None):
        """Log API request"""
        self.logger.info(
            f"API Request: {method} {path}",
            extra={
                "method": method,
                "path": path,
                "user_id": user_id,
                "organization_id": organization_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def log_response(self, method: str, path: str, status_code: int, response_time: float):
        """Log API response"""
        self.logger.info(
            f"API Response: {method} {path} - {status_code} ({response_time:.3f}s)",
            extra={
                "method": method,
                "path": path,
                "status_code": status_code,
                "response_time": response_time,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def log_error(self, method: str, path: str, error: Exception, user_id: str = None):
        """Log API error"""
        self.logger.error(
            f"API Error: {method} {path} - {str(error)}",
            extra={
                "method": method,
                "path": path,
                "error": str(error),
                "error_type": type(error).__name__,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            exc_info=True
        )

# Call logging
class CallLogger:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_call_start(self, call_id: str, assistant_id: str, call_type: str):
        """Log call start"""
        self.logger.info(
            f"Call Started: {call_id} - Type: {call_type}",
            extra={
                "call_id": call_id,
                "assistant_id": assistant_id,
                "call_type": call_type,
                "event": "call_start",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def log_call_end(self, call_id: str, duration: int, end_reason: str, cost: float = 0):
        """Log call end"""
        self.logger.info(
            f"Call Ended: {call_id} - Duration: {duration}s - Reason: {end_reason} - Cost: ${cost:.4f}",
            extra={
                "call_id": call_id,
                "duration": duration,
                "end_reason": end_reason,
                "cost": cost,
                "event": "call_end",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def log_call_error(self, call_id: str, error: Exception, context: dict = None):
        """Log call error"""
        self.logger.error(
            f"Call Error: {call_id} - {str(error)}",
            extra={
                "call_id": call_id,
                "error": str(error),
                "error_type": type(error).__name__,
                "context": context or {},
                "event": "call_error",
                "timestamp": datetime.utcnow().isoformat()
            },
            exc_info=True
        )

# Usage logging
class UsageLogger:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_usage(self, organization_id: str, usage_type: str, quantity: float, cost: float):
        """Log usage event"""
        self.logger.info(
            f"Usage: {organization_id} - {usage_type} - {quantity} units - ${cost:.4f}",
            extra={
                "organization_id": organization_id,
                "usage_type": usage_type,
                "quantity": quantity,
                "cost": cost,
                "event": "usage",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def log_billing_event(self, organization_id: str, event_type: str, amount: float):
        """Log billing event"""
        self.logger.info(
            f"Billing: {organization_id} - {event_type} - ${amount:.2f}",
            extra={
                "organization_id": organization_id,
                "event_type": event_type,
                "amount": amount,
                "event": "billing",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# Security logging
class SecurityLogger:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_auth_success(self, user_id: str, email: str, ip_address: str = None):
        """Log successful authentication"""
        self.logger.info(
            f"Auth Success: {email} ({user_id})",
            extra={
                "user_id": user_id,
                "email": email,
                "ip_address": ip_address,
                "event": "auth_success",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def log_auth_failure(self, email: str, reason: str, ip_address: str = None):
        """Log failed authentication"""
        self.logger.warning(
            f"Auth Failure: {email} - {reason}",
            extra={
                "email": email,
                "reason": reason,
                "ip_address": ip_address,
                "event": "auth_failure",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def log_suspicious_activity(self, user_id: str, activity: str, details: dict = None):
        """Log suspicious activity"""
        self.logger.warning(
            f"Suspicious Activity: {user_id} - {activity}",
            extra={
                "user_id": user_id,
                "activity": activity,
                "details": details or {},
                "event": "suspicious_activity",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# Setup default logger
logger = setup_logger()

# Create specialized loggers
api_logger = APIRequestLogger(logger)
call_logger = CallLogger(logger)
usage_logger = UsageLogger(logger)
security_logger = SecurityLogger(logger)

# Export commonly used loggers
__all__ = [
    "setup_logger",
    "get_logger",
    "logger",
    "api_logger", 
    "call_logger",
    "usage_logger",
    "security_logger",
    "APIRequestLogger",
    "CallLogger",
    "UsageLogger",
    "SecurityLogger"
]