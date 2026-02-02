from typing import Any, Dict, Optional, List, Annotated
import logging
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token, AccessToken
from fastmcp.dependencies import CurrentContext
from fastmcp.server.context import Context
from ..utils.fastmcp_helper import readonly_tool_annotations 

from ..utils.enrichment_helpers import get_cached_data, extract_patient_summary, extract_doctor_summary

from ..clients.eka_emr_client import EkaEMRClient
from ..auth.models import EkaAPIError
from ..services.doctor_clinic_service import DoctorClinicService
from ..utils.tool_registration import get_extra_headers
from ..services.appointment_service import AppointmentService
from ..utils.doctor_discovery_utils import (
    find_doctor_clinics,
    resolve_hospital_id,
    fetch_doctor_availability,
    build_doctor_details_for_card,
    build_elicitation_response
)

logger = logging.getLogger(__name__)


def register_doctor_clinic_tools(mcp: FastMCP) -> None:
    """Register Doctor and Clinic Information MCP tools."""
    
    @mcp.tool(
        tags={"doctor", "clinic", "read", "list", "primary"},
        annotations=readonly_tool_annotations()
    )
    async def get_business_entities(
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Retrieve all doctors and clinics associated with the business workspace.

        When to Use This Tool
        Use this tool when the user references a doctor or clinic by name and IDs are required for downstream actions.
        This is typically the first step before booking appointments or checking availability.

        Trigger Keywords / Phrases
        list doctors, available doctors, clinics list, book with doctor,
        find doctor id, find clinic id, doctor names

        What to Return
        Returns a structured list of doctors and clinics with their identifiers and associations.
        """
        await ctx.info(f"[get_business_entities] Getting business entities (clinics and doctors)")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            doctor_clinic_service = DoctorClinicService(client)
            result = await doctor_clinic_service.get_business_entities()
            
            clinic_count = len(result.get('clinics', [])) if isinstance(result, dict) else 0
            doctor_count = len(result.get('doctors', [])) if isinstance(result, dict) else 0
            await ctx.info(f"[get_business_entities] Completed successfully - {clinic_count} clinics, {doctor_count} doctors\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[get_business_entities] Failed: {e.message}\n")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool(
        tags={"doctor", "read", "profile"},
        annotations=readonly_tool_annotations()
    )
    async def get_doctor_profile_basic(
        doctor_id: Annotated[str, "Doctor UUID"],
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Retrieve basic profile information for a doctor without clinic or appointment context.

        When to Use This Tool
        Use this tool when only standalone doctor details are needed, such as specialization or background.
        For richer context including clinics and appointments, use get_comprehensive_doctor_profile instead.

        Trigger Keywords / Phrases
        doctor profile, doctor details, doctor information, doctor specialization

        What to Return
        Returns basic doctor profile data without clinic associations or appointment history.
        """
        await ctx.info(f"[get_doctor_profile_basic] Getting basic doctor profile for: {doctor_id}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            doctor_clinic_service = DoctorClinicService(client)
            result = await doctor_clinic_service.get_doctor_profile_basic(doctor_id)
            
            await ctx.info(f"[get_doctor_profile_basic] Completed successfully\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[get_doctor_profile_basic] Failed: {e.message}\n")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool(
        tags={"clinic", "read", "profile"},
        annotations=readonly_tool_annotations()
    )
    async def get_clinic_details_basic(
        clinic_id: Annotated[str, "Clinic UUID"],
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Retrieve basic profile information for a clinic without doctor or appointment context.

        When to Use This Tool
        Use this tool when only clinic-level details such as address or facilities are required.
        For full clinic context including doctors and appointments, use get_comprehensive_clinic_profile.

        Trigger Keywords / Phrases
        clinic details, clinic information, clinic address, clinic profile

        What to Return
        Returns basic clinic profile data without doctor associations or appointment history.
        """
        await ctx.info(f"[get_clinic_details_basic] Getting basic clinic details for: {clinic_id}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            doctor_clinic_service = DoctorClinicService(client)
            result = await doctor_clinic_service.get_clinic_details_basic(clinic_id)
            
            await ctx.info(f"[get_clinic_details_basic] Completed successfully\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[get_clinic_details_basic] Failed: {e.message}\n")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool(
        enabled=False,
        tags={"doctor", "read", "services"},
        annotations=readonly_tool_annotations()
    )
    async def get_doctor_services(
        doctor_id: Annotated[str, "Doctor UUID"],
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Retrieve the list of services and specialties offered by a specific doctor.

        When to Use This Tool
        Use this tool when the user wants to know what treatments or services a doctor provides.
        This is useful for service-based discovery or filtering.

        Trigger Keywords / Phrases
        doctor services, treatments offered, doctor specialties, services by doctor

        What to Return
        Returns a list of services and specialties associated with the doctor.
        """
        await ctx.info(f"[get_doctor_services] Getting services for doctor: {doctor_id}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            doctor_clinic_service = DoctorClinicService(client)
            result = await doctor_clinic_service.get_doctor_services(doctor_id)
            
            service_count = len(result) if isinstance(result, list) else 0
            await ctx.info(f"[get_doctor_services] Completed successfully - {service_count} services\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[get_doctor_services] Failed: {e.message}\n")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool(
        enabled=False,
        tags={"doctor", "read", "profile", "comprehensive"},
        annotations=readonly_tool_annotations()
    )
    async def get_comprehensive_doctor_profile(
        doctor_id: Annotated[str, "Doctor UUID"],
        include_clinics: Annotated[bool, "Include clinic associations"] = True,
        include_services: Annotated[bool, "Include doctor services"] = True,
        include_recent_appointments: Annotated[bool, "Include recent appointments"] = True,
        appointment_limit: Annotated[Optional[int], "Max recent appointments"] = 10,
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Retrieve a comprehensive doctor profile including clinics, services, and recent appointments.

        When to Use This Tool
        Use this tool when a complete view of a doctor is required, including where they practice,
        what services they offer, and recent appointment activity.

        Constraints:
        - Appointment history is limited by appointment_limit.

        Trigger Keywords / Phrases
        full doctor profile, doctor overview, doctor with clinics,
        doctor appointment history, complete doctor details

        What to Return
        Returns a fully enriched doctor profile with optional clinic, service, and appointment data.
        """
        await ctx.info(f"[get_comprehensive_doctor_profile] Getting comprehensive profile for doctor: {doctor_id}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            doctor_clinic_service = DoctorClinicService(client)
            result = await doctor_clinic_service.get_comprehensive_doctor_profile(
                doctor_id, include_clinics, include_services, include_recent_appointments, appointment_limit
            )
            
            await ctx.info(f"[get_comprehensive_doctor_profile] Completed successfully\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[get_comprehensive_doctor_profile] Failed: {e.message}\n")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool(
        enabled=False,
        tags={"clinic", "read", "profile", "comprehensive"},
        annotations=readonly_tool_annotations()
    )
    async def get_comprehensive_clinic_profile(
        clinic_id: Annotated[str, "Clinic ID"],
        include_doctors: Annotated[bool, "Include associated doctors"] = True,
        include_services: Annotated[bool, "Include clinic services"] = True,
        include_recent_appointments: Annotated[bool, "Include recent appointments"] = True,
        appointment_limit: Annotated[Optional[int], "Max recent appointments"] = 10,
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Retrieve a comprehensive clinic profile including doctors, services, and recent appointments.

        When to Use This Tool
        Use this tool when a full operational view of a clinic is required, including associated doctors
        and recent appointment activity.

        Trigger Keywords / Phrases
        clinic profile, clinic overview, doctors at clinic,
        clinic services, clinic appointment history

        What to Return
        Returns a fully enriched clinic profile with optional doctor, service, and appointment data.
        """
        await ctx.info(f"[get_comprehensive_clinic_profile] Getting comprehensive profile for clinic: {clinic_id}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            doctor_clinic_service = DoctorClinicService(client)
            result = await doctor_clinic_service.get_comprehensive_clinic_profile(
                clinic_id, include_doctors, include_services, include_recent_appointments, appointment_limit
            )
            
            await ctx.info(f"[get_comprehensive_clinic_profile] Completed successfully\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[get_comprehensive_clinic_profile] Failed: {e.message}\n")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }


# These functions are now handled by the DoctorClinicService class
# Keeping for backward compatibility if needed
async def _enrich_doctor_clinics(client: EkaEMRClient, doctor_id: str, business_entities: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Enrich doctor profile with associated clinic details."""
    try:
        clinics = []
        
        # Extract clinics associated with this doctor from business entities
        doctor_clinics = []
        if "doctors" in business_entities:
            for doctor in business_entities["doctors"]:
                if doctor.get("id") == doctor_id or doctor.get("doctor_id") == doctor_id:
                    doctor_clinics = doctor.get("clinics", [])
                    break
        
        # Get detailed information for each clinic
        for clinic_ref in doctor_clinics:
            clinic_id = clinic_ref.get("id") or clinic_ref.get("clinic_id")
            if clinic_id:
                try:
                    clinic_details = await client.get_clinic_details(clinic_id)
                    clinics.append(clinic_details)
                except Exception as e:
                    logger.warning(f"Could not fetch details for clinic {clinic_id}: {str(e)}")
        
        return clinics
    except Exception as e:
        logger.warning(f"Failed to enrich doctor clinics: {str(e)}")
        return []


async def _enrich_clinic_doctors(client: EkaEMRClient, clinic_id: str, business_entities: Dict[str, Any], include_services: bool = True) -> Dict[str, List[Any]]:
    """Enrich clinic profile with associated doctor details and services."""
    try:
        doctors = []
        all_services = []
        
        # Extract doctors associated with this clinic from business entities
        clinic_doctors = []
        if "clinics" in business_entities:
            for clinic in business_entities["clinics"]:
                if clinic.get("id") == clinic_id or clinic.get("clinic_id") == clinic_id:
                    clinic_doctors = clinic.get("doctors", [])
                    break
        
        # Get detailed information for each doctor and their services
        for doctor_ref in clinic_doctors:
            doctor_id = doctor_ref.get("id") or doctor_ref.get("doctor_id")
            if doctor_id:
                try:
                    doctor_details = await client.get_doctor_profile(doctor_id)
                    doctors.append(doctor_details)
                    
                    # Get services for this doctor if requested
                    if include_services:
                        try:
                            doctor_services = await client.get_doctor_services(doctor_id)
                            if isinstance(doctor_services, list):
                                all_services.extend(doctor_services)
                            elif isinstance(doctor_services, dict) and "services" in doctor_services:
                                all_services.extend(doctor_services["services"])
                        except Exception as e:
                            logger.warning(f"Could not fetch services for doctor {doctor_id}: {str(e)}")
                            
                except Exception as e:
                    logger.warning(f"Could not fetch details for doctor {doctor_id}: {str(e)}")
        
        return {"doctors": doctors, "services": all_services}
    except Exception as e:
        logger.warning(f"Failed to enrich clinic doctors: {str(e)}")
        return {"doctors": [], "services": []}


async def _enrich_doctor_appointments(client: EkaEMRClient, appointments_data: Dict[str, Any], limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Enrich doctor's recent appointments with patient details."""
    try:
        appointments_list = []
        if "appointments" in appointments_data:
            appointments_list = appointments_data.get("appointments", [])
        elif isinstance(appointments_data, list):
            appointments_list = appointments_data
        
        if limit:
            appointments_list = appointments_list[:limit]
        
        enriched_appointments = []
        patients_cache = {}
        
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
            
            enriched_appointments.append(enriched_appointment)
        
        return enriched_appointments
    except Exception as e:
        logger.warning(f"Failed to enrich doctor appointments: {str(e)}")
        return []


async def _enrich_clinic_appointments(client: EkaEMRClient, appointments_data: Dict[str, Any], limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Enrich clinic's recent appointments with patient and doctor details."""
    try:
        appointments_list = []
        if "appointments" in appointments_data:
            appointments_list = appointments_data.get("appointments", [])
        elif isinstance(appointments_data, list):
            appointments_list = appointments_data
        
        if limit:
            appointments_list = appointments_list[:limit]
        
        enriched_appointments = []
        patients_cache = {}
        doctors_cache = {}
        
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
            
            enriched_appointments.append(enriched_appointment)
        
        return enriched_appointments
    except Exception as e:
        logger.warning(f"Failed to enrich clinic appointments: {str(e)}")
        return []

### DOCTOR DISCOVERY / Availability TOOLS ###

def register_discovery_tools(mcp: FastMCP) -> None:
    """Register Doctor Availability Elicitation MCP tools."""
    
    @mcp.tool(
        tags={"doctor", "availability", "elicitation"},
        annotations=readonly_tool_annotations()
    )
    async def doctor_availability_elicitation(
        doctor_id: Annotated[str, "Doctor ID (mandatory)"],
        hospital_id: Annotated[Optional[str], "Hospital/Clinic ID (optional, if known)"] = None,
        preferred_date: Annotated[Optional[str], "Preferred date in YYYY-MM-DD format"] = None,
        preferred_slot_time: Annotated[Optional[str], "Preferred time slot in HH:MM format"] = None,
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Elicit doctor availability for appointment booking.
        
        Flow:
        1. Fetch doctor details
        2. Validate/resolve hospital (if provided & matches, use it; else return all doctor's hospitals)
        3. Fetch available dates (check if preferred_date is available)
        4. Fetch available slots (check if preferred_slot_time is available)
        
        Trigger Keywords:
        check availability, doctor available, when can I book, appointment slots,
        available times for doctor
        
        Returns:
            UI component format (doctor_card) with availability and callbacks
        """
        await ctx.info(f"[doctor_availability_elicitation] doctor_id: {doctor_id}, hospital_id: {hospital_id}, date: {preferred_date}, slot: {preferred_slot_time}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            doctor_clinic_service = DoctorClinicService(client)
            appointment_service = AppointmentService(client)
            
            # 1. Fetch doctor profile
            try:
                doctor_profile = await doctor_clinic_service.get_doctor_profile_basic(doctor_id)
            except EkaAPIError:
                return {"error": f"Doctor with ID '{doctor_id}' not found"}
            
            # 2. Get doctor's clinics from business entities
            # Response structure: { "success": true, "data": { "clinics": [...], "doctors": [...] } }
            entities_response = await doctor_clinic_service.get_business_entities()
            entities_data = entities_response.get('data', entities_response)
            clinics_list = entities_data.get('clinics', [])
            
            # Find clinics where this doctor works (clinics contain doctor IDs)
            doctor_clinics = find_doctor_clinics(clinics_list, doctor_id)
            
            # 3. Resolve hospital
            resolved_hospital_id = resolve_hospital_id(doctor_clinics, hospital_id)
            
            # 4. Build doctor entry
            doctor_entry: Dict[str, Any] = {"doctor_id": doctor_id}
            if resolved_hospital_id:
                doctor_entry["hospital_id"] = resolved_hospital_id
            if preferred_date:
                doctor_entry["date_preference"] = preferred_date
            if preferred_slot_time:
                doctor_entry["slot_preference"] = preferred_slot_time
            
            # 5. Fetch availability
            if resolved_hospital_id:
                availability_list, selected_date = await fetch_doctor_availability(
                    appointment_service, doctor_id, resolved_hospital_id,
                    preferred_date, preferred_slot_time
                )
                if availability_list:
                    doctor_entry["availability"] = availability_list
                if selected_date:
                    doctor_entry["selected_date"] = selected_date
            
            # 6. Build and return response
            doctor_details = build_doctor_details_for_card(doctor_profile, doctor_clinics)
            response = build_elicitation_response(doctor_id, doctor_entry, doctor_details)
            
            await ctx.info(f"[doctor_availability_elicitation] Completed\n")
            return response
            
        except EkaAPIError as e:
            await ctx.error(f"[doctor_availability_elicitation] Failed: {e.message}\n")
            return {"error": e.message}
