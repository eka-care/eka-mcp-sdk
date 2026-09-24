import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from eka_mcp_sdk import EkaAPIError

# Horus is an optional dependency (install with the "tele" extra); tele-consultation
# links are skipped when it is not installed.
try:
    from horus import AsyncHorusClient
except ImportError:
    AsyncHorusClient = None

from ..utils.book_appointment_utils import (
    build_100ms_meeting_url,
    check_slot_availability,
    create_unavailable_slot_response,
    extract_all_slots_from_schedule,
    get_slot_end_time,
    validate_clinic_schedule,
)
from ..utils.doctor_discovery_utils import (
    build_doctor_details,
    build_elicitation_response,
    build_elicitation_success_response,
    build_plain_availability_from_entries,
    build_plain_availability_response,
    find_doctor_clinics,
    resolve_hospital_id,
)
from ..utils.eka_response_parsers import (
    parse_available_dates,
    parse_business_entities,
    parse_doctor_profile,
    parse_slots_to_common_format,
)
from .base_emr_client import BaseEMRClient

logger = logging.getLogger(__name__)


class EkaEMRClient(BaseEMRClient):
    """Client for Doctor Tool Integration APIs based on official OpenAPI spec.
    Uses utils/eka_response_parsers.py for Eka-specific parsing logic."""

    def get_api_module_name(self) -> str:
        return "Doctor Tools"

    # Patient Management APIs
    async def add_patient(self, patient_data: dict[str, Any]) -> dict[str, Any]:
        """Create a patient profile."""
        return await self._make_request(
            method="POST", endpoint="/profiles/v1/patient/", data=patient_data
        )

    async def get_patient_details(self, patient_id: str) -> dict[str, Any]:
        """Retrieve patient profile."""
        return await self._make_request(
            method="GET", endpoint=f"/profiles/v1/patient/{patient_id}"
        )

    async def search_patients(
        self, prefix: str, limit: int | None = None, select: str | None = None
    ) -> dict[str, Any]:
        """Search patient profiles by username, mobile, or full name (prefix match)."""
        params = {"prefix": prefix}
        if limit:
            params["limit"] = limit
        if select:
            params["select"] = select

        return await self._make_request(
            method="GET", endpoint="/profiles/v1/patient/search", params=params
        )

    async def list_patients(
        self,
        page_no: int,
        page_size: int | None = None,
        select: str | None = None,
        from_timestamp: int | None = None,
        include_archived: bool = False,
    ) -> dict[str, Any]:
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
            method="GET", endpoint="/profiles/v1/patient/minified/", params=params
        )

    async def update_patient(
        self, patient_id: str, update_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update patient profile details."""
        return await self._make_request(
            method="PATCH",
            endpoint=f"/profiles/v1/patient/{patient_id}",
            data=update_data,
        )

    async def archive_patient(
        self,
        patient_id: str,
    ) -> dict[str, Any]:
        """Archive patient profile."""

        return await self._make_request(
            method="DELETE",
            endpoint=f"/profiles/v1/patient/{patient_id}",
        )

    async def get_patient_by_mobile(
        self, mobile: str, full_profile: bool = False
    ) -> dict[str, Any]:
        """Retrieve patient profiles by mobile number."""
        params = {"mob": mobile}
        if full_profile:
            params["full_profile"] = True

        return await self._make_request(
            method="GET", endpoint="/profiles/v1/patient/by-mobile/", params=params
        )

    # Doctor and Clinic APIs
    async def get_business_entities_raw(self) -> dict[str, Any]:
        """Get raw Clinic and Doctor details from API."""
        return await self._make_request(
            method="GET", endpoint="/dr/v1/business/entities"
        )

    async def get_business_entities(self) -> dict[str, Any]:
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

    async def get_clinic_details(self, clinic_id: str) -> dict[str, Any]:
        """Get Clinic details."""
        return await self._make_request(
            method="GET", endpoint=f"/dr/v1/business/clinic/{clinic_id}"
        )

    async def get_doctor_profile_raw(self, doctor_id: str) -> dict[str, Any]:
        """Get raw Doctor profile from API."""
        return await self._make_request(
            method="GET", endpoint=f"/dr/v1/doctor/{doctor_id}"
        )

    async def get_doctor_profile(self, doctor_id: str) -> dict[str, Any]:
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

    async def get_doctor_services(self, doctor_id: str) -> dict[str, Any]:
        """Get Doctor services."""
        return await self._make_request(
            method="GET", endpoint=f"/dr/v1/doctor/service/{doctor_id}"
        )

    async def create_crm_lead(self, lead_data: dict[str, Any]) -> dict[str, Any]:
        """Create a CRM lead."""
        return {
            "error": "Not implemented",
            "message": "CRM lead creation is not available for this workspace",
        }

    # Appointment Slot APIs
    async def get_appointment_slots_raw(
        self, doctor_id: str, clinic_id: str, start_date: str, end_date: str
    ) -> dict[str, Any]:
        """Get raw Appointment Slots response from API."""
        return await self._make_request(
            method="GET",
            endpoint=f"/dr/v1/doctor/{doctor_id}/clinic/{clinic_id}/appointment/slot",
            params={"start_date": start_date, "end_date": end_date},
        )

    async def get_appointment_slots(
        self, doctor_id: str, clinic_id: str, start_date: str, end_date: str
    ) -> dict[str, Any]:
        """
        Get Appointment Slots in common contract format.

        Returns:
            {
                "date": "YYYY-MM-DD",  # requested start date
                "doctor_id": "...",
                "clinic_id": "...",
                "dates": [
                    {
                        "date": "YYYY-MM-DD",
                        "all_slots": ["HH:MM", ...],
                        "slot_categories": [{"category": "consultation", "slots": [...]}]
                    }
                ],
                "slot_config": {"interval_minutes": 15},
                "pricing": {"consultation_fee": 500, "currency": "INR"},
                "metadata": {}
            }
        """
        raw_response = await self.get_appointment_slots_raw(
            doctor_id, clinic_id, start_date, end_date
        )

        # Parse the date from start_date (format: "YYYY-MM-DDTHH:MM:SS.sssZ")
        date = start_date.split("T")[0] if "T" in start_date else start_date

        return parse_slots_to_common_format(raw_response, clinic_id, date, doctor_id)

    async def get_available_dates(
        self, doctor_id: str, clinic_id: str, start_date: str, end_date: str
    ) -> dict[str, Any]:
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
        self, doctor_id: str, clinic_id: str, date: str
    ) -> dict[str, Any]:
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
        suggested_doctor_ids: list[str] | None = None,
        doctor_id: str | None = None,
        hospital_id: str | None = None,
        preferred_date: str | None = None,
        preferred_slot_time: str | None = None,
        supports_elicitation: bool = True,
        meta: dict[Any, Any] | None = None,
    ) -> dict[str, Any]:
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
        try:
            if not suggested_doctor_ids and not doctor_id:
                raise EkaAPIError(
                    "Invalid request: either suggested_doctor_ids or doctor_id is required"
                )
            if meta:
                meta = dict(meta)
            else:
                meta = {}

            doctor_entries = []
            doctor_details = dict()
            is_doctor_selected = False
            # is_date_slot_available = False

            if doctor_id:  # single doctor is selected -> old flow
                is_doctor_selected = True
                selected_date = preferred_date
                selected_slot = preferred_slot_time
                # Fetch doctor profile
                doctor_profile = await self.get_doctor_profile(doctor_id)
                if not doctor_profile or not doctor_profile.get("id"):
                    return {"error": f"Doctor with ID '{doctor_id}' not found"}

                entities_response = await self.get_business_entities()
                all_clinics_list = entities_response.get("clinics", [])

                doctor_clinics = find_doctor_clinics(all_clinics_list, doctor_id)
                selected_doctor_details = build_doctor_details(
                    doctor_profile, doctor_clinics, hospital_id
                )

                resolved_clinic_id = (
                    resolve_hospital_id(doctor_clinics, hospital_id) or hospital_id
                )

                doctor_entry = {
                    "doctor_id": doctor_id,
                    "hospital_id": resolved_clinic_id,
                    "preferred_date": selected_date,
                    "availability": [],
                }

                (
                    availability_list,
                    new_preferred_date,
                ) = await self._fetch_doctor_availability(
                    doctor_id, resolved_clinic_id, preferred_date, preferred_slot_time
                )
                if availability_list:
                    doctor_entry["availability"] = availability_list
                    # is_date_slot_available = True
                if new_preferred_date:
                    doctor_entry["preferred_date"] = new_preferred_date

                # User has already selected a slot
                if selected_date and selected_slot:
                    slot_confirmed = self._is_slot_available(
                        availability_list, selected_date, selected_slot
                    )
                    # if the slot user has selected is available, return success response, else continue with elicitation
                    if slot_confirmed:
                        return build_elicitation_success_response(
                            doctor_id,
                            selected_doctor_details,
                            selected_date,
                            selected_slot,
                            resolved_clinic_id,
                        )

                doctor_entries.append(doctor_entry)
                doctor_details[doctor_id] = selected_doctor_details

            elif suggested_doctor_ids:  # doctor not selected but multiple suggestions
                for suggested_doctor_id in suggested_doctor_ids:
                    try:
                        suggested_doctor_profile = await self.get_doctor_profile(
                            suggested_doctor_id
                        )
                        entities_response = await self.get_business_entities()
                        all_clinics_list = entities_response.get("clinics", [])

                        doctor_clinics = find_doctor_clinics(
                            all_clinics_list, suggested_doctor_id
                        )
                        suggested_doctor_details = build_doctor_details(
                            suggested_doctor_profile, doctor_clinics
                        )

                        doctor_entry = {
                            "doctor_id": suggested_doctor_id,
                            "availability": [],
                        }
                        doctor_entries.append(doctor_entry)
                        doctor_details[suggested_doctor_id] = suggested_doctor_details
                    except Exception as e:
                        logger.warning(
                            f"Could not fetch availability for doctor {suggested_doctor_id}: {e!s}"
                        )
                        continue

            else:  # neither doctor_id nor suggested_doctor_ids are provided -> unexpected behaviour
                raise EkaAPIError(
                    "Invalid request: either suggested_doctor_ids or doctor_id is required"
                )

            # Build response based on client capability
            if supports_elicitation:
                response = build_elicitation_response(
                    doctor_entries,
                    doctor_details,
                    is_doctor_selected,
                    doctor_id,
                    hospital_id,
                )
            else:
                response = build_plain_availability_from_entries(
                    doctor_entries,
                    doctor_details,
                    doctor_id,
                    preferred_date,
                    preferred_slot_time,
                )
            return response

        except Exception as e:
            if supports_elicitation:
                # structured error component for elicitation
                resp = {
                    "status": "failure",
                    "is_elicitation": True,
                    "component": "error",
                    "input": {},
                    "_meta": {
                        "disp_message": "Something went wrong, please try again.",
                    },
                }
                return resp
            else:
                raise ValueError(f"Failed to fetch availability: {e}")

    def _is_slot_available(
        self,
        availability_list: list[dict[str, Any]],
        preferred_date: str,
        preferred_slot_time: str,
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
        preferred_date: str | None = None,
        preferred_slot_time: str | None = None,
        days: int = 10,
    ) -> tuple[list[dict[str, Any]], str | None]:
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

            available_dates = available_dates_result.get("available_dates", [])[:days]

            availability_list = []
            selected_date = None

            # For each available date, get the slots
            for date_str in available_dates:
                slots_result = await self.get_available_slots(
                    doctor_id, clinic_id, date_str
                )
                slots = []
                for day in slots_result.get("dates", []):
                    if day.get("date") == date_str:
                        slots = day.get("all_slots", [])
                        break

                # Filter slots for today to have at least 15 min buffer from current time
                if date_str == today_str and slots:
                    slots = self._filter_slots_with_buffer(slots, buffer_minutes=15)

                if slots:
                    day_availability: dict[str, Any] = {
                        "date": date_str,
                        "slots": slots,
                    }

                    # Mark selected slot if preference matches
                    if (
                        preferred_slot_time
                        and date_str == preferred_date
                        and preferred_slot_time in slots
                    ):
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

    def _filter_slots_with_buffer(
        self, slots: list[str], buffer_minutes: int = 15
    ) -> list[str]:
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
        self, appointment_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Book Appointment Slot (raw API call)."""
        return await self._make_request(
            method="POST", endpoint="/dr/v1/appointment", data=appointment_data
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
        reason: str | None = None,
        patient_name: str | None = None,
        dob: str | None = None,
        gender: str | None = None,
        tag_ids: list[str] | None = None,
        session_id: str | None = None,
        token: int | None = None,
    ) -> dict[str, Any]:
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
                    "error_code": "NO_SCHEDULE",
                },
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
                    "error_code": "SLOT_NOT_FOUND",
                },
            }

        # Handle unavailable slot
        if not is_available:
            return create_unavailable_slot_response(
                date, start_time, end_time, alternate_slots
            )

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
                "mode": mode,
            },
            "partner_meta": {
                "conversation_id": session_id,
                "source": "EkaAgents",
            },
        }

        if tag_ids:
            appointment_data.setdefault("appointment_details", {}).setdefault(
                "custom_attributes", {}
            )["tags"] = tag_ids

        if reason:
            appointment_data["appointment_details"]["reason"] = reason

        if token is not None:
            appointment_data["token"] = token

        # Tele-consultation: create a video consultation link via Horus
        vc_link_error = None
        if mode == "VIDEO" and AsyncHorusClient is not None:
            try:
                async with AsyncHorusClient() as horus_client:
                    link = await horus_client.create_consultation_link(
                        aid=f"{doctor_id}-{clinic_id}-{start_timestamp}"
                    )
                appointment_data["vc_meta"] = {
                    "host_link": build_100ms_meeting_url(link.host_url),
                    "meet_link": build_100ms_meeting_url(link.guest_url),
                    "platform": "eka",
                }
            except Exception as e:
                vc_link_error = str(e)
                logger.warning(f"Failed to create video consultation link: {e}")

        result = await self.book_appointment(appointment_data)

        # Build successful response
        booked_slot_info = {
            "date": date,
            "start_time": start_time,
            "end_time": actual_end_time,
        }

        response = {"success": True, "data": result, "booked_slot": booked_slot_info}

        if "vc_meta" in appointment_data:
            response["vc_meta"] = appointment_data["vc_meta"]
        if vc_link_error:
            response["vc_link_warning"] = (
                f"Appointment booked, but the video consultation link could not be created: {vc_link_error}"
            )

        return response

    async def show_appointments(
        self,
        doctor_id: str | None = None,
        clinic_id: str | None = None,
        patient_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        page_no: int = 0,
    ) -> dict[str, Any]:
        """Get Appointments with flexible filters."""
        params = {"page_no": page_no}
        if doctor_id:
            params["doctor_id"] = doctor_id
        if clinic_id:
            params["clinic_id"] = clinic_id
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if patient_id:
            params = {
                "patient_id": patient_id
            }  # API constraint: patient_id cannot be combined with other filters

        return await self._make_request(
            method="GET", endpoint="/dr/v1/appointment", params=params
        )

    async def get_appointment_details(
        self, appointment_id: str, partner_id: str | None = None
    ) -> dict[str, Any]:
        """Get Appointment Details by appointment ID."""
        params = {}
        if partner_id:
            params["partner_id"] = partner_id

        return await self._make_request(
            method="GET",
            endpoint=f"/dr/v1/appointment/{appointment_id}",
            params=params if params else None,
        )

    async def update_appointment(
        self,
        appointment_id: str,
        update_data: dict[str, Any],
        partner_id: str | None = None,
    ) -> dict[str, Any]:
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
            params=params if params else None,
        )

    async def complete_appointment(
        self, appointment_id: str, completion_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Complete Appointment."""
        return await self._make_request(
            method="POST",
            endpoint=f"/dr/v1/appointment/{appointment_id}/complete",
            data=completion_data,
        )

    async def cancel_appointment(
        self, appointment_id: str, cancel_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Cancel Appointment."""
        return await self._make_request(
            method="PUT",
            endpoint=f"/dr/v1/appointment/{appointment_id}/cancel",
            data=cancel_data,
        )

    async def reschedule_appointment(
        self, reschedule_data_json: dict[str, Any]
    ) -> dict[str, Any]:
        """Reschedule Appointment."""
        # return await self._make_request(
        #     method="PUT",
        #     endpoint=f"/dr/v1/appointment/{appointment_id}/reschedule",
        #     data=reschedule_data
        # )
        return {
            "error": "Not implemented",
            "message": "reschedule_appointment is not available for this workspace",
        }

    async def park_appointment(
        self, appointment_id: str, park_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Park Appointment."""
        return await self._make_request(
            method="POST",
            endpoint=f"/dr/v1/appointment/{appointment_id}/parked",
            data=park_data,
        )

    async def update_appointment_custom_attribute(
        self, appointment_id: str, custom_attributes: dict[str, Any]
    ) -> dict[str, Any]:
        """Update Appointment Custom Attribute."""
        return await self._make_request(
            method="PATCH",
            endpoint=f"/dr/v1/appointment/{appointment_id}/custom_attribute",
            data=custom_attributes,
        )

    async def get_patient_appointments(
        self,
        patient_id: str,
        limit: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Get all appointments for a patient profile using the appointments endpoint.

        Note: If patient_id is provided, no other filters (dates, doctor_id, clinic_id) are allowed.
        """
        # Note: API constraint - patient_id cannot be combined with date filters
        params = {"patient_id": patient_id, "page_no": 0}

        # Get appointments using the standard endpoint
        result = await self._make_request(
            method="GET", endpoint="/dr/v1/appointment", params=params
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
                        start_ts = int(
                            datetime.strptime(start_date, "%Y-%m-%d").timestamp()
                        )
                        if appt_time < start_ts:
                            continue
                    if end_date:
                        end_ts = (
                            int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())
                            + 86400
                        )  # end of day
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
        practitioner_uuid: str | None = None,
        patient_uuid: str | None = None,
        unique_identifier: str | None = None,
        transaction_id: str | None = None,
        wfids: list[str] | None = None,
        status: str = "COMPLETED",
    ) -> dict[str, Any]:
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
            params=params if params else None,
        )

    # Prescription APIs
    async def get_prescription_details(self, prescription_id: str) -> dict[str, Any]:
        """Get Prescription details."""
        return await self._make_request(
            method="GET", endpoint=f"/dr/v1/prescription/{prescription_id}"
        )

    # Medical Records (Vault) APIs
    async def list_medical_records(
        self,
        patient_id: str,
        updated_after: int | None = None,
        offset: str | None = None,
    ) -> dict[str, Any]:
        """List a patient's medical records (documents).

        Args:
            patient_id: Eka user OID of the patient (sent as the X-Pt-Id header)
            updated_after: Only return records updated after this epoch (seconds)
            offset: Pagination token (next_token from a previous response)
        """
        params: dict[str, Any] = {}
        if updated_after is not None:
            params["u_at__gt"] = updated_after
        if offset:
            params["offset"] = offset
        return await self._make_request(
            method="GET",
            endpoint="/mr/api/v1/docs",
            params=params or None,
            headers={"X-Pt-Id": patient_id, "Accept": "application/json"},
        )

    async def get_medical_record(
        self,
        patient_id: str,
        document_id: str,
    ) -> dict[str, Any]:
        """Get a single medical record's metadata and signed download URL.

        Args:
            patient_id: Eka user OID of the patient (sent as the X-Pt-Id header)
            document_id: Unique identifier of the record/document
        """
        return await self._make_request(
            method="GET",
            endpoint=f"/mr/api/v1/docs/{document_id}",
            headers={"X-Pt-Id": patient_id, "Accept": "application/json"},
        )

    async def delete_medical_record(
        self,
        patient_id: str,
        document_id: str,
    ) -> dict[str, Any]:
        """Delete a patient's medical record (document). Irreversible.

        Args:
            patient_id: Eka user OID of the patient (sent as the X-Pt-Id header)
            document_id: Unique identifier of the record/document to delete
        """
        return await self._make_request(
            method="DELETE",
            endpoint=f"/mr/api/v1/docs/{document_id}",
            headers={"X-Pt-Id": patient_id, "Accept": "application/json"},
        )

    async def initiate_medical_record_upload(
        self,
        patient_id: str,
        batch_request: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Step 1 of upload: register document metadata and obtain presigned upload URLs.

        Args:
            patient_id: Eka user OID of the patient (sent as the X-Pt-Id header)
            batch_request: List of document upload requests, each containing at
                least a ``files`` array of ``{contentType, file_size}`` entries.
        """
        return await self._make_request(
            method="POST",
            endpoint="/mr/api/v1/docs",
            data={"batch_request": batch_request},
            headers={"X-Pt-Id": patient_id},
        )

    async def upload_file_to_presigned_url(
        self,
        url: str,
        fields: dict[str, Any],
        file_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> int:
        """Step 2 of upload: POST the file bytes to the presigned storage URL.

        Makes a direct multipart/form-data request (bypassing _make_request)
        because this hits object storage (S3) directly and must NOT include the
        eka auth headers or client-id.

        Returns:
            The HTTP status code from storage (204 on success).
        """
        files = {"file": (filename, file_bytes, content_type)}
        response = await self._http_client.request(
            method="POST",
            url=url,
            data=fields,
            files=files,
        )
        if response.status_code >= 400:
            raise EkaAPIError(
                message=f"Failed to upload file to storage: {response.text[:200]}",
                status_code=response.status_code,
            )
        return response.status_code

    async def download_file(
        self, url: str, max_bytes: int, timeout_seconds: float = 10.0
    ) -> bytes:
        """Download a file from a URL, aborting once it exceeds ``max_bytes``.

        Makes a direct request (bypassing _make_request) so the eka auth
        headers are never sent to a third-party host. Redirects are not
        followed, so the caller-validated URL is the only host contacted.

        Raises:
            EkaAPIError: On HTTP errors, redirects, oversized files, network
                errors, or if the whole download takes longer than ``timeout_seconds``.
        """
        try:
            return await asyncio.wait_for(
                self._stream_download(url, max_bytes), timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            raise EkaAPIError(
                f"File download timed out after {timeout_seconds:g} seconds"
            )
        except httpx.HTTPError as e:
            raise EkaAPIError(
                f"Network error while downloading file: {type(e).__name__}"
            )

    async def _stream_download(self, url: str, max_bytes: int) -> bytes:
        async with self._http_client.stream(
            "GET", url, follow_redirects=False
        ) as response:
            if response.status_code >= 400:
                raise EkaAPIError(
                    message=f"Failed to download file (HTTP {response.status_code})",
                    status_code=response.status_code,
                )
            if response.status_code >= 300:
                raise EkaAPIError(
                    "File URL redirects elsewhere; provide the direct file URL"
                )

            content = bytearray()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > max_bytes:
                    raise EkaAPIError(
                        f"File exceeds the maximum allowed size of {max_bytes // (1024 * 1024)} MB"
                    )
            return bytes(content)

    # Service APIs
    async def service_availability_elicitation(self, *args, **kwargs) -> dict[str, Any]:
        """Not implemented for EkaEMRClient."""
        return {
            "error": "Not implemented",
            "message": "service_availability_elicitation is not available for this workspace",
        }

    async def book_service(self, *args, **kwargs) -> dict[str, Any]:
        """Not implemented for EkaEMRClient."""
        return {
            "error": "Not implemented",
            "message": "book_service is not available for this workspace",
        }

    # Abstract method implementations (Not implemented for this client)
    async def get_appointments(self, *args, **kwargs) -> dict[str, Any]:
        """Not implemented for EkaEMRClient."""
        return {
            "error": "Not implemented",
            "message": "get_appointments is not available for this workspace",
        }

    def mobile_number_verification(self, *args, **kwargs) -> dict[str, Any]:
        """Not implemented for EkaEMRClient."""
        return {
            "error": "Not implemented",
            "message": "mobile_number_verification is not available for this workspace",
        }

    def authentication_elicitation(self, *args, **kwargs) -> dict[str, Any]:
        """Not implemented for EkaEMRClient."""
        return {
            "error": "Not implemented",
            "message": "authentication_elicitation is not available for this workspace",
        }

    async def list_all_patient_profiles(self) -> dict[str, Any]:
        """Not implemented for EkaEMRClient."""
        return {
            "error": "Not implemented",
            "message": "list_all_patient_profiles is not available for this workspace",
        }

    async def get_patient_vitals(self, patient_id: str) -> dict[str, Any]:
        """Not implemented for EkaEMRClient."""
        return {
            "error": "Not implemented",
            "message": "get_patient_vitals is not available for this workspace",
        }

    def get_workspace_name(self) -> str:
        """Return workspace name for EkaEMRClient."""
        return "ekaemr"
