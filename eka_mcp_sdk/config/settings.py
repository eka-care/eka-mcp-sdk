from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Type, TypeVar
from pathlib import Path

T = TypeVar('T', bound='BaseEkaSettings')


class BaseEkaSettings(BaseSettings):
    """Base configuration settings for Eka.care SDK."""
    
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
    
    # Token Storage Configuration
    token_storage_dir: Optional[str] = Field(
        default=None,
        description="Directory for storing authentication tokens (default: ~/.eka_mcp)"
    )
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    
    @classmethod
    def create_settings_class(
        cls: Type[T],
        env_prefix: str = "EKA_",
        env_file: str = ".env",
        case_sensitive: bool = False,
        extra: str = "ignore"
    ) -> Type[T]:
        """Create a settings class with custom configuration."""
        
        class ConfiguredSettings(cls):
            model_config = SettingsConfigDict(
                env_file=env_file,
                env_prefix=env_prefix,
                case_sensitive=case_sensitive,
                extra=extra
            )
        
        return ConfiguredSettings


class EkaSettings(BaseEkaSettings):
    """Default MCP Server configuration settings."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="EKA_",
        case_sensitive=False,
        extra="ignore"  # Allow extra fields in .env file
    )
    
    # MCP Server Configuration
    mcp_server_host: str = Field(default="localhost", description="MCP server host")
    mcp_server_port: int = Field(default=8000, description="MCP server port")


# Global settings registry
_current_settings: Optional[BaseEkaSettings] = None


def configure_settings(settings_instance: BaseEkaSettings) -> None:
    """Configure global settings for the SDK. Call this at startup."""
    global _current_settings
    _current_settings = settings_instance


def get_current_settings() -> BaseEkaSettings:
    """Get the currently configured settings instance."""
    if _current_settings is None:
        # Auto-initialize with default settings if not configured
        configure_settings(EkaSettings())
    return _current_settings


def reset_settings() -> None:
    """Reset settings to None. Useful for testing."""
    global _current_settings
    _current_settings = None


# For backward compatibility - initialize with default settings
settings = EkaSettings()