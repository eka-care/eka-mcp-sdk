from typing import List, TypedDict


class DayAvailability(TypedDict):
    date: str
    slots: List[str]


class DoctorAvailability(TypedDict):
    doctor_id: str
    doctor_availability: List[DayAvailability]


class DoctorAvailabilityV2Response(TypedDict):
    doctors: List[DoctorAvailability]
