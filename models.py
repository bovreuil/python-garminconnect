#!/usr/bin/env python3
"""
Shared models for Garmin Heart Rate Analyzer
"""

import json
import logging
import math
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TRIMPCalculator:
    """Class to calculate TRIMP (Training Impulse) using exponential model."""
    
    def __init__(self, resting_hr: int = 48, max_hr: int = 167):
        """
        Initialize TRIMP calculator with personal HR parameters.
        
        Args:
            resting_hr: Resting heart rate in BPM
            max_hr: Maximum heart rate in BPM
        """
        self.resting_hr = resting_hr
        self.max_hr = max_hr
        self.hr_reserve = max_hr - resting_hr
        
        # Presentation buckets (10 BPM each) for charts
        self.presentation_buckets = [
            (80, 89), (90, 99), (100, 109), (110, 119), (120, 129),
            (130, 139), (140, 149), (150, 159), (160, 999)
        ]
        
        # Color temperature scale for presentation buckets
        self.bucket_colors = [
            '#002040',  # Midnight (80-89)
            '#1f77b4',  # Blue (90-99)
            '#7fb3d3',  # Light blue (100-109)
            '#17becf',  # Cyan (110-119)
            '#2ca02c',  # Green (120-129)
            '#ff7f0e',  # Orange (130-139)
            '#ff6b35',  # Dark orange (140-149)
            '#d62728',  # Red (150-159)
            '#8b0000'   # Dark red (160+)
        ]
    
    def calculate_hr_reserve_ratio(self, hr: int) -> float:
        """Calculate heart rate reserve ratio for a given HR."""
        if hr <= self.resting_hr:
            return 0.0
        return (hr - self.resting_hr) / self.hr_reserve
    
    def calculate_trimp_for_hr(self, hr: int, minutes: int) -> float:
        """
        Calculate TRIMP for a specific heart rate and time duration.
        
        Args:
            hr: Heart rate in BPM
            minutes: Time spent at this HR in minutes
            
        Returns:
            TRIMP value for this HR/duration combination
        """
        if hr < 80:  # Below exercise threshold
            return 0.0
        
        hr_reserve_ratio = self.calculate_hr_reserve_ratio(hr)
        y = 1.92 * hr_reserve_ratio
        trimp = minutes * hr_reserve_ratio * 0.64 * (math.exp(y))
        
        return trimp
    
    def bucket_heart_rates(self, heart_rate_data: Dict) -> Dict:
        """
        Bucket heart rate values into individual buckets and calculate TRIMP.
        
        Returns:
            Dict with individual buckets, presentation buckets, and TRIMP data
        """
        if not heart_rate_data or 'heartRateValues' not in heart_rate_data:
            return {
                'individual_buckets': {},
                'presentation_buckets': {},
                'trimp_data': {},
                'total_trimp': 0.0
            }
        
        # Initialize buckets
        individual_buckets = {}  # 80, 81, 82, etc.
        presentation_buckets = {  # 80-89, 90-99, 100-109, etc.
            '80-89': {'minutes': 0, 'trimp': 0.0},
            '90-99': {'minutes': 0, 'trimp': 0.0},
            '100-109': {'minutes': 0, 'trimp': 0.0},
            '110-119': {'minutes': 0, 'trimp': 0.0},
            '120-129': {'minutes': 0, 'trimp': 0.0},
            '130-139': {'minutes': 0, 'trimp': 0.0},
            '140-149': {'minutes': 0, 'trimp': 0.0},
            '150-159': {'minutes': 0, 'trimp': 0.0},
            '160+': {'minutes': 0, 'trimp': 0.0}
        }
        trimp_data = {}
        total_trimp = 0.0
        
        heart_rate_values = heart_rate_data['heartRateValues']
        
        for hr_value in heart_rate_values:
            # Handle both list and dict formats
            if isinstance(hr_value, list):
                # Format: [timestamp, value]
                timestamp, hr = hr_value
            else:
                # Format: {"value": x, "timestamp": y}
                hr = hr_value.get('value')
            
            if hr is not None and hr >= 80:  # Only count HR >= 80
                # Individual bucket
                individual_buckets[hr] = individual_buckets.get(hr, 0) + 1
                
                # Calculate TRIMP for this HR
                trimp = self.calculate_trimp_for_hr(hr, 1)  # 1 minute intervals
                trimp_data[hr] = trimp_data.get(hr, 0.0) + trimp
                total_trimp += trimp
                
                # Presentation bucket
                for i, (min_hr, max_hr) in enumerate(self.presentation_buckets):
                    if min_hr <= hr <= max_hr:
                        bucket_name = f"{min_hr}-{max_hr if max_hr != 999 else '999'}"
                        if bucket_name == "160-999":
                            bucket_name = "160+"
                        presentation_buckets[bucket_name]['minutes'] += 1
                        presentation_buckets[bucket_name]['trimp'] += trimp
                        break
        
        return {
            'individual_buckets': individual_buckets,
            'presentation_buckets': presentation_buckets,
            'trimp_data': trimp_data,
            'total_trimp': total_trimp
        }

class HeartRateAnalyzer:
    """Class to analyze heart rate data using TRIMP calculations."""
    
    def __init__(self, resting_hr: int = 48, max_hr: int = 167):
        """
        Initialize with personal HR parameters.
        
        Args:
            resting_hr: Resting heart rate in BPM
            max_hr: Maximum heart rate in BPM
        """
        self.trimp_calculator = TRIMPCalculator(resting_hr, max_hr)
    
    def analyze_heart_rate_data(self, heart_rate_data: Dict) -> Dict:
        """
        Analyze heart rate data and return comprehensive results.
        
        Returns:
            Dict with buckets, TRIMP data, and analysis results
        """
        # Get TRIMP calculations
        trimp_results = self.trimp_calculator.bucket_heart_rates(heart_rate_data)
        
        # Calculate activity type based on TRIMP distribution
        presentation_buckets = trimp_results['presentation_buckets']
        activity_type = self._determine_activity_type(presentation_buckets)
        
        # Calculate legacy daily score (keeping for compatibility)
        daily_score = self._calculate_legacy_score(presentation_buckets)
        
        return {
            'individual_hr_buckets': trimp_results['individual_buckets'],
            'presentation_buckets': trimp_results['presentation_buckets'],
            'trimp_data': trimp_results['trimp_data'],
            'total_trimp': trimp_results['total_trimp'],
            'daily_score': daily_score,
            'activity_type': activity_type
        }
    
    def _determine_activity_type(self, presentation_buckets: Dict) -> str:
        """Determine activity type based on TRIMP distribution."""
        low_intensity_trimp = (
            presentation_buckets['80-89']['trimp'] +
            presentation_buckets['90-99']['trimp'] +
            presentation_buckets['100-109']['trimp'] +
            presentation_buckets['110-119']['trimp']
        )
        high_intensity_trimp = (
            presentation_buckets['130-139']['trimp'] +
            presentation_buckets['140-149']['trimp'] +
            presentation_buckets['150-159']['trimp'] +
            presentation_buckets['160+']['trimp']
        )
        
        if low_intensity_trimp > high_intensity_trimp * 2:
            return "long_low_intensity"
        elif high_intensity_trimp > low_intensity_trimp * 2:
            return "short_high_intensity"
        else:
            return "mixed"
    
    def _calculate_legacy_score(self, presentation_buckets: Dict) -> float:
        """Calculate legacy daily score for backward compatibility."""
        total_minutes = sum(bucket['minutes'] for bucket in presentation_buckets.values())
        if total_minutes == 0:
            return 0.0
        
        # Weighted score based on time in each zone
        zone_weights = {
            "80-89": 0.5, "90-99": 1.0, "100-109": 1.5, "110-119": 2.0, "120-129": 2.5,
            "130-139": 3.0, "140-149": 3.5, "150-159": 4.0, "160+": 4.5
        }
        
        total_score = 0
        for zone, data in presentation_buckets.items():
            weight = zone_weights.get(zone, 1.0)
            total_score += (data['minutes'] / total_minutes) * weight * 100
        
        return total_score 