#!/usr/bin/env python3
"""
ShadowMap Mission Control Test Suite v1.3.0

This script simulates real ride scenarios to verify the entire pipeline:
1. Signal Intelligence (High-pass filter, Impact magnitude, Sliding window)
2. Spatial Intelligence (Clustering, Confidence decay)
3. Edge Computing (Event-triggered uploads with pre/post trigger windows)
4. Proximity Engine (Forward-looking cone alerts)
5. Signature Analysis (FFT, Gyroscope fusion, Dynamic thresholding)
6. PotholeNet AI classification
7. PostgreSQL anomaly storage
8. Leaflet UI visualization with Rider HUD v3

Run this script while Flask server is active to test the complete system.
"""

import requests
import json
import time
from datetime import datetime
import sys

class ShadowMapTester:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.api_endpoint = f"{base_url}/api/telemetry"
        self.event_endpoint = f"{base_url}/api/event"
        self.proximity_endpoint = f"{base_url}/api/proximity"
        self.geojson_endpoint = f"{base_url}/api/export/geojson"
        self.roads_endpoint = f"{base_url}/roads"
        
        # Test scenarios with realistic coordinates (Ghaziabad area)
        # v1.3.0: Event-triggered uploads with pre/post trigger windows + gyroscope fusion
        self.test_scenarios = [
            {
                "name": "Scenario A: Major Pothole (High Impact + Gyro)",
                "payload": {
                    "lat": 28.6692,
                    "lng": 77.3538,
                    "accel_x": 2.5,
                    "accel_y": 1.8,
                    "accel_z": -25.0,
                    "gyro_x": 0.1,
                    "gyro_y": 0.1,
                    "gyro_z": 0.1,
                    "velocity": 20.0
                },
                "expected_classification": "POTHOLE",
                "expected_event": True,
                "expected_save": True,
                "expected_cluster": False
            },
            {
                "name": "Scenario B: Same Location (Clustering Test)", 
                "payload": {
                    "lat": 28.6692,
                    "lng": 77.3538,
                    "accel_x": 2.3,
                    "accel_y": 1.6,
                    "accel_z": -22.0,
                    "gyro_x": 0.1,
                    "gyro_y": 0.1,
                    "gyro_z": 0.1,
                    "velocity": 20.0
                },
                "expected_classification": "POTHOLE",
                "expected_event": True,
                "expected_save": True,
                "expected_cluster": True
            },
            {
                "name": "Scenario C: Sharp Turn (Gyro Compensation Test)",
                "payload": {
                    "lat": 28.6693,
                    "lng": 77.3539,
                    "accel_x": 2.5,
                    "accel_y": 1.8,
                    "accel_z": -15.0,
                    "gyro_x": 0.5,
                    "gyro_y": 0.5,
                    "gyro_z": 0.1,
                    "velocity": 30.0
                },
                "expected_classification": "POTHOLE",
                "expected_event": False,  # Gyro compensation should reduce this
                "expected_save": False,
                "expected_cluster": False
            },
            {
                "name": "Scenario D: Smooth Road",
                "payload": {
                    "lat": 28.6694,
                    "lng": 77.3540,
                    "accel_x": 0.1,
                    "accel_y": 0.1,
                    "accel_z": -9.8,
                    "gyro_x": 0.1,
                    "gyro_y": 0.1,
                    "gyro_z": 0.1,
                    "velocity": 20.0
                },
                "expected_classification": "SMOOTH",
                "expected_event": False,
                "expected_save": False,
                "expected_cluster": False
            }
        ]
        
        # v1.3.0: Event-triggered upload scenarios with signature analysis
        self.event_scenarios = [
            {
                "name": "Event A: Event-Triggered Upload with Signature Analysis",
                "payload": {
                    "event_type": "ANOMALY_DETECTED",
                    "peak_magnitude": 25.0,
                    "peak_coordinates": {
                        "lat": 28.6695,
                        "lng": 77.3541
                    },
                    "pre_trigger_window": [
                        {"lat": 28.6695, "lng": 77.3541, "accel_x": 0.1, "accel_y": 0.1, "accel_z": -9.8, "timestamp": datetime.now().isoformat()},
                        {"lat": 28.6695, "lng": 77.3541, "accel_x": 0.2, "accel_y": 0.2, "accel_z": -10.0, "timestamp": datetime.now().isoformat()}
                    ],
                    "post_trigger_window": [
                        {"lat": 28.6695, "lng": 77.3541, "accel_x": 2.5, "accel_y": 1.8, "accel_z": -25.0, "timestamp": datetime.now().isoformat()},
                        {"lat": 28.6695, "lng": 77.3541, "accel_x": 2.3, "accel_y": 1.6, "accel_z": -22.0, "timestamp": datetime.now().isoformat()}
                    ],
                    "gyro_history": [
                        {"gyro_x": 0.1, "gyro_y": 0.1, "gyro_z": 0.1, "timestamp": datetime.now().isoformat()},
                        {"gyro_x": 0.1, "gyro_y": 0.1, "gyro_z": 0.1, "timestamp": datetime.now().isoformat()}
                    ],
                    "velocity": 20.0,
                    "window_duration_ms": 40,
                    "sampling_rate": 100
                },
                "expected_save": True,
                "expected_cluster": False
            }
        ]
        
    def print_header(self):
        """Print test suite header"""
        print("=" * 80)
        print("🔧 SHADOWMAP MISSION CONTROL TEST SUITE")
        print("=" * 80)
        print(f"Testing Endpoint: {self.api_endpoint}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 80)
        
    def print_scenario_header(self, scenario):
        """Print individual scenario header"""
        print(f"\n📍 {scenario['name']}")
        print(f"   Payload: {json.dumps(scenario['payload'], indent=6)}")
        if 'expected_classification' in scenario:
            print(f"   Expected: {scenario['expected_classification']} | Event: {scenario['expected_event']} | "
                  f"Save: {scenario['expected_save']} | Cluster: {scenario['expected_cluster']}")
        else:
            print(f"   Expected: Save: {scenario['expected_save']} | Cluster: {scenario['expected_cluster']}")
        print("-" * 50)
        
    def send_telemetry(self, payload):
        """Send telemetry data to Flask API"""
        try:
            response = requests.post(
                self.api_endpoint,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            return response
        except requests.exceptions.RequestException as e:
            print(f"   ❌ REQUEST FAILED: {e}")
            return None
            
    def validate_response(self, response, scenario):
        """Validate API response and print results (v1.1.0)"""
        if response is None:
            return False
            
        print(f"   📡 Status Code: {response.status_code}")
        
        if response.status_code not in [200, 201]:
            print(f"   ❌ Unexpected status code: {response.status_code}")
            print(f"   📄 Response: {response.text}")
            return False
            
        try:
            data = response.json()
            classification = data.get('classification', {})
            
            print(f"   🤖 Classification: {classification.get('classification', 'N/A')}")
            print(f"   📊 Impact Magnitude: {classification.get('impact_magnitude', 'N/A')}")
            print(f"   ⚡ Event Detected: {classification.get('is_event', 'N/A')}")
            print(f"   🎯 Confidence: {classification.get('confidence', 'N/A')}")
            print(f"   💾 Saved to DB: {data.get('saved_to_db', 'N/A')}")
            print(f"   🔗 Clustered: {data.get('clustered', 'N/A')}")
            
            # Debug information
            if 'debug' in data:
                debug = data['debug']
                print(f"   🔍 Debug Info:")
                print(f"      Coordinates: {debug.get('coordinates', 'N/A')}")
                if 'anomaly_id' in data:
                    print(f"      Anomaly ID: {data['anomaly_id']}")
                if 'cluster_hit_count' in debug:
                    print(f"      Cluster Hits: {debug['cluster_hit_count']}")
                    print(f"      Cluster Confidence: {debug['cluster_confidence']:.3f}")
                if 'severity_class' in debug:
                    print(f"      Severity Class: {debug['severity_class']}")
                if 'note' in debug:
                    print(f"      Note: {debug['note']}")
            
            # Validation
            classification_result = classification.get('classification', '')
            is_event = classification.get('is_event', False)
            saved_to_db = data.get('saved_to_db', False)
            clustered = data.get('clustered', False)
            
            success = True
            if classification_result != scenario['expected_classification']:
                print(f"   ⚠️  Classification mismatch: Expected {scenario['expected_classification']}, got {classification_result}")
                success = False
                
            if is_event != scenario['expected_event']:
                print(f"   ⚠️  Event detection mismatch: Expected {scenario['expected_event']}, got {is_event}")
                success = False
                
            if saved_to_db != scenario['expected_save']:
                print(f"   ⚠️  DB save mismatch: Expected {scenario['expected_save']}, got {saved_to_db}")
                success = False
                
            if clustered != scenario['expected_cluster']:
                print(f"   ⚠️  Clustering mismatch: Expected {scenario['expected_cluster']}, got {clustered}")
                success = False
                
            if success:
                print(f"   ✅ Scenario PASSED")
            else:
                print(f"   ❌ Scenario FAILED")
                
            return success
            
        except json.JSONDecodeError as e:
            print(f"   ❌ JSON decode error: {e}")
            print(f"   📄 Raw response: {response.text}")
            return False
            
    def check_database_state(self):
        """Check current database state via /roads endpoint (v1.1.0)"""
        print(f"\n🗄️  DATABASE STATE CHECK")
        print("-" * 50)
        
        try:
            response = requests.get(self.roads_endpoint, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"   📊 Total anomalies in DB: {len(data)}")
                
                # Count by severity class
                severity_counts = {}
                total_hits = 0
                avg_confidence = 0
                
                for anomaly in data:
                    severity = anomaly.get('severity', 'unknown')
                    severity_counts[severity] = severity_counts.get(severity, 0) + 1
                    total_hits += anomaly.get('hit_count', 1)
                    avg_confidence += anomaly.get('confidence', 0)
                
                if data:
                    avg_confidence = avg_confidence / len(data)
                
                print(f"   📈 Severity Distribution:")
                for severity, count in sorted(severity_counts.items()):
                    severity_name = {1: "Minor", 2: "Moderate", 3: "Major"}.get(severity, f"Unknown({severity})")
                    print(f"      {severity_name}: {count} anomalies")
                
                print(f"   🎯 Total Cluster Hits: {total_hits}")
                print(f"   📊 Average Confidence: {avg_confidence:.3f}")
                
                # Show recent entries
                if data:
                    print(f"   📍 Recent anomalies:")
                    for i, anomaly in enumerate(data[-3:]):  # Last 3 entries
                        print(f"      {i+1}. ID: {anomaly['id']}, Lat: {anomaly['lat']:.6f}, Lng: {anomaly['lng']:.6f}, "
                              f"Confidence: {anomaly['confidence']:.3f}, Hits: {anomaly['hit_count']}")
                        
            else:
                print(f"   ❌ Failed to get database state: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Database check failed: {e}")
    
    def test_event_upload(self, scenario):
        """Test event-triggered upload endpoint (v1.2.0)"""
        print(f"\n📡 {scenario['name']}")
        print("-" * 50)
        
        try:
            response = requests.post(
                self.event_endpoint,
                json=scenario['payload'],
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            return response
        except requests.exceptions.RequestException as e:
            print(f"   ❌ REQUEST FAILED: {e}")
            return None
    
    def validate_event_response(self, response, scenario):
        """Validate event upload response (v1.2.0)"""
        if response is None:
            return False
            
        print(f"   📡 Status Code: {response.status_code}")
        
        if response.status_code not in [200, 201]:
            print(f"   ❌ Unexpected status code: {response.status_code}")
            print(f"   📄 Response: {response.text}")
            return False
            
        try:
            data = response.json()
            print(f"   🤖 Event Processed: {data.get('event_processed', 'N/A')}")
            print(f"   💾 Saved to DB: {data.get('saved_to_db', 'N/A')}")
            print(f"   🔗 Clustered: {data.get('clustered', 'N/A')}")
            
            if 'window_stats' in data:
                stats = data['window_stats']
                print(f"   📊 Window Stats:")
                print(f"      Pre-samples: {stats.get('pre_samples', 'N/A')}")
                print(f"      Post-samples: {stats.get('post_samples', 'N/A')}")
                print(f"      Peak Magnitude: {stats.get('peak_magnitude', 'N/A')}")
            
            # Validation
            saved_to_db = data.get('saved_to_db', False)
            clustered = data.get('clustered', False)
            
            success = True
            if saved_to_db != scenario['expected_save']:
                print(f"   ⚠️  DB save mismatch: Expected {scenario['expected_save']}, got {saved_to_db}")
                success = False
                
            if clustered != scenario['expected_cluster']:
                print(f"   ⚠️  Clustering mismatch: Expected {scenario['expected_cluster']}, got {clustered}")
                success = False
                
            if success:
                print(f"   ✅ Event Upload PASSED")
            else:
                print(f"   ❌ Event Upload FAILED")
                
            return success
            
        except json.JSONDecodeError as e:
            print(f"   ❌ JSON decode error: {e}")
            print(f"   📄 Raw response: {response.text}")
            return False
    
    def test_proximity_alerts(self):
        """Test proximity alert endpoint (v1.2.0)"""
        print(f"\n🎯 PROXIMITY ALERT TEST")
        print("-" * 50)
        
        try:
            # Test with a position near known anomalies
            params = {
                'lat': 28.6692,
                'lng': 77.3538,
                'heading': 45,  # Northeast heading
                'range_m': 1000
            }
            
            response = requests.get(self.proximity_endpoint, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"   📊 Current Position: {data.get('current_position', {})}")
                print(f"   📏 Search Range: {data.get('search_range_m', 0)}m")
                print(f"   🔺 Cone Angle: {data.get('cone_angle', 0)}°")
                print(f"   ⚠️  Total Alerts: {len(data.get('alerts', []))}")
                print(f"   🚨 Critical Alerts: {len(data.get('critical_alerts', []))}")
                print(f"   ⚡ Warning Alerts: {len(data.get('warning_alerts', []))}")
                
                if data.get('alerts'):
                    print(f"   📍 Nearest Alert:")
                    nearest = data['alerts'][0]
                    print(f"      Distance: {nearest['distance_m']}m")
                    print(f"      Bearing: {nearest['bearing']}°")
                    print(f"      Severity: {nearest['severity']}")
                    print(f"      Alert Level: {nearest['alert_level']}")
                
                return True
            else:
                print(f"   ❌ Proximity query failed: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Proximity test failed: {e}")
            return False
    
    def test_geojson_export(self):
        """Test GeoJSON export endpoint (v1.2.0)"""
        print(f"\n📄 GEOJSON EXPORT TEST")
        print("-" * 50)
        
        try:
            response = requests.get(self.geojson_endpoint, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"   📊 Export Type: {data.get('type', 'N/A')}")
                print(f"   📍 Features: {len(data.get('features', []))}")
                
                if data.get('features'):
                    print(f"   📄 Sample Feature:")
                    sample = data['features'][0]
                    print(f"      Type: {sample.get('type', 'N/A')}")
                    print(f"      Geometry: {sample.get('geometry', {}).get('type', 'N/A')}")
                    print(f"      Properties: {list(sample.get('properties', {}).keys())}")
                
                return True
            else:
                print(f"   ❌ GeoJSON export failed: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ GeoJSON test failed: {e}")
            return False
            
    def run_test_suite(self):
        """Run the complete test suite (v1.2.0)"""
        self.print_header()
        
        results = []
        
        # Run standard telemetry tests
        for i, scenario in enumerate(self.test_scenarios, 1):
            self.print_scenario_header(scenario)
            
            response = self.send_telemetry(scenario['payload'])
            success = self.validate_response(response, scenario)
            
            results.append({
                'name': scenario['name'],
                'success': success
            })
            
            # Delay between requests
            if i < len(self.test_scenarios):
                time.sleep(1)
        
        # Run event-triggered upload tests (v1.2.0)
        print(f"\n{'=' * 80}")
        print("📡 v1.2.0 EVENT-TRIGGERED UPLOAD TESTS")
        print("=" * 80)
        
        for scenario in self.event_scenarios:
            response = self.test_event_upload(scenario)
            success = self.validate_event_response(response, scenario)
            
            results.append({
                'name': scenario['name'],
                'success': success
            })
            
            time.sleep(1)
        
        # Run proximity alert test (v1.2.0)
        print(f"\n{'=' * 80}")
        print("🎯 v1.2.0 PROXIMITY ALERT TEST")
        print("=" * 80)
        
        proximity_success = self.test_proximity_alerts()
        results.append({
            'name': 'Proximity Alert Test',
            'success': proximity_success
        })
        
        # Run GeoJSON export test (v1.2.0)
        print(f"\n{'=' * 80}")
        print("📄 v1.2.0 GEOJSON EXPORT TEST")
        print("=" * 80)
        
        geojson_success = self.test_geojson_export()
        results.append({
            'name': 'GeoJSON Export Test',
            'success': geojson_success
        })
        
        # Print summary
        print(f"\n{'=' * 80}")
        print("� TEST SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for r in results if r['success'])
        total = len(results)
        
        for result in results:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"   {status} - {result['name']}")
            
        print(f"\n🎯 Overall: {passed}/{total} tests passed")
        
        # Database state check
        self.check_database_state()
        
        # Instructions for log comparison
        print(f"\n📝 LOG COMPARISON INSTRUCTIONS")
        print("-" * 80)
        print(f"1. Check Flask console for '[CLUSTER UPDATE]', '[NEW ANOMALY]', and '[EVENT CLUSTER]' messages")
        print(f"2. Verify spatial clustering is working (Scenario B should cluster with A)")
        print(f"3. Ensure confidence scores are properly calculated with decay")
        print(f"4. Compare console output with this script's results")
        print(f"5. Look for any error messages in Flask logs")
        
        print(f"\n🚀 CALIBRATION NOTES (v1.3.0)")
        print("-" * 80)
        print(f"- Adjust 3-axis acceleration values to test signal intelligence")
        print(f"- Use Scenario A+B to verify 2-meter clustering radius")
        print(f"- Monitor confidence decay over time (λ = 0.1 per hour)")
        print(f"- Check Leaflet map for confidence-based heatmaps")
        print(f"- Verify Rider HUD displays critical hazard warnings")
        print(f"- Test event-triggered uploads with pre/post trigger windows")
        print(f"- Verify proximity engine detects hazards within forward-looking cone")
        print(f"- Confirm GeoJSON export works for offline navigation apps")
        print(f"- Test gyroscope fusion for leaning angle compensation")
        print(f"- Verify FFT signature analysis classifies impulse vs periodic events")
        print(f"- Check adaptive thresholding adjusts for vibration floor")
        print(f"- Validate velocity-based magnitude scaling")
        print(f"- Test swerve-to-avoid detection with high-G turns")
        print(f"- Verify road surface classification (Pavement, Gravel, Cobblestone)")
        
        print(f"\n✨ Test suite completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

def main():
    """Main entry point"""
    print("🏁 Starting ShadowMap Mission Control Test Suite...")
    
    # Check if Flask server is running
    tester = ShadowMapTester()
    
    try:
        # Quick connectivity check
        response = requests.get(f"{tester.base_url}/", timeout=5)
        if response.status_code == 200:
            print("✅ Flask server is reachable")
        else:
            print(f"⚠️  Flask server responded with {response.status_code}")
    except requests.exceptions.RequestException:
        print("❌ Cannot reach Flask server at http://127.0.0.1:5000")
        print("   Please start the Flask app first: python app.py")
        sys.exit(1)
    
    # Run the test suite
    tester.run_test_suite()

if __name__ == "__main__":
    main()
