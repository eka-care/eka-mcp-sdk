"""
Library module for direct usage of eka-mcp-sdk without MCP.

This module provides both asynchronous service classes and synchronous wrapper functions
for use with frameworks like CrewAI that don't support async operations.

Example usage (Direct async):
    from eka_mcp_sdk.lib import PatientService, AppointmentService
    from eka_mcp_sdk.clients.eka_emr_client import EkaEMRClient
    
    client = EkaEMRClient()
    patient_service = PatientService(client)
    
    # Use async methods directly
    result = await patient_service.search_patients("john")

Example usage (Synchronous for CrewAI):
    from eka_mcp_sdk.lib import search_patients_sync, get_patient_details_sync
    
    # Use sync wrappers
    result = search_patients_sync("john", limit=10)
    patient = get_patient_details_sync("patient_123")
"""
import asyncio
from typing import Any, Dict, Optional, List
from functools import wraps
import logging

from .clients.eka_emr_client import EkaEMRClient
from .services import (
    PatientService, 
    AppointmentService, 
    PrescriptionService, 
    DoctorClinicService
)
from .auth.models import EkaAPIError

logger = logging.getLogger(__name__)

# Global client instance for sync functions
_default_client = None

def get_default_client() -> EkaEMRClient:
    """Get or create default client instance."""
    global _default_client
    if _default_client is None:
        _default_client = EkaEMRClient()
    return _default_client

def sync_wrapper(func):
    """Decorator to convert async functions to sync."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Try to get the current event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in an async context, run in a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, func(*args, **kwargs))
                    return future.result()
            except RuntimeError:
                # No event loop running, we can use asyncio.run directly
                return asyncio.run(func(*args, **kwargs))
        except Exception as e:
            logger.error(f"Error in sync wrapper for {func.__name__}: {str(e)}")
            raise
    return wrapper

# Export service classes for direct async usage
__all__ = [
    # Service classes (async)
    "PatientService",
    "AppointmentService", 
    "PrescriptionService",
    "DoctorClinicService",
    # Sync wrapper functions - Patient
    "search_patients_sync",
    "get_patient_details_basic_sync",
    "get_comprehensive_patient_profile_sync",
    "add_patient_sync",
    "list_patients_sync",
    "update_patient_sync",
    "archive_patient_sync",
    "get_patient_by_mobile_sync",
    # Sync wrapper functions - Appointments
    "get_appointment_slots_sync",
    "book_appointment_sync",
    "get_appointments_enriched_sync",
    "get_appointments_basic_sync",
    "get_appointment_details_enriched_sync",
    "get_appointment_details_basic_sync",
    "get_patient_appointments_enriched_sync",
    "get_patient_appointments_basic_sync",
    "update_appointment_sync",
    "complete_appointment_sync",
    "cancel_appointment_sync",
    "reschedule_appointment_sync",
    # Sync wrapper functions - Prescriptions
    "get_prescription_details_basic_sync",
    "get_comprehensive_prescription_details_sync",
    # Sync wrapper functions - Doctor/Clinic
    "get_business_entities_sync",
    "get_doctor_profile_basic_sync",
    "get_clinic_details_basic_sync",
    "get_doctor_services_sync",
    "get_comprehensive_doctor_profile_sync",
    "get_comprehensive_clinic_profile_sync",
    # Utility
    "get_default_client"
]

# ============================================================================
# PATIENT SERVICE SYNC WRAPPERS
# ============================================================================

@sync_wrapper
async def search_patients_sync(
    prefix: str,
    limit: Optional[int] = None,
    select: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search patient profiles by username, mobile, or full name (prefix match).
    
    Args:
        prefix: Search term to match against patient profiles
        limit: Maximum number of results to return
        select: Comma-separated list of additional fields to include
        
    Returns:
        List of patients matching the search criteria
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = PatientService(client)
    return await service.search_patients(prefix, limit, select)

@sync_wrapper
async def get_patient_details_basic_sync(patient_id: str) -> Dict[str, Any]:
    """
    Get basic patient details by profile ID (profile data only).
    
    Args:
        patient_id: Patient's unique identifier
        
    Returns:
        Basic patient profile including personal and medical information
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = PatientService(client)
    return await service.get_patient_details_basic(patient_id)

@sync_wrapper
async def get_comprehensive_patient_profile_sync(
    patient_id: str,
    include_appointments: bool = True,
    appointment_limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get comprehensive patient profile including detailed appointment history.
    
    Args:
        patient_id: Patient's unique identifier
        include_appointments: Whether to include appointment history
        appointment_limit: Limit number of appointments returned
        
    Returns:
        Complete patient profile with enriched appointment history
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = PatientService(client)
    return await service.get_comprehensive_patient_profile(
        patient_id, include_appointments, appointment_limit
    )

@sync_wrapper
async def add_patient_sync(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new patient profile.
    
    Args:
        patient_data: Patient information including required and optional fields
        
    Returns:
        Created patient profile with oid identifier
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = PatientService(client)
    return await service.add_patient(patient_data)

@sync_wrapper
async def list_patients_sync(
    page_no: int,
    page_size: Optional[int] = None,
    select: Optional[str] = None,
    from_timestamp: Optional[int] = None,
    include_archived: bool = False
) -> Dict[str, Any]:
    """
    List patient profiles with pagination.
    
    Args:
        page_no: Page number (required)
        page_size: Number of records per page
        select: Comma-separated list of additional fields
        from_timestamp: Get profiles created after this timestamp
        include_archived: Include archived profiles in response
        
    Returns:
        Paginated list of patient profiles
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = PatientService(client)
    return await service.list_patients(
        page_no, page_size, select, from_timestamp, include_archived
    )

@sync_wrapper
async def update_patient_sync(
    patient_id: str,
    update_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update patient profile details.
    
    Args:
        patient_id: Patient's unique identifier
        update_data: Fields to update
        
    Returns:
        Success message confirming profile update
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = PatientService(client)
    return await service.update_patient(patient_id, update_data)

@sync_wrapper
async def archive_patient_sync(
    patient_id: str,
    archive: bool = True
) -> Dict[str, Any]:
    """
    Archive patient profile (soft delete).
    
    Args:
        patient_id: Patient's unique identifier
        archive: Whether to archive the profile
        
    Returns:
        Success message confirming profile archival
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = PatientService(client)
    return await service.archive_patient(patient_id, archive)

@sync_wrapper
async def get_patient_by_mobile_sync(
    mobile: str,
    full_profile: bool = False
) -> Dict[str, Any]:
    """
    Retrieve patient profiles by mobile number.
    
    Args:
        mobile: Mobile number in format +<country_code><number>
        full_profile: If True, returns full patient profile details
        
    Returns:
        Patient profile(s) matching the mobile number
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = PatientService(client)
    return await service.get_patient_by_mobile(mobile, full_profile)

# ============================================================================
# APPOINTMENT SERVICE SYNC WRAPPERS
# ============================================================================

@sync_wrapper
async def get_appointment_slots_sync(
    doctor_id: str,
    clinic_id: str,
    date: str
) -> Dict[str, Any]:
    """
    Get available appointment slots for a doctor at a specific clinic on a given date.
    
    Args:
        doctor_id: Doctor's unique identifier
        clinic_id: Clinic's unique identifier
        date: Date for appointment slots (YYYY-MM-DD format)
        
    Returns:
        Available appointment slots with timing and pricing information
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = AppointmentService(client)
    return await service.get_appointment_slots(doctor_id, clinic_id, date)

@sync_wrapper
async def book_appointment_sync(appointment_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Book an appointment slot for a patient.
    
    Args:
        appointment_data: Appointment details including patient, doctor, timing, and mode
        
    Returns:
        Booked appointment details with confirmation
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = AppointmentService(client)
    return await service.book_appointment(appointment_data)

@sync_wrapper
async def get_appointments_enriched_sync(
    doctor_id: Optional[str] = None,
    clinic_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page_no: int = 0
) -> Dict[str, Any]:
    """
    Get appointments with comprehensive details including patient names, doctor profiles, and clinic information.
    
    Args:
        doctor_id: Filter by doctor ID (optional)
        clinic_id: Filter by clinic ID (optional)
        patient_id: Filter by patient ID (optional)
        start_date: Start date filter (YYYY-MM-DD format, optional)
        end_date: End date filter (YYYY-MM-DD format, optional)
        page_no: Page number for pagination (starts from 0)
        
    Returns:
        Enriched appointments with patient names, doctor details, and clinic information
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = AppointmentService(client)
    return await service.get_appointments_enriched(
        doctor_id, clinic_id, patient_id, start_date, end_date, page_no
    )

@sync_wrapper
async def get_appointments_basic_sync(
    doctor_id: Optional[str] = None,
    clinic_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page_no: int = 0
) -> Dict[str, Any]:
    """
    Get basic appointments data (IDs only).
    
    Args:
        doctor_id: Filter by doctor ID (optional)
        clinic_id: Filter by clinic ID (optional)
        patient_id: Filter by patient ID (optional)
        start_date: Start date filter (YYYY-MM-DD format, optional)
        end_date: End date filter (YYYY-MM-DD format, optional)
        page_no: Page number for pagination (starts from 0)
        
    Returns:
        Basic appointments with entity IDs only
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = AppointmentService(client)
    return await service.get_appointments_basic(
        doctor_id, clinic_id, patient_id, start_date, end_date, page_no
    )

@sync_wrapper
async def get_appointment_details_enriched_sync(
    appointment_id: str,
    partner_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get comprehensive appointment details with complete patient, doctor, and clinic information.
    
    Args:
        appointment_id: Appointment's unique identifier
        partner_id: If set to 1, uses partner_appointment_id instead of eka appointment_id
        
    Returns:
        Complete appointment details with enriched patient, doctor, and clinic information
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = AppointmentService(client)
    return await service.get_appointment_details_enriched(appointment_id, partner_id)

@sync_wrapper
async def get_appointment_details_basic_sync(
    appointment_id: str,
    partner_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get basic appointment details (IDs only).
    
    Args:
        appointment_id: Appointment's unique identifier
        partner_id: If set to 1, uses partner_appointment_id instead of eka appointment_id
        
    Returns:
        Basic appointment details with entity IDs only
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = AppointmentService(client)
    return await service.get_appointment_details_basic(appointment_id, partner_id)

@sync_wrapper
async def get_patient_appointments_enriched_sync(
    patient_id: str,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get all appointments for a specific patient with enriched doctor and clinic details.
    
    Args:
        patient_id: Patient's unique identifier
        limit: Maximum number of appointments to return
        
    Returns:
        List of enriched appointments for the patient with doctor and clinic information
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = AppointmentService(client)
    return await service.get_patient_appointments_enriched(patient_id, limit)

@sync_wrapper
async def get_patient_appointments_basic_sync(
    patient_id: str,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get basic appointments for a specific patient (IDs only).
    
    Args:
        patient_id: Patient's unique identifier
        limit: Maximum number of appointments to return
        
    Returns:
        Basic appointments with entity IDs only
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = AppointmentService(client)
    return await service.get_patient_appointments_basic(patient_id, limit)

@sync_wrapper
async def update_appointment_sync(
    appointment_id: str,
    update_data: Dict[str, Any],
    partner_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update an existing appointment.
    
    Args:
        appointment_id: Appointment's unique identifier
        update_data: Fields to update (status, timing, custom attributes, etc.)
        partner_id: If set to 1, uses partner_appointment_id instead of eka appointment_id
        
    Returns:
        Updated appointment details
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = AppointmentService(client)
    return await service.update_appointment(appointment_id, update_data, partner_id)

@sync_wrapper
async def complete_appointment_sync(
    appointment_id: str,
    completion_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Mark an appointment as completed.
    
    Args:
        appointment_id: Appointment's unique identifier
        completion_data: Completion details including status and notes
        
    Returns:
        Completion confirmation with updated appointment status
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = AppointmentService(client)
    return await service.complete_appointment(appointment_id, completion_data)

@sync_wrapper
async def cancel_appointment_sync(
    appointment_id: str,
    cancel_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Cancel an appointment.
    
    Args:
        appointment_id: Appointment's unique identifier
        cancel_data: Cancellation details including reason and notes
        
    Returns:
        Cancellation confirmation with updated appointment status
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = AppointmentService(client)
    return await service.cancel_appointment(appointment_id, cancel_data)

@sync_wrapper
async def reschedule_appointment_sync(
    appointment_id: str,
    reschedule_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Reschedule an appointment to a new date/time.
    
    Args:
        appointment_id: Appointment's unique identifier
        reschedule_data: New appointment timing and details
        
    Returns:
        Rescheduled appointment details with new timing
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = AppointmentService(client)
    return await service.reschedule_appointment(appointment_id, reschedule_data)

# ============================================================================
# PRESCRIPTION SERVICE SYNC WRAPPERS
# ============================================================================

@sync_wrapper
async def get_prescription_details_basic_sync(prescription_id: str) -> Dict[str, Any]:
    """
    Get basic prescription details (prescription data only).
    
    Args:
        prescription_id: Prescription's unique identifier
        
    Returns:
        Basic prescription details including medications and diagnosis only
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = PrescriptionService(client)
    return await service.get_prescription_details_basic(prescription_id)

@sync_wrapper
async def get_comprehensive_prescription_details_sync(
    prescription_id: str,
    include_patient_details: bool = True,
    include_doctor_details: bool = True,
    include_clinic_details: bool = True
) -> Dict[str, Any]:
    """
    Get comprehensive prescription details with enriched patient, doctor, and clinic information.
    
    Args:
        prescription_id: Prescription's unique identifier
        include_patient_details: Whether to include patient details
        include_doctor_details: Whether to include doctor details
        include_clinic_details: Whether to include clinic details
        
    Returns:
        Complete prescription details with enriched patient, doctor, and clinic information
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = PrescriptionService(client)
    return await service.get_comprehensive_prescription_details(
        prescription_id, include_patient_details, include_doctor_details, include_clinic_details
    )

# ============================================================================
# DOCTOR/CLINIC SERVICE SYNC WRAPPERS
# ============================================================================

@sync_wrapper
async def get_business_entities_sync() -> Dict[str, Any]:
    """
    Get Clinic and Doctor details for the business.
    
    Returns:
        Complete list of clinics and doctors associated with the business
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = DoctorClinicService(client)
    return await service.get_business_entities()

@sync_wrapper
async def get_doctor_profile_basic_sync(doctor_id: str) -> Dict[str, Any]:
    """
    Get basic doctor profile information (profile data only).
    
    Args:
        doctor_id: Doctor's unique identifier
        
    Returns:
        Basic doctor profile including specialties, contact info, and background only
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = DoctorClinicService(client)
    return await service.get_doctor_profile_basic(doctor_id)

@sync_wrapper
async def get_clinic_details_basic_sync(clinic_id: str) -> Dict[str, Any]:
    """
    Get basic information about a clinic (clinic data only).
    
    Args:
        clinic_id: Clinic's unique identifier
        
    Returns:
        Basic clinic details including address, facilities, and services only
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = DoctorClinicService(client)
    return await service.get_clinic_details_basic(clinic_id)

@sync_wrapper
async def get_doctor_services_sync(doctor_id: str) -> Dict[str, Any]:
    """
    Get services offered by a doctor.
    
    Args:
        doctor_id: Doctor's unique identifier
        
    Returns:
        List of services and specialties offered by the doctor
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = DoctorClinicService(client)
    return await service.get_doctor_services(doctor_id)

@sync_wrapper
async def get_comprehensive_doctor_profile_sync(
    doctor_id: str,
    include_clinics: bool = True,
    include_services: bool = True,
    include_recent_appointments: bool = True,
    appointment_limit: Optional[int] = 10
) -> Dict[str, Any]:
    """
    Get comprehensive doctor profile including associated clinics, services, and recent appointments.
    
    Args:
        doctor_id: Doctor's unique identifier
        include_clinics: Whether to include associated clinic details
        include_services: Whether to include doctor services
        include_recent_appointments: Whether to include recent appointments
        appointment_limit: Limit number of recent appointments
        
    Returns:
        Complete doctor profile with enriched clinic details, services, and appointment history
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = DoctorClinicService(client)
    return await service.get_comprehensive_doctor_profile(
        doctor_id, include_clinics, include_services, include_recent_appointments, appointment_limit
    )

@sync_wrapper
async def get_comprehensive_clinic_profile_sync(
    clinic_id: str,
    include_doctors: bool = True,
    include_services: bool = True,
    include_recent_appointments: bool = True,
    appointment_limit: Optional[int] = 10
) -> Dict[str, Any]:
    """
    Get comprehensive clinic profile including associated doctors, services, and recent appointments.
    
    Args:
        clinic_id: Clinic's unique identifier
        include_doctors: Whether to include associated doctor details
        include_services: Whether to include clinic services through doctors
        include_recent_appointments: Whether to include recent appointments
        appointment_limit: Limit number of recent appointments
        
    Returns:
        Complete clinic profile with enriched doctor details, services, and appointment history
        
    Raises:
        EkaAPIError: If the API call fails
    """
    client = get_default_client()
    service = DoctorClinicService(client)
    return await service.get_comprehensive_clinic_profile(
        clinic_id, include_doctors, include_services, include_recent_appointments, appointment_limit
    )