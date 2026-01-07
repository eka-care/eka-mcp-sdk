#!/usr/bin/env python3
"""
Eka.care MCP SDK - Direct Usage Example

This example demonstrates how to use the Eka.care MCP SDK clients directly
without the MCP protocol layer. It shows both authentication methods and
various API operations.

Setup:
1. Copy .env.example to .env and configure your credentials
2. pip install -e .
3. python examples/direct_usage.py
"""

import asyncio
import json
from typing import Dict, Any
import logging

from eka_mcp_sdk.clients.eka_emr_client import EkaEMRClient
from eka_mcp_sdk.auth.models import EkaAPIError
from eka_mcp_sdk.config.settings import EkaSettings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_result(title: str, result: Any, max_items: int = 3):
    """Helper function to print API results in a readable format."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    
    if isinstance(result, dict):
        if 'success' in result and result['success']:
            data = result.get('data', {})
            if isinstance(data, list):
                print(f"Found {len(data)} items:")
                for i, item in enumerate(data[:max_items]):
                    print(f"  {i+1}. {item.get('name', item.get('firstName', str(item)[:100]))}")
                if len(data) > max_items:
                    print(f"  ... and {len(data) - max_items} more items")
            else:
                print(json.dumps(data, indent=2)[:500] + "..." if len(str(data)) > 500 else json.dumps(data, indent=2))
        else:
            print(f"Error: {result.get('error', {}).get('message', 'Unknown error')}")
    else:
        print(json.dumps(result, indent=2)[:500] + "..." if len(str(result)) > 500 else json.dumps(result, indent=2))


async def demo_client_credentials_auth():
    """Demonstrate usage with client credentials authentication (uses file storage)."""
    print("\n🔑 CLIENT CREDENTIALS AUTHENTICATION")
    print("Uses EKA_CLIENT_ID and EKA_CLIENT_SECRET from .env")
    print("Tokens are automatically stored and refreshed")
    
    try:
        # Create client without external token - uses client credentials
        client = EkaEMRClient()
        
        # Test basic patient search
        result = await client.search_patients(
            prefix="+91",  # Search by phone prefix
            limit=5
        )
        print_result("Patient Search (by phone prefix)", result)
        
        # Test business entities
        result = await client.get_business_entities()
        print_result("Business Entities (Doctors & Clinics)", result)
        
        # Close the client
        await client.close()
        
    except EkaAPIError as e:
        print(f"❌ API Error: {e.message}")
        if e.status_code:
            print(f"   Status Code: {e.status_code}")
        if e.error_code:
            print(f"   Error Code: {e.error_code}")
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")


async def demo_external_token_auth():
    """Demonstrate usage with external access token (no file storage)."""
    print("\n🎯 EXTERNAL TOKEN AUTHENTICATION") 
    print("Uses provided access token directly")
    print("No file storage or token refresh")
    
    # This would use a token from your external auth system
    external_token = "your_external_access_token_here"
    
    try:
        # Create client with external token - no storage used
        client = EkaEMRClient(access_token=external_token)
        
        print(f"📝 Using external token: {external_token[:20]}...")
        print(f"📁 File storage disabled: {client._auth_manager._storage is None}")
        
        # This would fail with the demo token, but shows the pattern
        # In real usage, you'd provide a valid token
        
        await client.close()
        print("✅ External token authentication configured (demo token used)")
        
    except EkaAPIError as e:
        print(f"⚠️  Expected error with demo token: {e.message}")
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")


async def demo_patient_operations():
    """Demonstrate various patient-related operations."""
    print("\n👥 PATIENT OPERATIONS")
    
    try:
        client = EkaEMRClient()
        
        # Search patients by name prefix
        result = await client.search_patients(prefix="Test", limit=3)
        print_result("Search Patients by Name", result)
        
        # Search patients by mobile
        result = await client.get_patient_by_mobile("+919999999999")
        print_result("Get Patient by Mobile", result)
        
        # If we had a patient ID, we could get details
        # patient_id = "some_patient_id"
        # result = await client.get_patient_details(patient_id)
        # print_result("Patient Details", result)
        
        await client.close()
        
    except EkaAPIError as e:
        print(f"❌ API Error: {e.message}")
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")


async def demo_appointment_operations():
    """Demonstrate appointment-related operations."""
    print("\n📅 APPOINTMENT OPERATIONS")
    
    try:
        client = EkaEMRClient()
        
        # Get business entities first to find doctor and clinic IDs
        entities_result = await client.get_business_entities()
        print_result("Business Entities", entities_result)
        
        # If we have valid IDs, we could demo appointment slots
        # doctor_id = "some_doctor_id"
        # clinic_id = "some_clinic_id"
        # date = "2024-12-04"
        
        # result = await client.get_appointment_slots(doctor_id, clinic_id, date)
        # print_result("Available Appointment Slots", result)
        
        # Get appointments with filters
        result = await client.get_appointments(page_no=0)
        print_result("Recent Appointments", result)
        
        await client.close()
        
    except EkaAPIError as e:
        print(f"❌ API Error: {e.message}")
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")


async def demo_settings_configuration():
    """Demonstrate settings and configuration options."""
    print("\n⚙️  SETTINGS CONFIGURATION")
    
    # Show current settings
    settings = EkaSettings()
    print(f"API Base URL: {settings.api_base_url}")
    print(f"Client ID: {settings.client_id}")
    print(f"Client Secret: {'***' if settings.client_secret else 'Not set'}")
    print(f"API Key: {'***' if settings.api_key else 'Not set'}")
    print(f"Token Storage Dir: {settings.token_storage_dir or 'Default (~/.eka_mcp)'}")
    print(f"Log Level: {settings.log_level}")


async def main():
    """Main demo function."""
    print("🏥 Eka.care MCP SDK - Direct Usage Demo")
    print("="*60)
    
    # Show configuration
    await demo_settings_configuration()
    
    # Demo both authentication methods
    await demo_client_credentials_auth()
    await demo_external_token_auth()
    
    # Demo various API operations
    await demo_patient_operations()
    await demo_appointment_operations()
    
    print(f"\n{'='*60}")
    print("✨ Demo completed!")
    print("💡 Tip: Check the logs for detailed HTTP request/response information")
    print("📖 For more examples, see: examples/mcp_usage.py and examples/crewai_usage.py")


if __name__ == "__main__":
    asyncio.run(main())