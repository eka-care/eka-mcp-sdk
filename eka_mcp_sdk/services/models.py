from typing import Any, Dict, List, Optional, TypedDict


class DayAvailability(TypedDict):
    date: str
    slots: List[str]


class DoctorAvailability(TypedDict):
    doctor_id: str
    doctor_availability: List[DayAvailability]


class DoctorAvailabilityV2Response(TypedDict):
    doctors: List[DoctorAvailability]


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
