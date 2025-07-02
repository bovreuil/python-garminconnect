#!/usr/bin/env python3
"""
Simple test to verify garth login works directly.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('test.env')

# Get credentials
email = os.getenv('GARMIN_EMAIL')
password = os.getenv('GARMIN_PASSWORD')

print(f"Testing with email: {email}")
print(f"Password length: {len(password) if password else 0}")

try:
    import garth
    
    # Create a garth client
    client = garth.Client()
    
    print("🔄 Attempting direct garth login...")
    
    # Try to login directly with garth
    client.login(email, password)
    
    # Check if login was successful by looking at the tokens
    if client.oauth1_token and client.oauth2_token:
        print("✅ Direct garth login successful!")
        print(f"OAuth1 token: {client.oauth1_token.oauth_token[:10]}...")
        print(f"OAuth2 token: {client.oauth2_token.access_token[:10]}...")
    else:
        print("❌ Login failed - no tokens found")
        print(f"OAuth1 token: {client.oauth1_token}")
        print(f"OAuth2 token: {client.oauth2_token}")
    
except Exception as e:
    print(f"❌ Direct garth login failed: {e}")
    import traceback
    traceback.print_exc() 