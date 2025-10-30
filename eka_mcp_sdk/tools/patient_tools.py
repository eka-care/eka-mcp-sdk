from typing import Any, Dict, Optional, List
import logging
from fastmcp import FastMCP

from ..clients.doctor_tools_client import DoctorToolsClient
from ..auth.models import EkaAPIError
from ..utils.enrichment_helpers import (
    get_cached_data, 
    extract_doctor_summary, 
    extract_clinic_summary,
    get_appointment_status_info
)

logger = logging.getLogger(__name__)


def register_patient_tools(mcp: FastMCP) -> None:
    """Register Patient Management MCP tools."""
    client = DoctorToolsClient()
    
    @mcp.tool()
    async def search_patients(
        prefix: str,
        limit: Optional[int] = None,
        select: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search patient profiles by username, mobile, or full name (prefix match).
        
        Args:
            prefix: Search term to match against patient profiles (username, mobile, or full name)
            limit: Maximum number of results to return (default: 50, max: 50)
            select: Comma-separated list of additional fields to include
        
        Returns:
            List of patients matching the search criteria
        """
        try:
            result = await client.search_patients(prefix, limit, select)
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
    async def get_patient_details_basic(patient_id: str) -> Dict[str, Any]:
        """
        Get basic patient details by profile ID (profile data only).
        
        ⚠️  Consider using get_comprehensive_patient_profile instead for complete information.
        Only use this if you specifically need basic patient data without appointment history.
        
        Args:
            patient_id: Patient's unique identifier
        
        Returns:
            Basic patient profile including personal and medical information only
        """
        try:
            result = await client.get_patient_details(patient_id)
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
    async def get_comprehensive_patient_profile(
        patient_id: str,
        include_appointments: bool = True,
        appointment_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        🌟 RECOMMENDED: Get comprehensive patient profile including detailed appointment history with enriched doctor and clinic information.
        
        This is the preferred tool for getting patient information as it provides complete context
        including appointment history with doctor names, clinic details, and appointment status.
        Use this instead of get_patient_details_basic unless you specifically need only profile data.
        
        Args:
            patient_id: Patient's unique identifier
            include_appointments: Whether to include appointment history (default: True)
            appointment_limit: Limit number of appointments returned (optional)
        
        Returns:
            Complete patient profile with enriched appointment history including doctor and clinic details
        """
        try:
            # Get basic patient details
            patient_profile = await client.get_patient_details(patient_id)
            
            comprehensive_profile = {
                "patient_profile": patient_profile,
                "appointments": []
            }
            
            if include_appointments:
                # Get patient appointments
                appointments_result = await client.get_patient_appointments(patient_id, appointment_limit)
                
                # Enrich appointments with doctor and clinic details
                enriched_appointments = await _enrich_patient_appointments(client, appointments_result)
                comprehensive_profile["appointments"] = enriched_appointments
            
            return {"success": True, "data": comprehensive_profile}
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
    async def add_patient(patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new patient profile.
        
        Args:
            patient_data: Patient information including name (fn/ln or fln), dob, gen, and optional fields like mobile, email, etc.
        
        Returns:
            Created patient profile with oid identifier
        """
        try:
            result = await client.add_patient(patient_data)
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
    async def list_patients(
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
            page_size: Number of records per page (default: 500, max: 2000)
            select: Comma-separated list of additional fields to include
            from_timestamp: Get profiles created after this epoch timestamp
            include_archived: Include archived profiles in response
        
        Returns:
            Paginated list of patient profiles
        """
        try:
            result = await client.list_patients(page_no, page_size, select, from_timestamp, include_archived)
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
    async def update_patient(
        patient_id: str,
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update patient profile details.
        
        Args:
            patient_id: Patient's unique identifier (oid)
            update_data: Fields to update (name, dob, gen, mobile, email, etc.)
        
        Returns:
            Success message confirming profile update
        """
        try:
            result = await client.update_patient(patient_id, update_data)
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
    async def archive_patient(
        patient_id: str,
        archive: bool = True
    ) -> Dict[str, Any]:
        """
        Archive patient profile (soft delete).
        
        Args:
            patient_id: Patient's unique identifier (oid)
            archive: Whether to archive the profile (default: True)
        
        Returns:
            Success message confirming profile archival
        """
        try:
            result = await client.archive_patient(patient_id, archive)
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
    async def get_patient_by_mobile(
        mobile: str,
        full_profile: bool = False
    ) -> Dict[str, Any]:
        """
        Retrieve patient profiles by mobile number.
        
        Args:
            mobile: Mobile number in format +<country_code><number> (e.g., +911234567890)
            full_profile: If True, returns full patient profile details
        
        Returns:
            Patient profile(s) matching the mobile number
        """
        try:
            result = await client.get_patient_by_mobile(mobile, full_profile)
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


async def _enrich_patient_appointments(client: DoctorToolsClient, appointments_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Enrich patient appointments with doctor and clinic details.
    
    Args:
        client: DoctorToolsClient instance
        appointments_data: Raw appointments data from API
    
    Returns:
        List of enriched appointments with doctor and clinic information
    """
    try:
        # Handle different response structures
        appointments_list = []
        if isinstance(appointments_data, list):
            appointments_list = appointments_data
        elif isinstance(appointments_data, dict):
            if "appointments" in appointments_data:
                appointments_list = appointments_data.get("appointments", [])
            elif "data" in appointments_data:
                appointments_list = appointments_data.get("data", [])
            else:
                appointments_list = [appointments_data] if appointments_data.get("appointment_id") else []
        
        if not appointments_list:
            return []
        
        enriched_appointments = []
        
        # Cache for avoiding duplicate API calls
        doctors_cache = {}
        clinics_cache = {}
        
        for appointment in appointments_list:
            enriched_appointment = appointment.copy()
            
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
            
            # Add appointment status context
            status = appointment.get("status", "")
            enriched_appointment["status_info"] = get_appointment_status_info(status)
            
            enriched_appointments.append(enriched_appointment)
        
        return enriched_appointments
        
    except Exception as e:
        logger.warning(f"Failed to enrich patient appointments: {str(e)}")
        # Return original data if enrichment fails
        if isinstance(appointments_data, list):
            return appointments_data
        elif isinstance(appointments_data, dict) and "appointments" in appointments_data:
            return appointments_data.get("appointments", [])
        else:
            return []


