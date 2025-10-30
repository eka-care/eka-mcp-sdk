from typing import Any, Dict, Optional
import logging
from fastmcp import FastMCP

from ..clients.doctor_tools_client import DoctorToolsClient
from ..auth.models import EkaAPIError
from ..utils.enrichment_helpers import (
    calculate_age_from_dob,
    extract_doctor_summary,
    extract_clinic_summary
)

logger = logging.getLogger(__name__)


def register_prescription_tools(mcp: FastMCP) -> None:
    """Register Prescription Management MCP tools."""
    client = DoctorToolsClient()
    
    @mcp.tool()
    async def get_prescription_details_basic(prescription_id: str) -> Dict[str, Any]:
        """
        Get basic prescription details (prescription data only).
        
        ⚠️  Consider using get_comprehensive_prescription_details instead for complete information.
        Only use this if you specifically need basic prescription data without patient/doctor/clinic details.
        
        Args:
            prescription_id: Prescription's unique identifier
        
        Returns:
            Basic prescription details including medications and diagnosis only
        """
        try:
            result = await client.get_prescription_details(prescription_id)
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
    async def get_comprehensive_prescription_details(
        prescription_id: str,
        include_patient_details: bool = True,
        include_doctor_details: bool = True,
        include_clinic_details: bool = True
    ) -> Dict[str, Any]:
        """
        🌟 RECOMMENDED: Get comprehensive prescription details with enriched patient, doctor, and clinic information.
        
        This is the preferred tool for getting prescription information as it provides complete context
        including patient demographics, prescribing doctor details, and clinic information.
        Use this instead of get_prescription_details_basic unless you specifically need only prescription data.
        
        Args:
            prescription_id: Prescription's unique identifier
            include_patient_details: Whether to include patient details (default: True)
            include_doctor_details: Whether to include doctor details (default: True)
            include_clinic_details: Whether to include clinic details (default: True)
        
        Returns:
            Complete prescription details with enriched patient, doctor, and clinic information
        """
        try:
            # Get basic prescription details
            prescription = await client.get_prescription_details(prescription_id)
            
            comprehensive_prescription = {
                "prescription": prescription,
                "patient_details": None,
                "doctor_details": None,
                "clinic_details": None
            }
            
            # Enrich with patient details
            if include_patient_details and prescription.get("patient_id"):
                try:
                    patient_info = await client.get_patient_details(prescription["patient_id"])
                    patient_summary = {
                        "name": patient_info.get("fln", ""),
                        "mobile": patient_info.get("mobile", ""),
                        "email": patient_info.get("email", ""),
                        "age": calculate_age_from_dob(patient_info.get("dob")),
                        "gender": patient_info.get("gen", ""),
                        "blood_group": patient_info.get("bg", ""),
                        "full_profile": patient_info
                    }
                    comprehensive_prescription["patient_details"] = patient_summary
                except Exception as e:
                    logger.warning(f"Could not fetch patient details for prescription {prescription_id}: {str(e)}")
            
            # Enrich with doctor details
            if include_doctor_details and prescription.get("doctor_id"):
                try:
                    doctor_info = await client.get_doctor_profile(prescription["doctor_id"])
                    doctor_summary = extract_doctor_summary(doctor_info)
                    doctor_summary["full_profile"] = doctor_info
                    comprehensive_prescription["doctor_details"] = doctor_summary
                except Exception as e:
                    logger.warning(f"Could not fetch doctor details for prescription {prescription_id}: {str(e)}")
            
            # Enrich with clinic details
            if include_clinic_details and prescription.get("clinic_id"):
                try:
                    clinic_info = await client.get_clinic_details(prescription["clinic_id"])
                    clinic_summary = extract_clinic_summary(clinic_info)
                    clinic_summary["full_profile"] = clinic_info
                    comprehensive_prescription["clinic_details"] = clinic_summary
                except Exception as e:
                    logger.warning(f"Could not fetch clinic details for prescription {prescription_id}: {str(e)}")
            
            return {"success": True, "data": comprehensive_prescription}
        except EkaAPIError as e:
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }


