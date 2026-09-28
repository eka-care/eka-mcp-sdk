"""
Abstract Base EMR Client Interface.

All EMR client implementations (EkaEMR, Moolchand, etc.) must implement this interface.
This enables workspace-agnostic tool implementations via the factory pattern.
"""

from abc import abstractmethod
from typing import Any

from .base_client import BaseEkaClient


class BaseEMRClient(BaseEkaClient):
    """Abstract interface for EMR client implementations.

    All EMR clients must implement these methods to be usable by
    the factory pattern and workspace routing.
    """

    @abstractmethod
    def get_workspace_name(self) -> str:
        """Return the name of the workspace this client handles."""

    # ==================== Patient Operations ====================

    async def mobile_number_verification(
        self, mobile_number: str, otp: str | None = None, stage: str = "send_otp"
    ) -> dict[str, Any]:
        """
        Unified mobile number verification - handles both OTP send and verify stages.
        """

    async def authentication_elicitation(
        self,
        method: str,
        mobile_number: str | None = None,
        email_address: str | None = None,
        meta: dict[Any, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Unified mobile number verification - handles both OTP send and verify stages.
        """

    @abstractmethod
    async def add_patient(self, patient_data: dict[str, Any]) -> dict[str, Any]:
        """Create a patient profile."""

    @abstractmethod
    async def get_patient_details(self, patient_id: str) -> dict[str, Any]:
        """Retrieve patient profile."""

    @abstractmethod
    async def search_patients(
        self, prefix: str, limit: int | None = None, select: str | None = None
    ) -> dict[str, Any]:
        """Search patient profiles by username, mobile, or full name."""

    @abstractmethod
    async def list_patients(
        self,
        page_no: int,
        page_size: int | None = None,
        select: str | None = None,
        from_timestamp: int | None = None,
        include_archived: bool = False,
    ) -> dict[str, Any]:
        """List patient profiles with pagination."""

    @abstractmethod
    async def update_patient(
        self, patient_id: str, update_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update patient profile details."""

    @abstractmethod
    async def archive_patient(self, patient_id: str) -> dict[str, Any]:
        """Archive patient profile."""

    @abstractmethod
    async def get_patient_by_mobile(
        self, mobile: str, full_profile: bool = False
    ) -> dict[str, Any]:
        """Retrieve patient profiles by mobile number."""

    # ==================== Doctor & Clinic Operations ====================

    @abstractmethod
    async def get_business_entities(self) -> dict[str, Any]:
        """Get Clinic and Doctor details for the business."""

    @abstractmethod
    async def get_clinic_details(self, clinic_id: str) -> dict[str, Any]:
        """Get Clinic details."""

    @abstractmethod
    async def get_doctor_profile(self, doctor_id: str) -> dict[str, Any]:
        """Get Doctor profile."""

    @abstractmethod
    async def get_doctor_services(self, doctor_id: str) -> dict[str, Any]:
        """Get Doctor services."""

    # ==================== CRM Operations ====================

    @abstractmethod
    async def create_crm_lead(self, lead_data: dict[str, Any]) -> dict[str, Any]:
        """Create a CRM lead."""

    # ==================== Appointment Operations ====================

    @abstractmethod
    async def get_appointment_slots(
        self, doctor_id: str, clinic_id: str, start_date: str, end_date: str
    ) -> dict[str, Any]:
        """Get Appointment Slots for a doctor at a clinic within a date range."""

    @abstractmethod
    async def get_available_slots(
        self, doctor_id: str, clinic_id: str, date: str
    ) -> dict[str, Any]:
        """Get Appointment Slots for a specific date in common contract format."""

    @abstractmethod
    async def get_available_dates(
        self, doctor_id: str, clinic_id: str, start_date: str, end_date: str
    ) -> dict[str, Any]:
        """Get available appointment dates in common contract format."""

    @abstractmethod
    async def doctor_availability_elicitation(
        self,
        doctor_id: str,
        clinic_id: str | None = None,
        preferred_date: str | None = None,
        preferred_slot_time: str | None = None,
        supports_elicitation: bool = True,
        meta: dict[Any, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Get doctor availability for appointment booking in UI contract format.

        Returns doctor details, available dates, and slots with UI callbacks.
        If supports_elicitation is False, returns plain availability data
        without the doctor_card UI component.
        """

    @abstractmethod
    async def book_appointment(
        self, appointment_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Book Appointment Slot (raw API call)."""

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
        partner_patient_id: str | None = None,
        reason: str | None = None,
        patient_name: str | None = None,
        dob: str | None = None,
        gender: str | None = None,
        tag_ids: list[str] | None = None,
        session_id: str | None = None,
        token: int | None = None,
    ) -> dict[str, Any]:
        """
        Book appointment with automatic availability checking and alternate slot suggestions.

        Returns:
            - If slot available: {"success": True, "data": {...}, "booked_slot": {...}}
            - If slot unavailable: {"success": False, "slot_unavailable": True, "alternate_slots": [...]}
        """

    @abstractmethod
    async def get_appointments(
        self,
        doctor_id: str | None = None,
        clinic_id: str | None = None,
        patient_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        page_no: int = 0,
    ) -> dict[str, Any]:
        """Get Appointments with flexible filters."""

    @abstractmethod
    async def get_appointment_details(
        self, appointment_id: str, partner_id: str | None = None
    ) -> dict[str, Any]:
        """Get Appointment Details by appointment ID."""

    @abstractmethod
    async def update_appointment(
        self,
        appointment_id: str,
        update_data: dict[str, Any],
        partner_id: str | None = None,
    ) -> dict[str, Any]:
        """Update Appointment."""

    @abstractmethod
    async def complete_appointment(
        self, appointment_id: str, completion_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Complete Appointment."""

    @abstractmethod
    async def cancel_appointment(
        self, appointment_id: str, cancel_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Cancel Appointment."""

    @abstractmethod
    async def reschedule_appointment(
        self, appointment_id: str, reschedule_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Reschedule Appointment."""

    @abstractmethod
    async def get_patient_appointments(
        self,
        patient_id: str,
        limit: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Get all appointments for a patient profile."""

    # ==================== Prescription Operations ====================

    @abstractmethod
    async def get_prescription_details(self, prescription_id: str) -> dict[str, Any]:
        """Get Prescription details."""

    # ==================== Medical Records Operations ====================

    @abstractmethod
    async def list_medical_records(
        self,
        patient_id: str,
        updated_after: int | None = None,
        offset: str | None = None,
    ) -> dict[str, Any]:
        """List a patient's medical records (documents)."""

    @abstractmethod
    async def get_medical_record(
        self, patient_id: str, document_id: str
    ) -> dict[str, Any]:
        """Get a single medical record's metadata and download URL."""

    @abstractmethod
    async def delete_medical_record(
        self, patient_id: str, document_id: str
    ) -> dict[str, Any]:
        """Delete a patient's medical record (document)."""

    @abstractmethod
    async def initiate_medical_record_upload(
        self, patient_id: str, batch_request: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Register document metadata and obtain presigned upload URLs."""

    # ==================== Services Tools ====================
    @abstractmethod
    async def service_availability_elicitation(
        self,
        suggested_service_ids: list[str] | None = None,
        service_id: str | None = None,
        hospital_id: str | None = None,
        preferred_date: str | None = None,
        preferred_slot_time: str | None = None,
        supports_elicitation: bool = True,
        meta: dict[Any, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Get Service availability for booking in UI contract format.
        Returns service details, available dates, and slots with UI callbacks.
        If supports_elicitation is False, returns plain availability data
        without the doctor_card UI component.
        """

    @abstractmethod
    async def book_service(
        self, booking_data: dict[str, Any], meta: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Book an appointment for a health package.
        """

    # ==================== Lifecycle ====================

    async def close(self) -> None:
        """Close HTTP client connections."""
        await self._http_client.aclose()
