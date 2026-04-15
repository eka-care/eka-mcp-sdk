from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta, timezone
import copy
import logging
import random
import time
import os
import asyncio

import httpx

from .base_emr_client import BaseEMRClient
from ..utils.auth_schemas import (
    ASK_MOBILE_SCHEMA,
    ASK_OTP_SCHEMA,
    LIST_UHIDS_SCHEMA,
    UHID_SELECTED_SCHEMA,
    ERROR_ELICITATION_SCHEMA,
    MobileAuthStage,
    AuthStatus,
    SessionKey,
    UnauthenticatedError,
)
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
    build_plain_availability_response
)
from ..utils.book_appointment_utils import (
    extract_all_slots_from_schedule,
    check_slot_availability,
    create_unavailable_slot_response,
    validate_clinic_schedule,
    get_slot_end_time
)

logger = logging.getLogger(__name__)

_SESSION_TTL_SECONDS = 3600
_SESSION_STORE: Dict[str, Dict[str, Any]] = {}

_MESSENGER_BASE_URL = os.getenv(
    "EKA_MESSENGER_BASE_URL", "http://messenger.orbi.orbi/internal/v1/message"
)
_MESSENGER_TEMPLATE_ID = os.getenv("EKA_MESSENGER_OTP_TEMPLATE_ID", "otp_start##14")
_MESSENGER_HASHCODE = os.getenv("EKA_MESSENGER_HASHCODE", "##jfhjd")


class EkaEMRClient(BaseEMRClient):
    """Client for Doctor Tool Integration APIs based on official OpenAPI spec.
    Uses utils/eka_response_parsers.py for Eka-specific parsing logic."""
    
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
    ) -> Dict[str, Any]:
        """Archive patient profile."""
            
        return await self._make_request(
            method="DELETE",
            endpoint=f"/profiles/v1/patient/{patient_id}",
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
        doctor_id: str
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
        end_date: str
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
        date: str
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
        preferred_slot_time: Optional[str] = None,
        supports_elicitation: bool = True
    ) -> Dict[str, Any]:
        """
        Get doctor availability for appointment booking in UI contract format.
        
        Eka-specific orchestration:
        1. Fetch doctor profile
        2. Get business entities and find doctor's clinics
        3. Resolve clinic_id (validate or use first available)
        4. Fetch available dates and slots
        5. Build UI response with callbacks
        6. Determine if this is a confirmed slot or needs elicitation
        
        Returns:
            UI contract with doctor_card component, availability, callbacks, and:
            - slot_confirmed: True if preferred_date + preferred_slot_time are available
            - slot_confirmed: False if elicitation is needed (user must select)
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
        slot_confirmed = False
        if resolved_clinic_id:
            availability_list, selected_date = await self._fetch_doctor_availability(
                doctor_id, resolved_clinic_id, preferred_date, preferred_slot_time
            )
            if availability_list:
                doctor_entry["availability"] = availability_list
            if selected_date:
                doctor_entry["selected_date"] = selected_date
            
            # 6. Check if the specific preferred slot is available
            if preferred_date and preferred_slot_time:
                slot_confirmed = self._is_slot_available(
                    availability_list, preferred_date, preferred_slot_time
                )
        
        # 7. If slot is confirmed, return a simple confirmation response
        if slot_confirmed:
            return {
                "slot_confirmed": True,
                "doctor_id": doctor_id,
                "hospital_id": resolved_clinic_id,
                "date": preferred_date,
                "time": preferred_slot_time,
                "message": f"Slot available at {preferred_slot_time} on {preferred_date}",
                "doctor_name": doctor_profile.get("name", ""),
            }
        
        # 8. Build response based on client capability
        doctor_details = build_doctor_details_for_card(doctor_profile, doctor_clinics)
        if supports_elicitation:
            response = build_elicitation_response(doctor_id, doctor_entry, doctor_details)
        else:
            response = build_plain_availability_response(doctor_id, doctor_entry, doctor_details)
        response["slot_confirmed"] = False
        return response
    
    def _is_slot_available(
        self,
        availability_list: List[Dict[str, Any]],
        preferred_date: str,
        preferred_slot_time: str
    ) -> bool:
        """
        Check if the requested date and time slot is available.
        
        Args:
            availability_list: List of availability entries with date and slots
            preferred_date: The requested date in YYYY-MM-DD format
            preferred_slot_time: The requested time slot in HH:MM format
        
        Returns:
            True if the specific slot is available, False otherwise
        """
        for day_availability in availability_list:
            if day_availability.get("date") == preferred_date:
                slots = day_availability.get("slots", [])
                return preferred_slot_time in slots
        return False

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
        today_str = today.strftime("%Y-%m-%d")
        
        # Calculate start date
        if preferred_date:
            try:
                pref_date = datetime.strptime(preferred_date, "%Y-%m-%d").date()
                start_date = max(today, pref_date - timedelta(days=2))
            except ValueError:
                start_date = today
        else:
            start_date = today
        
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
                
                # Filter slots for today to have at least 15 min buffer from current time
                if date_str == today_str and slots:
                    slots = self._filter_slots_with_buffer(slots, buffer_minutes=15)
                
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
    
    def _filter_slots_with_buffer(self, slots: List[str], buffer_minutes: int = 15) -> List[str]:
        """
        Filter out slots that are within buffer_minutes from the current time.
        
        Args:
            slots: List of time slots in HH:MM format
            buffer_minutes: Minimum minutes from now for a slot to be valid (default: 15)
        
        Returns:
            Filtered list of slots that are at least buffer_minutes away
        """
        now = datetime.now()
        min_valid_time = now + timedelta(minutes=buffer_minutes)
        
        filtered_slots = []
        for slot in slots:
            try:
                # Parse slot time (HH:MM format)
                slot_time = datetime.strptime(slot, "%H:%M").replace(
                    year=now.year, month=now.month, day=now.day
                )
                if slot_time >= min_valid_time:
                    filtered_slots.append(slot)
            except ValueError:
                # If parsing fails, include the slot anyway
                filtered_slots.append(slot)
        
        return filtered_slots

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
        reason: Optional[str] = None
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
        reschedule_data_json: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Reschedule Appointment."""
        # return await self._make_request(
        #     method="PUT",
        #     endpoint=f"/dr/v1/appointment/{appointment_id}/reschedule",
        #     data=reschedule_data
        # )
        return {"error": "Not implemented", "message": "reschedule_appointment is not available for this workspace"}

    
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
    
    def _get_session_id(self) -> str:
        session_id = (self._custom_headers or {}).get("session-id")
        if not session_id:
            raise ValueError("Session ID not found. Please try again.")
        return session_id

    def _get_session_context(self) -> Tuple[str, Dict[str, Any]]:
        session_id = self._get_session_id()
        stored = _SESSION_STORE.get(session_id)
        if not stored:
            return session_id, {}

        expires_at = float(stored.get("expires_at") or 0)
        if expires_at and time.time() > expires_at:
            _SESSION_STORE.pop(session_id, None)
            return session_id, {}

        ctx = stored.get("data")
        return session_id, ctx if isinstance(ctx, dict) else {}

    def _set_session_context(self, session_context: Dict[str, Any]) -> None:
        session_id = self._get_session_id()
        _SESSION_STORE[session_id] = {
            "expires_at": time.time() + _SESSION_TTL_SECONDS,
            "data": session_context,
        }

    def _delete_session_context(self) -> None:
        session_id = self._get_session_id()
        _SESSION_STORE.pop(session_id, None)

    def _authenticate_request(self) -> None:
        _, session_context = self._get_session_context()
        if not session_context:
            raise UnauthenticatedError()
        if (session_context.get(SessionKey.MOBILE_AUTH_AUTHENTICATION) or "") != AuthStatus.AUTHENTICATED:
            raise UnauthenticatedError()

    async def authentication_elicitation(
        self,
        method: str,
        mobile_number: Optional[str] = None,
        country_code: Optional[str] = "+91",
        email_address: Optional[str] = None,
        meta: Optional[Dict[Any, Any]] = None,
    ) -> Dict[str, Any]:
        if method == "email":
            schema = copy.deepcopy(ERROR_ELICITATION_SCHEMA)
            schema["_meta"]["disp_toast_msg"] = "Email authentication is not supported for this workspace."
            schema["_meta"]["disp_message"] = "Email authentication is not supported for this workspace."
            return schema
        return await self._handle_mobile_auth_flow(mobile_number, country_code, meta)

    async def _handle_mobile_auth_flow(
        self,
        mobile_number: Optional[str] = None,
        country_code: Optional[str] = "+91",
        meta: Optional[Dict[Any, Any]] = None,
    ) -> Dict[str, Any]:
        if mobile_number:
            if len(mobile_number) not in (10, 13):
                ask_mobile_schema = copy.deepcopy(ASK_MOBILE_SCHEMA)
                ask_mobile_schema["_meta"]["disp_toast_msg"] = (
                    "Invalid mobile number. Please try again with valid mobile number."
                )
                return ask_mobile_schema
            mobile_number = mobile_number[-10:]

        if not country_code:
            country_code = "+91"
        if not str(country_code).startswith("+"):
            country_code = f"+{country_code}"

        meta = dict(meta) if meta else {}

        if meta.get("is_resend"):
            toast = "OTP resent successfully, please enter the OTP"
            return await self._send_otp(mobile_number, country_code, {}, toast=toast)

        _, session_context = self._get_session_context()

        if session_context:
            stage = session_context.get(SessionKey.MOBILE_AUTH_STAGE) or ""

            if stage == MobileAuthStage.MOBILE_UHID_SELECTED:
                return await self._return_uhid_selected(session_context)

            if stage == MobileAuthStage.MOBILE_UHIDS_LISTED:
                selected = meta.get("value")
                allowed = session_context.get(SessionKey.MOBILE_AUTH_UHIDS_LIST) or []
                if selected and isinstance(allowed, list):
                    if selected in allowed:
                        return await self._select_and_return_uhid(session_context, selected)
                    invalid_toast = "Invalid profile selection. Please try again."
                    return await self._list_uhids(session_context, toast=invalid_toast)
                return await self._list_uhids(session_context)

            if stage == MobileAuthStage.MOBILE_OTP_SENT:
                user_otp = meta.get("otp")
                prev_mobile = session_context.get(SessionKey.MOBILE_NUMBER)
                prev_country_code = session_context.get(SessionKey.COUNTRY_CODE)
                if user_otp:
                    return await self._verify_otp_and_list_uhids(session_context, str(user_otp))
                if prev_mobile:
                    return await self._send_otp(
                        mobile_number or prev_mobile,
                        country_code or prev_country_code or "+91",
                        session_context,
                    )
                return copy.deepcopy(ASK_MOBILE_SCHEMA)

            if stage == MobileAuthStage.MOBILE_OTP_SENT_RETRY:
                prev_mobile = session_context.get(SessionKey.MOBILE_NUMBER)
                prev_country_code = session_context.get(SessionKey.COUNTRY_CODE)
                toast = (
                    "Too many incorrect OTP attempts. Sent a new OTP, please check and enter the OTP."
                )
                if mobile_number:
                    return await self._send_otp(mobile_number, country_code, session_context, toast=toast)
                if prev_mobile:
                    return await self._send_otp(prev_mobile, prev_country_code or country_code or "+91", session_context, toast=toast)
                return copy.deepcopy(ASK_MOBILE_SCHEMA)

        if mobile_number:
            return await self._send_otp(mobile_number, country_code, session_context)
        return copy.deepcopy(ASK_MOBILE_SCHEMA)

    async def _send_otp(
        self,
        mobile_number: Optional[str],
        country_code: Optional[str],
        session_context: Dict[str, Any],
        toast: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not mobile_number:
            return copy.deepcopy(ASK_MOBILE_SCHEMA)

        try:
            otp = str(random.randint(100000, 999999))
            # to_sms = self._normalize_sms_to(mobile_number, country_code or "+91")
            to_sms = mobile_number
            resp = await self._send_otp_sms_via_messenger(to_sms=to_sms, otp=otp)
            if resp.get("status") == "failure":
                raise Exception(resp.get("message"))

        except Exception as e:
            logger.error("Failed to send OTP: %s", e)
            error_schema = copy.deepcopy(ERROR_ELICITATION_SCHEMA)
            error_schema["_meta"]["disp_toast_msg"] = "Something went wrong. Failed to send OTP."
            return error_schema

        session_context[SessionKey.MOBILE_AUTH_STAGE] = MobileAuthStage.MOBILE_OTP_SENT
        session_context[SessionKey.MOBILE_NUMBER] = mobile_number
        session_context[SessionKey.COUNTRY_CODE] = country_code or "+91"
        session_context[SessionKey.MOBILE_AUTH_OTP_VALUE] = otp
        self._set_session_context(session_context)

        ask_otp_schema = copy.deepcopy(ASK_OTP_SCHEMA)
        if toast:
            ask_otp_schema["_meta"]["disp_toast_msg"] = toast
        return ask_otp_schema

    async def _increase_otp_retries(self) -> None:
        _, session_context = self._get_session_context()
        retries = int(session_context.get(SessionKey.MOBILE_AUTH_OTP_RETRIES) or 0) + 1
        if retries >= 3:
            session_context[SessionKey.MOBILE_AUTH_OTP_RETRIES] = 0
            session_context[SessionKey.MOBILE_AUTH_STAGE] = MobileAuthStage.MOBILE_OTP_SENT_RETRY
        else:
            session_context[SessionKey.MOBILE_AUTH_OTP_RETRIES] = retries
        self._set_session_context(session_context)

    async def _verify_otp_and_list_uhids(
        self,
        session_context: Dict[str, Any],
        user_otp: str,
    ) -> Dict[str, Any]:
        stored_otp = session_context.get(SessionKey.MOBILE_AUTH_OTP_VALUE)
        if stored_otp and str(user_otp).strip() == str(stored_otp).strip():
            session_context[SessionKey.MOBILE_AUTH_STAGE] = MobileAuthStage.MOBILE_OTP_VERIFIED
            session_context[SessionKey.MOBILE_AUTH_AUTHENTICATION] = AuthStatus.AUTHENTICATED
            session_context.pop(SessionKey.MOBILE_AUTH_OTP_VALUE, None)
            self._set_session_context(session_context)
            return await self._list_uhids(session_context, toast="OTP verified successfully.")

        await self._increase_otp_retries()
        otp_retry_schema = copy.deepcopy(ASK_OTP_SCHEMA)
        otp_retry_schema["_meta"]["disp_toast_msg"] = "Incorrect OTP. Please try again."
        otp_retry_schema["input"] = {
            "mobile_number": session_context.get(SessionKey.MOBILE_NUMBER),
            "country_code": session_context.get(SessionKey.COUNTRY_CODE),
        }
        return otp_retry_schema

    # def _normalize_sms_to(self, mobile_number: str, country_code: str) -> str:
    #     digits = "".join(ch for ch in str(mobile_number) if ch.isdigit())
    #     cc_digits = "".join(ch for ch in str(country_code) if ch.isdigit())
    #     if len(digits) == 10:
    #         return (cc_digits or "91") + digits
    #     if len(digits) == 12 and (digits.startswith("91") or (cc_digits and digits.startswith(cc_digits))):
    #         return digits
    #     if len(digits) > 10:
    #         return (cc_digits or "91") + digits[-10:]
    #     return digits

    async def _send_otp_sms_via_messenger(self, to_sms: str, otp: str) -> Dict[str, Any]:
        payload = {
            "channels": ["sms"],
            "client_id": "auth",
            "components": [
                {"type": "body", "parameters": [{"type": "text", "text": otp}]},
                {
                    "type": "button",
                    "sub_type": "url",
                    "parameters": [{"type": "text", "text": otp}],
                },
            ],
            "language": "en",
            "params": {"hashcode": _MESSENGER_HASHCODE, "otp": otp},
            "template_id": _MESSENGER_TEMPLATE_ID,
            "to": {"sms": to_sms},
            "vendor": "eka",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            enqueue_resp = await client.post(
                _MESSENGER_BASE_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            enqueue_resp.raise_for_status()

            enqueue_json: Dict[str, Any] = {}
            try:
                enqueue_json = enqueue_resp.json()
            except Exception:
                enqueue_json = {
                    "status": "queued",
                    "status_code": enqueue_resp.status_code,
                    "raw_response": enqueue_resp.text,
                }

            message_id = enqueue_json.get("id")
            if not message_id:
                return {
                    "status": "failure",
                    "status_code": 400,
                    "message": "Failed to send OTP. Please try again later.",
                }

            return await self._poll_messenger_message_status(
                client=client, message_id=str(message_id)
            )

    async def _poll_messenger_message_status(
        self,
        client: httpx.AsyncClient,
        message_id: str,
        timeout_seconds: float = 10.0,
        initial_backoff_seconds: float = 1.0,
    ) -> List[Dict[str, Any]]:
        deadline = time.time() + timeout_seconds
        backoff = initial_backoff_seconds

        while time.time() < deadline:
            resp = await client.get(
                _MESSENGER_BASE_URL,
                params={"id": message_id},
            )
            try:
                payload = resp.json()
            except Exception:
                payload = []

            items: List[Dict[str, Any]] = payload if isinstance(payload, list) else []

            if any((i.get("status") or "").lower() == "success" for i in items if isinstance(i, dict)):
                return {
                    "status": "success",
                    "status_code": 200,
                    "message": "OTP sent successfully.",
                }

            for i in items:
                if isinstance(i, dict):
                    if i.get("status") or "".lower() in ("failed", "failure", "error"):
                        if i.get("vendor") or "" == "user-channel-quota-exceeded":
                            message = str(i)
                        return {
                            "status": "failure",
                            "status_code": 400,
                            "message": message,
                        }

            sleep_for = min(backoff, max(0.0, deadline - time.time()))
            if sleep_for <= 0:
                break
            await asyncio.sleep(sleep_for)
            backoff *= 2

        return {
            "status": "failure",
            "status_code": 400,
            "message": f"Messenger delivery not confirmed in {timeout_seconds}s.",
        }

    def _build_profile_label(self, profile: Dict[str, Any]) -> str:
        fln = (profile.get("fln") or "").strip()
        if fln:
            base = fln
        else:
            parts = [profile.get("fn"), profile.get("mn"), profile.get("ln")]
            base = " ".join([p for p in parts if isinstance(p, str) and p.strip()]).strip()
        if not base:
            base = "Patient"

        username = (profile.get("username") or "").strip()
        if username:
            return f"{base} ({username})"
        return base

    def _extract_profile_value(self, profile: Dict[str, Any]) -> Optional[str]:
        oid = profile.get("oid")
        if isinstance(oid, str) and oid.strip():
            return oid.strip()
        uuid = profile.get("uuid") or profile.get("_custom_uuid")
        if isinstance(uuid, str) and uuid.strip():
            return uuid.strip()
        return None

    async def _list_uhids(
        self,
        session_context: Dict[str, Any],
        toast: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            mobile_number = session_context.get(SessionKey.MOBILE_NUMBER)
            country_code = session_context.get(SessionKey.COUNTRY_CODE) or "+91"
            raw = await self.get_patient_by_mobile(f"{country_code}{mobile_number}", full_profile=True)

            profiles: List[Dict[str, Any]] = []
            if isinstance(raw, list):
                profiles = [p for p in raw if isinstance(p, dict)]
            elif isinstance(raw, dict):
                data = raw.get("data") or raw.get("patients") or raw.get("profiles")
                if isinstance(data, list):
                    profiles = [p for p in data if isinstance(p, dict)]

            pills = []
            for p in profiles:
                value = self._extract_profile_value(p)
                if not value:
                    continue
                pills.append({"label": self._build_profile_label(p), "value": value})

            if not pills:
                success_schema = copy.deepcopy(UHID_SELECTED_SCHEMA)
                success_schema["session_context"] = {"mobile": mobile_number}
                success_schema["_meta"] = {
                    "disp_toast_msg": "OTP verified successfully.",
                    "disp_message": "OTP verified but no patient profile found, lets create a new patient profile.",
                    "tool_result": {
                        "result": f"User has authenticated themselves on mobile number {mobile_number}",
                        "mobile_number": mobile_number,
                    },
                }
                return success_schema

            list_schema = copy.deepcopy(LIST_UHIDS_SCHEMA)
            list_schema["input"]["options"] = pills
            list_schema["user_context"] = {"mobile": mobile_number}

            session_context[SessionKey.MOBILE_AUTH_STAGE] = MobileAuthStage.MOBILE_UHIDS_LISTED
            session_context[SessionKey.MOBILE_AUTH_UHIDS_LIST] = [p["value"] for p in pills]

            meta_out: Dict[str, Any] = {
                "tool_result": {
                    "result": f"User has authenticated themselves on mobile number {mobile_number}",
                    "mobile_number": mobile_number,
                }
            }
            if toast:
                meta_out["disp_toast_msg"] = toast
            list_schema["_meta"].update(meta_out)

            self._set_session_context(session_context)
            return list_schema
        except Exception as e:
            logger.error("Failed to list patient profiles: %s", e)
            error_schema = copy.deepcopy(ERROR_ELICITATION_SCHEMA)
            error_schema["_meta"]["disp_toast_msg"] = (
                "Something went wrong. Failed to list patient profiles."
            )
            return error_schema

    async def _return_uhid_selected(self, session_context: Dict[str, Any]) -> Dict[str, Any]:
        schema = copy.deepcopy(UHID_SELECTED_SCHEMA)
        selected = session_context.get(SessionKey.MOBILE_AUTH_SELECTED_UHID)
        mobile_number = session_context.get(SessionKey.MOBILE_NUMBER)
        country_code = session_context.get(SessionKey.COUNTRY_CODE) or "+91"
        mob_with_country_code = f"{country_code}{mobile_number}"
        if selected:
            schema["_meta"] = {
                "disp_toast_msg": f"Proceeding with user: {selected}",
                "disp_message": "Authenticated and profile selected successfully.",
                "tool_result": {
                    "result": (
                        f"User has authenticated themselves on mobile number {mob_with_country_code} "
                        f"and selected patient profile {selected}"
                    ),
                    "mobile_number": mob_with_country_code,
                    "country_code": country_code,
                    "patient_id": selected,
                },
            }
        schema["session_context"] = {"mobile": mobile_number, "country_code": country_code, "patient_id": selected}
        return schema

    async def _select_and_return_uhid(
        self,
        session_context: Dict[str, Any],
        selected_value: str,
    ) -> Dict[str, Any]:
        session_context[SessionKey.MOBILE_AUTH_SELECTED_UHID] = selected_value
        session_context[SessionKey.MOBILE_AUTH_STAGE] = MobileAuthStage.MOBILE_UHID_SELECTED
        self._set_session_context(session_context)
        return await self._return_uhid_selected(session_context)

    async def list_all_patient_profiles(self) -> Dict[str, Any]:
        """Not implemented for EkaEMRClient."""
        return {"error": "Not implemented", "message": "list_all_patient_profiles is not available for this workspace"}
    
    async def get_patient_vitals(self, patient_id: str) -> Dict[str, Any]:
        """Not implemented for EkaEMRClient."""
        return {"error": "Not implemented", "message": "get_patient_vitals is not available for this workspace"}
    
    def get_workspace_name(self) -> str:
        """Return workspace name for EkaEMRClient."""
        return "ekaemr"