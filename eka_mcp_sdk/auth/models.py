from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import base64
import json
import jwt


class TokenResponse(BaseModel):
    """Token response from Eka.care API."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 1800  # 30 minutes


class AuthContext(BaseModel):
    """Authentication context for API requests."""
    access_token: str
    
    @property
    def is_token_expired(self) -> bool:
        """Check if the access token is expired by parsing JWT exp claim."""
        try:
            token_data =  jwt.decode(self.access_token, options={"verify_signature": False})
            exp_timestamp = token_data.get('exp')
            if not exp_timestamp:
                return False  # No expiry claim, assume valid
            
            return datetime.now().timestamp() >= exp_timestamp
            
        except Exception:
            return True  # If parsing fails, assume expired
    
    @property
    def auth_headers(self) -> dict:
        """Get authorization headers for API requests."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "jwt-payload": json.dumps(jwt.decode(self.access_token, options={"verify_signature": False}))
        }
        return headers


class EkaAPIError(Exception):
    """Custom exception for Eka.care API errors."""
    
    def __init__(self, message: str, status_code: int = None, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)
