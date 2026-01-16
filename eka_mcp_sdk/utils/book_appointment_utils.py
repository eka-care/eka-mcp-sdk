from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from ..tools.models import AppointmentBookingRequest
from ..services.appointment_service import AppointmentService


def find_alternate_slots(
    all_slots: List[Dict[str, Any]], 
    requested_date: str, 
    requested_time: str,
    max_alternatives: int = 6
) -> List[Dict[str, str]]:
    """
    Find up to 6 nearest available slots around the requested time.
    Returns slots both before and after the requested time.
    
    Args:
        all_slots: List of all slots from the schedule
        requested_date: Date in YYYY-MM-DD format
        requested_time: Time in HH:MM format
        max_alternatives: Maximum number of alternatives to return (default: 6)
    
    Returns:
        List of alternate slot dictionaries with start_time, end_time, and date
    """
    # Parse requested datetime
    requested_dt = datetime.strptime(f"{requested_date} {requested_time}", "%Y-%m-%d %H:%M")
    
    # Collect available slots with their time difference from requested time
    available_with_distance = []
    
    for slot in all_slots:
        if not slot.get('available', False):
            continue
        
        slot_start = slot.get('s', '')
        slot_end = slot.get('e', '')
        
        if not slot_start or not slot_end:
            continue
        
        try:
            # Parse slot start time (handle timezone)
            # Format: "2026-01-13T14:15:00+05:30"
            slot_start_clean = slot_start.split('+')[0] if '+' in slot_start else slot_start.split('-')[0] if '-' in slot_start and slot_start.count('-') > 2 else slot_start
            slot_end_clean = slot_end.split('+')[0] if '+' in slot_end else slot_end.split('-')[0] if '-' in slot_end and slot_end.count('-') > 2 else slot_end
            
            slot_dt = datetime.strptime(slot_start_clean, "%Y-%m-%dT%H:%M:%S")
            
            # Calculate time difference in minutes
            time_diff = abs((slot_dt - requested_dt).total_seconds() / 60)
            
            available_with_distance.append({
                'start_time': slot_dt.strftime("%H:%M"),
                'end_time': datetime.strptime(slot_end_clean, "%Y-%m-%dT%H:%M:%S").strftime("%H:%M"),
                'date': slot_dt.strftime("%Y-%m-%d"),
                'datetime': slot_dt,
                'distance': time_diff,
                'is_before': slot_dt < requested_dt
            })
        except Exception:
            # Skip slots with parsing errors
            continue
    
    # Sort by distance from requested time
    available_with_distance.sort(key=lambda x: x['distance'])
    
    # Take the nearest slots up to max_alternatives
    nearest_slots = available_with_distance[:max_alternatives]
    
    # Format for response (remove helper fields)
    formatted_slots = [
        {
            'date': slot['date'],
            'start_time': slot['start_time'],
            'end_time': slot['end_time'],
            'time_difference_minutes': int(slot['distance'])
        }
        for slot in nearest_slots
    ]
    
    return formatted_slots


def normalize_slot_time(slot_time: str) -> str:
    """
    Normalize slot time by removing timezone information.
    
    Args:
        slot_time: Slot time string (e.g., "2026-01-13T14:15:00+05:30")
    
    Returns:
        Normalized time string without timezone
    """
    if '+' in slot_time:
        return slot_time.split('+')[0]
    elif '-' in slot_time and slot_time.count('-') > 2:
        return slot_time.split('-')[0]
    return slot_time


def extract_all_slots_from_schedule(clinic_schedule: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract all slots from clinic schedule services.
    
    Args:
        clinic_schedule: List of services with their slots
    
    Returns:
        Flattened list of all slots from all services
    """
    all_slots = []
    for service in clinic_schedule:
        all_slots.extend(service.get('slots', []))
    return all_slots


def find_requested_slot(
    all_slots: List[Dict[str, Any]], 
    requested_date: str, 
    requested_start_time: str,
    requested_end_time: str = None  # end_time is now optional, will match by start_time only
) -> Optional[Dict[str, Any]]:
    """
    Find the specific slot that matches the requested start time.
    Matches by start_time only to handle variable slot durations (15min, 30min, etc.)
    
    Args:
        all_slots: List of all available slots
        requested_date: Date in YYYY-MM-DD format
        requested_start_time: Start time in HH:MM format
        requested_end_time: End time in HH:MM format (ignored - kept for backwards compatibility)
    
    Returns:
        The matching slot dict or None if not found
    """
    requested_start = f"{requested_date}T{requested_start_time}"
    
    for slot in all_slots:
        slot_start = slot.get('s', '')
        
        # Normalize to same format (remove timezone for comparison)
        slot_start_normalized = normalize_slot_time(slot_start)
        
        # Match by start time only - slot duration is determined by doctor's schedule
        if slot_start_normalized.startswith(requested_start):
            return slot
    
    return None


def check_slot_availability(
    all_slots: List[Dict[str, Any]], 
    booking_date: str,
    start_time: str, 
    end_time: str
) -> Tuple[bool, Optional[Dict[str, Any]], List[Dict[str, str]]]:
    """
    Check if the requested slot is available and return alternatives if not.
    
    Args:
        all_slots: List of all slots from the schedule
        booking_date: Date in YYYY-MM-DD format
        start_time: Start time in HH:MM format
        end_time: End time in HH:MM format
    
    Returns:
        Tuple of (is_available, requested_slot, alternate_slots)
        - is_available: Boolean indicating if the requested slot is available
        - requested_slot: The requested slot dict (or None if not found)
        - alternate_slots: List of alternative slots if unavailable
    """
    # Find the requested slot
    requested_slot = find_requested_slot(all_slots, booking_date, start_time, end_time)
    
    if not requested_slot:
        return False, None, []
    
    # Check if slot is available
    if requested_slot.get('available', False):
        return True, requested_slot, []
    
    # Slot is unavailable, find alternatives
    alternate_slots = find_alternate_slots(all_slots, booking_date, start_time, max_alternatives=6)
    return False, requested_slot, alternate_slots


def convert_to_timestamps(booking_date: str, start_time: str, end_time: str) -> Tuple[int, int]:
    """
    Convert date and time strings to Unix timestamps.
    
    Args:
        booking_date: Date in YYYY-MM-DD format
        start_time: Start time in HH:MM format
        end_time: End time in HH:MM format
    
    Returns:
        Tuple of (start_timestamp, end_timestamp)
    """
    date_time_start = datetime.strptime(f"{booking_date} {start_time}", "%Y-%m-%d %H:%M")
    date_time_end = datetime.strptime(f"{booking_date} {end_time}", "%Y-%m-%d %H:%M")
    start_timestamp = int(date_time_start.timestamp())
    end_timestamp = int(date_time_end.timestamp())
    return start_timestamp, end_timestamp


def build_appointment_data(booking: AppointmentBookingRequest, actual_end_time: str = None) -> Dict[str, Any]:
    """
    Build the appointment data structure for API call.
    
    Args:
        booking: AppointmentBookingRequest object
        actual_end_time: Actual end time from slot (HH:MM format), overrides booking.end_time if provided
    
    Returns:
        Dictionary containing formatted appointment data
    """
    # Use actual slot end time if provided, otherwise fall back to booking end_time
    end_time = actual_end_time if actual_end_time else booking.end_time
    
    start_timestamp, end_timestamp = convert_to_timestamps(
        booking.date, booking.start_time, end_time
    )
    
    appointment_data = {
        "clinic_id": booking.clinic_id,
        "doctor_id": booking.doctor_id,
        "patient_id": booking.patient_id,
        "appointment_details": {
            "start_time": start_timestamp,
            "end_time": end_timestamp,
            "mode": booking.mode
        }
    }
    
    if booking.reason:
        appointment_data["appointment_details"]["reason"] = booking.reason
    
    return appointment_data


def get_slot_end_time(slot: Dict[str, Any]) -> Optional[str]:
    """
    Extract end time from slot in HH:MM format.
    
    Args:
        slot: Slot dictionary with 's' (start) and 'e' (end) fields
    
    Returns:
        End time in HH:MM format or None
    """
    slot_end = slot.get('e', '')
    if not slot_end:
        return None
    
    try:
        slot_end_normalized = normalize_slot_time(slot_end)
        end_dt = datetime.strptime(slot_end_normalized, "%Y-%m-%dT%H:%M:%S")
        return end_dt.strftime("%H:%M")
    except Exception:
        return None


def create_unavailable_slot_response(
    booking_date: str,
    start_time: str,
    end_time: str,
    alternate_slots: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Create a standardized response for unavailable slots.
    
    Args:
        booking_date: Date in YYYY-MM-DD format
        start_time: Start time in HH:MM format
        end_time: End time in HH:MM format
        alternate_slots: List of alternative slot options
    
    Returns:
        Dictionary containing error response with alternatives
    """
    return {
        "success": False,
        "slot_unavailable": True,
        "message": f"The requested time slot {start_time}-{end_time} is not available.",
        "requested_slot": {
            "date": booking_date,
            "start_time": start_time,
            "end_time": end_time,
            "available": False
        },
        "alternate_slots": alternate_slots,
        "error": {
            "message": "Requested slot is already booked",
            "status_code": 409,
            "error_code": "SLOT_UNAVAILABLE"
        }
    }


async def fetch_appointment_slots(
    appointment_service: AppointmentService,
    doctor_id: str,
    clinic_id: str,
    booking_date: str,
    ctx
) -> Dict[str, Any]:
    """
    Fetch appointment slots for the given date range.
    
    Args:
        appointment_service: The appointment service instance
        doctor_id: Doctor's unique identifier
        clinic_id: Clinic's unique identifier
        booking_date: Date in YYYY-MM-DD format
        ctx: Context for logging
    
    Returns:
        Dictionary containing slots data
    """
    # Calculate end_date as start_date + 1
    start_date_obj = datetime.strptime(booking_date, "%Y-%m-%d")
    end_date = (start_date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
    
    await ctx.info(f"[fetch_appointment_slots] Fetching slots from {booking_date} to {end_date}")
    
    slots_result = await appointment_service.get_appointment_slots(
        doctor_id, clinic_id, booking_date, end_date
    )
    
    return slots_result


def validate_clinic_schedule(slots_result: Dict[str, Any], clinic_id: str) -> Optional[List[Dict[str, Any]]]:
    """
    Validate and extract clinic schedule from slots result.
    
    Args:
        slots_result: Result from get_appointment_slots API call
        clinic_id: Clinic's unique identifier
    
    Returns:
        Clinic schedule list or None if not found
    """
    schedule_data = slots_result.get('data', {}).get('schedule', {})
    clinic_schedule = schedule_data.get(clinic_id, [])
    
    if not clinic_schedule:
        return None
    
    return clinic_schedule