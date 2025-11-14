"""
Eka.care MCP SDK - Healthcare API integration for LLM applications.

This package provides an MCP (Model Context Protocol) server that exposes
Eka.care's healthcare APIs to LLM applications like Claude Desktop.

For building remote MCP servers, import from eka_mcp_sdk.core:

    from eka_mcp_sdk.core import (
        BaseEkaClient,
        AuthenticationManager,
        AuthContext,
        EkaAPIError,
        DoctorToolsClient,
        EkaSettings
    )
"""

__version__ = "0.1.0"
__author__ = "Eka.care Team"
__email__ = "ekaconnect@eka.care"

# Export main components for package-level imports
from .config.settings import EkaSettings
from .auth.manager import AuthenticationManager
from .auth.models import AuthContext, EkaAPIError
from .clients.base import BaseEkaClient
from .clients.doctor_tools_client import DoctorToolsClient
from .server import create_mcp_server, main
from .sdk import EkaMCPSDK

__all__ = [
    "__version__",
    "__author__", 
    "__email__",
    "EkaSettings",
    "AuthenticationManager",
    "AuthContext",
    "EkaAPIError", 
    "BaseEkaClient",
    "DoctorToolsClient",
    "EkaMCPSDK",
    "create_mcp_server",
    "main"
]