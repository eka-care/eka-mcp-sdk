from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
import logging

from .base_emr_client import BaseEMRClient
from ..utils.eka_response_parsers import (
    parse_slots_to_common_format,
    parse_available_dates,
    parse_doctor_profile,
    parse_business_entities
)
from ..utils.doctor_discovery_utils import (
    find_doctor_clinics,
    resolve_hospital_id,
    build_doctor_details_for_card,
    build_elicitation_response
)
from ..utils.book_appointment_utils import (
    extract_all_slots_from_schedule,
    check_slot_availability,
    build_appointment_data,
    create_unavailable_slot_response,
    validate_clinic_schedule,
    get_slot_end_time
)

logger = logging.getLogger(__name__)


class EkaEMRClient(BaseEMRClient):
    """Client for Doctor Tool Integration APIs based on official OpenAPI spec.
    Uses utils/eka_response_parsers.py for Eka-specific parsing logic."""
    
    def get_api_module_name(self) -> str:
        return "Doctor Tools"
    
    # Patient Management APIs
    async def add_patient(
        self,
        patient_data: Dict[str, Any],
        auth_token: Optional[str] = None
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
    ) -> Dict[str, Any]:
        """Archive patient profile."""
            
        return await self._make_request(
            method="DELETE",
            endpoint=f"/profiles/v1/patient/{patient_id}",
        )
    
    async def get_patient_by_mobile(
        self,
        mobile: str,
        full_profile: bool = False,
        auth_token: Optional[str] = None
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
    async def get_business_entities_raw(self) -> Dict[str, Any]:
        """Get raw Clinic and Doctor details from API."""
        return await self._make_request(
            method="GET",
            endpoint="/dr/v1/business/entities"
        )
    
    async def get_business_entities(self) -> Dict[str, Any]:
        """
        Get business entities in common contract format.
        
        Returns:
            {
                "clinics": [{"clinic_id": "...", "name": "...", "doctors": [...]}],
                "doctors": [{"doctor_id": "...", "name": "..."}],
                "business": {"business_id": "...", "name": "..."}
            }
        """
        raw_response = await self.get_business_entities_raw()
        return parse_business_entities(raw_response)
    
    async def get_clinic_details(
        self,
        clinic_id: str
    ) -> Dict[str, Any]:
        """Get Clinic details."""
        return await self._make_request(
            method="GET",
            endpoint=f"/dr/v1/business/clinic/{clinic_id}"
        )
    
    async def get_doctor_profile_raw(
        self,
        doctor_id: str
    ) -> Dict[str, Any]:
        """Get raw Doctor profile from API."""
        return await self._make_request(
            method="GET",
            endpoint=f"/dr/v1/doctor/{doctor_id}"
        )
    
    async def get_doctor_profile(
        self,
        doctor_id: str,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get Doctor profile in common contract format.
        
        Returns:
            {
                "id": "do...",
                "name": "Dr. Mayank Garg",
                "specialty": "Acupuncture",
                "specialties": ["Acupuncture"],
                "profile_pic": "https://...",
                "languages": [],
                "clinics": [{"clinic_id": "...", "name": "...", "address": {...}}]
            }
        """
        raw_response = await self.get_doctor_profile_raw(doctor_id)
        return parse_doctor_profile(raw_response)
    
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
    async def get_appointment_slots_raw(
        self,
        doctor_id: str,
        clinic_id: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """Get raw Appointment Slots response from API."""
        return await self._make_request(
            method="GET",
            endpoint=f"/dr/v1/doctor/{doctor_id}/clinic/{clinic_id}/appointment/slot",
            params={"start_date": start_date, "end_date": end_date}
        )
    
    async def get_appointment_slots(
        self,
        doctor_id: str,
        clinic_id: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        Get Appointment Slots in common contract format.
        
        Returns:
            {
                "date": "YYYY-MM-DD",
                "doctor_id": "...",
                "clinic_id": "...",
                "all_slots": ["HH:MM", ...],
                "slot_config": {"interval_minutes": 15},
                "slot_categories": [{"category": "consultation", "slots": [...]}],
                "pricing": {"consultation_fee": 500, "currency": "INR"},
                "metadata": {}
            }
        """
        raw_response = await self.get_appointment_slots_raw(
            doctor_id, clinic_id, start_date, end_date
        )
        
        # Parse the date from start_date (format: "YYYY-MM-DDTHH:MM:SS.sssZ")
        date = start_date.split('T')[0] if 'T' in start_date else start_date
        
        return parse_slots_to_common_format(raw_response, clinic_id, date, doctor_id)
    
    async def get_available_dates(
        self,
        doctor_id: str,
        clinic_id: str,
        start_date: str,
        end_date: str,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get available appointment dates in common contract format.
        
        Returns:
            {
                "available_dates": ["YYYY-MM-DD", ...],
                "date_range": {"start": "...", "end": "..."}
            }
        """
        raw_response = await self.get_appointment_slots_raw(
            doctor_id, clinic_id, start_date, end_date
        )
        
        return parse_available_dates(raw_response, clinic_id, start_date, end_date)
    
    async def get_available_slots(
        self,
        doctor_id: str,
        clinic_id: str,
        date: str,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get available slots for a specific date in common contract format.
        
        Convenience method that wraps get_appointment_slots for single-day queries.
        
        Args:
            doctor_id: Doctor's unique identifier
            clinic_id: Clinic's unique identifier
            date: Date in YYYY-MM-DD format
        
        Returns:
            Common contract format with all_slots, pricing, etc.
        """
        # Convert simple date to ISO datetime range
        start_datetime = f"{date}T00:00:00.000Z"
        end_datetime = f"{date}T23:59:59.000Z"
        
        return await self.get_appointment_slots(
            doctor_id, clinic_id, start_datetime, end_datetime
        )
    
    async def doctor_availability_elicitation(
        self,
        doctor_id: str,
        clinic_id: Optional[str] = None,
        preferred_date: Optional[str] = None,
        preferred_slot_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get doctor availability for appointment booking in UI contract format.
        
        Eka-specific orchestration:
        1. Fetch doctor profile
        2. Get business entities and find doctor's clinics
        3. Resolve clinic_id (validate or use first available)
        4. Fetch available dates and slots
        5. Build UI response with callbacks
        
        Returns:
            UI contract with doctor_card component, availability, and callbacks
        """
        # 1. Fetch doctor profile
        doctor_profile = await self.get_doctor_profile(doctor_id)
        if not doctor_profile or not doctor_profile.get('id'):
            return {"error": f"Doctor with ID '{doctor_id}' not found"}
        
        # 2. Get doctor's clinics from business entities
        entities_response = await self.get_business_entities()
        clinics_list = entities_response.get('clinics', [])
        
        # Find clinics where this doctor works
        doctor_clinics = find_doctor_clinics(clinics_list, doctor_id)
        
        # 3. Resolve clinic_id
        resolved_clinic_id = resolve_hospital_id(doctor_clinics, clinic_id)
        
        # 4. Build doctor entry with preferences
        doctor_entry: Dict[str, Any] = {"doctor_id": doctor_id}
        if resolved_clinic_id:
            doctor_entry["hospital_id"] = resolved_clinic_id
        if preferred_date:
            doctor_entry["date_preference"] = preferred_date
        if preferred_slot_time:
            doctor_entry["slot_preference"] = preferred_slot_time
        
        # 5. Fetch availability if clinic is resolved
        if resolved_clinic_id:
            availability_list, selected_date = await self._fetch_doctor_availability(
                doctor_id, resolved_clinic_id, preferred_date, preferred_slot_time
            )
            if availability_list:
                doctor_entry["availability"] = availability_list
            if selected_date:
                doctor_entry["selected_date"] = selected_date
        
        # 6. Build and return response
        doctor_details = build_doctor_details_for_card(doctor_profile, doctor_clinics)
        return build_elicitation_response(doctor_id, doctor_entry, doctor_details)
    
    async def _fetch_doctor_availability(
        self,
        doctor_id: str,
        clinic_id: str,
        preferred_date: Optional[str] = None,
        preferred_slot_time: Optional[str] = None,
        days: int = 10
    ) -> tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Fetch doctor availability for a date range.
        Internal helper for doctor_availability_elicitation.
        
        Returns:
            tuple: (availability_list, selected_date)
        """
        today = datetime.now().date()
        
        # Calculate start date
        if preferred_date:
            try:
                pref_date = datetime.strptime(preferred_date, "%Y-%m-%d").date()
                start_date = max(today, pref_date - timedelta(days=2))
            except ValueError:
                start_date = today + timedelta(days=1)
        else:
            start_date = today + timedelta(days=1)
        
        try:
            # Fetch available dates for the range
            start_datetime = f"{start_date.strftime('%Y-%m-%d')}T00:00:00.000Z"
            end_date_calc = start_date + timedelta(days=days - 1)
            end_datetime = f"{end_date_calc.strftime('%Y-%m-%d')}T23:59:59.000Z"
            
            available_dates_result = await self.get_available_dates(
                doctor_id, clinic_id, start_datetime, end_datetime
            )
            
            available_dates = available_dates_result.get('available_dates', [])[:days]
            
            availability_list = []
            selected_date = None
            
            # For each available date, get the slots
            for date_str in available_dates:
                slots_result = await self.get_available_slots(doctor_id, clinic_id, date_str)
                slots = slots_result.get('all_slots', [])
                
                if slots:
                    day_availability: Dict[str, Any] = {"date": date_str, "slots": slots}
                    
                    # Mark selected slot if preference matches
                    if preferred_slot_time and date_str == preferred_date and preferred_slot_time in slots:
                        day_availability["selected_slot"] = preferred_slot_time
                    
                    availability_list.append(day_availability)
            
            # Determine selected date
            if preferred_date and preferred_date in available_dates:
                selected_date = preferred_date
            elif available_dates:
                selected_date = available_dates[0]
            
            return availability_list, selected_date
            
        except Exception as e:
            logger.warning(f"Failed to fetch availability: {e}")
            return [], None

    # Appointment Management APIs
    async def book_appointment(
        self,
        appointment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Book Appointment Slot (raw API call)."""
        return await self._make_request(
            method="POST",
            endpoint="/dr/v1/appointment",
            data=appointment_data
        )
    
    async def book_appointment_with_validation(
        self,
        patient_id: str,
        doctor_id: str,
        clinic_id: str,
        date: str,
        start_time: str,
        end_time: str,
        mode: str = "in_clinic",
        reason: Optional[str] = None,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Smart appointment booking with automatic availability checking and alternate slot suggestions.
        
        Eka-specific orchestration:
        1. Fetch appointment slots for the date
        2. Check if requested slot is available
        3. If available, book immediately
        4. If unavailable, return alternate slot suggestions
        
        Returns:
            - If slot available: {"success": True, "data": {...}, "booked_slot": {...}}
            - If slot unavailable: {"success": False, "slot_unavailable": True, "alternate_slots": [...]}
            - If error: {"success": False, "error": {...}}
        """
        # Step 1: Fetch appointment slots (raw for availability flags)
        start_datetime = f"{date}T00:00:00.000Z"
        end_datetime = f"{date}T23:59:59.000Z"
        
        slots_result = await self.get_appointment_slots_raw(
            doctor_id, clinic_id, start_datetime, end_datetime
        )
        
        # Step 2: Validate clinic schedule
        clinic_schedule = validate_clinic_schedule(slots_result, clinic_id)
        if not clinic_schedule:
            return {
                "success": False,
                "error": {
                    "message": "No appointment schedule available for this clinic",
                    "status_code": 404,
                    "error_code": "NO_SCHEDULE"
                }
            }
        
        # Step 3: Extract all slots and check availability
        all_slots = extract_all_slots_from_schedule(clinic_schedule)
        is_available, requested_slot, alternate_slots = check_slot_availability(
            all_slots, date, start_time, end_time
        )
        
        # Handle slot not found
        if requested_slot is None:
            return {
                "success": False,
                "error": {
                    "message": f"Time slot {start_time}-{end_time} not found in doctor's schedule",
                    "status_code": 404,
                    "error_code": "SLOT_NOT_FOUND"
                }
            }
        
        # Handle unavailable slot
        if not is_available:
            return create_unavailable_slot_response(date, start_time, end_time, alternate_slots)
        
        # Step 4: Slot is available, proceed with booking
        # Use actual slot end time from schedule (handles 15min, 30min, etc. slots)
        actual_end_time = get_slot_end_time(requested_slot) or end_time
        
        # Build appointment data using IST timestamps
        IST = timezone(timedelta(hours=5, minutes=30))
        date_time_start = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
        date_time_end = datetime.strptime(f"{date} {actual_end_time}", "%Y-%m-%d %H:%M")
        
        start_timestamp = int(date_time_start.replace(tzinfo=IST).timestamp())
        end_timestamp = int(date_time_end.replace(tzinfo=IST).timestamp())
        
        appointment_data = {
            "clinic_id": clinic_id,
            "doctor_id": doctor_id,
            "patient_id": patient_id,
            "appointment_details": {
                "start_time": start_timestamp,
                "end_time": end_timestamp,
                "mode": mode
            }
        }
        
        if reason:
            appointment_data["appointment_details"]["reason"] = reason
        
        result = await self.book_appointment(appointment_data)
        
        # Build successful response
        booked_slot_info = {
            "date": date,
            "start_time": start_time,
            "end_time": actual_end_time
        }
        
        return {
            "success": True,
            "data": result,
            "booked_slot": booked_slot_info
        }

    async def show_appointments(
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
        """Update Appointment using V2 API.
        
        Note: V2 API requires doctor_id, clinic_id, and patient_id in the request body.
        """
        params = {}
        if partner_id:
            params["partner_id"] = partner_id
            
        return await self._make_request(
            method="PATCH",
            endpoint=f"/dr/v2/appointment/{appointment_id}",
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
        limit: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get all appointments for a patient profile using the appointments endpoint.
        
        Note: If patient_id is provided, no other filters (dates, doctor_id, clinic_id) are allowed.
        """
        # Note: API constraint - patient_id cannot be combined with date filters
        params = {"patient_id": patient_id, "page_no": 0}
            
        # Get appointments using the standard endpoint
        result = await self._make_request(
            method="GET",
            endpoint="/dr/v1/appointment",
            params=params
        )
        
        # Filter by dates client-side if needed, and apply limit
        if isinstance(result, dict):
            appointments = result.get("appointments", [])
            
            # Apply date filtering client-side if dates provided
            if start_date or end_date:
                from datetime import datetime
                filtered = []
                for appt in appointments:
                    appt_time = appt.get("start_time", 0)
                    if start_date:
                        start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
                        if appt_time < start_ts:
                            continue
                    if end_date:
                        end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp()) + 86400  # end of day
                        if appt_time > end_ts:
                            continue
                    filtered.append(appt)
                appointments = filtered
            
            # Apply limit
            if limit and len(appointments) > limit:
                appointments = appointments[:limit]
            
            result["appointments"] = appointments
        
        return result
    
    # Assessment APIs
    async def fetch_grouped_assessments(
        self,
        practitioner_uuid: Optional[str] = None,
        patient_uuid: Optional[str] = None,
        unique_identifier: Optional[str] = None,
        transaction_id: Optional[str] = None,
        wfids: Optional[List[str]] = None,
        status: str = "COMPLETED"
    ) -> Dict[str, Any]:
        """Fetch grouped assessment conversations."""
        params = {}
        if practitioner_uuid:
            params["practitioner_uuid"] = practitioner_uuid
        if patient_uuid:
            params["patient_uuid"] = patient_uuid
        if unique_identifier:
            params["unique_identifier"] = unique_identifier
        if transaction_id:
            params["transaction_id"] = transaction_id
        if wfids:
            params["wfids"] = ",".join(wfids)
        if status:
            params["status"] = status
            
        return await self._make_request(
            method="GET",
            endpoint="/assessment/api/fetch_interviews/v2/",
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
    
    # Abstract method implementations (Not implemented for this client)
    async def doctor_discovery(self, *args, **kwargs) -> Dict[str, Any]:
        """Not implemented for EkaEMRClient."""
        return {"error": "Not implemented", "message": "doctor_discovery is not available for this workspace"}
    
    async def get_appointments(self, *args, **kwargs) -> Dict[str, Any]:
        """Not implemented for EkaEMRClient."""
        return {"error": "Not implemented", "message": "get_appointments is not available for this workspace"}
    
    def mobile_number_verification(self, *args, **kwargs) -> Dict[str, Any]:
        """Not implemented for EkaEMRClient."""
        return {"error": "Not implemented", "message": "mobile_number_verification is not available for this workspace"}
    
    def get_workspace_name(self) -> str:
        """Return workspace name for EkaEMRClient."""
        return "ekaemr"