from pydantic import Field, ValidationError
from fastmcp.settings import ENV_FILE
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class EkaSettings(BaseSettings):
    """Base configuration settings for Eka.care SDK."""
    
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_prefix="EKA_",
        extra="ignore"
    )
    
    # API Configuration
    api_base_url: str = Field(
        default="https://api.eka.care",
        description="Base URL for Eka.care APIs"
    )
    
    # Authentication
    client_id: str = Field(
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
    
    # Token Storage Configuration
    token_storage_dir: Optional[str] = Field(
        default=None,
        description="Directory for storing authentication tokens (default: ~/.eka_mcp)"
    )
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Workspace Configuration
    workspace_client_type: str = Field(
        default="ekaemr",
        description="Workspace client type: ekaemr, moolchand, ekap"
    )
    