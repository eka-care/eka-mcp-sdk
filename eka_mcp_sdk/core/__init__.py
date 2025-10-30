"""
Core module that can be imported by hosted MCP implementations.

This module provides the foundational components that can be reused
in more complex multi-tenant or hosted MCP server implementations.
"""

from ..auth.models import TokenResponse, AuthContext, EkaAPIError
from ..clients.base import BaseEkaClient
from ..clients.doctor_tools_client import DoctorToolsClient

__all__ = [
    "TokenResponse",
    "AuthContext", 
    "EkaAPIError",
    "BaseEkaClient",
    "DoctorToolsClient",
]