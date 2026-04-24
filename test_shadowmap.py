#!/usr/bin/env python3
"""
ShadowMap Mission Control Test Suite

This script simulates real ride scenarios to verify the entire pipeline:
1. PotholeNet AI classification
2. PostgreSQL database storage  
3. Leaflet UI visualization

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
        self.roads_endpoint = f"{base_url}/roads"
        
        # Test scenarios with realistic coordinates (Ghaziabad area)
        self.test_scenarios = [
            {
                "name": "Scenario A: Major Pothole",
                "payload": {
                    "lat": 28.6692,
                    "lng": 77.3538,
                    "accel_z": -20.5  # High vertical acceleration
                },
                "expected_classification": "POTHOLE",
                "expected_save": True,
                "expected_color": "Deep Red"
            },
            {
                "name": "Scenario B: Minor Bump", 
                "payload": {
                    "lat": 28.6693,
                    "lng": 77.3539,
                    "accel_z": -12.0  # Moderate acceleration
                },
                "expected_classification": "POTHOLE",  # May classify as pothole depending on sensitivity
                "expected_save": True,
                "expected_color": "Orange/Yellow"
            },
            {
                "name": "Scenario C: Smooth Road",
                "payload": {
                    "lat": 28.6694,
                    "lng": 77.3540,
                    "accel_z": -9.8  # Standard gravity
                },
                "expected_classification": "SMOOTH",
                "expected_save": False,
                "expected_color": "Not saved"
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
        print(f"   Expected: {scenario['expected_classification']} | Save: {scenario['expected_save']} | Color: {scenario['expected_color']}")
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
        """Validate API response and print results"""
        if response is None:
            return False
            
        print(f"   📡 Status Code: {response.status_code}")
        
        if response.status_code not in [200, 201]:
            print(f"   ❌ Unexpected status code: {response.status_code}")
            print(f"   📄 Response: {response.text}")
            return False
            
        try:
            data = response.json()
            print(f"   🤖 Classification: {data.get('classification', {}).get('classification', 'N/A')}")
            print(f"   📊 Severity Score: {data.get('classification', {}).get('severity_score', 'N/A')}")
            print(f"   🎯 Confidence: {data.get('classification', {}).get('confidence', 'N/A')}")
            print(f"   💾 Saved to DB: {data.get('saved_to_db', 'N/A')}")
            
            # Debug information
            if 'debug' in data:
                debug = data['debug']
                print(f"   🔍 Debug Info:")
                print(f"      Coordinates: {debug.get('coordinates', 'N/A')}")
                print(f"      DB Quality Score: {debug.get('database_quality_score', 'N/A')}")
                if 'note' in debug:
                    print(f"      Note: {debug['note']}")
            
            # Validation
            classification = data.get('classification', {}).get('classification', '')
            saved_to_db = data.get('saved_to_db', False)
            
            success = True
            if classification != scenario['expected_classification']:
                print(f"   ⚠️  Classification mismatch: Expected {scenario['expected_classification']}, got {classification}")
                success = False
                
            if saved_to_db != scenario['expected_save']:
                print(f"   ⚠️  DB save mismatch: Expected {scenario['expected_save']}, got {saved_to_db}")
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
        """Check current database state via /roads endpoint"""
        print(f"\n🗄️  DATABASE STATE CHECK")
        print("-" * 50)
        
        try:
            response = requests.get(self.roads_endpoint, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"   📊 Total road segments in DB: {len(data)}")
                
                # Count by quality
                quality_counts = {}
                for segment in data:
                    quality = segment.get('quality', 'unknown')
                    quality_counts[quality] = quality_counts.get(quality, 0) + 1
                
                print(f"   📈 Quality Distribution:")
                for quality, count in sorted(quality_counts.items()):
                    quality_name = {0: "Smooth", 1: "Bumpy", 2: "Pothole"}.get(quality, f"Unknown({quality})")
                    print(f"      {quality_name}: {count} segments")
                    
                # Show recent entries
                if data:
                    print(f"   📍 Recent entries:")
                    for i, segment in enumerate(data[-3:]):  # Last 3 entries
                        print(f"      {i+1}. Lat: {segment['lat']:.6f}, Lng: {segment['lng']:.6f}, Quality: {segment['quality']}")
                        
            else:
                print(f"   ❌ Failed to get database state: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Database check failed: {e}")
            
    def run_test_suite(self):
        """Run the complete test suite"""
        self.print_header()
        
        results = []
        
        for i, scenario in enumerate(self.test_scenarios, 1):
            self.print_scenario_header(scenario)
            
            # Send telemetry
            response = self.send_telemetry(scenario['payload'])
            
            # Validate response
            success = self.validate_response(response, scenario)
            results.append((scenario['name'], success))
            
            # Delay between requests (except after last one)
            if i < len(self.test_scenarios):
                print(f"\n   ⏳ Waiting 2 seconds before next test...")
                time.sleep(2)
        
        # Final results
        print(f"\n📋 TEST RESULTS SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for name, success in results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"   {status} - {name}")
            
        print(f"\n🎯 Overall: {passed}/{total} tests passed")
        
        # Database state check
        self.check_database_state()
        
        # Instructions for log comparison
        print(f"\n📝 LOG COMPARISON INSTRUCTIONS")
        print("-" * 80)
        print(f"1. Check your Flask console for '[DATABASE COMMIT]' messages")
        print(f"2. Verify the lat/lng data types match the PostgreSQL schema")
        print(f"3. Ensure severity scores are properly formatted")
        print(f"4. Compare the console output with this script's results")
        print(f"5. Look for any error messages in Flask logs")
        
        print(f"\n🚀 CALIBRATION NOTES")
        print("-" * 80)
        print(f"- Adjust accel_z values to test PotholeNet sensitivity")
        print(f"- Use this script to fine-tune classification thresholds")
        print(f"- Monitor the /roads endpoint to verify data persistence")
        print(f"- Check the Leaflet map for visual confirmation")
        
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
