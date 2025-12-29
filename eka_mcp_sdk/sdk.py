"""
Main SDK class for Eka.care MCP integration.
"""

from typing import Optional
import logging

from .config.settings import EkaSettings
from .auth.manager import AuthenticationManager
from .clients.eka_emr_client import EkaEMRClient

logger = logging.getLogger(__name__)


class EkaMCPSDK:
    """Main SDK class for Eka.care MCP integration."""
    
    def __init__(
        self,
        access_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base_url: Optional[str] = None
    ):
        """
        Initialize the Eka.care MCP SDK.
        
        Args:
            access_token: External JWT access token (if provided, client_id/secret not needed)
            client_id: Eka client ID (defaults to settings or "eka-doctool-mcp")
            client_secret: Eka client secret (required if access_token not provided)
            api_key: Optional API key for additional authentication
            api_base_url: API base URL (defaults to settings)
        """
        # Set parameters with fallbacks to settings
        
        settings = EkaSettings()
        self.client_id = client_id or settings.eka_client_id
        self.client_secret = client_secret or settings.eka_client_secret
        self.api_key = api_key or settings.eka_api_key
        self.api_base_url = api_base_url or settings.eka_api_base_url
        self.access_token = access_token
        
        # Validate authentication parameters
        if not access_token and not client_secret:
            raise ValueError("Either access_token or client_secret must be provided")
        
        # Create authentication manager based on provided credentials
        if access_token:
            logger.info("Initializing SDK with external access token")
            self._auth_manager = AuthenticationManager(external_access_token=access_token)
        else:
            logger.info("Initializing SDK with client credentials")
            self._auth_manager = AuthenticationManager()
        
        # Initialize clients
        self._eka_emr_client = None
    
    @property 
    def doctor_tools(self) -> EkaEMRClient:
        """Get Doctor Tools client instance."""
        if self._eka_emr_client is None:
            self._eka_emr_client = EkaEMRClient(auth_manager_instance=self._auth_manager)
        return self._eka_emr_client
    
    async def get_auth_context(self):
        """Get current authentication context."""
        return await self._auth_manager.get_auth_context()
    
    async def close(self):
        """Close all client connections."""
        if self._eka_emr_client:
            await self._eka_emr_client.close()
        await self._auth_manager.close()