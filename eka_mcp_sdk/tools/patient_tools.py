from typing import Any, Dict, Optional, List, Annotated
import logging
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token, AccessToken
from fastmcp.dependencies import CurrentContext
from fastmcp.server.context import Context

from ..utils.enrichment_helpers import (
    get_cached_data,
    extract_doctor_summary,
    extract_clinic_summary,
    get_appointment_status_info
)

from ..clients.eka_emr_client import EkaEMRClient
from ..auth.models import EkaAPIError
from ..services.patient_service import PatientService

logger = logging.getLogger(__name__)


def register_patient_tools(mcp: FastMCP) -> None:
    """Register Patient Management MCP tools."""
    
    # @mcp.tool(
    #     description="It is workspace specific so don't use it for now. Instead refer to list_patients or get_patient_by_mobile."
    # )
    async def search_patients(
        prefix: Annotated[str, "Search prefix to match against patient profiles (username, mobile, or full name)"],
        limit: Annotated[Optional[int], "Maximum number of results to return (default: 50, max: 50)"] = None,
        select: Annotated[Optional[str], "Comma-separated list of additional fields to include"] = None,
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Search patients by prefix (workspace-specific feature).
        
        For general patient lookup, use:
        - list_patients: View all patients with pagination
        - get_patient_by_mobile: Find by exact mobile number
        """
        await ctx.info(f"[search_patients] Searching patients with prefix: {prefix}")
        await ctx.debug(f"Search parameters - limit: {limit}, select: {select}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None)
            patient_service = PatientService(client)
            result = await patient_service.search_patients(prefix, limit, select)
            
            patient_count = len(result.get('patients', [])) if isinstance(result, dict) else 0
            await ctx.info(f"[search_patients] Found {patient_count} patients matching search criteria\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[search_patients] Failed: {e.message}\n")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool(
        description="Get basic patient details by profile ID (profile data only). Consider using get_comprehensive_patient_profile instead for complete information."
    )
    async def get_patient_details_basic(
        patient_id: Annotated[str, "Patient's unique identifier"],
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """Returns basic patient profile including personal and medical information only."""
        await ctx.info(f"[get_patient_details_basic] Getting basic patient details for: {patient_id}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None)
            patient_service = PatientService(client)
            result = await patient_service.get_patient_details_basic(patient_id)
            
            await ctx.info(f"[get_patient_details_basic] Completed successfully\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[get_patient_details_basic] Failed: {e.message}\n")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool(
        description="Get complete patient profile with appointment history. Use for 'show patient details' or viewing appointments."
    )
    async def get_comprehensive_patient_profile(
        patient_id: Annotated[str, "Patient ID (oid from list/mobile lookup)"],
        include_appointments: Annotated[bool, "Include appointments (default: True)"] = True,
        appointment_limit: Annotated[Optional[int], "Limit appointments"] = None,
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        RECOMMENDED: Get comprehensive patient profile including detailed appointment history with enriched doctor and clinic information.
        
        This is the preferred tool for getting patient information as it provides complete context
        including appointment history with doctor names, clinic details, and appointment status.
        Use this instead of get_patient_details_basic unless you specifically need only profile data.
        
        Use when:
        - "Show patient details"
        - "Patient medical history"
        - Need appointments with doctor/clinic names
        
        Returns:
            Complete patient profile with enriched appointment history including doctor and clinic details
        """
        await ctx.info(f"[get_comprehensive_patient_profile] Getting comprehensive profile for patient: {patient_id}")
        await ctx.debug(f"Include appointments: {include_appointments}, limit: {appointment_limit}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None)
            patient_service = PatientService(client)
            result = await patient_service.get_comprehensive_patient_profile(
                patient_id, include_appointments, appointment_limit
            )
            
            await ctx.info(f"[get_comprehensive_patient_profile] Completed successfully\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[get_comprehensive_patient_profile] Failed: {e.message}\n")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool(
        description="Create new patient. Required: fln (name), dob (YYYY-MM-DD), gen (M/F/O). Use when patient not found."
    )
    # pydantic model should be used here for patient_data
    async def add_patient(
        patient_data: Annotated[Dict[str, Any], "Required: fln, dob, gen. Optional: mobile (+91...), email, address"],
        ctx: Context = CurrentContext()
        ) -> Dict[str, Any]:
        """
        Create patient profile.
        
        Required: fln, dob, gen
        Optional: mobile, email, address
        
        Example: {"fln": "John Doe", "dob": "1990-01-15", "gen": "M", "mobile": "+919876543210"}
        
        Returns: Patient with oid (patient_id)
        """
        await ctx.info(f"[add_patient] Creating new patient profile")
        await ctx.debug(f"Patient data keys: {list(patient_data.keys())}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None)
            patient_service = PatientService(client)
            result = await patient_service.add_patient(patient_data)
            
            patient_id = result.get('oid') if isinstance(result, dict) else None
            await ctx.info(f"[add_patient] Completed successfully - patient ID: {patient_id}\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[add_patient] Failed: {e.message}\n")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool(
        description="List patient profiles by browsing pages when no identifier is known"
    )
    async def list_patients(
        page_no: Annotated[int, "Page number (starts from 0)"],
        page_size: Annotated[Optional[int], "Records per page (default: 500, max: 2000)"] = None,
        select: Annotated[Optional[str], "Additional fields"] = None,
        from_timestamp: Annotated[Optional[int], "Filter: created after timestamp"] = None,
        include_archived: Annotated[bool, "Include archived (default: False)"] = False,
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        List all patients with pagination.
        
        Use when the user wants to:
        - browse patients
        - scroll through patient records
        - refer to themselves without providing an identifier
        
        Returns: List with oid (patient_id), fln (name), mobile
        """
        await ctx.info(f"[list_patients] Listing patients - page {page_no}, size: {page_size or 'default'}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None)
            patient_service = PatientService(client)
            result = await patient_service.list_patients(page_no, page_size, select, from_timestamp, include_archived)
            
            patient_count = len(result.get('patients', [])) if isinstance(result, dict) else 0
            await ctx.info(f"[list_patients] Completed successfully - retrieved {patient_count} patients\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[list_patients] Failed: {e.message}\n")
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
        update_data: Dict[str, Any],
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Update patient profile details.
        
        Args:
            patient_id: Patient's unique identifier (oid)
            update_data: Fields to update (name, dob, gen, mobile, email, etc.)
        
        Returns:
            Success message confirming profile update
        """
        await ctx.info(f"[update_patient] Updating patient {patient_id} - fields: {list(update_data.keys())}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None)
            patient_service = PatientService(client)
            result = await patient_service.update_patient(patient_id, update_data)
            
            await ctx.info(f"[update_patient] Completed successfully\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[update_patient] Failed: {e.message}\n")
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
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None)
            patient_service = PatientService(client)
            result = await patient_service.archive_patient(patient_id, archive)
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
            description="🌟 Find patient by mobile number. Use this when user provides mobile. Fast and exact match."
    )
    async def get_patient_by_mobile(
        mobile: Annotated[str, "Mobile with country code: +919876543210"],
        full_profile: Annotated[bool, "Return full profile (default: False)"] = False,
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Find patient by exact mobile number.
        
        Format: +<country_code><number>
        - India: +919876543210
        - US: +11234567890
        
        Use when: "Book appointment" → Ask "Your mobile?" → Call this
        
        Returns: Patient with oid (patient_id)
        """
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None)
            patient_service = PatientService(client)
            result = await patient_service.get_patient_by_mobile(mobile, full_profile)
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


# This function is now handled by the PatientService class
# Keeping for backward compatibility if needed
async def _enrich_patient_appointments(client: EkaEMRClient, appointments_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Enrich patient appointments with doctor and clinic details.
    
    Args:
        client: EkaEMRClient instance
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


