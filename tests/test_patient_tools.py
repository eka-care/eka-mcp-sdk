"""
Test suite for Patient Tools APIs in eka-mcp-sdk

This test suite provides comprehensive testing for patient management APIs including:
- Search patients
- Get patient details (basic and comprehensive)
- List patients
- Add patient
- Update patient
- Archive patient
- Get patient by mobile

Usage:
    # Run all tests
    python -m tests.test_patient_tools

    # Run specific tests
    python -m tests.test_patient_tools search list_patients

    # List available tests
    python -m tests.test_patient_tools --list

    # Run with detailed output
    python -m tests.test_patient_tools --verbose

Requirements:
    - .env file with valid EKA_CLIENT_ID and EKA_CLIENT_SECRET
    - Active OAuth tokens (will prompt for login if needed)
"""

import argparse
import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Any, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from eka_mcp_sdk.clients.doctor_tools_client import DoctorToolsClient
from eka_mcp_sdk.core.patient_service import PatientService
from eka_mcp_sdk.auth.models import EkaAPIError
from eka_mcp_sdk.config.settings import EkaSettings


class TestRunner:
    """Test runner with logging and error handling"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.settings = EkaSettings()
        self.client: Optional[DoctorToolsClient] = None
        self.service: Optional[PatientService] = None
        self.test_patient_id: Optional[str] = None
        
    async def setup(self):
        """Initialize client and service"""
        print("\n" + "=" * 70)
        print("🔧 Setting up test environment")
        print("=" * 70)
        
        # Initialize client (will handle OAuth flow)
        self.client = DoctorToolsClient()
        self.service = PatientService(self.client)
        
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
                    summary_keys = ['oid', 'status', 'message', 'currPageMeta', 'patients']
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


async def test_search_patients(*args, **kwargs):
    """Test search_patients API"""
    r = get_runner()
    await r.setup()
    
    prefix = kwargs.get("prefix", "test")
    limit = kwargs.get("limit", 10)
    
    r.log_request("search_patients", prefix=prefix, limit=limit)
    
    try:
        result = await r.service.search_patients(prefix=prefix, limit=limit)
        
        # Get curl command from client
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": True, "data": result}, curl_cmd=curl_cmd)
        
        # Validation
        assert result is not None, "Result should not be None"
        print(f"   ✓ Found patients with prefix '{prefix}'")
        
        return result
        
    except EkaAPIError as e:
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": False, "error": {"message": str(e)}}, success=False, curl_cmd=curl_cmd)
        raise
    except Exception as e:
        r.log_error(e)
        raise


async def test_list_patients(*args, **kwargs):
    """Test list_patients API"""
    r = get_runner()
    await r.setup()
    
    page_no = kwargs.get("page_no", 1)
    page_size = kwargs.get("page_size", 50)
    
    r.log_request("list_patients", page_no=page_no, page_size=page_size)
    
    try:
        result = await r.service.list_patients(page_no=page_no, page_size=page_size)
        
        # Get curl command from client
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": True, "data": result}, curl_cmd=curl_cmd)
        
        # Validation
        assert result is not None, "Result should not be None"
        if isinstance(result, dict):
            data = result.get("data", [])
            print(f"   ✓ Retrieved {len(data)} patients (Page {page_no})")
            
            # Store first patient ID for other tests
            if data and isinstance(data, list) and len(data) > 0:
                r.test_patient_id = data[0].get("oid")
                if r.test_patient_id:
                    print(f"   ℹ️  Stored patient ID for subsequent tests: {r.test_patient_id}")
        
        return result
        
    except EkaAPIError as e:
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": False, "error": {"message": str(e)}}, success=False, curl_cmd=curl_cmd)
        raise
    except Exception as e:
        r.log_error(e)
        raise


async def test_get_patient_basic(*args, **kwargs):
    """Test get_patient_details_basic API"""
    r = get_runner()
    await r.setup()
    
    # Get patient ID from kwargs or use stored test patient ID
    patient_id = kwargs.get("patient_id", r.test_patient_id)
    
    if not patient_id:
        # Try to get a patient ID first
        print("   ℹ️  No patient ID provided, fetching from list_patients...")
        list_result = await test_list_patients(page_no=1, page_size=1)
        if isinstance(list_result, dict):
            data = list_result.get("data", [])
            if data and len(data) > 0:
                patient_id = data[0].get("oid")
    
    if not patient_id:
        print("   ⚠️  No patient ID available, skipping test")
        return None
    
    r.log_request("get_patient_details_basic", patient_id=patient_id)
    
    try:
        result = await r.service.get_patient_details_basic(patient_id=patient_id)
        
        # Get curl command from client
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": True, "data": result}, curl_cmd=curl_cmd)
        
        # Validation
        assert result is not None, "Result should not be None"
        if isinstance(result, dict):
            name = result.get("fln") or result.get("fn", "Unknown")
            print(f"   ✓ Retrieved patient: {name} (ID: {patient_id})")
        
        return result
        
    except EkaAPIError as e:
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": False, "error": {"message": str(e)}}, success=False, curl_cmd=curl_cmd)
        raise
    except Exception as e:
        r.log_error(e)
        raise


async def test_get_patient_comprehensive(*args, **kwargs):
    """Test get_comprehensive_patient_profile API"""
    r = get_runner()
    await r.setup()
    
    # Get patient ID from kwargs or use stored test patient ID
    patient_id = kwargs.get("patient_id", r.test_patient_id)
    include_appointments = kwargs.get("include_appointments", True)
    appointment_limit = kwargs.get("appointment_limit", 10)
    
    if not patient_id:
        # Try to get a patient ID first
        print("   ℹ️  No patient ID provided, fetching from list_patients...")
        list_result = await test_list_patients(page_no=1, page_size=1)
        if isinstance(list_result, dict):
            data = list_result.get("data", [])
            if data and len(data) > 0:
                patient_id = data[0].get("oid")
    
    if not patient_id:
        print("   ⚠️  No patient ID available, skipping test")
        return None
    
    r.log_request(
        "get_comprehensive_patient_profile",
        patient_id=patient_id,
        include_appointments=include_appointments,
        appointment_limit=appointment_limit
    )
    
    try:
        result = await r.service.get_comprehensive_patient_profile(
            patient_id=patient_id,
            include_appointments=include_appointments,
            appointment_limit=appointment_limit
        )
        
        # Get curl command from client
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": True, "data": result}, curl_cmd=curl_cmd)
        
        # Validation
        assert result is not None, "Result should not be None"
        if isinstance(result, dict):
            profile = result.get("profile", {})
            appointments = result.get("appointments", [])
            name = profile.get("fln") or profile.get("fn", "Unknown")
            print(f"   ✓ Retrieved comprehensive profile: {name}")
            print(f"   ✓ Appointments: {len(appointments)}")
        
        return result
        
    except EkaAPIError as e:
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": False, "error": {"message": str(e)}}, success=False, curl_cmd=curl_cmd)
        raise
    except Exception as e:
        r.log_error(e)
        raise


async def test_get_patient_by_mobile(*args, **kwargs):
    """Test get_patient_by_mobile API"""
    r = get_runner()
    await r.setup()
    
    mobile = kwargs.get("mobile")
    full_profile = kwargs.get("full_profile", False)
    
    if not mobile:
        print("   ⚠️  No mobile number provided, skipping test")
        print("   💡 Usage: python -m tests.test_patient_tools get_by_mobile --mobile +919876543210")
        return None
    
    r.log_request("get_patient_by_mobile", mobile=mobile, full_profile=full_profile)
    
    try:
        result = await r.service.get_patient_by_mobile(mobile=mobile, full_profile=full_profile)
        
        # Get curl command from client
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": True, "data": result}, curl_cmd=curl_cmd)
        
        # Validation
        assert result is not None, "Result should not be None"
        if isinstance(result, list):
            print(f"   ✓ Found {len(result)} patient(s) with mobile: {mobile}")
        elif isinstance(result, dict):
            print(f"   ✓ Found patient with mobile: {mobile}")
        
        return result
        
    except EkaAPIError as e:
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": False, "error": {"message": str(e)}}, success=False, curl_cmd=curl_cmd)
        raise
    except Exception as e:
        r.log_error(e)
        raise


async def test_add_patient(*args, **kwargs):
    """Test add_patient API"""
    r = get_runner()
    await r.setup()
    
    # Use provided data or create test data
    patient_data = kwargs.get("patient_data", {
        "fln": "Test Patient",
        "dob": "1990-01-01",
        "gen": "M",
        "mobile": "+919999999999",
        "email": "test@example.com"
    })
    
    r.log_request("add_patient", patient_data=patient_data)
    
    try:
        result = await r.service.add_patient(patient_data=patient_data)
        
        # Get curl command from client
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": True, "data": result}, curl_cmd=curl_cmd)
        
        # Validation
        assert result is not None, "Result should not be None"
        if isinstance(result, dict):
            patient_id = result.get("oid")
            name = result.get("fln") or result.get("fn", "Unknown")
            print(f"   ✓ Created patient: {name} (ID: {patient_id})")
            
            # Store for cleanup
            r.test_patient_id = patient_id
        
        return result
        
    except EkaAPIError as e:
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": False, "error": {"message": str(e)}}, success=False, curl_cmd=curl_cmd)
        raise
    except Exception as e:
        r.log_error(e)
        raise


async def test_update_patient(*args, **kwargs):
    """Test update_patient API"""
    r = get_runner()
    await r.setup()
    
    patient_id = kwargs.get("patient_id", r.test_patient_id)
    update_data = kwargs.get("update_data", {
        "email": f"updated_{datetime.now().timestamp()}@example.com"
    })
    
    if not patient_id:
        print("   ⚠️  No patient ID available, skipping test")
        return None
    
    r.log_request("update_patient", patient_id=patient_id, update_data=update_data)
    
    try:
        result = await r.service.update_patient(patient_id=patient_id, update_data=update_data)
        
        # Get curl command from client
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": True, "data": result}, curl_cmd=curl_cmd)
        
        # Validation
        assert result is not None, "Result should not be None"
        print(f"   ✓ Updated patient: {patient_id}")
        
        return result
        
    except EkaAPIError as e:
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": False, "error": {"message": str(e)}}, success=False, curl_cmd=curl_cmd)
        raise
    except Exception as e:
        r.log_error(e)
        raise


async def test_archive_patient(*args, **kwargs):
    """Test archive_patient API"""
    r = get_runner()
    await r.setup()
    
    patient_id = kwargs.get("patient_id", r.test_patient_id)
    archive = kwargs.get("archive", True)
    
    if not patient_id:
        print("   ⚠️  No patient ID available, skipping test")
        return None
    
    r.log_request("archive_patient", patient_id=patient_id, archive=archive)
    
    try:
        result = await r.service.archive_patient(patient_id=patient_id, archive=archive)
        
        # Get curl command from client
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": True, "data": result}, curl_cmd=curl_cmd)
        
        # Validation
        assert result is not None, "Result should not be None"
        action = "Archived" if archive else "Unarchived"
        print(f"   ✓ {action} patient: {patient_id}")
        
        return result
        
    except EkaAPIError as e:
        curl_cmd = r.client.last_curl_command if r.client else None
        r.log_response({"success": False, "error": {"message": str(e)}}, success=False, curl_cmd=curl_cmd)
        raise
    except Exception as e:
        r.log_error(e)
        raise


async def test_all(*args, **kwargs):
    """Run all patient tools tests"""
    print("\n" + "=" * 70)
    print("🧪 Running ALL Patient Tools Tests")
    print("=" * 70)
    
    results = []
    
    # Test 1: List patients (to get a patient ID)
    print("\n[1/7] Testing list_patients...")
    try:
        result = await test_list_patients(page_no=1, page_size=10)
        results.append(("list_patients", True, None))
    except Exception as e:
        results.append(("list_patients", False, str(e)))
    
    # Test 2: Search patients
    print("\n[2/7] Testing search_patients...")
    try:
        result = await test_search_patients(prefix="test", limit=5)
        results.append(("search_patients", True, None))
    except Exception as e:
        results.append(("search_patients", False, str(e)))
    
    # Test 3: Get patient basic
    print("\n[3/7] Testing get_patient_details_basic...")
    try:
        result = await test_get_patient_basic()
        results.append(("get_patient_basic", True, None))
    except Exception as e:
        results.append(("get_patient_basic", False, str(e)))
    
    # Test 4: Get patient comprehensive
    print("\n[4/7] Testing get_comprehensive_patient_profile...")
    try:
        result = await test_get_patient_comprehensive(include_appointments=True, appointment_limit=5)
        results.append(("get_patient_comprehensive", True, None))
    except Exception as e:
        results.append(("get_patient_comprehensive", False, str(e)))
    
    # Test 5: Add patient (optional - creates data)
    if kwargs.get("test_write", False):
        print("\n[5/7] Testing add_patient...")
        try:
            result = await test_add_patient()
            results.append(("add_patient", True, None))
        except Exception as e:
            results.append(("add_patient", False, str(e)))
        
        # Test 6: Update patient
        print("\n[6/7] Testing update_patient...")
        try:
            result = await test_update_patient()
            results.append(("update_patient", True, None))
        except Exception as e:
            results.append(("update_patient", False, str(e)))
        
        # Test 7: Archive patient
        print("\n[7/7] Testing archive_patient...")
        try:
            result = await test_archive_patient()
            results.append(("archive_patient", True, None))
        except Exception as e:
            results.append(("archive_patient", False, str(e)))
    else:
        print("\n   ℹ️  Skipping write operations (add/update/archive)")
        print("   💡 Use --test-write to include write operations")
        results.append(("add_patient", None, "Skipped"))
        results.append(("update_patient", None, "Skipped"))
        results.append(("archive_patient", None, "Skipped"))
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, success, _ in results if success is True)
    failed = sum(1 for _, success, _ in results if success is False)
    skipped = sum(1 for _, success, _ in results if success is None)
    
    for test_name, success, error in results:
        if success is True:
            print(f"✅ {test_name:30s} PASSED")
        elif success is False:
            print(f"❌ {test_name:30s} FAILED - {error}")
        else:
            print(f"⏭️  {test_name:30s} SKIPPED")
    
    print(f"\nTotal: {len(results)} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
    
    return results


# Dictionary mapping test names to test functions
TEST_FUNCTIONS = {
    "all": test_all,
    "search": test_search_patients,
    "search_patients": test_search_patients,
    "list": test_list_patients,
    "list_patients": test_list_patients,
    "get_basic": test_get_patient_basic,
    "get_patient_basic": test_get_patient_basic,
    "get_comprehensive": test_get_patient_comprehensive,
    "get_patient_comprehensive": test_get_patient_comprehensive,
    "get_by_mobile": test_get_patient_by_mobile,
    "add": test_add_patient,
    "add_patient": test_add_patient,
    "update": test_update_patient,
    "update_patient": test_update_patient,
    "archive": test_archive_patient,
    "archive_patient": test_archive_patient,
}


def main():
    """Main function to run specified test cases"""
    parser = argparse.ArgumentParser(
        description="Run eka-mcp-sdk Patient Tools test cases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m tests.test_patient_tools                      # Run all read-only tests
  python -m tests.test_patient_tools search list          # Run specific tests
  python -m tests.test_patient_tools all --test-write     # Run all including write ops
  python -m tests.test_patient_tools --list               # List available tests
  python -m tests.test_patient_tools --verbose            # Run with detailed output
  python -m tests.test_patient_tools get_by_mobile --mobile +919876543210
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
        help="Include write operations (add, update, archive) in tests"
    )
    parser.add_argument(
        "--patient-id",
        type=str,
        help="Patient ID to use for tests"
    )
    parser.add_argument(
        "--mobile",
        type=str,
        help="Mobile number for get_by_mobile test (format: +919876543210)"
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="test",
        help="Search prefix for search_patients test"
    )
    
    args = parser.parse_args()
    
    if args.list:
        print("\n📋 Available test cases:")
        print("=" * 50)
        for test_name in sorted(set(TEST_FUNCTIONS.keys())):
            print(f"  • {test_name}")
        print("\n💡 Usage: python -m tests.test_patient_tools <test_name>")
        return
    
    # Initialize global runner with verbose setting
    global runner
    runner = TestRunner(verbose=args.verbose)
    
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
                
                if args.patient_id:
                    test_kwargs["patient_id"] = args.patient_id
                if args.mobile:
                    test_kwargs["mobile"] = args.mobile
                if args.prefix:
                    test_kwargs["prefix"] = args.prefix
                
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
