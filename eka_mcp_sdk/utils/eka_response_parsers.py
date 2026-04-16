"""
Eka API Response Parsers

Utility functions to parse Eka-specific API responses into common contract formats.
These are used by EkaEMRClient to transform raw API responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


def parse_slots_to_common_format(
    raw_response: Dict[str, Any],
    clinic_id: str,
    date: str,
    doctor_id: str
) -> Dict[str, Any]:
    """
    Parse Eka API slot response into common contract format.
    
    Eka API response structure:
    {
        "data": {
            "schedule": {
                "<clinic_id>": [
                    {
                        "service_name": "Consultation",
                        "fee": 500,
                        "slots": [
                            {"s": "2026-01-13T14:15:00+05:30", "e": "...", "available": true}
                        ]
                    }
                ]
            }
        }
    }
    
    Returns:
        Common format:
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
    schedule_data = raw_response.get('data', {}).get('schedule', {})
    clinic_schedule = schedule_data.get(clinic_id, [])
    
    all_slots: List[str] = []
    slot_categories: List[Dict[str, Any]] = []
    pricing: Dict[str, Any] = {}
    interval_minutes: Optional[int] = None
    
    for service in clinic_schedule:
        service_name = service.get('service_name', 'Consultation')
        category_slots: List[str] = []
        
        # Extract pricing from first service
        if not pricing:
            if service.get('fee'):
                pricing['consultation_fee'] = service.get('fee')
            if service.get('registration_fee'):
                pricing['registration_fee'] = service.get('registration_fee')
            if pricing:
                pricing['currency'] = 'INR'
        
        for slot in service.get('slots', []):
            if slot.get('available', False):
                slot_start = slot.get('s', '')
                
                if slot_start:
                    time_str = extract_time_24h(slot_start)
                    if time_str:
                        all_slots.append(time_str)
                        category_slots.append(time_str)
                        
                        # Calculate interval from first two slots
                        if interval_minutes is None and len(all_slots) >= 2:
                            interval_minutes = calculate_interval(all_slots[0], all_slots[1])
        
        # Add category if has slots
        if category_slots:
            slot_categories.append({
                "category": service_name.lower().replace(' ', '_'),
                "slots": sorted(category_slots)
            })
    
    # Sort and deduplicate all slots
    all_slots = sorted(set(all_slots))
    
    # Build response
    response: Dict[str, Any] = {
        "date": date,
        "doctor_id": doctor_id,
        "clinic_id": clinic_id,
        "all_slots": all_slots
    }
    
    # Add optional fields
    if interval_minutes:
        response["slot_config"] = {"interval_minutes": interval_minutes}
    
    if slot_categories:
        response["slot_categories"] = slot_categories
    
    if pricing:
        response["pricing"] = pricing
    
    response["metadata"] = {}
    
    return response


def parse_available_dates(
    raw_response: Dict[str, Any],
    clinic_id: str,
    start_date: str,
    end_date: str
) -> Dict[str, Any]:
    """
    Parse Eka API response to extract available dates.
    
    Returns dates that have at least one available slot.
    
    Returns:
        {
            "available_dates": ["YYYY-MM-DD", ...],
            "date_range": {"start": "...", "end": "..."}
        }
    """
    schedule_data = raw_response.get('data', {}).get('schedule', {})
    clinic_schedule = schedule_data.get(clinic_id, [])
    
    available_dates_set = set()
    
    for service in clinic_schedule:
        for slot in service.get('slots', []):
            if slot.get('available', False):
                slot_start = slot.get('s', '')
                if slot_start:
                    # Extract date from "2026-01-13T14:15:00+05:30"
                    date_part = slot_start.split('T')[0]
                    available_dates_set.add(date_part)
    
    # Sort dates
    available_dates = sorted(available_dates_set)
    
    # Parse date range
    start = start_date.split('T')[0] if 'T' in start_date else start_date
    end = end_date.split('T')[0] if 'T' in end_date else end_date
    
    return {
        "available_dates": available_dates,
        "date_range": {
            "start": start,
            "end": end
        }
    }


def parse_doctor_profile(raw_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse Eka doctor profile API response into common format.
    
    Eka API response structure:
    {
        "success": true,
        "data": {
            "id": "do...",
            "profile": {
                "personal": {"first_name": "...", "last_name": "...", "pic": "..."},
                "professional": {
                    "major_speciality": {"name": "..."},
                    "speciality": [{"name": "..."}],
                    "language": [],
                    "clinics": [{...}]
                }
            }
        }
    }
    
    Returns:
        {
            "id": "do...",
            "name": "Dr. Mayank Garg",
            "specialty": "Acupuncture",
            "specialties": ["Acupuncture"],
            "profile_pic": "...",
            "languages": [],
            "clinics": [{"clinic_id": "...", "name": "...", "address": {...}}]
        }
    """
    data = raw_response.get('data', raw_response)
    profile = data.get('profile', {})
    personal = profile.get('personal', {})
    professional = profile.get('professional', {})
    
    # Extract name
    first_name = personal.get('first_name', '')
    last_name = personal.get('last_name', '')
    name = f"{first_name} {last_name}".strip()
    
    # Extract specialty
    major_speciality = professional.get('major_speciality', {})
    specialty = major_speciality.get('name', '')
    
    # Extract all specialties as list
    specialties = []
    if specialty:
        specialties.append(specialty)
    for spec in professional.get('speciality', []):
        spec_name = spec.get('name', '')
        if spec_name and spec_name not in specialties:
            specialties.append(spec_name)
    
    # Extract clinics with standardized structure
    clinics = []
    for clinic in professional.get('clinics', []):
        clinic_entry = {
            "clinic_id": clinic.get('id', ''),
            "name": clinic.get('name', ''),
            "address": clinic.get('address', {})
        }
        if clinic.get('contacts'):
            clinic_entry["contacts"] = clinic.get('contacts')
        clinics.append(clinic_entry)
    
    return {
        "id": data.get('id', ''),
        "name": name,
        "specialty": specialty,
        "specialties": specialties,
        "profile_pic": personal.get('pic', ''),
        "languages": professional.get('language', []),
        "clinics": clinics
    }


def parse_business_entities(raw_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse Eka business entities API response into common format.
    
    Eka API response structure:
    {
        "success": true,
        "data": {
            "business": {"business_id": "...", "name": "..."},
            "clinics": [{"clinic_id": "...", "name": "...", "doctors": [...]}],
            "doctors": [{"doctor_id": "...", "name": "..."}]
        }
    }
    
    Returns:
        Unwrapped data with consistent structure.
    """
    data = raw_response.get('data', raw_response)
    
    return {
        "business": data.get('business', {}),
        "clinics": data.get('clinics', []),
        "doctors": data.get('doctors', [])
    }


def extract_time_24h(iso_datetime: str) -> Optional[str]:
    """Extract HH:MM time from ISO datetime string."""
    if not iso_datetime:
        return None
    
    try:
        clean_str = iso_datetime.split('+')[0] if '+' in iso_datetime else iso_datetime
        dt = datetime.strptime(clean_str, "%Y-%m-%dT%H:%M:%S")
        return dt.strftime("%H:%M")
    except (ValueError, AttributeError):
        return None


def calculate_interval(time1: str, time2: str) -> Optional[int]:
    """Calculate interval in minutes between two HH:MM time strings."""
    try:
        t1 = datetime.strptime(time1, "%H:%M")
        t2 = datetime.strptime(time2, "%H:%M")
        diff = int((t2 - t1).total_seconds() / 60)
        return diff if diff > 0 else None
    except (ValueError, AttributeError):
        return None
