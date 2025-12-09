"""
Core module that provides both foundational components and service classes.

This module provides:
1. Foundational components for hosted MCP implementations
2. Reusable service classes for direct library usage

Example usage for building a remote MCP server:

    from eka_mcp_sdk.core import (
        BaseEkaClient,
        AuthenticationManager, 
        AuthContext,
        EkaAPIError,
        DoctorToolsClient,
        EkaSettings
    )

Example usage for direct service access:

    from eka_mcp_sdk.core import (
        PatientService,
        AppointmentService,
        PrescriptionService,
        DoctorClinicService
    )
    from eka_mcp_sdk.clients.doctor_tools_client import DoctorToolsClient
    
    # Initialize client and services
    client = DoctorToolsClient()
    patient_service = PatientService(client)
    appointment_service = AppointmentService(client)
"""

from ..auth.models import TokenResponse, AuthContext, EkaAPIError
from ..auth.manager import AuthenticationManager
from ..clients.base import BaseEkaClient
from ..clients.doctor_tools_client import DoctorToolsClient
from ..config.settings import EkaSettings

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
    "DoctorToolsClient",
    "EkaSettings",
    # Service classes
    "PatientService",
    "AppointmentService",
    "PrescriptionService",
    "DoctorClinicService"
]