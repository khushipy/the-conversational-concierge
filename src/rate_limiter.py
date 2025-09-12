"""
Rate limiting middleware for FastAPI application.

This module provides rate limiting functionality using slowapi and in-memory storage.
For production use, consider using Redis or another distributed storage backend.
"""

from typing import Callable, Optional, List
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from functools import wraps
import logging

from config import settings

logger = logging.getLogger(__name__)

# Initialize rate limiter with configuration from settings
limiter = Limiter(
    key_func=get_remote_address,  # Rate limit by IP address
    default_limits=[settings.RATE_LIMIT],
    storage_uri=settings.RATE_LIMIT_STORAGE_URI,
    headers_enabled=True,
)

def get_limiter():
    """Get the rate limiter instance."""
    return limiter

def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded errors."""
    logger.warning(f"Rate limit exceeded for {request.client.host}")
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": f"Rate limit exceeded: {exc.detail}",
            "retry_after": f"{exc.retry_after} seconds",
            "limits": {
                "limit": exc.limit,
                "remaining": 0,
                "reset": exc.reset
            }
        },
        headers={
            "Retry-After": str(exc.retry_after),
            "X-RateLimit-Limit": str(exc.limit),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(exc.reset)
        }
    )

def get_rate_limiter_middleware():
    """Get the rate limiter middleware."""
    return SlowAPIMiddleware(
        limiter=limiter,
        key_func=get_remote_address,
        default_limits=[f"{settings.RATE_LIMIT} per minute"],
        headers_enabled=True,
    )

def get_rate_limit_decorator(limit: str = None):
    """
    Get a rate limit decorator for specific endpoints.
    
    Args:
        limit: Rate limit string (e.g., "5 per minute", "100 per hour")
    
    Returns:
        Decorator function that applies rate limiting
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        # Apply the rate limit if specified
        if limit:
            wrapper = limiter.limit(limit)(wrapper)
        
        return wrapper
    return decorator

# Common rate limits from settings
RATE_LIMITS = {
    "default": settings.RATE_LIMIT,
    "strict": settings.RATE_LIMIT_STRICT,
    "public": settings.RATE_LIMIT_PUBLIC,
    "auth": settings.RATE_LIMIT_AUTH,
}

# Apply rate limiting to specific endpoints
rate_limited = get_rate_limit_decorator()
rate_limited_strict = get_rate_limit_decorator(RATE_LIMITS["strict"])
rate_limited_generous = get_rate_limit_decorator(RATE_LIMITS["generous"])
rate_limited_public = get_rate_limit_decorator(RATE_LIMITS["public"])
rate_limited_auth = get_rate_limit_decorator(RATE_LIMITS["auth"])
