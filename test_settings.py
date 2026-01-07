#!/usr/bin/env python3

import os
from eka_mcp_sdk.config.settings import EkaSettings

print("Current working directory:", os.getcwd())
print("Environment variables with EKA_ prefix:")
for key, value in os.environ.items():
    if key.startswith("EKA_"):
        print(f"  {key}={value}")

print("\nTrying to load settings...")
try:
    settings = EkaSettings()
    print("Settings loaded successfully!")
    print(f"Client ID: {settings.eka_client_id}")
    print(f"Client Secret: {settings.eka_client_secret[:10]}...")
    print(f"API Key: {settings.eka_api_key[:10] if settings.eka_api_key else 'None'}...")
    print(f"API Base URL: {settings.eka_api_base_url}")
except Exception as e:
    print(f"Error loading settings: {e}")
    print(f"Error type: {type(e)}")