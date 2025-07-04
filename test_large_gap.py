#!/usr/bin/env python3
"""
Test script to verify the large gap fix works with realistic scenarios
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import TRIMPCalculator

def test_large_gap_scenario():
    """Test the 284-minute gap scenario mentioned by the user."""
    
    # Initialize calculator
    calculator = TRIMPCalculator(resting_hr=48, max_hr=167)
    
    print("=== Testing Large Gap Scenario (284 minutes) ===")
    
    # Scenario: 284-minute gap followed by HR 99, then 1-second intervals
    # Timestamps in milliseconds
    large_gap_data = {
        'heartRateValues': [
            [1000, 120],           # First reading
            [2000, 125],           # Second reading
            [17040000, 99],        # Reading after 284-minute gap (17040000 - 2000 = 17038000 ms = 284.6 minutes)
            [17041000, 110],       # Next reading (1 second later)
            [17042000, 115]        # Next reading (1 second later)
        ]
    }
    
    results = calculator.bucket_heart_rates(large_gap_data)
    print(f"With 284-minute gap: TRIMP={results['total_trimp']:.2f}, Minutes={sum(bucket['minutes'] for bucket in results['presentation_buckets'].values()):.2f}")
    
    # Compare with same data but no gap
    no_gap_data = {
        'heartRateValues': [
            [1000, 120],           # First reading
            [2000, 125],           # Second reading
            [3000, 99],            # No gap
            [4000, 110],           # Next reading
            [5000, 115]            # Next reading
        ]
    }
    
    results_no_gap = calculator.bucket_heart_rates(no_gap_data)
    print(f"Without gap: TRIMP={results_no_gap['total_trimp']:.2f}, Minutes={sum(bucket['minutes'] for bucket in results_no_gap['presentation_buckets'].values()):.2f}")
    
    print(f"Difference: TRIMP={results['total_trimp'] - results_no_gap['total_trimp']:.2f}, Minutes={sum(bucket['minutes'] for bucket in results['presentation_buckets'].values()) - sum(bucket['minutes'] for bucket in results_no_gap['presentation_buckets'].values()):.2f}")
    
    # The large gap should result in lower or equal TRIMP/minutes
    if results['total_trimp'] <= results_no_gap['total_trimp']:
        print("✅ SUCCESS: Large gap correctly reduced or did not inflate TRIMP calculation")
    else:
        print("❌ FAILURE: Large gap increased TRIMP calculation")

if __name__ == "__main__":
    test_large_gap_scenario() 