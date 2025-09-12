"""Local configuration settings for the Wine Concierge application."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional, Any
import os
from pathlib import Path

class Settings(BaseSettings):
    """Application settings with local defaults."""
    
    # Application
    APP_NAME: str = "Wine Concierge"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # LLM Settings (GPT4All)
    LLM_MODEL: str = Field(
        default="orca-2-7b.Q4_0.gguf",
        description="Name of the GPT4All model to use"
    )
    LLM_MODEL_PATH: str = Field(
        default=str(Path(__file__).parent.parent / "models"),
        description="Path to store/load LLM models"
    )
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 1000

    # Search Settings (DuckDuckGo)
    SEARCH_MAX_RESULTS: int = Field(
        default=5,
        description="Maximum number of search results to return"
    )
    
    # Weather
    DEFAULT_LOCATION: str = Field(
        default="New York,US",
        description="Default location for weather queries"
    )
    OPENWEATHER_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenWeather API key (optional for weather features)"
    )

    # Pydantic v2 config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore'
    )

# Create instance of settings
settings = Settings()

# Create models directory if it doesn't exist
os.makedirs(settings.LLM_MODEL_PATH, exist_ok=True)
