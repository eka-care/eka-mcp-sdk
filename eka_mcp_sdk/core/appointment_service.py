"""
Appointment service module containing core business logic for appointment management.

This module provides reusable service classes that can be used both by MCP tools
and directly by other applications like CrewAI agents.
"""
from typing import Any, Dict, Optional, List
import logging

from ..clients.doctor_tools_client import DoctorToolsClient
from ..auth.models import EkaAPIError
from ..utils.enrichment_helpers import (
    get_cached_data, 
    extract_patient_summary, 
    extract_doctor_summary, 
    extract_clinic_summary
)

logger = logging.getLogger(__name__)


class AppointmentService:
    """Core service for appointment management operations."""
    
    def __init__(self, client: DoctorToolsClient):
        """
        Initialize the appointment service.
        
        Args:
            client: DoctorToolsClient instance for API calls
        """
        self.client = client
    
    async def get_appointment_slots(
        self,
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
            
        Raises:
            EkaAPIError: If the API call fails
        """
        return await self.client.get_appointment_slots(doctor_id, clinic_id, date)
    
    async def book_appointment(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Book an appointment slot for a patient.
        
        Args:
            appointment_data: Appointment details including patient, doctor, timing, and mode
            
        Returns:
            Booked appointment details with confirmation
            
        Raises:
            EkaAPIError: If the API call fails
        """
        return await self.client.book_appointment(appointment_data)
    
    async def get_appointments_enriched(
        self,
        doctor_id: Optional[str] = None,
        clinic_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page_no: int = 0
    ) -> Dict[str, Any]:
        """
        Get appointments with comprehensive details including patient names, doctor profiles, and clinic information.
        
        This method provides complete context without requiring additional API calls.
        
        Args:
            doctor_id: Filter by doctor ID (optional)
            clinic_id: Filter by clinic ID (optional)
            patient_id: Filter by patient ID (optional)
            start_date: Start date filter (YYYY-MM-DD format, optional)
            end_date: End date filter (YYYY-MM-DD format, optional)
            page_no: Page number for pagination (starts from 0)
            
        Returns:
            Enriched appointments with patient names, doctor details, and clinic information
            
        Raises:
            EkaAPIError: If the API call fails
        """
        # Get basic appointments
        appointments_result = await self.client.get_appointments(
            doctor_id=doctor_id,
            clinic_id=clinic_id,
            patient_id=patient_id,
            start_date=start_date,
            end_date=end_date,
            page_no=page_no
        )
        
        # Enrich with additional details
        enriched_result = await self._enrich_appointments_data(appointments_result)
        
        return enriched_result
    
    async def get_appointments_basic(
        self,
        doctor_id: Optional[str] = None,
        clinic_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page_no: int = 0
    ) -> Dict[str, Any]:
        """
        Get basic appointments data (IDs only).
        
        Args:
            doctor_id: Filter by doctor ID (optional)
            clinic_id: Filter by clinic ID (optional)
            patient_id: Filter by patient ID (optional)
            start_date: Start date filter (YYYY-MM-DD format, optional)
            end_date: End date filter (YYYY-MM-DD format, optional)
            page_no: Page number for pagination (starts from 0)
            
        Returns:
            Basic appointments with entity IDs only
            
        Raises:
            EkaAPIError: If the API call fails
        """
        return await self.client.get_appointments(
            doctor_id=doctor_id,
            clinic_id=clinic_id,
            patient_id=patient_id,
            start_date=start_date,
            end_date=end_date,
            page_no=page_no
        )
    
    async def get_appointment_details_enriched(
        self,
        appointment_id: str,
        partner_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive appointment details with complete patient, doctor, and clinic information.
        
        This method provides complete context without requiring additional API calls.
        
        Args:
            appointment_id: Appointment's unique identifier
            partner_id: If set to 1, uses partner_appointment_id instead of eka appointment_id
            
        Returns:
            Complete appointment details with enriched patient, doctor, and clinic information
            
        Raises:
            EkaAPIError: If the API call fails
        """
        # Get basic appointment details
        appointment_result = await self.client.get_appointment_details(appointment_id, partner_id)
        
        # Enrich with additional details (treat as single-item list)
        enriched_result = await self._enrich_appointments_data({"appointments": [appointment_result]})
        
        # Return the single enriched appointment
        enriched_appointment = enriched_result.get("appointments", [{}])[0] if enriched_result.get("appointments") else appointment_result
        
        return enriched_appointment
    
    async def get_appointment_details_basic(
        self,
        appointment_id: str,
        partner_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get basic appointment details (IDs only).
        
        Args:
            appointment_id: Appointment's unique identifier
            partner_id: If set to 1, uses partner_appointment_id instead of eka appointment_id
            
        Returns:
            Basic appointment details with entity IDs only
            
        Raises:
            EkaAPIError: If the API call fails
        """
        return await self.client.get_appointment_details(appointment_id, partner_id)
    
    async def get_patient_appointments_enriched(
        self,
        patient_id: str,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get all appointments for a specific patient with enriched doctor and clinic details.
        
        This method provides complete context without requiring additional API calls.
        
        Args:
            patient_id: Patient's unique identifier
            limit: Maximum number of appointments to return
            
        Returns:
            List of enriched appointments for the patient with doctor and clinic information
            
        Raises:
            EkaAPIError: If the API call fails
        """
        # Get basic appointments
        appointments_result = await self.client.get_patient_appointments(patient_id, limit)
        
        # Enrich with additional details
        enriched_result = await self._enrich_appointments_data(appointments_result)
        
        return enriched_result
    
    async def get_patient_appointments_basic(
        self,
        patient_id: str,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get basic appointments for a specific patient (IDs only).
        
        Args:
            patient_id: Patient's unique identifier
            limit: Maximum number of appointments to return
            
        Returns:
            Basic appointments with entity IDs only
            
        Raises:
            EkaAPIError: If the API call fails
        """
        return await self.client.get_patient_appointments(patient_id, limit)
    
    async def update_appointment(
        self,
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
            
        Raises:
            EkaAPIError: If the API call fails
        """
        return await self.client.update_appointment(appointment_id, update_data, partner_id)
    
    async def complete_appointment(
        self,
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
            
        Raises:
            EkaAPIError: If the API call fails
        """
        return await self.client.complete_appointment(appointment_id, completion_data)
    
    async def cancel_appointment(
        self,
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
            
        Raises:
            EkaAPIError: If the API call fails
        """
        return await self.client.cancel_appointment(appointment_id, cancel_data)
    
    async def reschedule_appointment(
        self,
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
            
        Raises:
            EkaAPIError: If the API call fails
        """
        return await self.client.reschedule_appointment(appointment_id, reschedule_data)
    
    async def _enrich_appointments_data(self, appointments_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Unified function to enrich appointment data with patient, doctor, and clinic details.
        Works with both single appointments and lists of appointments.
        
        Args:
            appointments_data: Raw appointments data from API
            
        Returns:
            Enriched appointments data with additional context
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
                
                # Enrich with clinic details
                clinic_id = appointment.get("clinic_id")
                if clinic_id:
                    clinic_info = await get_cached_data(
                        self.client.get_clinic_details, clinic_id, clinics_cache
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