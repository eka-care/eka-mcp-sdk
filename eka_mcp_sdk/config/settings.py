from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path


class EkaSettings(BaseSettings):
    """Configuration settings for Eka.care MCP Server."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="EKA_",
        case_sensitive=False,
        extra="ignore"  # Allow extra fields in .env file
    )
    
    # API Configuration
    api_base_url: str = Field(
        default="https://api.eka.care",
        description="Base URL for Eka.care APIs"
    )
    
    # Authentication
    client_id: Optional[str] = Field(
        default=None,
        description="Eka.care client ID - required for all API calls"
    )
    client_secret: Optional[str] = Field(
        default=None,
        description="Eka.care client secret - required only if not using external access token"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="Optional API key for additional authentication"
    )
    
    # MCP Server Configuration
    mcp_server_host: str = Field(default="localhost", description="MCP server host")
    mcp_server_port: int = Field(default=8000, description="MCP server port")
    
    # Token Storage Configuration
    token_storage_dir: Optional[str] = Field(
        default=None,
        description="Directory for storing authentication tokens (default: ~/.eka_mcp)"
    )
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    


settings = EkaSettings()