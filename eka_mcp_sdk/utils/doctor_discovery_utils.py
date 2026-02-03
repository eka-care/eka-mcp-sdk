"""
Doctor Discovery Utilities

Helper functions for filtering doctors, building UI responses,
and fetching availability in the doctor_card component format.
"""

import logging
from typing import Any, Dict, List, Optional

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
    """
    Parse slot results into a date -> slots map.
    
    Works with common format from client:
    {
        "date": "YYYY-MM-DD",
        "all_slots": ["HH:MM", ...],
        ...
    }
    """
    date_slots_map: Dict[str, List[str]] = {}
    
    # Common format from client
    date = slots_result.get('date', '')
    all_slots = slots_result.get('all_slots', [])
    
    if date and all_slots:
        date_slots_map[date] = all_slots
    
    return date_slots_map


def build_elicitation_response(
    doctor_id: str,
    doctor_entry: Dict[str, Any],
    doctor_details: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Build the UI contract response for doctor availability elicitation.
    
    Callback format follows:
    ToolCallbacks = {
        [callback_name]: {
            tool_name: string,
            input_schema: Record<string, unknown>
        }
    }
    """
    return {
        "component": "doctor_card",
        "input": {
            "doctors": [doctor_entry],
            "doctor_details": {doctor_id: doctor_details}
        },
        "_meta": {
            "callbacks": {
                "get_doctor_details": {
                    "tool_name": "get_doctor_profile_basic",
                    "input_schema": {
                        "doctor_id": {"type": "string", "description": "Doctor ID"}
                    }
                },
                "get_available_dates": {
                    "tool_name": "get_available_dates",
                    "input_schema": {
                        "doctor_id": {"type": "string", "description": "Doctor ID"},
                        "clinic_id": {"type": "string", "description": "Clinic/Hospital ID"},
                        "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                        "max_days": {"type": "integer", "description": "Max days to check (default: 7)"}
                    }
                },
                "get_available_slots": {
                    "tool_name": "get_available_slots",
                    "input_schema": {
                        "doctor_id": {"type": "string", "description": "Doctor ID"},
                        "clinic_id": {"type": "string", "description": "Clinic/Hospital ID"},
                        "date": {"type": "string", "description": "Date (YYYY-MM-DD)"}
                    }
                }
            }
        }
    }



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
    
    doctor_profile structure (from client - already in common format):
    {
        "id": "do...",
        "name": "Dr. Mayank Garg",
        "specialty": "Acupuncture",
        "specialties": ["Acupuncture"],
        "profile_pic": "...",
        "languages": [],
        "clinics": [{"clinic_id": "...", "name": "...", "address": {...}}]
    }
    
    doctor_clinics structure (from business entities):
    [{ "clinic_id": "c-...", "name": "...", "doctors": [...] }]
    """
    # Use doctor_clinics from business entities, fallback to profile clinics
    clinics_to_use = doctor_clinics if doctor_clinics else doctor_profile.get('clinics', [])
    
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
        "name": doctor_profile.get('name', ''),
        "specialty": doctor_profile.get('specialty', ''),
        "hospitals": hospitals
    }
    
    # Add optional fields from common format
    if doctor_profile.get('profile_pic'):
        details["profile_pic"] = doctor_profile['profile_pic']
    
    if doctor_profile.get('languages'):
        details["languages"] = doctor_profile['languages']
    
    if doctor_profile.get('experience'):
        details["experience"] = str(doctor_profile['experience'])
    
    if doctor_profile.get('timings'):
        details["timings"] = doctor_profile['timings']
    
    if doctor_profile.get('profile_link'):
        details["profile_link"] = doctor_profile['profile_link']
    
    return details
