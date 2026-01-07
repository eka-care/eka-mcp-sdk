"""
Test suite for Appointment Tools APIs in eka-mcp-sdk

This test suite provides comprehensive testing for appointment management APIs including:
- Get appointment slots
- List appointments (basic and enriched)
- Get appointment details (basic and enriched)
- Get patient appointments
- Book appointment
- Update appointment
- Complete appointment
- Cancel appointment
- Reschedule appointment

Usage:
    # Run all tests
    python -m tests.test_appointment_tools

    # Run specific tests
    python -m tests.test_appointment_tools list_appointments get_slots

    # List available tests
    python -m tests.test_appointment_tools --list

    # Run with detailed output
    python -m tests.test_appointment_tools --verbose

Requirements:
    - .env file with valid EKA_CLIENT_ID and EKA_CLIENT_SECRET
    - Active OAuth tokens (will prompt for login if needed)
    - Valid doctor_id, clinic_id, and patient_id for testing
"""

import argparse
import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from eka_mcp_sdk.clients.eka_emr_client import EkaEMRClient
from eka_mcp_sdk.services.appointment_service import AppointmentService
from eka_mcp_sdk.auth.models import EkaAPIError
from eka_mcp_sdk.config.settings import EkaSettings


class TestRunner:
    """Test runner with logging and error handling"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.settings = EkaSettings()
        self.client: Optional[EkaEMRClient] = None
        self.service: Optional[AppointmentService] = None
        self.test_appointment_id: Optional[str] = None
        self.test_doctor_id: Optional[str] = None
        self.test_clinic_id: Optional[str] = None
        self.test_patient_id: Optional[str] = None
        self.test_cancellation_appointment_id: Optional[str] = None
        self.test_reschedule_appointment_id: Optional[str] = None
        
    async def setup(self):
        """Initialize client and service"""
        print("\n" + "=" * 70)
        print("🔧 Setting up test environment")
        print("=" * 70)
        
        # Initialize client (will handle OAuth flow)
        self.client = EkaEMRClient()
        self.service = AppointmentService(self.client)
        
        print(f"✅ API Base URL: {self.settings.api_base_url}")
        print(f"✅ Client initialized successfully")
        
    def log_request(self, test_name: str, **kwargs):
        """Log request details"""
        print(f"\n📤 REQUEST: {test_name}")
        if self.verbose and kwargs:
            print(f"   Parameters: {json.dumps(kwargs, indent=2)}")
    
    def log_response(self, response: Any, success: bool = True, curl_cmd: str = None):
        """Log response details"""
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"📥 RESPONSE: {status}")
        
        if self.verbose:
            if curl_cmd:
                print(f"\n🔧 CURL COMMAND:")
                print(f"   {curl_cmd}\n")
            print(f"   Response: {json.dumps(response, indent=2, default=str)}")
        elif isinstance(response, dict):
            # Show summary for non-verbose mode
            if response.get("success"):
                data = response.get("data", {})
                if isinstance(data, dict):
                    # Show key fields
                    summary_keys = ['appointment_id', 'status', 'message', 'appointments', 'slots']
                    summary = {k: data.get(k) for k in summary_keys if k in data}
                    if summary:
                        print(f"   Summary: {json.dumps(summary, indent=2, default=str)}")
            else:
                error = response.get("error", {})
                print(f"   Error: {error.get('message', 'Unknown error')}")
                if error.get('status_code'):
                    print(f"   Status: {error.get('status_code')}")
    
    def log_error(self, error: Exception):
        """Log error details"""
        print(f"❌ ERROR: {str(error)}")
        if self.verbose:
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")


# Initialize global test runner
runner: Optional[TestRunner] = None


def get_runner() -> TestRunner:
    """Get or create test runner instance"""
    global runner
    if not runner:
        runner = TestRunner(verbose=False)
    return runner


async def test_get_appointment_slots(*args, **kwargs):
    """Test get_appointment_slots API"""
    r = get_runner()
    await r.setup()
    
    doctor_id = kwargs.get("doctor_id", r.test_doctor_id)
    clinic_id = kwargs.get("clinic_id", r.test_clinic_id)
    
    # API only supports D to D+1 date range
    if not kwargs.get("start_date"):
        start_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
    else:
        start_date = kwargs.get("start_date")
        end_date = kwargs.get("end_date", (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d"))
    
    if not doctor_id or not clinic_id:
        print("   ⚠️  No doctor_id or clinic_id provided, skipping test")
        print("   💡 Usage: python -m tests.test_appointment_tools get_slots --doctor-id <id> --clinic-id <id>")
        return None
    
    r.log_request("get_appointment_slots", doctor_id=doctor_id, clinic_id=clinic_id, start_date=start_date, end_date=end_date)
    
    try:
        result = await r.service.get_appointment_slots(doctor_id=doctor_id, clinic_id=clinic_id, start_date=start_date, end_date=end_date)
        
        # Get curl command from client
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": True, "data": result}, curl_cmd=curl_cmd)
        
        # Validation
        assert result is not None, "Result should not be None"
        if isinstance(result, dict):
            data = result.get("data", {})
            schedule = data.get("schedule", {})
            total_slots = sum(len(slots) for date_slots in schedule.values() for service in date_slots for slots in [service.get("slots", [])])
            print(f"   ✓ Found {total_slots} slots in schedule for date range {start_date} to {end_date}")
        
        return result
        
    except EkaAPIError as e:
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": False, "error": {"message": str(e)}}, success=False, curl_cmd=curl_cmd)
        raise
    except Exception as e:
        r.log_error(e)
        raise


async def test_list_appointments(*args, **kwargs):
    """Test get_appointments_enriched API (list all appointments)"""
    r = get_runner()
    await r.setup()
    
    doctor_id = kwargs.get("doctor_id", r.test_doctor_id)
    clinic_id = kwargs.get("clinic_id", r.test_clinic_id)
    patient_id = kwargs.get("patient_id", r.test_patient_id)
    
    # API requires one of these combinations:
    # 1. patient_id (alone)
    # 2. doctor_id, start_date, end_date
    # 3. clinic_id, start_date, end_date
    # 4. start_date, end_date (default)
    # 5. doctor_id, clinic_id, start_date, end_date
    
    # Default to last 7 days if no dates provided and no patient_id
    if not patient_id and not kwargs.get("start_date"):
        start_date = kwargs.get("start_date", (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"))
        end_date = kwargs.get("end_date", datetime.now().strftime("%Y-%m-%d"))
    else:
        start_date = kwargs.get("start_date")
        end_date = kwargs.get("end_date")
    
    page_no = kwargs.get("page_no", 0)
    
    r.log_request("get_appointments_enriched", 
                 doctor_id=doctor_id, 
                 clinic_id=clinic_id, 
                 patient_id=patient_id,
                 start_date=start_date,
                 end_date=end_date,
                 page_no=page_no)
    
    try:
        result = await r.service.get_appointments_enriched(
            doctor_id=doctor_id,
            clinic_id=clinic_id,
            patient_id=patient_id,
            start_date=start_date,
            end_date=end_date,
            page_no=page_no
        )
        
        # Get curl command from client
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": True, "data": result}, curl_cmd=curl_cmd)
        
        # Validation
        assert result is not None, "Result should not be None"
        if isinstance(result, dict):
            appointments = result.get("appointments", [])
            print(f"   ✓ Retrieved {len(appointments)} appointments")
            
            # Store IDs from first appointment for other tests
            # Prefer an appointment with patient_details (indicates valid patient)
            selected_appts = []
            selected_appt = None
            for appt in appointments:
                if appt.get("patient_details"):
                    selected_appts.append(appt)
            if len(selected_appts) < 3 and appointments:
                for appt in appointments:
                    selected_appts.append(appt)
            
            if len(selected_appts):
                selected_appt = selected_appts[0]
                r.test_appointment_id = selected_appt.get("appointment_id")
                r.test_doctor_id = selected_appt.get("doctor_id")
                r.test_clinic_id = selected_appt.get("clinic_id")
                r.test_patient_id = selected_appt.get("patient_id")
                if len(selected_appts) > 1:
                    r.test_cancellation_appointment_id = selected_appts[1].get("appointment_id")
                if len(selected_appts) > 2:
                    r.test_reschedule_appointment_id = selected_appts[2].get("appointment_id")
                
                print(f"   ℹ️  Stored IDs for subsequent tests:")
                if r.test_appointment_id:
                    print(f"      - Appointment ID: {r.test_appointment_id}")
                if r.test_doctor_id:
                    print(f"      - Doctor ID: {r.test_doctor_id}")
                if r.test_clinic_id:
                    print(f"      - Clinic ID: {r.test_clinic_id}")
                if r.test_patient_id:
                    print(f"      - Patient ID: {r.test_patient_id}")
                if r.test_appointment_id:
                    print(f"      - Cancellation Appointment ID: {r.test_cancellation_appointment_id}")
                if r.test_appointment_id:
                    print(f"      - Reschedule Appointment ID: {r.test_reschedule_appointment_id}")
        
        return result
        
    except EkaAPIError as e:
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": False, "error": {"message": str(e)}}, success=False, curl_cmd=curl_cmd)
        raise
    except Exception as e:
        r.log_error(e)
        raise


async def test_get_appointment_details(*args, **kwargs):
    """Test get_appointment_details_enriched API"""
    r = get_runner()
    await r.setup()
    
    appointment_id = kwargs.get("appointment_id", r.test_appointment_id)
    partner_id = kwargs.get("partner_id")
    
    if not appointment_id:
        print("   ℹ️  No appointment ID provided, fetching from list_appointments...")
        list_result = await test_list_appointments(page_no=0)
        if isinstance(list_result, dict):
            appointments = list_result.get("appointments", [])
            if appointments and len(appointments) > 0:
                appointment_id = appointments[0].get("appointment_id")
    
    if not appointment_id:
        print("   ⚠️  No appointment ID available, skipping test")
        return None
    
    r.log_request("get_appointment_details_enriched", appointment_id=appointment_id, partner_id=partner_id)
    
    try:
        result = await r.service.get_appointment_details_enriched(appointment_id=appointment_id, partner_id=partner_id)
        
        # Get curl command from client
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": True, "data": result}, curl_cmd=curl_cmd)
        
        # Validation
        assert result is not None, "Result should not be None"
        if isinstance(result, dict):
            status = result.get("status", "Unknown")
            print(f"   ✓ Retrieved appointment details (ID: {appointment_id}, Status: {status})")
        
        return result
        
    except EkaAPIError as e:
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": False, "error": {"message": str(e)}}, success=False, curl_cmd=curl_cmd)
        raise
    except Exception as e:
        r.log_error(e)
        raise


async def test_get_patient_appointments(*args, **kwargs):
    """Test get_patient_appointments_enriched API"""
    r = get_runner()
    await r.setup()
    
    patient_id = kwargs.get("patient_id", r.test_patient_id)
    limit = kwargs.get("limit", 10)
    start_date = kwargs.get("start_date", (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
    end_date = kwargs.get("end_date", datetime.now().strftime("%Y-%m-%d"))
    
    if not patient_id:
        print("   ⚠️  No patient ID available, skipping test")
        print("   💡 Usage: python -m tests.test_appointment_tools get_patient_appts --patient-id <id>")
        return None
    
    r.log_request("get_patient_appointments_enriched", patient_id=patient_id, limit=limit, start_date=start_date, end_date=end_date)
    
    try:
        result = await r.service.get_patient_appointments_enriched(patient_id=patient_id, limit=limit, start_date=start_date, end_date=end_date)
        
        # Get curl command from client
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": True, "data": result}, curl_cmd=curl_cmd)
        
        # Validation
        assert result is not None, "Result should not be None"
        if isinstance(result, list):
            print(f"   ✓ Retrieved {len(result)} appointments for patient: {patient_id}")
        elif isinstance(result, dict):
            appointments = result.get("appointments", [])
            print(f"   ✓ Retrieved {len(appointments)} appointments for patient: {patient_id}")
        
        return result
        
    except EkaAPIError as e:
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": False, "error": {"message": str(e)}}, success=False, curl_cmd=curl_cmd)
        raise
    except Exception as e:
        r.log_error(e)
        raise


async def test_book_appointment(*args, **kwargs):
    """Test book_appointment API"""
    r = get_runner()
    await r.setup()
    
    # Extract IDs from previous tests or use provided ones
    doctor_id = kwargs.get("doctor_id", r.test_doctor_id)
    clinic_id = kwargs.get("clinic_id", r.test_clinic_id)
    patient_id = kwargs.get("patient_id", r.test_patient_id)
    
    # If no IDs available, try to fetch from list_appointments first
    if not all([doctor_id, clinic_id, patient_id]):
        print("   ℹ️  No IDs provided, fetching from list_appointments...")
        list_result = await test_list_appointments(**kwargs)
        doctor_id = r.test_doctor_id
        clinic_id = r.test_clinic_id
        patient_id = r.test_patient_id
    
    # Calculate appointment time (2 days from now, 10:00 AM)
    appointment_date = datetime.now() + timedelta(days=2)
    appointment_date = appointment_date.replace(hour=10, minute=0, second=0, microsecond=0)
    start_timestamp = int(appointment_date.timestamp())
    end_timestamp = int((appointment_date + timedelta(minutes=30)).timestamp())
    
    # Use provided data or create test data with correct structure per API docs
    # Using EkaIds mode (not PartnerIds) since we have eka internal IDs
    appointment_data = kwargs.get("appointment_data", {
        "doctor_id": doctor_id,  # Use eka IDs, not partner IDs
        "clinic_id": clinic_id,
        "patient_id": patient_id,
        "appointment_details": {
            "start_time": start_timestamp,
            "end_time": end_timestamp,
            "mode": "INCLINIC"
        },
        "patient_details": {
            "designation": "Mr.",
            "first_name": "Test",
            "middle_name": "",
            "last_name": "Patient",
            "mobile": "+919999999999",
            "gender": "M",
            "dob": "1990-01-01",  # Required field
        }
    })
    
    if not all([appointment_data.get("doctor_id"), appointment_data.get("clinic_id"), appointment_data.get("patient_id")]):
        print("   ⚠️  Missing required IDs (doctor_id, clinic_id, patient_id), skipping test")
        print("   💡 Usage: python -m tests.test_appointment_tools book --doctor-id <id> --clinic-id <id> --patient-id <id> --test-write")
        return None
    
    r.log_request("book_appointment", appointment_data=appointment_data)
    
    try:
        result = await r.service.book_appointment(appointment_data=appointment_data)
        
        # Get curl command from client
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": True, "data": result}, curl_cmd=curl_cmd)
        
        # Validation
        assert result is not None, "Result should not be None"
        if isinstance(result, dict):
            appointment_id = result.get("appointment_id")
            print(f"   ✓ Booked appointment (ID: {appointment_id})")
            
            # Store for cleanup
            r.test_appointment_id = appointment_id
        
        return result
        
    except EkaAPIError as e:
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": False, "error": {"message": str(e)}}, success=False, curl_cmd=curl_cmd)
        raise
    except Exception as e:
        r.log_error(e)
        raise


async def test_update_appointment(*args, **kwargs):
    """Test update_appointment API (V2)"""
    r = get_runner()
    await r.setup()
    
    appointment_id = kwargs.get("appointment_id", r.test_appointment_id)
    
    # V2 API requires doctor_id, clinic_id, and patient_id
    update_data = kwargs.get("update_data", {
        "doctor_id": r.test_doctor_id,
        "clinic_id": r.test_clinic_id,
        "patient_id": r.test_patient_id,
        "token": 1,
        "appointment_details": {
            "custom_attributes": {
                "label": [],
                "tags": []
            }
        },
        "display_meta": {
            "test_update": f"Updated at {datetime.now().isoformat()}"
        }
    })
    
    if not appointment_id:
        print("   ⚠️  No appointment ID available, skipping test")
        return None
    
    if not all([r.test_doctor_id, r.test_clinic_id, r.test_patient_id]):
        print("   ⚠️  Missing required IDs (doctor_id, clinic_id, patient_id) for V2 API, skipping test")
        return None
    
    r.log_request("update_appointment", appointment_id=appointment_id, update_data=update_data)
    
    try:
        result = await r.service.update_appointment(appointment_id=appointment_id, update_data=update_data)
        
        # Get curl command from client
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": True, "data": result}, curl_cmd=curl_cmd)
        
        # Validation
        assert result is not None, "Result should not be None"
        print(f"   ✓ Updated appointment: {appointment_id}")
        
        return result
        
    except EkaAPIError as e:
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": False, "error": {"message": str(e)}}, success=False, curl_cmd=curl_cmd)
        raise
    except Exception as e:
        r.log_error(e)
        raise


async def test_complete_appointment(*args, **kwargs):
    """Test complete_appointment API"""
    r = get_runner()
    await r.setup()
    
    appointment_id = kwargs.get("appointment_id", r.test_appointment_id)
    completion_data = kwargs.get("completion_data", {})
    
    if not appointment_id:
        print("   ⚠️  No appointment ID available, skipping test")
        return None
    
    r.log_request("complete_appointment", appointment_id=appointment_id, completion_data=completion_data)
    
    try:
        result = await r.service.complete_appointment(appointment_id=appointment_id, completion_data=completion_data)
        
        # Get curl command from client
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": True, "data": result}, curl_cmd=curl_cmd)
        
        # Validation
        assert result is not None, "Result should not be None"
        print(f"   ✓ Completed appointment: {appointment_id}")
        
        return result
        
    except EkaAPIError as e:
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": False, "error": {"message": str(e)}}, success=False, curl_cmd=curl_cmd)
        raise
    except Exception as e:
        r.log_error(e)
        raise


async def test_cancel_appointment(*args, **kwargs):
    """Test cancel_appointment API"""
    r = get_runner()
    await r.setup()
    
    appointment_id = kwargs.get("appointment_id", r.test_cancellation_appointment_id)
    cancel_data = kwargs.get("cancel_data", { "reason": "Test", "notes": "Testing" })
    
    if not appointment_id:
        print("   ⚠️  No appointment ID available, skipping test")
        return None
    
    r.log_request("cancel_appointment", appointment_id=appointment_id, cancel_data=cancel_data)
    
    try:
        result = await r.service.cancel_appointment(appointment_id=appointment_id, cancel_data=cancel_data)
        
        # Get curl command from client
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": True, "data": result}, curl_cmd=curl_cmd)
        
        # Validation
        assert result is not None, "Result should not be None"
        print(f"   ✓ Cancelled appointment: {appointment_id}")
        
        return result
        
    except EkaAPIError as e:
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": False, "error": {"message": str(e)}}, success=False, curl_cmd=curl_cmd)
        raise
    except Exception as e:
        r.log_error(e)
        raise


async def test_reschedule_appointment(*args, **kwargs):
    """Test reschedule_appointment API"""
    r = get_runner()
    await r.setup()
    
    appointment_id = kwargs.get("appointment_id", r.test_reschedule_appointment_id)
    doctor_id = kwargs.get("doctor_id", r.test_doctor_id)
    clinic_id = kwargs.get("clinic_id", r.test_clinic_id)
    patient_id = kwargs.get("patient_id", r.test_patient_id)

    # Calculate appointment time (2 days from now, 5:00 PM)
    appointment_date = datetime.now() + timedelta(days=2)
    appointment_date = appointment_date.replace(hour=17, minute=0, second=0, microsecond=0)
    start_timestamp = int(appointment_date.timestamp())
    end_timestamp = int((appointment_date + timedelta(minutes=30)).timestamp())


    appointment_data = kwargs.get("appointment_data", {
        "doctor_id": doctor_id,  # Use eka IDs, not partner IDs
        "clinic_id": clinic_id,
        "patient_id": patient_id,
        "appointment_details": {
            "start_time": start_timestamp,
            "end_time": end_timestamp,
            "mode": "INCLINIC"
        },
        "patient_details": {
            "designation": "Mr.",
            "first_name": "Test",
            "middle_name": "",
            "last_name": "Patient",
            "mobile": "+919999999999",
            "gender": "M",
            "dob": "1990-01-01",  # Required field
        }
    })
    
    if not appointment_id:
        print("   ⚠️  No appointment ID available, skipping test")
        return None
    
    r.log_request("reschedule_appointment", appointment_id=appointment_id, reschedule_data=appointment_data)
    
    try:
        result = await r.service.cancel_appointment(appointment_id=appointment_id, cancel_data={})

        # Get curl command from client
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": True, "data": result}, curl_cmd=curl_cmd)

        # Validation
        assert result is not None, "Result should not be None"
        print(f"   ✓ Cancelled appointment: {appointment_id}")

        result = await r.service.book_appointment(appointment_data=appointment_data)
        
        # Get curl command from client
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": True, "data": result}, curl_cmd=curl_cmd)
        
        # Validation
        assert result is not None, "Result should not be None"
        if isinstance(result, dict):
            appointment_id = result.get("appointment_id")
            print(f"   ✓ Booked appointment (ID: {appointment_id})")
        
        return result
        
    except EkaAPIError as e:
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": False, "error": {"message": str(e)}}, success=False, curl_cmd=curl_cmd)
        raise
    except Exception as e:
        r.log_error(e)
        raise


async def test_all(*args, **kwargs):
    """Run all appointment tools tests"""
    print("\n" + "=" * 70)
    print("🧪 Running ALL Appointment Tools Tests")
    print("=" * 70)
    
    results = []
    
    # Add default date range if not provided (last 7 days)
    if not kwargs.get("start_date") and not kwargs.get("patient_id"):
        kwargs["start_date"] = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        kwargs["end_date"] = datetime.now().strftime("%Y-%m-%d")
        print(f"\n💡 Using default date range: {kwargs['start_date']} to {kwargs['end_date']}")
    
    # Test 1: List appointments (to get an appointment ID)
    print("\n[1/5] Testing list_appointments...")
    try:
        result = await test_list_appointments(**kwargs)
        results.append(("list_appointments", True, None))
    except Exception as e:
        results.append(("list_appointments", False, str(e)))
    
    # Test 2: Get appointment details
    print("\n[2/5] Testing get_appointment_details...")
    try:
        result = await test_get_appointment_details()
        results.append(("get_appointment_details", True, None))
    except Exception as e:
        results.append(("get_appointment_details", False, str(e)))
    
    # Test 3: Get appointment slots (requires doctor_id and clinic_id)
    print("\n[3/5] Testing get_appointment_slots...")
    try:
        result = await test_get_appointment_slots(**kwargs)
        results.append(("get_appointment_slots", result is not None, None if result else "Missing IDs"))
    except Exception as e:
        results.append(("get_appointment_slots", False, str(e)))
    
    # Test 4: Get patient appointments (requires patient_id)
    print("\n[4/5] Testing get_patient_appointments...")
    try:
        result = await test_get_patient_appointments(**kwargs)
        results.append(("get_patient_appointments", result is not None, None if result else "Missing patient_id"))
    except Exception as e:
        results.append(("get_patient_appointments", False, str(e)))
    
    # Test 5: Write operations (optional - requires --test-write)
    if kwargs.get("test_write", False):
        print("\n[5/5] Testing write operations...")
        
        # Book appointment
        print("\n  [5a] Testing book_appointment...")
        try:
            result = await test_book_appointment(**kwargs)
            results.append(("book_appointment", result is not None, None if result else "Missing IDs"))
        except Exception as e:
            results.append(("book_appointment", False, str(e)))
        
        # Update appointment
        print("\n  [5b] Testing update_appointment...")
        try:
            result = await test_update_appointment()
            results.append(("update_appointment", True, None))
        except Exception as e:
            results.append(("update_appointment", False, str(e)))
    else:
        print("\n   ℹ️  Skipping write operations (book/update/complete/cancel/reschedule)")
        print("   💡 Use --test-write to include write operations")
        results.append(("book_appointment", None, "Skipped"))
        results.append(("update_appointment", None, "Skipped"))
        results.append(("complete_appointment", None, "Skipped"))
        results.append(("cancel_appointment", None, "Skipped"))
        results.append(("reschedule_appointment", None, "Skipped"))
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, success, _ in results if success is True)
    failed = sum(1 for _, success, _ in results if success is False)
    skipped = sum(1 for _, success, _ in results if success is None)
    
    for test_name, success, error in results:
        if success is True:
            print(f"✅ {test_name:35s} PASSED")
        elif success is False:
            print(f"❌ {test_name:35s} FAILED - {error}")
        else:
            print(f"⏭️  {test_name:35s} SKIPPED")
    
    print(f"\nTotal: {len(results)} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
    
    return results


# Dictionary mapping test names to test functions
TEST_FUNCTIONS = {
    "all": test_all,
    "list": test_list_appointments,
    "list_appointments": test_list_appointments,
    "get_details": test_get_appointment_details,
    "get_appointment_details": test_get_appointment_details,
    "get_slots": test_get_appointment_slots,
    "get_appointment_slots": test_get_appointment_slots,
    "get_patient_appts": test_get_patient_appointments,
    "get_patient_appointments": test_get_patient_appointments,
    "book": test_book_appointment,
    "book_appointment": test_book_appointment,
    "update": test_update_appointment,
    "update_appointment": test_update_appointment,
    "complete": test_complete_appointment,
    "complete_appointment": test_complete_appointment,
    "cancel": test_cancel_appointment,
    "cancel_appointment": test_cancel_appointment,
    "reschedule": test_reschedule_appointment,
    "reschedule_appointment": test_reschedule_appointment,
}


def main():
    """Main function to run specified test cases"""
    parser = argparse.ArgumentParser(
        description="Run eka-mcp-sdk Appointment Tools test cases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m tests.test_appointment_tools                                     # Run all read-only tests
  python -m tests.test_appointment_tools list get_details                    # Run specific tests
  python -m tests.test_appointment_tools all --test-write                    # Run all including write ops
  python -m tests.test_appointment_tools --list                              # List available tests
  python -m tests.test_appointment_tools --verbose                           # Run with detailed output
  python -m tests.test_appointment_tools get_slots --doctor-id <id> --clinic-id <id>
        """
    )
    
    parser.add_argument(
        "tests",
        nargs="*",
        help="Names of test cases to run (default: all read-only tests)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available test cases"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output with full request/response details"
    )
    parser.add_argument(
        "--test-write",
        action="store_true",
        help="Include write operations (book, update, complete, cancel, reschedule) in tests"
    )
    parser.add_argument(
        "--appointment-id",
        type=str,
        help="Appointment ID to use for tests"
    )
    parser.add_argument(
        "--doctor-id",
        type=str,
        help="Doctor ID for appointment tests"
    )
    parser.add_argument(
        "--clinic-id",
        type=str,
        help="Clinic ID for appointment tests"
    )
    parser.add_argument(
        "--patient-id",
        type=str,
        help="Patient ID for appointment tests"
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Date for appointment slot tests (YYYY-MM-DD)"
    )
    
    args = parser.parse_args()
    
    if args.list:
        print("\n📋 Available test cases:")
        print("=" * 50)
        for test_name in sorted(set(TEST_FUNCTIONS.keys())):
            print(f"  • {test_name}")
        print("\n💡 Usage: python -m tests.test_appointment_tools <test_name>")
        return
    
    # Initialize global runner with verbose setting
    global runner
    runner = TestRunner(verbose=args.verbose)
    
    # Set test IDs if provided
    if args.appointment_id:
        runner.test_appointment_id = args.appointment_id
    if args.doctor_id:
        runner.test_doctor_id = args.doctor_id
    if args.clinic_id:
        runner.test_clinic_id = args.clinic_id
    if args.patient_id:
        runner.test_patient_id = args.patient_id
    
    # If no tests specified, run all read-only tests
    if not args.tests:
        args.tests = ["all"]
    
    # Run specified tests
    for test_name in args.tests:
        if test_name in TEST_FUNCTIONS:
            print(f"\n{'=' * 70}")
            print(f"🧪 Running test: {test_name}")
            print(f"{'=' * 70}")
            
            try:
                # Prepare kwargs
                test_kwargs = {
                    "test_write": args.test_write,
                    "verbose": args.verbose,
                }
                
                if args.appointment_id:
                    test_kwargs["appointment_id"] = args.appointment_id
                if args.doctor_id:
                    test_kwargs["doctor_id"] = args.doctor_id
                if args.clinic_id:
                    test_kwargs["clinic_id"] = args.clinic_id
                if args.patient_id:
                    test_kwargs["patient_id"] = args.patient_id
                if args.date:
                    test_kwargs["date"] = args.date
                
                # Run test
                asyncio.run(TEST_FUNCTIONS[test_name](**test_kwargs))
                print(f"\n✅ Test '{test_name}' completed successfully")
                
            except EkaAPIError as e:
                print(f"\n❌ Test '{test_name}' failed with API error:")
                print(f"   Message: {e.message}")
                print(f"   Status: {e.status_code}")
                if e.error_code:
                    print(f"   Code: {e.error_code}")
            except Exception as e:
                print(f"\n❌ Test '{test_name}' failed with error: {str(e)}")
                if args.verbose:
                    import traceback
                    traceback.print_exc()
        else:
            print(f"\n❌ Unknown test case: {test_name}")
            print("💡 Use --list to see available test cases")


if __name__ == "__main__":
    main()
