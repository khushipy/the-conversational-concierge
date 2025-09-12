"""Configuration settings for the Wine Concierge application (free version)."""
from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings."""
    # Application
    APP_NAME: str = "Wine Concierge (Free)"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # LLM Settings (GPT4All)
    LLM_MODEL: str = "orca-mini-3b-gguf2-q4_0.ggml"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 1000

    # Search Settings (DuckDuckGo)
    SEARCH_MAX_RESULTS: int = 5
    
    # Weather
    DEFAULT_LOCATION: str = "New York,US"

    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings():
    """Get application settings."""
    return Settings()

# Global settings
settings = get_settings()
