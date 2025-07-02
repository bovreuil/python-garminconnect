#!/usr/bin/env python3
"""
Debug script to see what's being imported.
"""

import os
import sys

# Add the garminconnect library to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'garminconnect'))

print("Testing import...")

try:
    import garminconnect
    print(f"✅ Imported garminconnect from: {garminconnect.__file__}")
    
    # Check if it's the local version
    if 'python-garminconnect' in garminconnect.__file__:
        print("✅ This is the local version")
    else:
        print("❌ This is NOT the local version")
    
    # Check the Garmin class
    Garmin = garminconnect.Garmin
    print(f"✅ Garmin class from: {Garmin.__module__}")
    
    # Check the login method
    import inspect
    sig = inspect.signature(Garmin.login)
    print(f"✅ Login method signature: {sig}")
    
    # Try to create an instance
    api = Garmin(
        email="test@example.com",
        password="test",
        return_on_mfa=True
    )
    print("✅ Successfully created instance")
    
    # Check the instance's login method
    sig2 = inspect.signature(api.login)
    print(f"✅ Instance login method signature: {sig2}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc() 