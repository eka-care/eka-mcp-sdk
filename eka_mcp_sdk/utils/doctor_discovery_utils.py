"""
Doctor Discovery Utilities

Helper functions for filtering doctors, building UI responses,
and fetching availability in the doctor_card component format.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from ..services.appointment_service import AppointmentService

logger = logging.getLogger(__name__)

def find_doctor_clinics(
    clinics_list: List[Dict[str, Any]],
    doctor_id: str
) -> List[Dict[str, Any]]:
    """
    Find all clinics associated with a doctor.
    
    Note: In the API, clinics contain doctor IDs (not the reverse).
    clinics: [{ clinic_id: "...", doctors: ["do123", ...], name: "..." }]
    """
    doctor_clinics = []
    for clinic in clinics_list:
        doctor_ids = clinic.get('doctors', [])
        if doctor_id in doctor_ids:
            doctor_clinics.append(clinic)
    return doctor_clinics


def resolve_hospital_id(
    doctor_clinics: List[Dict[str, Any]],
    hospital_id: Optional[str]
) -> Optional[str]:
    """Resolve hospital ID - validate provided one or use first available."""
    if hospital_id:
        for clinic in doctor_clinics:
            clinic_id = clinic.get('clinic_id') or clinic.get('id')
            if clinic_id == hospital_id:
                return hospital_id
    # Fall back to first clinic
    if doctor_clinics:
        return doctor_clinics[0].get('clinic_id') or doctor_clinics[0].get('id')
    return None


def parse_slots_to_date_map(
    slots_result: Dict[str, Any],
    hospital_id: str
) -> Dict[str, List[str]]:
    """Parse slot results into a date -> slots map."""
    date_slots_map: Dict[str, List[str]] = {}
    schedule_data = slots_result.get('data', {}).get('schedule', {})
    clinic_schedule = schedule_data.get(hospital_id, [])
    
    for service in clinic_schedule:
        for slot in service.get('slots', []):
            if slot.get('available', False):
                slot_start = slot.get('s', '')
                if slot_start:
                    try:
                        slot_date = slot_start.split('T')[0]
                        slot_time = slot_start.split('T')[1].split('+')[0][:5]  # HH:MM
                        if slot_date not in date_slots_map:
                            date_slots_map[slot_date] = []
                        date_slots_map[slot_date].append(slot_time)
                    except Exception:
                        continue
    return date_slots_map


async def fetch_doctor_availability(
    appointment_service: AppointmentService,
    doctor_id: str,
    hospital_id: str,
    preferred_date: Optional[str] = None,
    preferred_slot_time: Optional[str] = None,
    days: int = 10
) -> tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Fetch doctor availability for a date range.
    
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
    
    # Build date range
    start_datetime = f"{start_date.strftime('%Y-%m-%d')}T00:00:00.000Z"
    end_date = start_date + timedelta(days=days - 1)
    end_datetime = f"{end_date.strftime('%Y-%m-%d')}T23:59:59.000Z"
    
    try:
        slots_result = await appointment_service.get_appointment_slots(
            doctor_id, hospital_id, start_datetime, end_datetime
        )
        
        date_slots_map = parse_slots_to_date_map(slots_result, hospital_id)
        sorted_dates = sorted(date_slots_map.keys())[:days]
        
        availability_list = []
        for date_str in sorted_dates:
            slots = sorted(date_slots_map[date_str])
            day_availability: Dict[str, Any] = {"date": date_str, "slots": slots}
            
            # Mark selected slot if preference matches
            if preferred_slot_time and date_str == preferred_date and preferred_slot_time in slots:
                day_availability["selected_slot"] = preferred_slot_time
            
            availability_list.append(day_availability)
        
        # Determine selected date
        selected_date = None
        if preferred_date and preferred_date in sorted_dates:
            selected_date = preferred_date
        elif sorted_dates:
            selected_date = sorted_dates[0]
        
        return availability_list, selected_date
        
    except Exception as e:
        logger.warning(f"Failed to fetch availability: {e}")
        return [], None


def build_elicitation_response(
    doctor_id: str,
    doctor_entry: Dict[str, Any],
    doctor_details: Dict[str, Any]
) -> Dict[str, Any]:
    """Build the UI contract response for doctor availability elicitation."""
    return {
        "component": "doctor_card",
        "input": {
            "doctors": [doctor_entry],
            "doctor_details": {doctor_id: doctor_details}
        },
        "_meta": {
            "callbacks": [
                {
                    "tool_name": "get_doctor_profile_basic",
                    "input_schema": {"doctor_id": "string"}
                },
                {
                    "tool_name": "get_available_slots",
                    "input_schema": {
                        "doctor_id": "string",
                        "clinic_id": "string",
                        "date": "string (YYYY-MM-DD)"
                    }
                }
            ]
        }
    }



def _extract_name_from_profile(profile_data: Dict[str, Any]) -> str:
    """Extract doctor name from profile data."""
    # Try direct name field first
    if profile_data.get('name'):
        return profile_data['name']
    
    # Try nested profile.personal structure
    personal = profile_data.get('profile', {}).get('personal', {})
    first_name = personal.get('first_name', '')
    last_name = personal.get('last_name', '')
    if first_name or last_name:
        return f"{first_name} {last_name}".strip()
    
    return ''


def _extract_specialty_from_profile(profile_data: Dict[str, Any]) -> str:
    """Extract specialty from profile data."""
    # Try direct specialty field
    if profile_data.get('specialty'):
        return profile_data['specialty']
    
    # Try nested profile.professional structure
    professional = profile_data.get('profile', {}).get('professional', {})
    
    # Try major_speciality first
    major_spec = professional.get('major_speciality', {})
    if major_spec.get('name'):
        return major_spec['name']
    
    # Try speciality array
    specialities = professional.get('speciality', [])
    if specialities and isinstance(specialities, list) and len(specialities) > 0:
        return specialities[0].get('name', '')
    
    return ''


def _extract_clinic_address(clinic: Dict[str, Any]) -> Dict[str, str]:
    """Extract address fields from clinic, handling nested address structure."""
    # Try direct fields first
    city = clinic.get('city', '')
    state = clinic.get('state', '')
    
    # Try nested address structure (from doctor profile's clinics)
    address = clinic.get('address', {})
    if address:
        city = city or address.get('city', '')
        state = state or address.get('state', '')
    
    return {'city': city, 'state': state}


def build_doctor_details_for_card(
    doctor_profile: Dict[str, Any],
    doctor_clinics: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Build doctor details in UI contract format.
    
    doctor_profile structure (from get_doctor_profile_basic):
    {
        "data": {
            "id": "do...",
            "profile": {
                "personal": { "first_name", "last_name", "pic", ... },
                "professional": { "major_speciality": {"name"}, "speciality": [...], "clinics": [...] }
            }
        }
    }
    
    doctor_clinics structure (from business entities):
    [{ "clinic_id": "c-...", "name": "...", "doctors": [...] }]
    """
    # Handle data wrapper if present
    profile_data = doctor_profile.get('data', doctor_profile)
    
    # Extract nested data
    personal = profile_data.get('profile', {}).get('personal', {})
    professional = profile_data.get('profile', {}).get('professional', {})
    
    # Build hospitals list from doctor_clinics (business entities)
    # Fallback to professional.clinics if no business entity clinics
    clinics_to_use = doctor_clinics if doctor_clinics else professional.get('clinics', [])
    
    hospitals = []
    for c in clinics_to_use:
        addr = _extract_clinic_address(c)
        hospitals.append({
            "hospital_id": c.get('clinic_id') or c.get('id', ''),
            "name": c.get('name', ''),
            "city": addr['city'],
            "state": addr['state'],
            "region_id": c.get('region_id', '')
        })
    
    details: Dict[str, Any] = {
        "name": _extract_name_from_profile(profile_data),
        "specialty": _extract_specialty_from_profile(profile_data),
        "hospitals": hospitals
    }
    
    # Add optional fields
    # Profile pic from personal
    pic = personal.get('pic') or profile_data.get('profile_pic') or profile_data.get('photo')
    if pic:
        details["profile_pic"] = pic
    
    # Languages from professional
    languages = professional.get('language') or profile_data.get('languages')
    if languages:
        details["languages"] = languages
    
    # Experience
    experience = profile_data.get('experience')
    if experience:
        details["experience"] = str(experience)
    
    # Timings
    timings = profile_data.get('timings')
    if timings:
        details["timings"] = timings
    
    # Profile link
    profile_link = profile_data.get('profile_link') or profile_data.get('profile_url')
    if profile_link:
        details["profile_link"] = profile_link
    
    return details
