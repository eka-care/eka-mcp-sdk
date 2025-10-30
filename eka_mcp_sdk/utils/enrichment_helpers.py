"""
Utility functions for data enrichment across MCP tools.

This module contains common helper functions used for enriching API responses
with additional data from related entities, caching mechanisms, and data transformations.
"""

from typing import Any, Dict, Optional, Callable, Awaitable
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


async def get_cached_data(
    api_function: Callable[[str], Awaitable[Dict[str, Any]]], 
    entity_id: str, 
    cache: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Get data from cache or API call with caching.
    
    Args:
        api_function: Async function that takes entity_id and returns data
        entity_id: Unique identifier for the entity
        cache: Cache dictionary to store results
    
    Returns:
        Entity data from cache or API, None if fetch fails
    """
    if entity_id not in cache:
        try:
            data = await api_function(entity_id)
            cache[entity_id] = data
        except Exception as e:
            logger.warning(f"Failed to get data for {entity_id}: {str(e)}")
            cache[entity_id] = None
    
    return cache.get(entity_id)


def calculate_age_from_dob(dob: str) -> Optional[int]:
    """
    Calculate age from date of birth string.
    
    Args:
        dob: Date of birth in YYYY-MM-DD format
    
    Returns:
        Age in years, None if calculation fails
    """
    try:
        if not dob:
            return None
        birth_date = datetime.strptime(dob, "%Y-%m-%d")
        today = datetime.now()
        age = today.year - birth_date.year
        if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
            age -= 1
        return age
    except Exception:
        return None


def extract_patient_summary(patient_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key patient information for enrichment.
    
    Args:
        patient_info: Full patient profile data
    
    Returns:
        Dictionary with essential patient details
    """
    if not patient_info:
        return {}
    
    return {
        "name": patient_info.get("fln", ""),
        "mobile": patient_info.get("mobile", ""),
        "email": patient_info.get("email", ""),
        "age": calculate_age_from_dob(patient_info.get("dob")),
        "gender": patient_info.get("gen", ""),
        "blood_group": patient_info.get("bg", "")
    }


def extract_doctor_summary(doctor_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key doctor information for enrichment.
    
    Args:
        doctor_info: Full doctor profile data
    
    Returns:
        Dictionary with essential doctor details
    """
    if not doctor_info:
        return {}
    
    return {
        "name": doctor_info.get("name", ""),
        "specialization": doctor_info.get("specialization", ""),
        "qualification": doctor_info.get("qualification", ""),
        "experience": doctor_info.get("experience", ""),
        "contact": doctor_info.get("contact", {})
    }


def extract_clinic_summary(clinic_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key clinic information for enrichment.
    
    Args:
        clinic_info: Full clinic profile data
    
    Returns:
        Dictionary with essential clinic details
    """
    if not clinic_info:
        return {}
    
    return {
        "name": clinic_info.get("name", ""),
        "address": clinic_info.get("address", ""),
        "phone": clinic_info.get("phone", ""),
        "timing": clinic_info.get("timing", ""),
        "location": clinic_info.get("location", {})
    }


def get_appointment_status_info(status: str) -> Dict[str, Any]:
    """
    Get enriched status information for an appointment.
    
    Args:
        status: Appointment status string
    
    Returns:
        Dictionary with status flags and information
    """
    return {
        "status": status,
        "is_upcoming": status.lower() in ["scheduled", "confirmed", "booked"],
        "is_completed": status.lower() in ["completed", "done"],
        "is_cancelled": status.lower() in ["cancelled", "canceled"]
    }