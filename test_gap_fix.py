#!/usr/bin/env python3
"""
Test script to verify the gap detection fix in TRIMP calculations
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import TRIMPCalculator

def test_gap_detection():
    """Test that large gaps in HR data are properly handled."""
    
    # Initialize calculator
    calculator = TRIMPCalculator(resting_hr=48, max_hr=167)
    
    print("=== Testing Gap Detection in TRIMP Calculation ===")
    
    # Test case 1: Normal HR data without gaps
    normal_data = {
        'heartRateValues': [
            [1000, 120],   # 1 second intervals
            [2000, 125],
            [3000, 130],
            [4000, 135],
            [5000, 140]
        ]
    }
    
    print("\n1. Normal HR data (no gaps):")
    results = calculator.bucket_heart_rates(normal_data)
    print(f"   Total TRIMP: {results['total_trimp']:.2f}")
    print(f"   Total minutes: {sum(bucket['minutes'] for bucket in results['presentation_buckets'].values()):.2f}")
    
    # Test case 2: HR data with a large gap (watch taken off) - 400 seconds gap
    gap_data = {
        'heartRateValues': [
            [1000, 120],   # Normal reading
            [2000, 125],   # Normal reading
            [402000, 130], # Large gap (400 seconds) - should be skipped
            [403000, 135], # Normal reading after gap
            [404000, 140]  # Normal reading
        ]
    }
    
    print("\n2. HR data with large gap (watch taken off) - 400 seconds gap:")
    results = calculator.bucket_heart_rates(gap_data)
    print(f"   Total TRIMP: {results['total_trimp']:.2f}")
    print(f"   Total minutes: {sum(bucket['minutes'] for bucket in results['presentation_buckets'].values()):.2f}")
    
    # Test case 3: HR data with small gap (should not be skipped)
    small_gap_data = {
        'heartRateValues': [
            [1000, 120],   # Normal reading
            [2000, 125],   # Normal reading
            [2300, 130],   # Small gap (3 seconds) - should NOT be skipped
            [2400, 135],   # Normal reading
            [2500, 140]    # Normal reading
        ]
    }
    
    print("\n3. HR data with small gap (should not be skipped):")
    results = calculator.bucket_heart_rates(small_gap_data)
    print(f"   Total TRIMP: {results['total_trimp']:.2f}")
    print(f"   Total minutes: {sum(bucket['minutes'] for bucket in results['presentation_buckets'].values()):.2f}")
    
    # Test case 4: First reading of the day (should not be skipped)
    first_reading_data = {
        'heartRateValues': [
            [1000, 120],   # First reading - should not be skipped
            [2000, 125],   # Normal reading
            [3000, 130],   # Normal reading
        ]
    }
    
    print("\n4. First reading of the day (should not be skipped):")
    results = calculator.bucket_heart_rates(first_reading_data)
    print(f"   Total TRIMP: {results['total_trimp']:.2f}")
    print(f"   Total minutes: {sum(bucket['minutes'] for bucket in results['presentation_buckets'].values()):.2f}")
    
    # Test case 5: Compare with and without gap detection
    print("\n5. Comparison - same data with and without large gap:")
    
    # Data with large gap
    data_with_gap = {
        'heartRateValues': [
            [1000, 120],
            [2000, 125],
            [402000, 130],  # 400 second gap
            [403000, 135],
            [404000, 140]
        ]
    }
    
    # Data without gap (continuous)
    data_without_gap = {
        'heartRateValues': [
            [1000, 120],
            [2000, 125],
            [3000, 130],   # No gap
            [4000, 135],
            [5000, 140]
        ]
    }
    
    results_with_gap = calculator.bucket_heart_rates(data_with_gap)
    results_without_gap = calculator.bucket_heart_rates(data_without_gap)
    
    print(f"   With gap: TRIMP={results_with_gap['total_trimp']:.2f}, Minutes={sum(bucket['minutes'] for bucket in results_with_gap['presentation_buckets'].values()):.2f}")
    print(f"   Without gap: TRIMP={results_without_gap['total_trimp']:.2f}, Minutes={sum(bucket['minutes'] for bucket in results_without_gap['presentation_buckets'].values()):.2f}")
    
    print("\n=== Summary ===")
    print("The fix should:")
    print("- Skip readings after gaps > 300 seconds (watch taken off)")
    print("- Include readings after small gaps < 300 seconds")
    print("- Always include the first reading of the day")
    print("- Maintain normal TRIMP calculation for continuous readings")

if __name__ == "__main__":
    test_gap_detection() 