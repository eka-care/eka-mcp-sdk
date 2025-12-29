"""
Prescription service module containing core business logic for prescription management.

This module provides reusable service classes that can be used both by MCP tools
and directly by other applications like CrewAI agents.
"""
from typing import Any, Dict, Optional
import logging

from ..clients.eka_emr_client import EkaEMRClient
from ..auth.models import EkaAPIError
from ..utils.enrichment_helpers import (
    calculate_age_from_dob,
    extract_doctor_summary,
    extract_clinic_summary
)

logger = logging.getLogger(__name__)


class PrescriptionService:
    """Core service for prescription management operations."""
    
    def __init__(self, client: EkaEMRClient):
        """
        Initialize the prescription service.
        
        Args:
            client: EkaEMRClient instance for API calls
        """
        self.client = client
    
    async def get_prescription_details_basic(self, prescription_id: str) -> Dict[str, Any]:
        """
        Get basic prescription details (prescription data only).
        
        Args:
            prescription_id: Prescription's unique identifier
            
        Returns:
            Basic prescription details including medications and diagnosis only
            
        Raises:
            EkaAPIError: If the API call fails
        """
        return await self.client.get_prescription_details(prescription_id)
    
    async def get_comprehensive_prescription_details(
        self,
        prescription_id: str,
        include_patient_details: bool = True,
        include_doctor_details: bool = True,
        include_clinic_details: bool = True
    ) -> Dict[str, Any]:
        """
        Get comprehensive prescription details with enriched patient, doctor, and clinic information.
        
        This method provides complete context including patient demographics, 
        prescribing doctor details, and clinic information.
        
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
        # Get basic prescription details
        prescription = await self.client.get_prescription_details(prescription_id)
        
        comprehensive_prescription = {
            "prescription": prescription,
            "patient_details": None,
            "doctor_details": None,
            "clinic_details": None
        }
        
        # Enrich with patient details
        if include_patient_details and prescription.get("patient_id"):
            try:
                patient_info = await self.client.get_patient_details(prescription["patient_id"])
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
                doctor_info = await self.client.get_doctor_profile(prescription["doctor_id"])
                doctor_summary = extract_doctor_summary(doctor_info)
                doctor_summary["full_profile"] = doctor_info
                comprehensive_prescription["doctor_details"] = doctor_summary
            except Exception as e:
                logger.warning(f"Could not fetch doctor details for prescription {prescription_id}: {str(e)}")
        
        # Enrich with clinic details
        if include_clinic_details and prescription.get("clinic_id"):
            try:
                clinic_info = await self.client.get_clinic_details(prescription["clinic_id"])
                clinic_summary = extract_clinic_summary(clinic_info)
                clinic_summary["full_profile"] = clinic_info
                comprehensive_prescription["clinic_details"] = clinic_summary
            except Exception as e:
                logger.warning(f"Could not fetch clinic details for prescription {prescription_id}: {str(e)}")
        
        return comprehensive_prescription