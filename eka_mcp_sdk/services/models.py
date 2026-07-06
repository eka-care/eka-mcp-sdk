from typing import Any, Dict, List, Optional, TypedDict


class DayAvailability(TypedDict):
    date: str
    slots: List[str]


class DoctorAvailability(TypedDict):
    doctor_id: str
    hospital_id: Optional[str]
    preferred_date: Optional[str]
    availability: List[DayAvailability]


class DoctorAvailabilityV2Response(TypedDict):
    doctors: List[DoctorAvailability]
    doctor_details: Dict[str, Any]


class ConfirmedSlotResponse(TypedDict):
    """
    Returned by the v2 flow when a single doctor's preferred date + slot are
    already available (selected and finalized). It carries only the raw data;
    building the elicitation success model is the tool's responsibility.
    """
    slot_confirmed: bool
    doctor_id: str
    doctor_details: Dict[str, Any]
    clinic_id: Optional[str]
    selected_date: str
    selected_slot: str


class PatientProfile(TypedDict):
    """Canonical patient profile mapped from the raw minified patient API."""
    patient_id: str
    name: str
    mobile: Optional[str]
    dob: Optional[str]
    gender: Optional[str]


class ListPatientProfilesResponse(TypedDict):
    """
    Contract between PatientService.list_patient_profiles and the tool layer.
    It carries only the canonical data; building the elicitation model is the
    tool's responsibility.
    """
    profiles: List[PatientProfile]
    page_meta: Optional[Dict[str, Any]]


class BookedSlot(TypedDict):
    date: str
    start_time: str
    end_time: str


class AppointmentBookingV2Response(TypedDict):
    """
    Contract between AppointmentService.book_appointment_v2 and the tool layer.

    booked=True carries the raw booking API response and the booked slot;
    booked=False means the requested slot is unavailable and carries
    alternatives. Hard failures (doctor not in clinic, no schedule, slot not
    found) raise EkaAPIError instead.
    """
    booked: bool
    appointment: Optional[Dict[str, Any]]
    booked_slot: Optional[BookedSlot]
    alternate_slots: List[Dict[str, str]]
