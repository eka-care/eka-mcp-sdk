from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TokenResponse(BaseModel):
    """Token response from Eka.care API."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 1800  # 30 minutes


class AuthContext(BaseModel):
    """Authentication context for API requests."""
    access_token: str
    token_expires_at: datetime
    api_key: Optional[str] = None
    
    @property
    def is_token_expired(self) -> bool:
        """Check if the access token is expired."""
        return datetime.now() >= self.token_expires_at
    
    @property
    def auth_headers(self) -> dict:
        """Get authorization headers for API requests."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers


class EkaAPIError(Exception):
    """Custom exception for Eka.care API errors."""
    
    def __init__(self, message: str, status_code: int = None, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)