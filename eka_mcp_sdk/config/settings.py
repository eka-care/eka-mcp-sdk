from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class EkaSettings(BaseSettings):
    """Configuration settings for Eka.care MCP Server."""
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )
    
    # API Configuration
    eka_api_base_url: str = Field(
        default="https://api.eka.care",
        description="Base URL for Eka.care APIs"
    )
    
    # Authentication
    eka_client_id: Optional[str] = Field(
        default=None,
        description="Eka.care client ID - get from ekaconnect@eka.care"
    )
    eka_client_secret: Optional[str] = Field(
        default=None,
        description="Eka.care client secret - get from ekaconnect@eka.care"
    )
    eka_api_key: Optional[str] = Field(
        default=None,
        description="Optional API key for additional authentication"
    )
    eka_access_token: Optional[str] = Field(
        default=None,
        description="External access token - if provided, client_id/secret not required"
    )
    
    # MCP Server Configuration
    mcp_server_host: str = Field(default="localhost", description="MCP server host")
    mcp_server_port: int = Field(default=8000, description="MCP server port")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    


settings = EkaSettings()