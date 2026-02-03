"""
EMR Client Factory.

Creates workspace-specific EMR clients based on workspace ID from request headers.
"""

import json
import logging
import os
from typing import Optional, Dict

from .eka_emr_client import EkaEMRClient


logger = logging.getLogger(__name__)


class EMRClientFactory:
    """Factory for creating workspace-specific EMR clients."""
    
    # Mapping of workspace IDs to their client classes
    # Default workspace type can be configured via EKA_WORKSPACE_CLIENT_TYPE env variable
    WORKSPACE_CLIENT_DICT = os.environ.get("WORKSPACE_CLIENT_DICT")
    WORKSPACE_CLIENT_DICT = json.loads(WORKSPACE_CLIENT_DICT) if WORKSPACE_CLIENT_DICT else {}
    
    @classmethod
    def _get_default_client_type(cls) -> str:
        """Get default client type from environment settings."""
        try:
            from ..config.settings import EkaSettings
            settings = EkaSettings()
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
        
        client_class = cls.WORKSPACE_CLIENT_DICT.get(workspace_id, EkaEMRClient)
        
        logger.debug(f"Creating {client_class.__name__} for workspace: {workspace_id}")
        
        return client_class(access_token=access_token, custom_headers=custom_headers)
    
    @classmethod
    def get_supported_workspaces(cls) -> list:
        """Return list of supported workspace IDs."""
        return [ws for ws in cls.WORKSPACE_CLIENT_DICT.keys()]
