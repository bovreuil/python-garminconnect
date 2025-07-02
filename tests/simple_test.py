#!/usr/bin/env python3
"""
Simple test to debug garminconnect import and basic functionality.
"""

import os
import sys

# Add the garminconnect library to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'garminconnect'))

print("Testing import...")

try:
    from garminconnect import Garmin
    print("✅ Successfully imported Garmin class")
    
    # Test creating an instance
    api = Garmin(
        email="test@example.com",
        password="test",
        return_on_mfa=True
    )
    print("✅ Successfully created Garmin instance with return_on_mfa=True")
    
    # Check the login method signature
    import inspect
    sig = inspect.signature(api.login)
    print(f"✅ Login method signature: {sig}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc() 