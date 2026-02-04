"""
Services module that provides both foundational components and service classes.

This module provides:
1. Foundational components for hosted MCP implementations
2. Reusable service classes for direct library usage

Example usage for building a remote MCP server:

    from eka_mcp_sdk.auth.models import AuthContext, EkaAPIError
    from eka_mcp_sdk.auth.manager import AuthenticationManager
    from eka_mcp_sdk.clients.base_client import BaseEkaClient
    from eka_mcp_sdk.clients.eka_emr_client import EkaEMRClient
    from eka_mcp_sdk.config.settings import settings

Example usage for direct service access:

    from eka_mcp_sdk.services import (
        PatientService,
        AppointmentService,
        PrescriptionService,
        DoctorClinicService
    )
    from eka_mcp_sdk.clients.eka_emr_client import EkaEMRClient
    
    # Initialize client and services
    client = EkaEMRClient()
    patient_service = PatientService(client)
    appointment_service = AppointmentService(client)
"""

from ..auth.models import TokenResponse, AuthContext, EkaAPIError
from ..auth.manager import AuthenticationManager
from ..clients.base_client import BaseEkaClient
from ..clients.eka_emr_client import EkaEMRClient
from ..config.settings import settings

# Import service classes
from .patient_service import PatientService
from .appointment_service import AppointmentService
from .prescription_service import PrescriptionService
from .doctor_clinic_service import DoctorClinicService

__all__ = [
    # Foundational components
    "TokenResponse",
    "AuthContext", 
    "EkaAPIError",
    "AuthenticationManager",
    "BaseEkaClient",
    "EkaEMRClient",
    "settings",
    # Service classes
    "PatientService",
    "AppointmentService",
    "PrescriptionService",
    "DoctorClinicService"
]