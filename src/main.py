"""
Main FastAPI application for the Wine Concierge Agent.
Handles web requests, serves the frontend, and manages API endpoints.
"""

from fastapi import FastAPI, Request, HTTPException, status, Depends, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any, Union, Callable, TypeVar, cast
import logging
import os
import time
import uuid
from pathlib import Path
from datetime import datetime, timedelta

# Import configuration
from config import settings

# Import rate limiter
from rate_limiter import (
    limiter,
    rate_limit_exceeded_handler,
    get_rate_limiter_middleware,
    rate_limited,
    rate_limited_strict,
    rate_limited_public,
    rate_limited_auth,
    RateLimitExceeded
)

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app with metadata
app = FastAPI(
    title="Wine Concierge Agent",
    description="A conversational AI agent for wine recommendations and information",
    version="1.0.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_middleware(get_rate_limiter_middleware())

# Mount static files
app.mount(
    "/static", 
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "static")), 
    name="static"
)

# Initialize templates
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))

# Models
class Message(BaseModel):
    """Represents a message in the chat."""
    role: str = Field(..., description="The role of the message sender, either 'user' or 'assistant'")
    content: str = Field(..., description="The content of the message")

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    messages: List[Message] = Field(..., description="List of messages in the conversation")
    location: Optional[str] = Field(
        None, 
        description="Optional location for weather context"
    )

class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    messages: List[Message] = Field(..., description="List of messages including the assistant's response")
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata about the response"
    )

class WeatherResponse(BaseModel):
    """Response model for weather endpoint."""
    location: str = Field(..., description="The location for which weather was requested")
    weather: str = Field(..., description="Current weather condition")
    temperature: float = Field(..., description="Current temperature in Fahrenheit")
    humidity: Optional[float] = Field(None, description="Current humidity percentage")
    wind_speed: Optional[float] = Field(None, description="Wind speed in mph")
    timestamp: str = Field(..., description="Timestamp of the weather data")

class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Current environment")

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with JSON responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions with a 500 status code."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )

# Middleware for logging requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and their responses."""
    logger.info(f"Request: {request.method} {request.url}")
    
    try:
        response = await call_next(request)
        logger.info(f"Response: {request.method} {request.url} - {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Error processing {request.method} {request.url}: {str(e)}")
        raise

# Routes
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def read_root(request: Request):
    """
    Serve the main chat interface.
    
    Args:
        request: The incoming request object.
        
    Returns:
        TemplateResponse: The rendered index.html template.
    """
    try:
        return templates.TemplateResponse(
            "index.html", 
            {
                "request": request,
                "environment": settings.ENVIRONMENT,
                "web_search_enabled": settings.is_web_search_enabled,
                "default_location": settings.DEFAULT_LOCATION
            }
        )
    except Exception as e:
        logger.error(f"Error rendering template: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error loading the application. Please try again later."
        )

@app.post("/api/chat", response_model=ChatResponse, tags=["chat"])
@rate_limited_strict  # Apply strict rate limiting to chat endpoint
@limiter.limit("10/minute")  # Additional rate limiting for extra protection
async def chat(
    request: Request,
    chat_request: ChatRequest,
    background_tasks: BackgroundTasks
):
    """
    Handle chat messages from the user and return the assistant's response.
    
    Args:
        chat_request: The chat request containing the conversation history.
        
    Returns:
        ChatResponse: The assistant's response along with any metadata.
    """
    try:
        # TODO: Integrate with LangGraph agent
        logger.info(f"Processing chat request: {chat_request}")
        
        # This is a placeholder response - will be replaced with actual agent integration
        response = ChatResponse(
            messages=[
                Message(
                    role="assistant",
                    content="I'm your wine concierge. How can I assist you with wine recommendations today?"
                )
            ],
            metadata={
                "model": settings.DEFAULT_LLM_MODEL,
                "location": chat_request.location or settings.DEFAULT_LOCATION,
                "web_search_used": False
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request."
        )

@app.get("/api/weather", response_model=WeatherResponse, tags=["weather"])
@rate_limited_public  # Apply public rate limiting to weather endpoint
@limiter.limit("30/minute")  # Additional rate limiting for weather API
async def get_weather(
    request: Request,
    location: str = settings.DEFAULT_LOCATION,
    units: str = "imperial"
):
    """
    Get current weather for a specified location.
    
    Args:
        location: The location to get weather for (city,country or lat,lon).
        units: The unit system to use (metric or imperial).
        
    Returns:
        WeatherResponse: The current weather information for the location.
    """
    try:
        # TODO: Integrate with weather service
        logger.info(f"Fetching weather for location: {location}")
        
        # This is a placeholder response - will be replaced with actual weather service integration
        return WeatherResponse(
            location=location,
            weather="sunny",
            temperature=72.0,
            humidity=45.0,
            wind_speed=5.2,
            timestamp="2023-11-15T14:30:00Z"
        )
        
    except Exception as e:
        logger.error(f"Error in weather endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch weather information. Please try again later."
        )

@app.get("/api/health", response_model=HealthCheckResponse, tags=["system"])
@rate_limited  # Apply default rate limiting to health check
async def health_check(request: Request):
    """
    Health check endpoint to verify the service is running.
    
    Returns:
        HealthCheckResponse: The current health status of the service.
    """
    try:
        # TODO: Add more comprehensive health checks (database, external services, etc.)
        return HealthCheckResponse(
            status="healthy",
            version=settings.VERSION if hasattr(settings, "VERSION") else "1.0.0",
            environment=settings.ENVIRONMENT
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is not healthy"
        )

# Application startup event
@app.on_event("startup")
async def startup_event():
    """Run startup tasks."""
    logger.info("Starting Wine Concierge Agent...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Ensure required directories exist
    for directory in [settings.DATA_DIR, settings.VECTOR_STORE_DIR, settings.LOG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # Log rate limiting configuration
    logger.info(f"Rate limiting enabled: {settings.RATE_LIMIT} requests per minute")
    logger.info("Startup tasks completed")

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        workers=1
    )
