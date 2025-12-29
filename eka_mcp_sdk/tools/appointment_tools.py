from typing import Any, Dict, Optional, List, Union, Annotated
import logging
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token, AccessToken
from fastmcp.dependencies import CurrentContext
from fastmcp.server.context import Context

from ..clients.eka_emr_client import EkaEMRClient
from ..auth.models import EkaAPIError
from ..services.appointment_service import AppointmentService
from ..utils.enrichment_helpers import (
    get_cached_data,
    extract_patient_summary,
    extract_doctor_summary,
    extract_clinic_summary
)

logger = logging.getLogger(__name__)


def register_appointment_tools(mcp: FastMCP) -> None:
    """Register Enhanced Appointment Management MCP tools."""
    
    @mcp.tool(
        description="Get available appointment slots for a doctor at a specific clinic on a given date"
    )
    async def get_appointment_slots(
        doctor_id: Annotated[str, "Doctor's unique identifier"],
        clinic_id: Annotated[str, "Clinic's unique identifier"],
        date: Annotated[str, "Date for appointment slots (YYYY-MM-DD format)"],
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """Returns available appointment slots with timing and pricing information."""
        await ctx.info(f"[get_appointment_slots] Getting slots for doctor {doctor_id} at clinic {clinic_id} on {date}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.get_appointment_slots(doctor_id, clinic_id, date)
            
            slot_count = len(result.get('slots', [])) if isinstance(result, dict) else 0
            await ctx.info(f"[get_appointment_slots] Completed successfully - {slot_count} slots available\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[get_appointment_slots] Failed: {e.message}\n")
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
        appointment_data: Annotated[Dict[str, Any], "Appointment details including patient, doctor, timing, and mode"],
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """Returns booked appointment details with confirmation."""
        await ctx.info(f"[book_appointment] Booking appointment for patient {appointment_data.get('patientId', 'unknown')}")
        await ctx.debug(f"Appointment data: mode={appointment_data.get('mode')}, doctor={appointment_data.get('doctorId')}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.book_appointment(appointment_data)
            
            appointment_id = result.get('appointmentId') or result.get('id')
            await ctx.info(f"[book_appointment] Completed successfully - ID: {appointment_id}\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[book_appointment] Failed: {e.message}\n")
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
        page_no: int = 0,
        ctx: Context = CurrentContext()
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
        filters = [f for f in [f"doctor={doctor_id}" if doctor_id else None, 
                              f"clinic={clinic_id}" if clinic_id else None,
                              f"patient={patient_id}" if patient_id else None,
                              f"dates={start_date} to {end_date}" if start_date or end_date else None] if f]
        filter_str = ", ".join(filters) if filters else "no filters"
        await ctx.info(f"[get_appointments_enriched] Getting enriched appointments with {filter_str}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.get_appointments_enriched(
                doctor_id=doctor_id,
                clinic_id=clinic_id,
                patient_id=patient_id,
                start_date=start_date,
                end_date=end_date,
                page_no=page_no
            )
            
            appointment_count = len(result.get('appointments', [])) if isinstance(result, dict) else 0
            await ctx.info(f"[get_appointments_enriched] Completed successfully - {appointment_count} appointments\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[get_appointments_enriched] Failed: {e.message}\n")
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
        page_no: int = 0,
        ctx: Context = CurrentContext()
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
        await ctx.info(f"[get_appointments_basic] Getting basic appointments - page {page_no}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.get_appointments_basic(
                doctor_id=doctor_id,
                clinic_id=clinic_id,
                patient_id=patient_id,
                start_date=start_date,
                end_date=end_date,
                page_no=page_no
            )
            
            appointment_count = len(result.get('appointments', [])) if isinstance(result, dict) else 0
            await ctx.info(f"[get_appointments_basic] Completed successfully - {appointment_count} appointments\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[get_appointments_basic] Failed: {e.message}\n")
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
        partner_id: Optional[str] = None,
        ctx: Context = CurrentContext()
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
        await ctx.info(f"[get_appointment_details_enriched] Getting enriched details for appointment: {appointment_id}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.get_appointment_details_enriched(appointment_id, partner_id)
            
            await ctx.info(f"[get_appointment_details_enriched] Completed successfully\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[get_appointment_details_enriched] Failed: {e.message}\n")
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
        partner_id: Optional[str] = None,
        ctx: Context = CurrentContext()
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
        await ctx.info(f"[get_appointment_details_basic] Getting basic details for appointment: {appointment_id}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.get_appointment_details_basic(appointment_id, partner_id)
            
            await ctx.info(f"[get_appointment_details_basic] Completed successfully\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[get_appointment_details_basic] Failed: {e.message}\n")
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
        limit: Optional[int] = None,
        ctx: Context = CurrentContext()
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
        await ctx.info(f"[get_patient_appointments_enriched] Getting enriched appointments for patient: {patient_id}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.get_patient_appointments_enriched(patient_id, limit)
            
            appointment_count = len(result) if isinstance(result, list) else 0
            await ctx.info(f"[get_patient_appointments_enriched] Completed successfully - {appointment_count} appointments\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[get_patient_appointments_enriched] Failed: {e.message}\n")
            client = EkaEMRClient(access_token=token.token if token else None)
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
        limit: Optional[int] = None,
        ctx: Context = CurrentContext()
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
        await ctx.info(f"[get_patient_appointments_basic] Getting basic appointments for patient: {patient_id}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.get_patient_appointments_basic(patient_id, limit)
            
            appointment_count = len(result) if isinstance(result, list) else 0
            await ctx.info(f"[get_patient_appointments_basic] Completed successfully - {appointment_count} appointments\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[get_patient_appointments_basic] Failed: {e.message}\n")
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
        partner_id: Optional[str] = None,
        ctx: Context = CurrentContext()
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
        await ctx.info(f"[update_appointment] Updating appointment {appointment_id} - fields: {list(update_data.keys())}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.update_appointment(appointment_id, update_data, partner_id)
            
            await ctx.info(f"[update_appointment] Completed successfully\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[update_appointment] Failed: {e.message}\n")
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
        completion_data: Dict[str, Any],
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Mark an appointment as completed.
        
        Args:
            appointment_id: Appointment's unique identifier
            completion_data: Completion details including status and notes
        
        Returns:
            Completion confirmation with updated appointment status
        """
        await ctx.info(f"[complete_appointment] Completing appointment: {appointment_id}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.complete_appointment(appointment_id, completion_data)
            
            await ctx.info(f"[complete_appointment] Completed successfully\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[complete_appointment] Failed: {e.message}\n")
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
        cancel_data: Dict[str, Any],
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Cancel an appointment.
        
        Args:
            appointment_id: Appointment's unique identifier
            cancel_data: Cancellation details including reason and notes
        
        Returns:
            Cancellation confirmation with updated appointment status
        """
        await ctx.info(f"[cancel_appointment] Cancelling appointment: {appointment_id}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.cancel_appointment(appointment_id, cancel_data)
            
            await ctx.info(f"[cancel_appointment] Completed successfully\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[cancel_appointment] Failed: {e.message}\n")
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
        reschedule_data: Dict[str, Any],
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Reschedule an appointment to a new date/time.
        
        Args:
            appointment_id: Appointment's unique identifier
            reschedule_data: New appointment timing and details
        
        Returns:
            Rescheduled appointment details with new timing
        """
        await ctx.info(f"[reschedule_appointment] Rescheduling appointment: {appointment_id}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None)
            appointment_service = AppointmentService(client)
            result = await appointment_service.reschedule_appointment(appointment_id, reschedule_data)
            
            await ctx.info(f"[reschedule_appointment] Completed successfully\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[reschedule_appointment] Failed: {e.message}\n")
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
async def _enrich_appointments_data(client: EkaEMRClient, appointments_data: Dict[str, Any]) -> Dict[str, Any]:
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


