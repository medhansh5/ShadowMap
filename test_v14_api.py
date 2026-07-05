#!/usr/bin/env python3
"""
ShadowMap v1.4 API Test Suite
Tests the enhanced /api/event endpoint with physics data
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import requests
import json
import time
from datetime import datetime

def test_v14_physics_api():
    """Test v1.4 API with physics data payload"""
    print("=== ShadowMap v1.4 API Test ===")
    
    # API endpoint
    url = "http://localhost:5000/api/event"
    
    # Test payload with v1.4 physics data
    v14_payload = {
        "event_type": "ANOMALY_DETECTED",
        "peak_magnitude": 18.5,
        "peak_coordinates": {
            "lat": 12.9716,
            "lng": 77.5946
        },
        "pre_trigger_window": [
            {"timestamp": "2026-05-09T10:30:00Z", "accel_x": 0.5, "accel_y": 0.3, "accel_z": 9.8},
            {"timestamp": "2026-05-09T10:30:01Z", "accel_x": 0.6, "accel_y": 0.4, "accel_z": 9.9}
        ],
        "post_trigger_window": [
            {"timestamp": "2026-05-09T10:30:02Z", "accel_x": 2.1, "accel_y": 1.8, "accel_z": -15.2},
            {"timestamp": "2026-05-09T10:30:03Z", "accel_x": 1.5, "accel_y": 1.2, "accel_z": -8.5}
        ],
        "velocity": 25.0,
        "gyro_history": [
            {"timestamp": "2026-05-09T10:29:58Z", "gyro_x": 0.1, "gyro_y": 0.05, "gyro_z": 0.02}
        ],
        # v1.4 Physics fields
        "estimated_depth": 45.8,
        "rider_id": "rider_test_123",
        "bottom_out": False,
        "heading": 45.5,
        "suspension_travel": 35.2,
        "physics_confidence": 0.85
    }
    
    print("Testing v1.4 physics payload...")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(v14_payload, indent=2)}")
    
    try:
        response = requests.post(url, json=v14_payload, timeout=10)
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 201:
            result = response.json()
            print(f"\n✅ SUCCESS: Event processed")
            print(f"Anomaly ID: {result.get('anomaly_id')}")
            print(f"Clustered: {result.get('clustered')}")
            print(f"Message: {result.get('message')}")
            
            # Check physics data in response
            signature = result.get('signature', {})
            physics = signature.get('physics', {})
            if physics:
                print(f"\n📊 Physics Data Received:")
                print(f"  Estimated Depth: {physics.get('estimated_depth')} mm")
                print(f"  Rider ID: {physics.get('rider_id')}")
                print(f"  Bottom Out: {physics.get('is_bottomed_out')}")
                print(f"  Heading: {physics.get('heading')}°")
                print(f"  Suspension Travel: {physics.get('suspension_travel_percent')}%")
                print(f"  Physics Confidence: {physics.get('physics_confidence')}")
                print(f"  Sensor Saturation: {physics.get('sensor_saturation')}")
            
        else:
            print(f"\n❌ ERROR: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error Message: {error_data.get('error')}")
            except:
                print(f"Error Response: {response.text}")
        
    except requests.exceptions.ConnectionError:
        print(f"\n❌ CONNECTION ERROR: Could not connect to {url}")
        print("Make sure the Flask app is running on port 5000")
    except requests.exceptions.Timeout:
        print(f"\n❌ TIMEOUT: Request timed out after 10 seconds")
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")

def test_sensor_saturation():
    """Test sensor saturation validation (>150mm depth)"""
    print("\n=== Sensor Saturation Test ===")
    
    url = "http://localhost:5000/api/event"
    
    # Payload with extreme depth (>150mm)
    saturation_payload = {
        "event_type": "ANOMALY_DETECTED",
        "peak_magnitude": 25.0,
        "peak_coordinates": {"lat": 12.9717, "lng": 77.5947},
        "pre_trigger_window": [],
        "post_trigger_window": [
            {"timestamp": "2026-05-09T10:35:00Z", "accel_x": 5.0, "accel_y": 4.0, "accel_z": -35.0}
        ],
        "velocity": 30.0,
        # v1.4 Physics - Extreme depth for saturation test
        "estimated_depth": 180.5,  # >150mm threshold
        "rider_id": "rider_saturation_test",
        "bottom_out": True,
        "heading": 90.0,
        "suspension_travel": 139.0,  # >100% (impossible)
        "physics_confidence": 0.3
    }
    
    print("Testing sensor saturation validation...")
    print(f"Depth: {saturation_payload['estimated_depth']} mm (>150mm threshold)")
    
    try:
        response = requests.post(url, json=saturation_payload, timeout=10)
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 201:
            result = response.json()
            print("✅ Event processed (saturation flagged)")
            
            # Check if saturation was detected
            signature = result.get('signature', {})
            physics = signature.get('physics', {})
            if physics.get('sensor_saturation'):
                print("🚨 SENSOR SATURATION DETECTED: Depth > 150mm")
                print("   Confidence should be reduced to 0.5")
                print("   Bottom-out flag should be set to True")
            
        else:
            print(f"❌ Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error: {error_data.get('error')}")
            except:
                print(f"Response: {response.text}")
                
    except Exception as e:
        print(f"❌ Test failed: {e}")

def test_missing_physics_fields():
    """Test API response to missing physics fields"""
    print("\n=== Missing Physics Fields Test ===")
    
    url = "http://localhost:5000/api/event"
    
    # Payload without v1.4 physics fields (should still work)
    minimal_payload = {
        "event_type": "ANOMALY_DETECTED",
        "peak_magnitude": 16.0,
        "peak_coordinates": {"lat": 12.9718, "lng": 77.5948},
        "pre_trigger_window": [],
        "post_trigger_window": [
            {"timestamp": "2026-05-09T10:40:00Z", "accel_x": 1.0, "accel_y": 0.8, "accel_z": -12.0}
        ],
        "velocity": 20.0
        # No physics fields - should default to None/0
    }
    
    print("Testing minimal payload (no physics fields)...")
    
    try:
        response = requests.post(url, json=minimal_payload, timeout=10)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 201:
            result = response.json()
            print("✅ Minimal payload accepted")
            print("Physics fields should default to None/0")
            
        else:
            print(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

def test_database_schema():
    """Test if database tables have v1.4 columns"""
    print("\n=== Database Schema Test ===")
    
    try:
        # Import and test database models
        import sys
        import os
        sys.path.append(os.path.dirname(__file__))
        
        from app import Anomaly, db, app
        
        with app.app_context():
            # Check if v1.4 columns exist in model
            anomaly_columns = [column.name for column in Anomaly.__table__.columns]
            
            v14_columns = [
                'estimated_depth',
                'rider_id', 
                'is_bottomed_out',
                'heading',
                'suspension_travel_percent',
                'physics_confidence'
            ]
            
            print("Checking Anomaly model columns...")
            print(f"Total columns: {len(anomaly_columns)}")
            
            missing_columns = []
            for col in v14_columns:
                if col in anomaly_columns:
                    print(f"✅ {col}")
                else:
                    print(f"❌ {col} - MISSING")
                    missing_columns.append(col)
            
            if not missing_columns:
                print("\n🎉 All v1.4 physics columns present in database schema!")
            else:
                print(f"\n⚠️  Missing columns: {missing_columns}")
                
    except Exception as e:
        print(f"❌ Schema test failed: {e}")

def main():
    """Run all v1.4 API tests"""
    print("ShadowMap v1.4 Backend API Test Suite")
    print("=" * 50)
    print()
    
    # Test database schema first
    test_database_schema()
    
    print("\n" + "=" * 50)
    print("Starting API tests...")
    print("Make sure Flask app is running: python app.py")
    print("=" * 50)
    
    # Wait a moment for user to start server
    time.sleep(2)
    
    try:
        # Test 1: Normal physics data
        test_v14_physics_api()
        
        time.sleep(1)
        
        # Test 2: Sensor saturation
        test_sensor_saturation()
        
        time.sleep(1)
        
        # Test 3: Missing physics fields
        test_missing_physics_fields()
        
        print("\n" + "=" * 50)
        print("v1.4 API testing complete!")
        print("Check server logs for detailed processing information.")
        
    except KeyboardInterrupt:
        print("\n\n⏹  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")

if __name__ == "__main__":
    main()
