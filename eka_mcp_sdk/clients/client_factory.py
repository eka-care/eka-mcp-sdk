"""
EMR Client Factory.

Creates workspace-specific EMR clients based on workspace ID from request headers.
"""

import logging
from typing import Optional, Dict

from .eka_emr_client import EkaEMRClient
from ..config.settings import settings

logger = logging.getLogger(__name__)


class ClientFactory:
    """Factory for creating workspace-specific EMR clients."""
    
    @classmethod
    def _get_default_client_type(cls) -> str:
        """Get default client type from environment settings."""
        try:
            return settings.workspace_client_type.lower()
        except Exception:
            return "ekaemr"
    
    @classmethod
    def create_client(
        cls,
        workspace_id: str,
        access_token: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None
    ):
        """
        Create an EMR client for the specified workspace.
        
        Args:
            workspace_id: The workspace identifier (e.g., 'moolchand', 'ekaemr')
            access_token: Optional access token for authenticated requests
            custom_headers: Optional custom headers to include in requests
            
        Returns:
            An EMR client instance for the workspace
        """
        workspace_id = workspace_id.lower() if workspace_id else "ekaemr"
        
        client_class = settings.get_client_class(workspace_id) or EkaEMRClient
        
        logger.debug(f"Creating {client_class.__name__} for workspace: {workspace_id}")
        
        return client_class(access_token=access_token, custom_headers=custom_headers)
    
    @classmethod
    def get_supported_workspaces(cls) -> list:
        """Return list of supported workspace IDs."""
        return [ws for ws in settings.workspace_client_dict.keys()]
