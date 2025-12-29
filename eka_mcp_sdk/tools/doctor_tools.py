from typing import Any, Dict
import logging
from fastmcp import FastMCP

from ..clients.eka_emr_client import EkaEMRClient
from ..auth.models import EkaAPIError

# Import tool registration functions from modular files
from .patient_tools import register_patient_tools
from .appointment_tools import register_appointment_tools
from .doctor_clinic_tools import register_doctor_clinic_tools
from .prescription_tools import register_prescription_tools
from .assessment_tools import register_assessment_tools

logger = logging.getLogger(__name__)


def register_doctor_tools(mcp: FastMCP) -> None:
    """Register Doctor Tools MCP tools from modular components."""
    
    # Register all modular tool categories
    register_patient_tools(mcp)
    register_appointment_tools(mcp)
    # register_doctor_clinic_tools(mcp)
    # register_prescription_tools(mcp)
    # register_assessment_tools(mcp)