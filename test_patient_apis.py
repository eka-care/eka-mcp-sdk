import asyncio
from fastmcp import Client
from eka_mcp_sdk.server import create_mcp_server

config = {
    "mcpServers": {
        "eka_mcp_sdk": {
            # Local stdio server using installed command
            "transport": "stdio",
            "command": "eka-mcp-server",
            "env": {
                "EKA_CLIENT_ID": "EC_174022407354131",
                "EKA_CLIENT_SECRET": "32d471f4-f0b9-4a6e-a4ba-1f22ad1a94c9",
                "EKA_API_KEY": "bf47bf1b-b1e6-4af7-b00d-fe48b9cd56e3",
                "EKA_API_BASE_URL": "https://api.eka.care",
                "LOG_LEVEL": "DEBUG"
            }
        }
    }
}

# In-memory server (ideal for testing)
client = Client(config)

async def main():
    async with client:
        print("🏓 Testing Patient API Updates...")
        
        # Test search_patients with new prefix-based search
        print("\n🔍 Testing search_patients with prefix search...")
        try:
            result = await client.call_tool("search_patients", {"prefix": "test"})
            print(f"✅ Search patients result: {result}")
        except Exception as e:
            print(f"⚠️  Search patients error: {e}")
        
        # Test list_patients with pagination
        print("\n📋 Testing list_patients with pagination...")
        try:
            result = await client.call_tool("list_patients", {"page_no": 1, "page_size": 10})
            print(f"✅ List patients result: {result}")
        except Exception as e:
            print(f"⚠️  List patients error: {e}")
        
        # Test get_patient_by_mobile with new endpoint
        print("\n📱 Testing get_patient_by_mobile...")
        try:
            result = await client.call_tool("get_patient_by_mobile", {"mobile": "+911234567890"})
            print(f"✅ Get patient by mobile result: {result}")
        except Exception as e:
            print(f"⚠️  Get patient by mobile error: {e}")
            
        print("\n🎉 Patient API test completed!")

asyncio.run(main())