from typing import Any, Dict, Optional, List, Union, Annotated
import logging
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token, AccessToken

from ..clients.doctor_tools_client import DoctorToolsClient
from ..auth.models import EkaAPIError
from ..core.appointment_service import AppointmentService

logger = logging.getLogger(__name__)


def register_appointment_tools(mcp: FastMCP) -> None:
    """Register Enhanced Appointment Management MCP tools."""
    
    @mcp.tool(
        description="Get available appointment slots for a doctor at a specific clinic on a given date"
    )
    async def get_appointment_slots(
        doctor_id: Annotated[str, "Doctor's unique identifier"],
        clinic_id: Annotated[str, "Clinic's unique identifier"],
        date: Annotated[str, "Date for appointment slots (YYYY-MM-DD format)"]
    ) -> Dict[str, Any]:
        """Returns available appointment slots with timing and pricing information."""
        try:
            token: AccessToken | None = get_access_token()
            client = DoctorToolsClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.get_appointment_slots(doctor_id, clinic_id, date)
            return {"success": True, "data": result}
        except EkaAPIError as e:
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool(
        description="Book an appointment slot for a patient"
    )
    async def book_appointment(
        appointment_data: Annotated[Dict[str, Any], "Appointment details including patient, doctor, timing, and mode"]
    ) -> Dict[str, Any]:
        """Returns booked appointment details with confirmation."""
        try:
            token: AccessToken | None = get_access_token()
            client = DoctorToolsClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.book_appointment(appointment_data)
            return {"success": True, "data": result}
        except EkaAPIError as e:
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool()
    async def get_appointments_enriched(
        doctor_id: Optional[str] = None,
        clinic_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page_no: int = 0
    ) -> Dict[str, Any]:
        """
        🌟 RECOMMENDED: Get appointments with comprehensive details including patient names, doctor profiles, and clinic information.
        
        This is the preferred tool for getting appointment information as it provides complete context
        without requiring additional API calls. Use this instead of get_appointments_basic unless you
        specifically need only basic appointment data.
        
        Args:
            doctor_id: Filter by doctor ID (optional)
            clinic_id: Filter by clinic ID (optional)
            patient_id: Filter by patient ID (optional)
            start_date: Start date filter (YYYY-MM-DD format, optional)
            end_date: End date filter (YYYY-MM-DD format, optional)
            page_no: Page number for pagination (starts from 0)
        
        Returns:
            Enriched appointments with patient names, doctor details, and clinic information
        """
        try:
            token: AccessToken | None = get_access_token()
            client = DoctorToolsClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.get_appointments_enriched(
                doctor_id=doctor_id,
                clinic_id=clinic_id,
                patient_id=patient_id,
                start_date=start_date,
                end_date=end_date,
                page_no=page_no
            )
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool()
    async def get_appointments_basic(
        doctor_id: Optional[str] = None,
        clinic_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page_no: int = 0
    ) -> Dict[str, Any]:
        """
        Get basic appointments data (IDs only). 
        
        ⚠️  Consider using get_appointments_enriched instead for complete information.
        Only use this if you specifically need raw appointment data without patient/doctor/clinic details.
        
        Args:
            doctor_id: Filter by doctor ID (optional)
            clinic_id: Filter by clinic ID (optional)
            patient_id: Filter by patient ID (optional)
            start_date: Start date filter (YYYY-MM-DD format, optional)
            end_date: End date filter (YYYY-MM-DD format, optional)
            page_no: Page number for pagination (starts from 0)
        
        Returns:
            Basic appointments with entity IDs only
        """
        try:
            token: AccessToken | None = get_access_token()
            client = DoctorToolsClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.get_appointments_basic(
                doctor_id=doctor_id,
                clinic_id=clinic_id,
                patient_id=patient_id,
                start_date=start_date,
                end_date=end_date,
                page_no=page_no
            )
            return {"success": True, "data": result}
        except EkaAPIError as e:
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool()
    async def get_appointment_details_enriched(
        appointment_id: str,
        partner_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        🌟 RECOMMENDED: Get comprehensive appointment details with complete patient, doctor, and clinic information.
        
        This is the preferred tool for getting single appointment details as it provides complete context
        without requiring additional API calls. Use this instead of get_appointment_details_basic.
        
        Args:
            appointment_id: Appointment's unique identifier
            partner_id: If set to 1, uses partner_appointment_id instead of eka appointment_id
        
        Returns:
            Complete appointment details with enriched patient, doctor, and clinic information
        """
        try:
            token: AccessToken | None = get_access_token()
            client = DoctorToolsClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.get_appointment_details_enriched(appointment_id, partner_id)
            return {"success": True, "data": result}
        except EkaAPIError as e:
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool()
    async def get_appointment_details_basic(
        appointment_id: str,
        partner_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get basic appointment details (IDs only).
        
        ⚠️  Consider using get_appointment_details_enriched instead for complete information.
        Only use this if you specifically need raw appointment data without patient/doctor/clinic details.
        
        Args:
            appointment_id: Appointment's unique identifier
            partner_id: If set to 1, uses partner_appointment_id instead of eka appointment_id
        
        Returns:
            Basic appointment details with entity IDs only
        """
        try:
            token: AccessToken | None = get_access_token()
            client = DoctorToolsClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.get_appointment_details_basic(appointment_id, partner_id)
            return {"success": True, "data": result}
        except EkaAPIError as e:
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool()
    async def get_patient_appointments_enriched(
        patient_id: str,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        🌟 RECOMMENDED: Get all appointments for a specific patient with enriched doctor and clinic details.
        
        This is the preferred tool for getting patient appointments as it provides complete context
        without requiring additional API calls. Use this instead of get_patient_appointments_basic.
        
        Args:
            patient_id: Patient's unique identifier
            limit: Maximum number of appointments to return
        
        Returns:
            List of enriched appointments for the patient with doctor and clinic information
        """
        try:
            token: AccessToken | None = get_access_token()
            client = DoctorToolsClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.get_patient_appointments_enriched(patient_id, limit)
            return {"success": True, "data": result}
        except EkaAPIError as e:
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool()
    async def get_patient_appointments_basic(
        patient_id: str,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get basic appointments for a specific patient (IDs only).
        
        ⚠️  Consider using get_patient_appointments_enriched instead for complete information.
        Only use this if you specifically need raw appointment data without doctor/clinic details.
        
        Args:
            patient_id: Patient's unique identifier
            limit: Maximum number of appointments to return
        
        Returns:
            Basic appointments with entity IDs only
        """
        try:
            token: AccessToken | None = get_access_token()
            client = DoctorToolsClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.get_patient_appointments_basic(patient_id, limit)
            return {"success": True, "data": result}
        except EkaAPIError as e:
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool()
    async def update_appointment(
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
        """
        try:
            token: AccessToken | None = get_access_token()
            client = DoctorToolsClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.update_appointment(appointment_id, update_data, partner_id)
            return {"success": True, "data": result}
        except EkaAPIError as e:
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool()
    async def complete_appointment(
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
        """
        try:
            token: AccessToken | None = get_access_token()
            client = DoctorToolsClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.complete_appointment(appointment_id, completion_data)
            return {"success": True, "data": result}
        except EkaAPIError as e:
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool()
    async def cancel_appointment(
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
        """
        try:
            token: AccessToken | None = get_access_token()
            client = DoctorToolsClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.cancel_appointment(appointment_id, cancel_data)
            return {"success": True, "data": result}
        except EkaAPIError as e:
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool()
    async def reschedule_appointment(
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
        """
        try:
            token: AccessToken | None = get_access_token()
            client = DoctorToolsClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.reschedule_appointment(appointment_id, reschedule_data)
            return {"success": True, "data": result}
        except EkaAPIError as e:
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }


# This function is now handled by the AppointmentService class
# Keeping for backward compatibility if needed
async def _enrich_appointments_data(client: DoctorToolsClient, appointments_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Unified function to enrich appointment data with patient, doctor, and clinic details.
    Works with both single appointments and lists of appointments.
    """
    try:
        # Handle different input structures
        appointments_list = []
        if "appointments" in appointments_data:
            appointments_list = appointments_data.get("appointments", [])
        elif isinstance(appointments_data, list):
            appointments_list = appointments_data
        elif isinstance(appointments_data, dict) and appointments_data.get("appointment_id"):
            # Single appointment
            appointments_list = [appointments_data]
        else:
            # Unknown structure, return as is
            return appointments_data
        
        if not appointments_list:
            return appointments_data
        
        enriched_appointments = []
        
        # Cache for avoiding duplicate API calls
        patients_cache = {}
        doctors_cache = {}
        clinics_cache = {}
        
        for appointment in appointments_list:
            enriched_appointment = appointment.copy()
            
            # Enrich with patient details
            patient_id = appointment.get("patient_id")
            if patient_id:
                patient_info = await get_cached_data(
                    client.get_patient_details, patient_id, patients_cache
                )
                if patient_info:
                    enriched_appointment["patient_details"] = extract_patient_summary(patient_info)
            
            # Enrich with doctor details
            doctor_id = appointment.get("doctor_id")
            if doctor_id:
                doctor_info = await get_cached_data(
                    client.get_doctor_profile, doctor_id, doctors_cache
                )
                if doctor_info:
                    enriched_appointment["doctor_details"] = extract_doctor_summary(doctor_info)
            
            # Enrich with clinic details
            clinic_id = appointment.get("clinic_id")
            if clinic_id:
                clinic_info = await get_cached_data(
                    client.get_clinic_details, clinic_id, clinics_cache
                )
                if clinic_info:
                    enriched_appointment["clinic_details"] = extract_clinic_summary(clinic_info)
            
            enriched_appointments.append(enriched_appointment)
        
        # Return enriched data with original structure preserved
        if "appointments" in appointments_data:
            result = appointments_data.copy()
            result["appointments"] = enriched_appointments
            return result
        elif isinstance(appointments_data, list):
            return enriched_appointments
        else:
            # Single appointment case
            return enriched_appointments[0] if enriched_appointments else appointments_data
        
    except Exception as e:
        logger.warning(f"Failed to enrich appointments data: {str(e)}")
        return appointments_data


