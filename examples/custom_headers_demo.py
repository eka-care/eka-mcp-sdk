#!/usr/bin/env python3
"""
Custom Headers Demo - Eka.care MCP SDK

This example demonstrates how to send custom HTTP headers with API requests.
The custom headers are set once on the client and automatically included 
in all API calls.

Setup:
1. Configure your .env file with credentials
2. python examples/custom_headers_demo.py
"""

import asyncio
import logging
from eka_mcp_sdk.clients.eka_emr_client import EkaEMRClient
from eka_mcp_sdk.config.settings import settings

# Configure logging to see headers in debug mode
logging.basicConfig(level=logging.INFO)


async def demo_without_custom_headers():
    """Demonstrate API calls without custom headers."""
    print("\n📡 API Call WITHOUT Custom Headers")
    print("="*50)
    
    client = EkaEMRClient()
    print(f"Client custom headers: {client._custom_headers}")
    
    try:
        # This call will only have standard headers (Authorization, client-id, etc.)
        result = await client.search_patients(prefix="test", limit=1)
        print("✅ API call successful")
        print(f"Result type: {type(result)}")
    except Exception as e:
        print(f"Expected result (no auth): {str(e)[:80]}...")
    
    await client.close()


async def demo_with_custom_headers():
    """Demonstrate API calls with custom headers."""
    print("\n🎯 API Call WITH Custom Headers")
    print("="*50)
    
    # Define custom headers
    custom_headers = {
        "X-Source": "MyHealthApp",
        "X-App-Version": "2.1.0", 
        "X-Request-ID": "req-12345-demo",
        "X-User-Context": "mobile-app",
        "X-Feature-Flag": "new-patient-search"
    }
    
    print(f"Custom headers to include:")
    for key, value in custom_headers.items():
        print(f"  {key}: {value}")
    
    # Create client with custom headers
    client = EkaEMRClient(custom_headers=custom_headers)
    print(f"\nClient initialized with {len(client._custom_headers)} custom headers")
    
    try:
        # ALL API calls through this client will automatically include these headers
        result = await client.search_patients(prefix="test", limit=1)
        print("✅ API call successful with custom headers")
        print(f"Result type: {type(result)}")
        
        # Another API call - same headers automatically included
        result2 = await client.get_business_entities()
        print("✅ Second API call also includes custom headers")
        
    except Exception as e:
        print(f"Expected result (no auth): {str(e)[:80]}...")
    
    await client.close()


async def demo_different_clients_different_headers():
    """Demonstrate multiple clients with different custom headers."""
    print("\n🔄 Multiple Clients with Different Headers")
    print("="*50)
    
    # Client 1: Mobile app headers
    mobile_headers = {
        "X-Source": "MobileApp",
        "X-Platform": "iOS",
        "X-App-Version": "1.2.3"
    }
    
    # Client 2: Web app headers  
    web_headers = {
        "X-Source": "WebApp",
        "X-Platform": "Browser", 
        "X-Session-ID": "web-session-456"
    }
    
    # Client 3: Admin dashboard headers
    admin_headers = {
        "X-Source": "AdminDashboard",
        "X-User-Role": "admin",
        "X-Admin-Level": "super"
    }
    
    mobile_client = EkaEMRClient(custom_headers=mobile_headers)
    web_client = EkaEMRClient(custom_headers=web_headers)
    admin_client = EkaEMRClient(custom_headers=admin_headers)
    
    print(f"Mobile client headers: {mobile_client._custom_headers}")
    print(f"Web client headers: {web_client._custom_headers}")  
    print(f"Admin client headers: {admin_client._custom_headers}")
    
    # Each client will send its own set of custom headers
    print("\n✅ Each client maintains its own custom headers")
    print("✅ Headers are automatically included in all requests")
    
    await mobile_client.close()
    await web_client.close()
    await admin_client.close()


async def demo_header_use_cases():
    """Demonstrate common custom header use cases."""
    print("\n💡 Common Custom Header Use Cases")
    print("="*50)
    
    use_cases = {
        "Request Tracking": {
            "X-Request-ID": "unique-request-id-123",
            "X-Correlation-ID": "trace-correlation-456"
        },
        
        "Application Context": {
            "X-Source": "PatientPortal",
            "X-App-Version": "3.2.1",
            "X-Platform": "Android"
        },
        
        "Feature Flags": {
            "X-Feature-NewUI": "enabled",
            "X-Feature-BetaSearch": "disabled",
            "X-Experiment-Group": "treatment-a"
        },
        
        "User Context": {
            "X-User-Type": "doctor",
            "X-Clinic-ID": "clinic-789",
            "X-Session-Context": "consultation-mode"
        },
        
        "Analytics & Monitoring": {
            "X-Analytics-ID": "analytics-session-999",
            "X-Monitoring-Tag": "production",
            "X-Performance-Trace": "enabled"
        }
    }
    
    for use_case, headers in use_cases.items():
        print(f"\n📋 {use_case}:")
        for key, value in headers.items():
            print(f"  {key}: {value}")
        
        # You could create a client for each use case
        client = EkaEMRClient(custom_headers=headers)
        print(f"  ✅ Client ready with {len(client._custom_headers)} headers")
        await client.close()


async def main():
    """Main demonstration function."""
    print("🏥 Eka.care MCP SDK - Custom Headers Demo")
    print("="*60)
    
    if not settings.client_id:
        print("ℹ️  Note: No authentication configured. API calls will show authentication errors,")
        print("   but custom headers functionality will be demonstrated.")
    
    await demo_without_custom_headers()
    await demo_with_custom_headers()
    await demo_different_clients_different_headers()
    await demo_header_use_cases()
    
    print("\n" + "="*60)
    print("✨ Custom Headers Demo Complete!")
    print("\n💡 Key Points:")
    print("  • Custom headers are set once during client initialization")
    print("  • All API calls automatically include the custom headers")
    print("  • Different clients can have different custom headers")
    print("  • Headers are merged with standard authentication headers")
    print("  • Useful for tracking, analytics, feature flags, and more")


if __name__ == "__main__":
    asyncio.run(main())