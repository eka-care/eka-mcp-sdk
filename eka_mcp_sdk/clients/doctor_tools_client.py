from typing import Dict, Any, Optional, List
import logging

from .base import BaseEkaClient

logger = logging.getLogger(__name__)


class DoctorToolsClient(BaseEkaClient):
    """Client for Doctor Tool Integration APIs based on official OpenAPI spec."""
    
    def get_api_module_name(self) -> str:
        return "Doctor Tools"
    
    # Patient Management APIs
    async def add_patient(
        self,
        patient_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a patient profile."""
        return await self._make_request(
            method="POST",
            endpoint="/profiles/v1/patient/",
            data=patient_data
        )
    
    async def get_patient_details(
        self,
        patient_id: str
    ) -> Dict[str, Any]:
        """Retrieve patient profile."""
        return await self._make_request(
            method="GET",
            endpoint=f"/profiles/v1/patient/{patient_id}"
        )
    
    async def search_patients(
        self,
        prefix: str,
        limit: Optional[int] = None,
        select: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search patient profiles by username, mobile, or full name (prefix match)."""
        params = {"prefix": prefix}
        if limit:
            params["limit"] = limit
        if select:
            params["select"] = select
            
        return await self._make_request(
            method="GET",
            endpoint="/profiles/v1/patient/search",
            params=params
        )
    
    async def list_patients(
        self,
        page_no: int,
        page_size: Optional[int] = None,
        select: Optional[str] = None,
        from_timestamp: Optional[int] = None,
        include_archived: bool = False
    ) -> Dict[str, Any]:
        """List patient profiles with pagination."""
        params = {"pageNo": page_no}
        if page_size:
            params["pageSize"] = page_size
        if select:
            params["select"] = select
        if from_timestamp:
            params["from"] = from_timestamp
        if include_archived:
            params["arc"] = True
            
        return await self._make_request(
            method="GET",
            endpoint="/profiles/v1/patient/minified/",
            params=params
        )
    
    async def update_patient(
        self,
        patient_id: str,
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update patient profile details."""
        return await self._make_request(
            method="PATCH",
            endpoint=f"/profiles/v1/patient/{patient_id}",
            data=update_data
        )
    
    async def archive_patient(
        self,
        patient_id: str,
        archive: bool = True
    ) -> Dict[str, Any]:
        """Archive patient profile."""
        params = {}
        if archive:
            params["arc"] = True
            
        return await self._make_request(
            method="DELETE",
            endpoint=f"/profiles/v1/patient/{patient_id}",
            params=params if params else None
        )
    
    async def get_patient_by_mobile(
        self,
        mobile: str,
        full_profile: bool = False
    ) -> Dict[str, Any]:
        """Retrieve patient profiles by mobile number."""
        params = {"mob": mobile}
        if full_profile:
            params["full_profile"] = True
            
        return await self._make_request(
            method="GET",
            endpoint="/profiles/v1/patient/by-mobile/",
            params=params
        )
    
    # Doctor and Clinic APIs
    async def get_business_entities(self) -> Dict[str, Any]:
        """Get Clinic and Doctor details for the business."""
        return await self._make_request(
            method="GET",
            endpoint="/dr/v1/business/entities"
        )
    
    async def get_clinic_details(
        self,
        clinic_id: str
    ) -> Dict[str, Any]:
        """Get Clinic details."""
        return await self._make_request(
            method="GET",
            endpoint=f"/dr/v1/business/clinic/{clinic_id}"
        )
    
    async def get_doctor_profile(
        self,
        doctor_id: str
    ) -> Dict[str, Any]:
        """Get Doctor profile."""
        return await self._make_request(
            method="GET",
            endpoint=f"/dr/v1/doctor/{doctor_id}"
        )
    
    async def get_doctor_services(
        self,
        doctor_id: str
    ) -> Dict[str, Any]:
        """Get Doctor services."""
        return await self._make_request(
            method="GET",
            endpoint=f"/dr/v1/doctor/service/{doctor_id}"
        )
    
    # Appointment Slot APIs
    async def get_appointment_slots(
        self,
        doctor_id: str,
        clinic_id: str,
        date: str
    ) -> Dict[str, Any]:
        """Get Appointment Slots for a doctor at a clinic on a specific date."""
        return await self._make_request(
            method="GET",
            endpoint=f"/dr/v1/doctor/{doctor_id}/clinic/{clinic_id}/appointment/slot",
            params={"date": date}
        )
    
    # Appointment Management APIs
    async def book_appointment(
        self,
        appointment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Book Appointment Slot."""
        return await self._make_request(
            method="POST",
            endpoint="/dr/v1/appointment",
            data=appointment_data
        )
    
    async def get_appointments(
        self,
        doctor_id: Optional[str] = None,
        clinic_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page_no: int = 0
    ) -> Dict[str, Any]:
        """Get Appointments with flexible filters."""
        params = {"page_no": page_no}
        if doctor_id:
            params["doctor_id"] = doctor_id
        if clinic_id:
            params["clinic_id"] = clinic_id
        if patient_id:
            params["patient_id"] = patient_id
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
            
        return await self._make_request(
            method="GET",
            endpoint="/dr/v1/appointment",
            params=params
        )
    
    async def get_appointment_details(
        self,
        appointment_id: str,
        partner_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get Appointment Details by appointment ID."""
        params = {}
        if partner_id:
            params["partner_id"] = partner_id
            
        return await self._make_request(
            method="GET",
            endpoint=f"/dr/v1/appointment/{appointment_id}",
            params=params if params else None
        )
    
    async def update_appointment(
        self,
        appointment_id: str,
        update_data: Dict[str, Any],
        partner_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update Appointment."""
        params = {}
        if partner_id:
            params["partner_id"] = partner_id
            
        return await self._make_request(
            method="PATCH",
            endpoint=f"/dr/v1/appointment/{appointment_id}",
            data=update_data,
            params=params if params else None
        )
    
    async def complete_appointment(
        self,
        appointment_id: str,
        completion_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Complete Appointment."""
        return await self._make_request(
            method="POST",
            endpoint=f"/dr/v1/appointment/{appointment_id}/complete",
            data=completion_data
        )
    
    async def cancel_appointment(
        self,
        appointment_id: str,
        cancel_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Cancel Appointment."""
        return await self._make_request(
            method="PUT",
            endpoint=f"/dr/v1/appointment/{appointment_id}/cancel",
            data=cancel_data
        )
    
    async def reschedule_appointment(
        self,
        appointment_id: str,
        reschedule_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Reschedule Appointment."""
        return await self._make_request(
            method="PUT",
            endpoint=f"/dr/v1/appointment/{appointment_id}/reschedule",
            data=reschedule_data
        )
    
    async def park_appointment(
        self,
        appointment_id: str,
        park_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Park Appointment."""
        return await self._make_request(
            method="POST",
            endpoint=f"/dr/v1/appointment/{appointment_id}/parked",
            data=park_data
        )
    
    async def update_appointment_custom_attribute(
        self,
        appointment_id: str,
        custom_attributes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update Appointment Custom Attribute."""
        return await self._make_request(
            method="PATCH",
            endpoint=f"/dr/v1/appointment/{appointment_id}/custom_attribute",
            data=custom_attributes
        )
    
    async def get_patient_appointments(
        self,
        patient_id: str,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get all appointments for a patient profile."""
        params = {}
        if limit:
            params["limit"] = limit
            
        return await self._make_request(
            method="GET",
            endpoint=f"/dr/v1/appointment/patient/{patient_id}",
            params=params if params else None
        )
    
    # Prescription APIs
    async def get_prescription_details(
        self,
        prescription_id: str
    ) -> Dict[str, Any]:
        """Get Prescription details."""
        return await self._make_request(
            method="GET",
            endpoint=f"/dr/v1/prescription/{prescription_id}"
        )