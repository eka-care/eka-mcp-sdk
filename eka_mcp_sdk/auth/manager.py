import httpx
from typing import Optional
from datetime import datetime, timedelta
import logging

from ..config.settings import EkaSettings
from .models import TokenResponse, AuthContext, EkaAPIError
from .storage import FileTokenStorage
from fastmcp.server.context import Context

logger = logging.getLogger(__name__)


class AuthenticationManager:
    """Manages authentication for Eka.care APIs."""
    
    def __init__(self, access_token: Optional[str] = None):
        self._auth_context: Optional[AuthContext] = None
        self._refresh_token: Optional[str] = None
        self._external_access_token = access_token
        self._http_client = httpx.AsyncClient(timeout=30.0)
        self._settings = EkaSettings()
        
        # Only use storage when not using external access token
        ctx : Optional[Context] = None
        if ctx:
            ctx.debug(f"CTX AuthenticationManager initialized, access token : {access_token}")
        else:   
            logger.debug(f"Logger AuthenticationManager initialized, access token : {access_token}")
        self._storage = None if access_token else FileTokenStorage()
    
    async def get_auth_context(self) -> AuthContext:
        """Get valid authentication context."""
        # If external access token is provided, use it directly - no storage/refresh logic
        if self._external_access_token:
            return AuthContext(
                access_token=self._external_access_token
            )
        
        # For client credentials flow only: check memory, storage, then refresh/login
        # Check if we have a valid access token in memory
        if (self._auth_context and 
            not self._auth_context.is_token_expired):
            return self._auth_context
        
        # Try to load tokens from storage if available
        if self._storage and not self._auth_context:
            await self._load_tokens_from_storage()
        
        # Check again after loading from storage
        if (self._auth_context and 
            not self._auth_context.is_token_expired):
            return self._auth_context
        
        # Need to obtain/refresh access token
        if self._refresh_token:
            await self._refresh_access_token()
        else:
            await self._obtain_access_token()
        
        return self._auth_context
    
    def set_external_access_token(self, access_token: Optional[str]) -> None:
        """Update the external access token. When set, disables storage and refresh logic."""
        self._external_access_token = access_token
        if access_token:
            # Clear any stored auth context and storage when switching to external token
            self._auth_context = None
            self._refresh_token = None
            self._storage = None
        else:
            # Re-enable storage when switching back to client credentials flow
            self._storage = FileTokenStorage()
    
    async def _load_tokens_from_storage(self) -> None:
        """Load tokens from storage."""
        if not self._storage:
            return
            
        try:
            stored_tokens = await self._storage.get_tokens()
            if stored_tokens:
                self._auth_context = AuthContext(
                    access_token=stored_tokens["access_token"]
                )
                self._refresh_token = stored_tokens["refresh_token"]
                logger.debug("Tokens loaded from storage")
        except Exception as e:
            logger.warning(f"Failed to load tokens from storage: {str(e)}")
    
    async def _obtain_access_token(self) -> None:
        """Obtain access token using client credentials."""
        if not self._settings.client_id or not self._settings.client_secret:
            raise EkaAPIError("Client ID and Client Secret are required for authentication")
            
        url = f"{self._settings.api_base_url}/connect-auth/v1/account/login"
        payload = {
            "client_id": self._settings.client_id,
            "client_secret": self._settings.client_secret,
            "api_key": self._settings.api_key
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
            
            # Save to storage if available
            if self._storage:
                await self._storage.store_tokens(
                    access_token=token_response.access_token,
                    refresh_token=token_response.refresh_token,
                    expires_in=token_response.expires_in
                )
            
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
        url = f"{self._settings.api_base_url}/connect-auth/v1/account/refresh"
        payload = {"refresh_token": self._refresh_token}
        
        logger.info(f"Making refresh token request to: {url}")
        logger.debug(f"Refresh token payload: {payload}")
        
        try:
            response = await self._http_client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {self._external_access_token}"}
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
            
            # Save to storage if available
            if self._storage:
                await self._storage.store_tokens(
                    access_token=token_response.access_token,
                    refresh_token=token_response.refresh_token,
                    expires_in=token_response.expires_in
                )
            
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

