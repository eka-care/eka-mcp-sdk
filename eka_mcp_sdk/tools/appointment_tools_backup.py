from typing import Any, Dict, Optional
import logging
from fastmcp import FastMCP

from ..clients.eka_emr_client import EkaEMRClient
from ..auth.models import EkaAPIError

logger = logging.getLogger(__name__)


def register_appointment_tools(mcp: FastMCP) -> None:
    """Register Appointment Management MCP tools."""
    client = EkaEMRClient()
    
    @mcp.tool()
    async def get_appointment_slots(
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
        """
        try:
            result = await client.get_appointment_slots(doctor_id, clinic_id, date)
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
    async def book_appointment(appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Book an appointment slot for a patient.
        
        Args:
            appointment_data: Appointment details including patient, doctor, timing, and mode
        
        Returns:
            Booked appointment details with confirmation
        """
        try:
            result = await client.book_appointment(appointment_data)
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
    async def get_appointments(
        doctor_id: Optional[str] = None,
        clinic_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page_no: int = 0
    ) -> Dict[str, Any]:
        """
        Get appointments with comprehensive details including patient, doctor, and clinic information.
        
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
            # Get basic appointments
            appointments_result = await client.get_appointments(
                doctor_id=doctor_id,
                clinic_id=clinic_id,
                patient_id=patient_id,
                start_date=start_date,
                end_date=end_date,
                page_no=page_no
            )
            
            # Enrich with additional details
            enriched_appointments = await _enrich_appointments_data(client, appointments_result)
            
            return {"success": True, "data": enriched_appointments}
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
    async def get_appointment_details(
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
        """
        try:
            # Get basic appointment details
            appointment_result = await client.get_appointment_details(appointment_id, partner_id)
            
            # Enrich with additional details
            enriched_appointment = await _enrich_single_appointment_data(client, appointment_result)
            
            return {"success": True, "data": enriched_appointment}
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
    async def get_patient_appointments(
        patient_id: str,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get all appointments for a specific patient.
        
        Args:
            patient_id: Patient's unique identifier
            limit: Maximum number of appointments to return
        
        Returns:
            List of all appointments for the patient
        """
        try:
            result = await client.get_patient_appointments(patient_id, limit)
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
            result = await client.update_appointment(appointment_id, update_data, partner_id)
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
            result = await client.complete_appointment(appointment_id, completion_data)
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
            result = await client.cancel_appointment(appointment_id, cancel_data)
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
            result = await client.reschedule_appointment(appointment_id, reschedule_data)
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