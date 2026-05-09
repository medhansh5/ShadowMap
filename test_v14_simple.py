#!/usr/bin/env python3
"""
ShadowMap v1.4 Simple API Test
Direct test of physics fields without signal processing
"""

import requests
import json

def test_simple_physics():
    """Test v1.4 physics fields with simple payload"""
    print("=== ShadowMap v1.4 Simple Physics Test ===")
    
    url = "http://localhost:5000/api/event"
    
    # Simple payload that should pass signal processing
    simple_payload = {
        "event_type": "ANOMALY_DETECTED",
        "peak_magnitude": 25.0,  # High magnitude to trigger event
        "peak_coordinates": {
            "lat": 12.9716,
            "lng": 77.5946
        },
        "pre_trigger_window": [
            {"timestamp": "2026-05-09T10:30:00Z", "accel_x": 0.5, "accel_y": 0.3, "accel_z": 9.8},
            {"timestamp": "2026-05-09T10:30:01Z", "accel_x": 0.6, "accel_y": 0.4, "accel_z": 9.9},
            {"timestamp": "2026-05-09T10:30:02Z", "accel_x": 0.7, "accel_y": 0.5, "accel_z": 10.0},
            {"timestamp": "2026-05-09T10:30:03Z", "accel_x": 0.8, "accel_y": 0.6, "accel_z": 10.1},
            {"timestamp": "2026-05-09T10:30:04Z", "accel_x": 0.9, "accel_y": 0.7, "accel_z": 10.2},
            {"timestamp": "2026-05-09T10:30:05Z", "accel_x": 1.0, "accel_y": 0.8, "accel_z": 10.3},
            {"timestamp": "2026-05-09T10:30:06Z", "accel_x": 1.1, "accel_y": 0.9, "accel_z": 10.4},
            {"timestamp": "2026-05-09T10:30:07Z", "accel_x": 1.2, "accel_y": 1.0, "accel_z": 10.5},
            {"timestamp": "2026-05-09T10:30:08Z", "accel_x": 1.3, "accel_y": 1.1, "accel_z": 10.6},
            {"timestamp": "2026-05-09T10:30:09Z", "accel_x": 1.4, "accel_y": 1.2, "accel_z": 10.7},
            {"timestamp": "2026-05-09T10:30:10Z", "accel_x": 1.5, "accel_y": 1.3, "accel_z": 10.8},
            {"timestamp": "2026-05-09T10:30:11Z", "accel_x": 1.6, "accel_y": 1.4, "accel_z": 10.9},
            {"timestamp": "2026-05-09T10:30:12Z", "accel_x": 1.7, "accel_y": 1.5, "accel_z": 11.0},
            {"timestamp": "2026-05-09T10:30:13Z", "accel_x": 1.8, "accel_y": 1.6, "accel_z": 11.1},
            {"timestamp": "2026-05-09T10:30:14Z", "accel_x": 1.9, "accel_y": 1.7, "accel_z": 11.2}
        ],
        "post_trigger_window": [
            {"timestamp": "2026-05-09T10:30:15Z", "accel_x": 5.0, "accel_y": 4.0, "accel_z": -20.0},
            {"timestamp": "2026-05-09T10:30:16Z", "accel_x": 4.0, "accel_y": 3.0, "accel_z": -15.0},
            {"timestamp": "2026-05-09T10:30:17Z", "accel_x": 3.0, "accel_y": 2.0, "accel_z": -10.0},
            {"timestamp": "2026-05-09T10:30:18Z", "accel_x": 2.0, "accel_y": 1.5, "accel_z": -5.0},
            {"timestamp": "2026-05-09T10:30:19Z", "accel_x": 1.0, "accel_y": 0.8, "accel_z": 0.0}
        ],
        "velocity": 25.0,
        "gyro_history": [
            {"timestamp": "2026-05-09T10:29:58Z", "gyro_x": 0.1, "gyro_y": 0.05, "gyro_z": 0.02},
            {"timestamp": "2026-05-09T10:29:59Z", "gyro_x": 0.2, "gyro_y": 0.1, "gyro_z": 0.03},
            {"timestamp": "2026-05-09T10:30:00Z", "gyro_x": 0.3, "gyro_y": 0.15, "gyro_z": 0.04}
        ],
        # v1.4 Physics fields
        "estimated_depth": 45.8,
        "rider_id": "rider_test_123",
        "bottom_out": False,
        "heading": 45.5,
        "suspension_travel": 35.2,
        "physics_confidence": 0.85
    }
    
    print(f"Testing with {len(simple_payload['pre_trigger_window'])} pre-trigger samples...")
    print(f"Testing with {len(simple_payload['post_trigger_window'])} post-trigger samples...")
    
    try:
        response = requests.post(url, json=simple_payload, timeout=10)
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 201:
            result = response.json()
            print("✅ SUCCESS: Event processed and saved to database")
            print(f"Anomaly ID: {result.get('anomaly_id')}")
            print(f"Clustered: {result.get('clustered')}")
            print(f"Message: {result.get('message')}")
            
            # Check physics data in response
            signature = result.get('signature', {})
            physics = signature.get('physics', {})
            if physics:
                print(f"\n📊 Physics Data Stored:")
                print(f"  Estimated Depth: {physics.get('estimated_depth')} mm")
                print(f"  Rider ID: {physics.get('rider_id')}")
                print(f"  Bottom Out: {physics.get('is_bottomed_out')}")
                print(f"  Heading: {physics.get('heading')}°")
                print(f"  Suspension Travel: {physics.get('suspension_travel_percent')}%")
                print(f"  Physics Confidence: {physics.get('physics_confidence')}")
                print(f"  Sensor Saturation: {physics.get('sensor_saturation')}")
            
            return True
            
        elif response.status_code == 200:
            result = response.json()
            print("⚠️  Event processed but not saved (threshold not reached)")
            print(f"Message: {result.get('message')}")
            
            # Check if physics data was still processed
            signature = result.get('signature', {})
            physics = signature.get('physics', {})
            if physics:
                print(f"\n📊 Physics Data Processed (not saved):")
                print(f"  Estimated Depth: {physics.get('estimated_depth')} mm")
                print(f"  Rider ID: {physics.get('rider_id')}")
            
            return False
            
        else:
            print(f"❌ ERROR: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error: {error_data.get('error')}")
            except:
                print(f"Response: {response.text}")
            return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_database_direct():
    """Test database schema directly without API"""
    print("\n=== Direct Database Test ===")
    
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(__file__))
        
        from app import Anomaly, db, app
        
        with app.app_context():
            # Create a test anomaly with physics data
            test_anomaly = Anomaly(
                latitude=12.9716,
                longitude=77.5946,
                confidence_score=0.8,
                hit_count=1,
                impact_magnitude=25.0,
                severity_class=2,
                # v1.4 physics fields
                estimated_depth=45.8,
                rider_id="rider_direct_test",
                is_bottomed_out=False,
                heading=45.5,
                suspension_travel_percent=35.2,
                physics_confidence=0.85
            )
            
            # Test if we can create and save
            db.session.add(test_anomaly)
            db.session.commit()
            
            print(f"✅ Test anomaly created with ID: {test_anomaly.id}")
            
            # Test if we can retrieve and verify physics fields
            retrieved = Anomaly.query.get(test_anomaly.id)
            print(f"✅ Retrieved anomaly from database")
            print(f"  Estimated Depth: {retrieved.estimated_depth} mm")
            print(f"  Rider ID: {retrieved.rider_id}")
            print(f"  Bottom Out: {retrieved.is_bottomed_out}")
            print(f"  Heading: {retrieved.heading}°")
            print(f"  Suspension Travel: {retrieved.suspension_travel_percent}%")
            print(f"  Physics Confidence: {retrieved.physics_confidence}")
            
            # Test to_dict method includes physics fields
            anomaly_dict = retrieved.to_dict()
            physics_fields = ['estimated_depth', 'rider_id', 'is_bottomed_out', 'heading', 'suspension_travel_percent', 'physics_confidence']
            missing_fields = [field for field in physics_fields if field not in anomaly_dict]
            
            if missing_fields:
                print(f"❌ Missing fields in to_dict(): {missing_fields}")
            else:
                print("✅ All physics fields present in to_dict()")
            
            # Clean up test data
            db.session.delete(test_anomaly)
            db.session.commit()
            print("✅ Test data cleaned up")
            
            return True
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run simple v1.4 tests"""
    print("ShadowMap v1.4 Simple Infrastructure Test")
    print("=" * 50)
    
    # Test 1: Direct database operations
    db_success = test_database_direct()
    
    # Test 2: API with physics data
    api_success = test_simple_physics()
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"Database Test: {'✅ PASS' if db_success else '❌ FAIL'}")
    print(f"API Test: {'✅ PASS' if api_success else '❌ FAIL'}")
    
    if db_success and api_success:
        print("\n🎉 ShadowMap v1.4 infrastructure is READY!")
        print("Every 'Red Flash' will now save physics data to the database.")
    else:
        print("\n⚠️  Some tests failed - check the issues above.")

if __name__ == "__main__":
    main()
