from typing import Any, Dict, Optional, List, Annotated
import logging
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token, AccessToken

from ..clients.doctor_tools_client import DoctorToolsClient
from ..auth.models import EkaAPIError
from ..core.doctor_clinic_service import DoctorClinicService

logger = logging.getLogger(__name__)


def register_doctor_clinic_tools(mcp: FastMCP) -> None:
    """Register Doctor and Clinic Information MCP tools."""
    
    @mcp.tool(
        description="Get clinic and doctor details for the business"
    )
    async def get_business_entities() -> Dict[str, Any]:
        """Returns complete list of clinics and doctors associated with the business."""
        try:
            token: AccessToken | None = get_access_token()
            client = DoctorToolsClient(access_token=token.token if token else None)
            doctor_clinic_service = DoctorClinicService(client)
            result = await doctor_clinic_service.get_business_entities()
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
    async def get_doctor_profile_basic(doctor_id: str) -> Dict[str, Any]:
        """
        Get basic doctor profile information (profile data only).
        
        ⚠️  Consider using get_comprehensive_doctor_profile instead for complete information.
        Only use this if you specifically need basic doctor data without clinic associations and appointments.
        
        Args:
            doctor_id: Doctor's unique identifier
        
        Returns:
            Basic doctor profile including specialties, contact info, and background only
        """
        try:
            token: AccessToken | None = get_access_token()
            client = DoctorToolsClient(access_token=token.token if token else None)
            doctor_clinic_service = DoctorClinicService(client)
            result = await doctor_clinic_service.get_doctor_profile_basic(doctor_id)
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
    async def get_clinic_details_basic(clinic_id: str) -> Dict[str, Any]:
        """
        Get basic information about a clinic (clinic data only).
        
        ⚠️  Consider using get_comprehensive_clinic_profile instead for complete information.
        Only use this if you specifically need basic clinic data without doctor associations and appointments.
        
        Args:
            clinic_id: Clinic's unique identifier
        
        Returns:
            Basic clinic details including address, facilities, and services only
        """
        try:
            token: AccessToken | None = get_access_token()
            client = DoctorToolsClient(access_token=token.token if token else None)
            doctor_clinic_service = DoctorClinicService(client)
            result = await doctor_clinic_service.get_clinic_details_basic(clinic_id)
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
    async def get_doctor_services(doctor_id: str) -> Dict[str, Any]:
        """
        Get services offered by a doctor.
        
        Args:
            doctor_id: Doctor's unique identifier
        
        Returns:
            List of services and specialties offered by the doctor
        """
        try:
            token: AccessToken | None = get_access_token()
            client = DoctorToolsClient(access_token=token.token if token else None)
            doctor_clinic_service = DoctorClinicService(client)
            result = await doctor_clinic_service.get_doctor_services(doctor_id)
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
    async def get_comprehensive_doctor_profile(
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
            include_clinics: Whether to include associated clinic details (default: True)
            include_services: Whether to include doctor services (default: True)
            include_recent_appointments: Whether to include recent appointments (default: True)
            appointment_limit: Limit number of recent appointments (default: 10)
        
        Returns:
            Complete doctor profile with enriched clinic details, services, and appointment history
        """
        try:
            token: AccessToken | None = get_access_token()
            client = DoctorToolsClient(access_token=token.token if token else None)
            doctor_clinic_service = DoctorClinicService(client)
            result = await doctor_clinic_service.get_comprehensive_doctor_profile(
                doctor_id, include_clinics, include_services, include_recent_appointments, appointment_limit
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
    async def get_comprehensive_clinic_profile(
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
            include_doctors: Whether to include associated doctor details (default: True)
            include_services: Whether to include clinic services through doctors (default: True)
            include_recent_appointments: Whether to include recent appointments (default: True)
            appointment_limit: Limit number of recent appointments (default: 10)
        
        Returns:
            Complete clinic profile with enriched doctor details, services, and appointment history
        """
        try:
            token: AccessToken | None = get_access_token()
            client = DoctorToolsClient(access_token=token.token if token else None)
            doctor_clinic_service = DoctorClinicService(client)
            result = await doctor_clinic_service.get_comprehensive_clinic_profile(
                clinic_id, include_doctors, include_services, include_recent_appointments, appointment_limit
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


# These functions are now handled by the DoctorClinicService class
# Keeping for backward compatibility if needed
async def _enrich_doctor_clinics(client: DoctorToolsClient, doctor_id: str, business_entities: Dict[str, Any]) -> List[Dict[str, Any]]:
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


async def _enrich_clinic_doctors(client: DoctorToolsClient, clinic_id: str, business_entities: Dict[str, Any], include_services: bool = True) -> Dict[str, List[Any]]:
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


async def _enrich_doctor_appointments(client: DoctorToolsClient, appointments_data: Dict[str, Any], limit: Optional[int] = None) -> List[Dict[str, Any]]:
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


async def _enrich_clinic_appointments(client: DoctorToolsClient, appointments_data: Dict[str, Any], limit: Optional[int] = None) -> List[Dict[str, Any]]:
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


