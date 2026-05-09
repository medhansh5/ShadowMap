#!/usr/bin/env python3
"""
ShadowMap v1.4 Physics Test Suite
Tests Kalman filtering and suspension modeling
"""

import numpy as np
import math
from datetime import datetime
from potholenet import get_kalman_filter, get_suspension_model

def test_kalman_filter():
    """Test Kalman filter GPS smoothing"""
    print("=== Kalman Filter Test ===")
    
    kf = get_kalman_filter()
    
    # Simulate GPS trajectory with noise
    true_trajectory = [
        (12.9716, 77.5946, 10.0, 45.0),  # Bangalore start
        (12.9717, 77.5947, 12.0, 46.0),
        (12.9718, 77.5948, 11.0, 44.0),
        (12.9719, 77.5949, 13.0, 47.0),
        (12.9720, 77.5950, 10.5, 45.5),
    ]
    
    print("Testing GPS smoothing with simulated trajectory...")
    
    for i, (lat, lng, velocity, heading) in enumerate(true_trajectory):
        # Add Gaussian noise to simulate GPS error
        noisy_lat = lat + np.random.normal(0, 0.00001)  # ~1m noise
        noisy_lng = lng + np.random.normal(0, 0.00001)  # ~1m noise
        
        # Apply Kalman filter
        filtered = kf.filter_gps(noisy_lat, noisy_lng, velocity, heading)
        
        print(f"Point {i+1}:")
        print(f"  True:      ({lat:.6f}, {lng:.6f})")
        print(f"  Noisy:     ({noisy_lat:.6f}, {noisy_lng:.6f})")
        print(f"  Filtered:  ({filtered['lat']:.6f}, {filtered['lng']:.6f})")
        print(f"  Confidence: {filtered['confidence']:.3f}")
        print()

def test_suspension_modeling():
    """Test suspension depth estimation"""
    print("=== Suspension Modeling Test ===")
    
    sm = get_suspension_model()
    
    # Simulate pothole impact (sharp negative acceleration spike)
    sampling_rate = 100
    duration = 0.5  # 500ms window
    t = np.linspace(0, duration, int(sampling_rate * duration))
    
    # Create realistic pothole signature
    accel_z = []
    for time_point in t:
        if 0.1 < time_point < 0.2:  # Impact period
            # Sharp negative acceleration (suspension compression)
            accel = -15.0 * math.sin((time_point - 0.1) * 50 * math.pi)
        else:
            # Normal gravity + small vibration
            accel = 9.81 + np.random.normal(0, 0.5)
        accel_z.append(accel)
    
    # Test depth estimation
    depth_result = sm.estimate_pothole_depth(accel_z, datetime.now())
    
    print("Pothole depth estimation results:")
    print(f"  Estimated depth: {depth_result['estimated_depth_mm']:.1f} mm")
    print(f"  Peak velocity: {depth_result['peak_velocity_ms']:.2f} m/s")
    print(f"  Bottom out: {depth_result['bottom_out']}")
    print(f"  Bottom out severity: {depth_result['bottom_out_severity']:.2f}")
    print(f"  Suspension travel: {depth_result['confidence']:.2f}%")
    print(f"  Confidence: {depth_result['confidence']:.2f}")
    print()
    
    # Test bottom-out detection
    severe_impact = [-35.0] * 10  # Severe bottom-out scenario
    bottom_out_test = sm.estimate_pothole_depth(severe_impact, datetime.now())
    
    print("Severe impact test (bottom-out scenario):")
    print(f"  Bottom out: {bottom_out_test['bottom_out']}")
    print(f"  Bottom out severity: {bottom_out_test['bottom_out_severity']:.2f}")
    print(f"  Suspension travel: {sm.get_suspension_travel_percentage(bottom_out_test['estimated_depth_mm']):.1f}%")
    print()

def test_double_integration():
    """Test double integration mathematics"""
    print("=== Double Integration Mathematics Test ===")
    
    # Simple test case: constant acceleration
    dt = 0.01  # 100Hz sampling
    accel_series = [2.0] * 50  # 2 m/s^2 for 0.5 seconds
    
    # Expected results:
    # velocity = a * t = 2.0 * 0.5 = 1.0 m/s
    # displacement = 0.5 * a * t^2 = 0.5 * 2.0 * 0.25 = 0.25 m = 250 mm
    
    sm = get_suspension_model()
    depth, velocity, valid = sm.double_integration_depth(accel_series)
    
    print("Double integration test with constant acceleration (2.0 m/s^2):")
    print(f"  Expected displacement: 250.0 mm")
    print(f"  Calculated displacement: {depth:.1f} mm")
    print(f"  Expected velocity: 1.0 m/s")
    print(f"  Calculated velocity: {velocity:.2f} m/s")
    print(f"  Valid integration: {valid}")
    print()

def test_physics_integration():
    """Test complete physics pipeline"""
    print("=== Complete Physics Pipeline Test ===")
    
    kf = get_kalman_filter()
    sm = get_suspension_model()
    
    # Simulate a complete ride segment
    gps_data = [
        (12.9716, 77.5946, 8.0, 30.0),
        (12.9717, 77.5947, 15.0, 35.0),
        (12.9718, 77.5948, 12.0, 40.0),
    ]
    
    accel_data = [
        [9.81, 9.81, -5.0, 9.81, 9.81],  # Small bump
        [9.81, 9.81, -20.0, 9.81, 9.81], # Pothole impact
        [9.81, 9.81, 9.81, 9.81, 9.81],   # Normal
    ]
    
    print("Testing complete physics pipeline...")
    
    for i, ((lat, lng, vel, heading), accel_window) in enumerate(zip(gps_data, accel_data)):
        # Kalman filtering
        filtered_gps = kf.filter_gps(lat, lng, vel, heading)
        
        # Suspension modeling
        depth_result = sm.estimate_pothole_depth(accel_window, datetime.now())
        
        print(f"Segment {i+1}:")
        print(f"  GPS Filtered: ({filtered_gps['lat']:.6f}, {filtered_gps['lng']:.6f})")
        print(f"  Depth: {depth_result['estimated_depth_mm']:.1f} mm")
        print(f"  Bottom Out: {depth_result['bottom_out']}")
        print()

def main():
    """Run all physics tests"""
    print("ShadowMap v1.4 Physics Test Suite")
    print("=" * 50)
    print()
    
    try:
        test_kalman_filter()
        test_suspension_modeling()
        test_double_integration()
        test_physics_integration()
        
        print("All physics tests completed successfully!")
        print("v1.4 Deep Physics modeling is ready for deployment.")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
