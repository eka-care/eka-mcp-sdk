"""
Abstract Base EMR Client Interface.

All EMR client implementations (EkaEMR, Moolchand, etc.) must implement this interface.
This enables workspace-agnostic tool implementations via the factory pattern.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from .base_client import BaseEkaClient

class BaseEMRClient(BaseEkaClient):
    """Abstract interface for EMR client implementations.
    
    All EMR clients must implement these methods to be usable by 
    the factory pattern and workspace routing.
    """
    
    @abstractmethod
    def get_workspace_name(self) -> str:
        """Return the name of the workspace this client handles."""
        pass
    
    # ==================== Patient Operations ====================
    
    async def mobile_number_verification(
        self,
        mobile_number: str,
        otp: Optional[str] = None,
        stage: str = "send_otp"
    ) -> Dict[str, Any]:
        """
        Unified mobile number verification - handles both OTP send and verify stages.
        """
        pass
    
    @abstractmethod
    async def add_patient(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a patient profile."""
        pass
    
    @abstractmethod
    async def get_patient_details(self, patient_id: str) -> Dict[str, Any]:
        """Retrieve patient profile."""
        pass
    
    @abstractmethod
    async def search_patients(self, prefix: str, limit: Optional[int] = None, select: Optional[str] = None) -> Dict[str, Any]:
        """Search patient profiles by username, mobile, or full name."""
        pass
    
    @abstractmethod
    async def list_patients(self, page_no: int, page_size: Optional[int] = None, select: Optional[str] = None,
                           from_timestamp: Optional[int] = None, include_archived: bool = False) -> Dict[str, Any]:
        """List patient profiles with pagination."""
        pass
    
    @abstractmethod
    async def update_patient(self, patient_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update patient profile details."""
        pass
    
    @abstractmethod
    async def archive_patient(self, patient_id: str) -> Dict[str, Any]:
        """Archive patient profile."""
        pass
    
    @abstractmethod
    async def get_patient_by_mobile(self, mobile: str, full_profile: bool = False) -> Dict[str, Any]:
        """Retrieve patient profiles by mobile number."""
        pass
    
    # ==================== Doctor & Clinic Operations ====================
    
    @abstractmethod
    async def get_business_entities(self) -> Dict[str, Any]:
        """Get Clinic and Doctor details for the business."""
        pass
    
    @abstractmethod
    async def get_clinic_details(self, clinic_id: str) -> Dict[str, Any]:
        """Get Clinic details."""
        pass
    
    @abstractmethod
    async def get_doctor_profile(self, doctor_id: str) -> Dict[str, Any]:
        """Get Doctor profile."""
        pass
    
    @abstractmethod
    async def get_doctor_services(self, doctor_id: str) -> Dict[str, Any]:
        """Get Doctor services."""
        pass

    @abstractmethod
    async def doctor_discovery(
        self, doctor_name=None, specialty=None, city=None, gender=None
    ) -> List[Dict[str, Any]]:
        """
        Search for doctors using the local Tantivy index.
        """
        pass

    
    # ==================== Appointment Operations ====================
    
    @abstractmethod
    async def get_appointment_slots(self, doctor_id: str, clinic_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get Appointment Slots for a doctor at a clinic within a date range."""
        pass
    
    @abstractmethod
    async def get_available_slots(self,
        doctor_id: str,
        clinic_id: str,
        date: str
    ) -> Dict[str, Any]:
        """Get Appointment Slots for a specific date in common contract format."""
        pass

    @abstractmethod
    async def get_available_dates(
        self, doctor_id: str, clinic_id: str, start_date: str, end_date: str
    ) -> Dict[str, Any]:
        """Get available appointment dates in common contract format."""
        pass
    
    @abstractmethod
    async def doctor_availability_elicitation(
        self,
        doctor_id: str,
        clinic_id: Optional[str] = None,
        preferred_date: Optional[str] = None,
        preferred_slot_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get doctor availability for appointment booking in UI contract format.
        
        Returns doctor details, available dates, and slots with UI callbacks.
        """
        pass

    @abstractmethod
    async def book_appointment(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Book Appointment Slot (raw API call)."""
        pass
    
    @abstractmethod
    async def book_appointment_with_validation(
        self,
        patient_id: str,
        doctor_id: str,
        clinic_id: str,
        date: str,
        start_time: str,
        end_time: str,
        mode: str = "in_clinic",
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Book appointment with automatic availability checking and alternate slot suggestions.
        
        Returns:
            - If slot available: {"success": True, "data": {...}, "booked_slot": {...}}
            - If slot unavailable: {"success": False, "slot_unavailable": True, "alternate_slots": [...]}
        """
        pass
    
    @abstractmethod
    async def get_appointments(self, doctor_id: Optional[str] = None, clinic_id: Optional[str] = None,
                              patient_id: Optional[str] = None, start_date: Optional[str] = None,
                              end_date: Optional[str] = None, page_no: int = 0) -> Dict[str, Any]:
        """Get Appointments with flexible filters."""
        pass
    
    @abstractmethod
    async def get_appointment_details(self, appointment_id: str, partner_id: Optional[str] = None) -> Dict[str, Any]:
        """Get Appointment Details by appointment ID."""
        pass
    
    @abstractmethod
    async def update_appointment(self, appointment_id: str, update_data: Dict[str, Any], partner_id: Optional[str] = None) -> Dict[str, Any]:
        """Update Appointment."""
        pass
    
    @abstractmethod
    async def complete_appointment(self, appointment_id: str, completion_data: Dict[str, Any]) -> Dict[str, Any]:
        """Complete Appointment."""
        pass
    
    @abstractmethod
    async def cancel_appointment(self, appointment_id: str, cancel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cancel Appointment."""
        pass
    
    @abstractmethod
    async def reschedule_appointment(self, appointment_id: str, reschedule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Reschedule Appointment."""
        pass
    
    @abstractmethod
    async def get_patient_appointments(self, patient_id: str, limit: Optional[int] = None,
                                       start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Get all appointments for a patient profile."""
        pass
    
    # ==================== Prescription Operations ====================
    
    @abstractmethod
    async def get_prescription_details(self, prescription_id: str) -> Dict[str, Any]:
        """Get Prescription details."""
        pass
    

    # ==================== Lifecycle ====================
    
    async def close(self) -> None:
        """Close HTTP client connections."""
        await self._http_client.aclose()
