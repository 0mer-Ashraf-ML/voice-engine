from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
import json
import uuid
from contextlib import asynccontextmanager

from app.config import settings
from app.database import Base, engine
from app.api import api_router
from app.utils.logger import get_logger, api_logger, security_logger
from app.auth import get_current_user
from app.models.user import User
from app.websocket import manager

# Initialize logger
logger = get_logger(__name__)

# Custom middleware for request logging and timing
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Log request
        api_logger.log_request(
            method=request.method,
            path=request.url.path,
            user_id=getattr(request.state, 'user_id', None),
            organization_id=getattr(request.state, 'organization_id', None)
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Log response
        api_logger.log_response(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            response_time=response_time
        )
        
        # Add response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{response_time:.3f}s"
        
        return response

# Custom middleware for user context
class UserContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for public endpoints
        public_paths = [
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/register",
            "/auth/login"
        ]
        
        if request.url.path in public_paths:
            return await call_next(request)
        
        # Try to get user from authorization header
        try:
            if hasattr(request.state, 'user'):
                user = request.state.user
                request.state.user_id = str(user.id)
                request.state.organization_id = str(user.organization_id)
        except Exception:
            # User context not available, continue without it
            pass
        
        return await call_next(request)

# Database startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Vapi Clone application...")
    
    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise
    
    # Additional startup tasks
    logger.info("Application startup completed")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Vapi Clone application...")
    # Cleanup tasks would go here
    logger.info("Application shutdown completed")

# Create FastAPI application
# app = FastAPI(
#     title=settings.APP_NAME,
#     version="1.0.0",
#     description="Voice AI platform - A complete Vapi AI clone",
#     docs_url="/docs" if settings.DEBUG else None,
#     redoc_url="/redoc" if settings.DEBUG else None,
#     openapi_url="/openapi.json" if settings.DEBUG else None,
#     lifespan=lifespan
# )
app = FastAPI()

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(UserContextMiddleware)

# Custom exception handlers
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Custom HTTP exception handler"""
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    
    # Log security-related errors
    if exc.status_code in [401, 403]:
        security_logger.log_auth_failure(
            email="unknown",
            reason=exc.detail,
            ip_address=request.client.host if request.client else None
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "request_id": getattr(request.state, 'request_id', None)
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom validation exception handler"""
    logger.error(f"Validation Error: {exc.errors()}")
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation failed",
            "details": exc.errors(),
            "status_code": 422,
            "request_id": getattr(request.state, 'request_id', None)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "request_id": getattr(request.state, 'request_id', None)
        }
    )

# Include API routers
app.include_router(api_router, prefix="/api/v1")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0",
        "service": settings.APP_NAME
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Vapi Clone - Voice AI Platform",
        "version": "1.0.0",
        "docs_url": "/docs" if settings.DEBUG else None,
        "health_url": "/health"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Additional startup tasks"""
    logger.info("Application started successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup tasks on shutdown"""
    logger.info("Application shutting down")

# WebSocket endpoint for real-time call handling
@app.websocket("/ws/calls/{call_id}")
async def websocket_endpoint(websocket, call_id: str):
    """WebSocket endpoint for real-time call communication"""
    from app.websocket import manager
    
    connection_id = str(uuid.uuid4())
    await manager.connect(websocket, connection_id)
    manager.register_call(call_id, connection_id)
    
    try:
        await manager.broadcast_call_status(call_id, "connected")
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "start_call":
                await manager.broadcast_call_status(call_id, "in-progress")
            elif message.get("type") == "end_call":
                await manager.broadcast_call_status(call_id, "completed")
                break
            elif message.get("type") == "transcript":
                await manager.broadcast_transcript(
                    call_id, 
                    message.get("text", ""), 
                    message.get("is_user", True)
                )
    
    except Exception as e:
        logger.error(f"WebSocket error for call {call_id}: {e}")
        await manager.broadcast_call_status(call_id, "error")
    
    finally:
        manager.disconnect(connection_id)

# API rate limiting (basic implementation)
from collections import defaultdict
from datetime import datetime, timedelta

rate_limit_storage = defaultdict(list)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Basic rate limiting middleware"""
    # Skip rate limiting for certain paths
    if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)
    
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Rate limit: 100 requests per minute
    now = datetime.utcnow()
    minute_ago = now - timedelta(minutes=1)
    
    # Clean old requests
    rate_limit_storage[client_ip] = [
        req_time for req_time in rate_limit_storage[client_ip] 
        if req_time > minute_ago
    ]
    
    # Check rate limit
    if len(rate_limit_storage[client_ip]) >= 100:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please try again later.",
                "retry_after": 60
            }
        )
    
    # Add current request
    rate_limit_storage[client_ip].append(now)
    
    return await call_next(request)

# API Documentation customization
if settings.DEBUG:
    @app.get("/api/docs")
    async def api_documentation():
        """API documentation endpoint"""
        return {
            "message": "API Documentation",
            "endpoints": {
                "authentication": "/api/v1/auth/",
                "assistants": "/api/v1/assistants/",
                "calls": "/api/v1/calls/",
                "phone_numbers": "/api/v1/phone-numbers/",
                "squads": "/api/v1/squads/",
                "tools": "/api/v1/tools/",
                "users": "/api/v1/users/",
                "usage": "/api/v1/usage/"
            },
            "websocket": "/ws/calls/{call_id}",
            "swagger_ui": "/docs",
            "redoc": "/redoc"
        }

# Metrics endpoint (basic)

@app.get("/metrics")
async def metrics():
    """Basic metrics endpoint"""
    return {
        "requests_total": len(rate_limit_storage),
        "active_connections": len(manager.active_connections),
        "uptime": time.time() - start_time if 'start_time' in globals() else 0,
        "memory_usage": "N/A",  # Would implement actual memory monitoring
        "database_connections": "N/A"  # Would implement actual DB monitoring
    }

# Admin endpoints (protected)
@app.get("/admin/health")
async def admin_health_check(current_user: User = Depends(get_current_user)):
    """Admin health check with detailed information"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return {
        "status": "healthy",
        "database": "connected",
        "integrations": {
            "elevenlabs": "configured" if settings.ELEVENLABS_API_KEY else "not configured",
            "deepgram": "configured" if settings.DEEPGRAM_API_KEY else "not configured",
            "openai": "configured" if settings.OPENAI_API_KEY else "not configured",
            "twilio": "configured" if settings.TWILIO_ACCOUNT_SID else "not configured",
            "stripe": "configured" if settings.STRIPE_SECRET_KEY else "not configured"
        },
        "environment": "debug" if settings.DEBUG else "production",
        "timestamp": datetime.utcnow().isoformat()
    }

# Error tracking for monitoring
error_counts = defaultdict(int)

@app.middleware("http")
async def error_tracking_middleware(request: Request, call_next):
    """Track errors for monitoring"""
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        error_type = type(e).__name__
        error_counts[error_type] += 1
        logger.error(f"Error tracked: {error_type} - Count: {error_counts[error_type]}")
        raise

# Development helpers
if settings.DEBUG:
    @app.get("/debug/errors")
    async def debug_errors():
        """Debug endpoint to view error counts"""
        return dict(error_counts)
    
    @app.get("/debug/rate-limits")
    async def debug_rate_limits():
        """Debug endpoint to view rate limit status"""
        return {
            "rate_limits": {
                ip: len(requests) for ip, requests in rate_limit_storage.items()
            }
        }

# Record start time for uptime calculation
start_time = time.time()


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Vapi Clone application...")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )