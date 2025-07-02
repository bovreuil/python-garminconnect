#!/usr/bin/env python3
"""
Test script for TRIMP calculations
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import TRIMPCalculator, HeartRateAnalyzer

def test_trimp_calculations():
    """Test TRIMP calculations with sample data."""
    
    # Initialize calculator with Pete's parameters
    calculator = TRIMPCalculator(resting_hr=48, max_hr=167)
    
    print("=== TRIMP Calculator Test ===")
    print(f"Resting HR: {calculator.resting_hr} BPM")
    print(f"Max HR: {calculator.max_hr} BPM")
    print(f"HR Reserve: {calculator.hr_reserve} BPM")
    print()
    
    # Test individual HR calculations
    test_hrs = [90, 100, 110, 120, 130, 140, 150, 160, 129]
    print("=== Individual HR TRIMP Calculations (1 minute) ===")
    for hr in test_hrs:
        trimp = calculator.calculate_trimp_for_hr(hr, 1)
        hr_reserve_ratio = calculator.calculate_hr_reserve_ratio(hr)
        print(f"HR {hr:3d} BPM: HRr={hr_reserve_ratio:.3f}, TRIMP={trimp:.3f}")
    
    print()
    
    # Test with sample heart rate data
    sample_data = {
        'heartRateValues': [
            [1000, 90],   # 1 minute at 90 BPM
            [2000, 100],  # 1 minute at 100 BPM
            [3000, 110],  # 1 minute at 110 BPM
            [4000, 120],  # 1 minute at 120 BPM
            [5000, 130],  # 1 minute at 130 BPM
            [6000, 140],  # 1 minute at 140 BPM
            [7000, 150],  # 1 minute at 150 BPM
            [8000, 160],  # 1 minute at 160 BPM
            [9000, 129],  # 1 minute at 129 BPM (should go in 120-129 bucket)
            [10000, 129], # Another minute at 129 BPM
        ]
    }
    
    print("=== Sample Data Analysis ===")
    results = calculator.bucket_heart_rates(sample_data)
    
    print("Individual buckets:")
    for hr in sorted(results['individual_buckets'].keys()):
        print(f"  HR {hr:3d}: {results['individual_buckets'][hr]} minutes")
    
    print("\nPresentation buckets:")
    for bucket, data in results['presentation_buckets'].items():
        print(f"  {bucket}: {data['minutes']} minutes, {data['trimp']:.2f} TRIMP")
    
    print(f"\nTotal TRIMP: {results['total_trimp']:.2f}")
    
    # Test with HeartRateAnalyzer
    print("\n=== HeartRateAnalyzer Test ===")
    analyzer = HeartRateAnalyzer(resting_hr=48, max_hr=167)
    analysis = analyzer.analyze_heart_rate_data(sample_data)
    
    print(f"Activity Type: {analysis['activity_type']}")
    print(f"Legacy Daily Score: {analysis['daily_score']:.1f}")
    print(f"Total TRIMP: {analysis['total_trimp']:.2f}")

if __name__ == "__main__":
    test_trimp_calculations() 