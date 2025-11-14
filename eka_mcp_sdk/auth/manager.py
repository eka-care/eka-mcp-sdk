import httpx
from typing import Optional
from datetime import datetime, timedelta
import logging

from ..config.settings import settings
from .models import TokenResponse, AuthContext, EkaAPIError

logger = logging.getLogger(__name__)


class AuthenticationManager:
    """Manages authentication for Eka.care APIs."""
    
    def __init__(self, external_access_token: Optional[str] = None):
        self._auth_context: Optional[AuthContext] = None
        self._refresh_token: Optional[str] = None
        self._external_access_token = external_access_token
        self._http_client = httpx.AsyncClient(timeout=30.0)
    
    async def get_auth_context(self) -> AuthContext:
        """Get valid authentication context."""
        # If external access token is provided, use it directly
        if self._external_access_token:
            return AuthContext(
                access_token=self._external_access_token,
                api_key=None  # Not needed with access token
            )
        
        # Check if we have a valid access token
        if (self._auth_context and 
            not self._auth_context.is_token_expired):
            return self._auth_context
        
        # Need to obtain/refresh access token
        if self._refresh_token:
            await self._refresh_access_token()
        else:
            await self._obtain_access_token()
        
        return self._auth_context
    
    async def _obtain_access_token(self) -> None:
        """Obtain access token using client credentials."""
        if not settings.eka_client_id or not settings.eka_client_secret:
            raise EkaAPIError("Client ID and Client Secret are required for authentication")
            
        url = f"{settings.eka_api_base_url}/connect-auth/v1/account/login"
        payload = {
            "client_id": settings.eka_client_id,
            "client_secret": settings.eka_client_secret,
            "api_key": settings.eka_api_key
        }
        
        logger.info(f"Making login request to: {url}")
        logger.debug(f"Request payload: {payload}")
        
        try:
            response = await self._http_client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            logger.info(f"Login response status: {response.status_code}")
            logger.debug(f"Login response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            token_data = response.json()
            logger.debug(f"Login response data: {token_data}")
            
            token_response = TokenResponse(**token_data)
            
            # Store auth context
            self._auth_context = AuthContext(
                access_token=token_response.access_token
            )
            self._refresh_token = token_response.refresh_token
            
            logger.info("Client credentials login successful")
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Client login failed - Status: {e.response.status_code}")
            logger.error(f"Client login failed - Response: {e.response.text}")
            logger.error(f"Client login failed - Headers: {dict(e.response.headers)}")
            raise EkaAPIError(f"Client login failed: {e.response.text}", e.response.status_code)
        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}")
            raise EkaAPIError(f"Login error: {str(e)}")
    
    async def _refresh_access_token(self) -> None:
        """Refresh access token using refresh token."""
        url = f"{settings.eka_api_base_url}/connect-auth/v1/account/refresh"
        payload = {"refreshToken": self._refresh_token}
        
        logger.info(f"Making refresh token request to: {url}")
        logger.debug(f"Refresh token payload: {payload}")
        
        try:
            response = await self._http_client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            logger.info(f"Refresh response status: {response.status_code}")
            logger.debug(f"Refresh response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            token_data = response.json()
            logger.debug(f"Refresh response data: {token_data}")
            
            token_response = TokenResponse(**token_data)
            
            # Update auth context
            self._auth_context = AuthContext(
                access_token=token_response.access_token
            )
            self._refresh_token = token_response.refresh_token
            
            logger.info("Token refreshed successfully")
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Token refresh failed - Status: {e.response.status_code}")
            logger.error(f"Token refresh failed - Response: {e.response.text}")
            logger.error(f"Token refresh failed - Headers: {dict(e.response.headers)}")
            # If refresh fails, try to obtain new token
            await self._obtain_access_token()
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {str(e)}")
            await self._obtain_access_token()
    
    async def close(self) -> None:
        """Close HTTP client connections."""
        await self._http_client.aclose()


# Global auth manager instance
auth_manager = AuthenticationManager(settings.eka_access_token)