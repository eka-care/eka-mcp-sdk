"""
Eka.care MCP SDK - Healthcare API integration for LLM applications.

This package provides multiple usage modes:

1. MCP Server Mode - Traditional MCP server for Claude Desktop and other MCP clients
2. Direct Library Mode - Use service classes directly in your applications  
3. CrewAI Integration - Synchronous functions for CrewAI and other agent frameworks

Usage Examples:

MCP Server (Traditional):
    # Install and run as MCP server
    eka-mcp-server
    
Direct Library (Async):
    from eka_mcp_sdk.services import PatientService, AppointmentService
    from eka_mcp_sdk.clients.eka_emr_client import EkaEMRClient
    
    client = EkaEMRClient()
    patient_service = PatientService(client)
    result = await patient_service.search_patients("john")

CrewAI/Sync Integration:
    from eka_mcp_sdk.lib import search_patients_sync, get_appointments_enriched_sync
    
    # Use in CrewAI tools or other sync contexts
    patients = search_patients_sync("john", limit=10)
    appointments = get_appointments_enriched_sync()

For building remote MCP servers, import from their respective modules:
    from eka_mcp_sdk.auth.models import AuthContext, EkaAPIError
    from eka_mcp_sdk.auth.manager import AuthenticationManager
    from eka_mcp_sdk.clients.base_client import BaseEkaClient
    from eka_mcp_sdk.clients.eka_emr_client import EkaEMRClient
    from eka_mcp_sdk.config.settings import EkaSettings
"""

__version__ = "0.1.0"
__author__ = "Eka.care Team"
__email__ = "ekaconnect@eka.care"

# Export main components for package-level imports
# Note: Avoiding circular imports by not importing from modules that depend on settings
from .auth.models import AuthContext, EkaAPIError

# Note: The following are available via direct import from their modules:
# - EkaSettings from eka_mcp_sdk.config.settings  
# - AuthenticationManager from eka_mcp_sdk.auth.manager
# - EkaEMRClient from eka_mcp_sdk.clients.eka_emr_client
# - create_mcp_server, main from eka_mcp_sdk.server
# - EkaMCPSDK from eka_mcp_sdk.sdk
# - Service classes from eka_mcp_sdk.services
# - Sync functions from eka_mcp_sdk.lib

__all__ = [
    "__version__",
    "__author__", 
    "__email__",
    "AuthContext",
    "EkaAPIError"
]