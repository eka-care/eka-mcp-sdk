from typing import Any, Dict
import logging
from fastmcp import FastMCP

from ..clients.doctor_tools_client import DoctorToolsClient
from ..auth.models import EkaAPIError

# Import tool registration functions from modular files
from .patient_tools import register_patient_tools
from .appointment_tools import register_appointment_tools
from .doctor_clinic_tools import register_doctor_clinic_tools
from .prescription_tools import register_prescription_tools

logger = logging.getLogger(__name__)


def register_doctor_tools(mcp: FastMCP) -> None:
    """Register Doctor Tools MCP tools from modular components."""
    client = DoctorToolsClient()
    
    # Register server info tool (general utility)
    @mcp.tool()
    async def get_server_info() -> Dict[str, Any]:
        """
        Get server information and configuration.

        Returns:
            Server configuration and status information
        """
        return {
            "server_name": "Eka.care Healthcare API Server",
            "version": "0.1.0",
            "api_base_url": "https://api.eka.care",
            "available_modules": [client.get_api_module_name()],
            "status": "running"
        }
    
    # Register all modular tool categories
    register_patient_tools(mcp)
    register_appointment_tools(mcp)
    register_doctor_clinic_tools(mcp)
    register_prescription_tools(mcp)