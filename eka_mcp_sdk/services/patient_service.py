"""
Patient service module containing core business logic for patient management.

This module provides reusable service classes that can be used both by MCP tools
and directly by other applications like CrewAI agents.
"""
from typing import Any, Dict, Optional, List
import logging

from ..clients.eka_emr_client import EkaEMRClient
from ..auth.models import EkaAPIError
from ..utils.enrichment_helpers import (
    get_cached_data, 
    extract_doctor_summary, 
    extract_clinic_summary,
    get_appointment_status_info
)

logger = logging.getLogger(__name__)


class PatientService:
    """Core service for patient management operations."""
    
    def __init__(self, client: EkaEMRClient):
        """
        Initialize the patient service.
        
        Args:
            client: EkaEMRClient instance for API calls
        """
        self.client = client
    
    async def search_patients(
        self,
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
        return await self.client.search_patients(prefix, limit, select)
    
    async def get_patient_details_basic(self, patient_id: str) -> Dict[str, Any]:
        """
        Get basic patient details by profile ID (profile data only).
        
        Args:
            patient_id: Patient's unique identifier
            
        Returns:
            Basic patient profile including personal and medical information
            
        Raises:
            EkaAPIError: If the API call fails
        """
        return await self.client.get_patient_details(patient_id)
    
    async def get_comprehensive_patient_profile(
        self,
        patient_id: str,
        include_appointments: bool = True,
        appointment_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive patient profile including detailed appointment history.
        
        This method provides complete context including appointment history with 
        doctor names, clinic details, and appointment status.
        
        Args:
            patient_id: Patient's unique identifier
            include_appointments: Whether to include appointment history
            appointment_limit: Limit number of appointments returned
            
        Returns:
            Complete patient profile with enriched appointment history
            
        Raises:
            EkaAPIError: If the API call fails
        """
        # Get basic patient details
        patient_profile = await self.client.get_patient_details(patient_id)
        
        comprehensive_profile = {
            "patient_profile": patient_profile,
            "appointments": []
        }
        
        if include_appointments:
            # Get patient appointments
            appointments_result = await self.client.get_patient_appointments(
                patient_id, appointment_limit
            )
            
            # Enrich appointments with doctor and clinic details
            enriched_appointments = await self._enrich_patient_appointments(
                appointments_result
            )
            comprehensive_profile["appointments"] = enriched_appointments
        
        return comprehensive_profile
    
    async def add_patient(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new patient profile.
        
        Args:
            patient_data: Patient information including required and optional fields
            
        Returns:
            Created patient profile with oid identifier
            
        Raises:
            EkaAPIError: If the API call fails
        """
        return await self.client.add_patient(patient_data)
    
    async def list_patients(
        self,
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
        return await self.client.list_patients(
            page_no, page_size, select, from_timestamp, include_archived
        )
    
    async def update_patient(
        self,
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
        return await self.client.update_patient(patient_id, update_data)
    
    async def archive_patient(
        self,
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
        return await self.client.archive_patient(patient_id)
    
    async def get_patient_by_mobile(
        self,
        mobile: str,
        full_profile: bool = False,
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
        return await self.client.get_patient_by_mobile(mobile, full_profile)
    
    async def mobile_number_verification(
        self,
        mobile_number: str,
        otp: Optional[str] = None,
        stage: str = "send_otp"
    ) -> Dict[str, Any]:
        """
        Unified mobile number verification - handles both OTP send and verify stages.
        
        Args:
            mobile_number: Mobile number to verify (10 digits without country code)
            otp: One-Time Password (required for verify_otp stage)
            stage: "send_otp" to send OTP, "verify_otp" to verify
            
        Returns:
            Response indicating OTP sent/verification status
        """
        return await self.client.mobile_number_verification(mobile_number, otp, stage)
    
    async def list_all_patient_profiles(self) -> Dict[str, Any]:
        """
        Retrieve all patient profiles.
        
        Returns:
            List of all patient profiles
            
        Raises:
            EkaAPIError: If the API call fails
        """
        return await self.client.list_all_patient_profiles()
    
    async def get_patient_vitals(self, patient_id: str) -> Dict[str, Any]:
        """
        Retrieve patient vitals.
        
        Args:
            patient_id: Patient's unique identifier
            
        Returns:
            Patient vitals data
            
        Raises:
            EkaAPIError: If the API call fails
        """
        return await self.client.get_patient_vitals(patient_id)
    
    async def _enrich_patient_appointments(
        self, 
        appointments_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Enrich patient appointments with doctor and clinic details.
        
        Args:
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
                        self.client.get_doctor_profile, doctor_id, doctors_cache
                    )
                    if doctor_info:
                        enriched_appointment["doctor_details"] = extract_doctor_summary(doctor_info)
                
                # Enrich with clinic details
                clinic_id = appointment.get("clinic_id")
                if clinic_id:
                    clinic_info = await get_cached_data(
                        self.client.get_clinic_details, clinic_id, clinics_cache
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