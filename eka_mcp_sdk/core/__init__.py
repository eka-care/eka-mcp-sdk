"""
Core module that can be imported by hosted MCP implementations.

This module provides the foundational components that can be reused
in more complex multi-tenant or hosted MCP server implementations.

Example usage for building a remote MCP server:

    from eka_mcp_sdk.core import (
        BaseEkaClient,
        AuthenticationManager, 
        AuthContext,
        EkaAPIError,
        DoctorToolsClient,
        EkaSettings
    )
    
    # Create custom client extending BaseEkaClient
    class CustomAPIClient(BaseEkaClient):
        async def custom_endpoint(self):
            return await self._make_request("GET", "/custom/endpoint")
    
    # Use authentication manager for token management
    auth_manager = AuthenticationManager(settings)
    client = CustomAPIClient()
"""

from ..auth.models import TokenResponse, AuthContext, EkaAPIError
from ..auth.manager import AuthenticationManager
from ..clients.base import BaseEkaClient
from ..clients.doctor_tools_client import DoctorToolsClient
from ..config.settings import EkaSettings
from ..server import create_mcp_server
from ..utils.tool_registration import register_all_tools

__all__ = [
    "TokenResponse",
    "AuthContext", 
    "EkaAPIError",
    "AuthenticationManager",
    "BaseEkaClient",
    "DoctorToolsClient",
    "EkaSettings",
    "create_mcp_server",
    "register_all_tools",
]