"""
Doctor and clinic service module containing core business logic for doctor and clinic management.

This module provides reusable service classes that can be used both by MCP tools
and directly by other applications like CrewAI agents.
"""
from typing import Any, Dict, Optional, List
import logging

from ..clients.eka_emr_client import EkaEMRClient
from ..auth.models import EkaAPIError
from ..utils.enrichment_helpers import (
    get_cached_data, 
    extract_patient_summary, 
    extract_doctor_summary, 
)

logger = logging.getLogger(__name__)


class DoctorClinicService:
    """Core service for doctor and clinic management operations."""
    
    def __init__(self, client: EkaEMRClient):
        """
        Initialize the doctor clinic service.
        
        Args:
            client: EkaEMRClient instance for API calls
        """
        self.client = client
    
    async def get_business_entities(self) -> Dict[str, Any]:
        """
        Get Clinic and Doctor details for the business.
        
        Returns:
            Complete list of clinics and doctors associated with the business
            
        Raises:
            EkaAPIError: If the API call fails
        """
        return await self.client.get_business_entities()
    
    async def get_doctor_profile_basic(self, doctor_id: str) -> Dict[str, Any]:
        """
        Get basic doctor profile information (profile data only).
        
        Args:
            doctor_id: Doctor's unique identifier
            
        Returns:
            Basic doctor profile including specialties, contact info, and background only
            
        Raises:
            EkaAPIError: If the API call fails
        """
        return await self.client.get_doctor_profile(doctor_id)
    
    async def get_clinic_details_basic(self, clinic_id: str) -> Dict[str, Any]:
        """
        Get basic information about a clinic (clinic data only).
        
        Args:
            clinic_id: Clinic's unique identifier
            
        Returns:
            Basic clinic details including address, facilities, and services only
            
        Raises:
            EkaAPIError: If the API call fails
        """
        return await self.client.get_clinic_details(clinic_id)
    
    async def get_doctor_services(self, doctor_id: str) -> Dict[str, Any]:
        """
        Get services offered by a doctor.
        
        Args:
            doctor_id: Doctor's unique identifier
            
        Returns:
            List of services and specialties offered by the doctor
            
        Raises:
            EkaAPIError: If the API call fails
        """
        return await self.client.get_doctor_services(doctor_id)
    
    async def doctor_availability_elicitation(
        self,
        doctor_id: str,
        clinic_id: Optional[str] = None,
        preferred_date: Optional[str] = None,
        preferred_slot_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get doctor availability for appointment booking in UI contract format.
        
        Delegates to client which handles the orchestration logic.
        
        Returns:
            UI contract with doctor_card component, availability, and callbacks
        """
        return await self.client.doctor_availability_elicitation(
            doctor_id, clinic_id, preferred_date, preferred_slot_time
        )
    
    async def doctor_discovery(
        self,
        doctor_name: Optional[str] = None,
        specialty: Optional[str] = None,
        city: Optional[str] = None,
        gender: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for doctors by various criteria.
        
        Args:
            doctor_name: Filter by doctor name
            specialty: Filter by specialty
            city: Filter by city
            gender: Filter by gender
            
        Returns:
            List of matching doctors
        """
        return await self.client.doctor_discovery(
            doctor_name, specialty, city, gender
        )
    
    async def get_comprehensive_doctor_profile(
        self,
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
            include_clinics: Whether to include associated clinic details
            include_services: Whether to include doctor services
            include_recent_appointments: Whether to include recent appointments
            appointment_limit: Limit number of recent appointments
            
        Returns:
            Complete doctor profile with enriched clinic details, services, and appointment history
            
        Raises:
            EkaAPIError: If the API call fails
        """
        # Get basic doctor profile
        doctor_profile = await self.client.get_doctor_profile(doctor_id)
        
        comprehensive_profile = {
            "doctor_profile": doctor_profile,
            "clinics": [],
            "services": [],
            "recent_appointments": []
        }
        
        # Get associated clinics and enrich them
        if include_clinics:
            business_entities = await self.client.get_business_entities()
            clinic_details = await self._enrich_doctor_clinics(doctor_id, business_entities)
            comprehensive_profile["clinics"] = clinic_details
        
        # Get doctor services
        if include_services:
            try:
                services = await self.client.get_doctor_services(doctor_id)
                comprehensive_profile["services"] = services
            except Exception as e:
                logger.warning(f"Could not fetch services for doctor {doctor_id}: {str(e)}")
                comprehensive_profile["services"] = []
        
        # Get recent appointments with patient details
        if include_recent_appointments:
            try:
                recent_appointments = await self.client.get_appointments(
                    doctor_id=doctor_id,
                    page_no=0
                )
                # Enrich with patient details
                enriched_appointments = await self._enrich_doctor_appointments(recent_appointments, appointment_limit)
                comprehensive_profile["recent_appointments"] = enriched_appointments
            except Exception as e:
                logger.warning(f"Could not fetch recent appointments for doctor {doctor_id}: {str(e)}")
                comprehensive_profile["recent_appointments"] = []
        
        return comprehensive_profile
    
    async def get_comprehensive_clinic_profile(
        self,
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
            include_doctors: Whether to include associated doctor details
            include_services: Whether to include clinic services through doctors
            include_recent_appointments: Whether to include recent appointments
            appointment_limit: Limit number of recent appointments
            
        Returns:
            Complete clinic profile with enriched doctor details, services, and appointment history
            
        Raises:
            EkaAPIError: If the API call fails
        """
        # Get basic clinic details
        clinic_details = await self.client.get_clinic_details(clinic_id)
        
        comprehensive_profile = {
            "clinic_details": clinic_details,
            "doctors": [],
            "services": [],
            "recent_appointments": []
        }
        
        # Get associated doctors and their services
        if include_doctors or include_services:
            business_entities = await self.client.get_business_entities()
            doctors_info = await self._enrich_clinic_doctors(clinic_id, business_entities, include_services)
            comprehensive_profile["doctors"] = doctors_info["doctors"]
            if include_services:
                comprehensive_profile["services"] = doctors_info["services"]
        
        # Get recent appointments with patient and doctor details
        if include_recent_appointments:
            try:
                recent_appointments = await self.client.get_appointments(
                    clinic_id=clinic_id,
                    page_no=0
                )
                # Enrich with patient and doctor details
                enriched_appointments = await self._enrich_clinic_appointments(recent_appointments, appointment_limit)
                comprehensive_profile["recent_appointments"] = enriched_appointments
            except Exception as e:
                logger.warning(f"Could not fetch recent appointments for clinic {clinic_id}: {str(e)}")
                comprehensive_profile["recent_appointments"] = []
        
        return comprehensive_profile
    
    async def _enrich_doctor_clinics(self, doctor_id: str, business_entities: Dict[str, Any]) -> List[Dict[str, Any]]:
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
                        clinic_details = await self.client.get_clinic_details(clinic_id)
                        clinics.append(clinic_details)
                    except Exception as e:
                        logger.warning(f"Could not fetch details for clinic {clinic_id}: {str(e)}")
            
            return clinics
        except Exception as e:
            logger.warning(f"Failed to enrich doctor clinics: {str(e)}")
            return []
    
    async def _enrich_clinic_doctors(self, clinic_id: str, business_entities: Dict[str, Any], include_services: bool = True) -> Dict[str, List[Any]]:
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
                        doctor_details = await self.client.get_doctor_profile(doctor_id)
                        doctors.append(doctor_details)
                        
                        # Get services for this doctor if requested
                        if include_services:
                            try:
                                doctor_services = await self.client.get_doctor_services(doctor_id)
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
    
    async def _enrich_doctor_appointments(self, appointments_data: Dict[str, Any], limit: Optional[int] = None) -> List[Dict[str, Any]]:
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
                        self.client.get_patient_details, patient_id, patients_cache
                    )
                    if patient_info:
                        enriched_appointment["patient_details"] = extract_patient_summary(patient_info)
                
                enriched_appointments.append(enriched_appointment)
            
            return enriched_appointments
        except Exception as e:
            logger.warning(f"Failed to enrich doctor appointments: {str(e)}")
            return []
    
    async def _enrich_clinic_appointments(self, appointments_data: Dict[str, Any], limit: Optional[int] = None) -> List[Dict[str, Any]]:
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
                        self.client.get_patient_details, patient_id, patients_cache
                    )
                    if patient_info:
                        enriched_appointment["patient_details"] = extract_patient_summary(patient_info)
                
                # Enrich with doctor details
                doctor_id = appointment.get("doctor_id")
                if doctor_id:
                    doctor_info = await get_cached_data(
                        self.client.get_doctor_profile, doctor_id, doctors_cache
                    )
                    if doctor_info:
                        enriched_appointment["doctor_details"] = extract_doctor_summary(doctor_info)
                
                enriched_appointments.append(enriched_appointment)
            
            return enriched_appointments
        except Exception as e:
            logger.warning(f"Failed to enrich clinic appointments: {str(e)}")
            return []