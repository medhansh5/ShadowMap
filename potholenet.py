import pandas as pd
import numpy as np
from scipy.signal import butter, filtfilt
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import os
import requests
import json
import time
from datetime import datetime, timedelta
from collections import deque
import math
import numpy as np

def upload_with_wakeup(lat, lng, quality):
    API_URL = "https://shadowmap-api.onrender.com/upload"
    # Round to 5 decimal places (~1.1 meter precision)
    payload = {
        "lat": round(float(lat), 5),
        "lng": round(float(lng), 5),
        "quality": int(quality)
    }
    # Render Free Tier takes ~50s to spin up. 
    # We use a 60s timeout for the "Wake-up" attempt.
    try:
        print("Sending data (Waiting for server to wake up...)")
        response = requests.post(API_URL, json=payload, timeout=60)
        if response.status_code == 201:
            print("Server is awake! Data uploaded.")
            return True
    except requests.exceptions.ReadTimeout:
        print("Server wake-up timed out. Retrying on next bump...")
    except Exception as e:
        print(f"Connection error: {e}")
    return False

class PotholeNet:
    """
    PotholeNet: Road Quality Classifier
    Optimized for Royal Enfield Classic 350 ("Shadow")
    
    This class handles the ingestion of smartphone accelerometer data,
    filters out mechanical noise from the engine, and classifies
    road surface anomalies.
    """
    
    def __init__(self, sampling_rate=100):
        self.fs = sampling_rate  # Target sampling frequency (Hz)
        self.model = RandomForestClassifier(
            n_estimators=100, 
            max_depth=12, 
            random_state=42
        )

    def _apply_butterworth_highpass(self, data, cutoff=12, order=4):
        """
        Removes low-frequency engine 'thump' vibrations.
        Specifically tuned for the 350cc long-stroke engine signature.
        """
        nyq = 0.5 * self.fs
        normal_cutoff = cutoff / nyq
        b, a = butter(order, normal_cutoff, btype='high', analog=False)
        return filtfilt(b, a, data)

    def extract_features(self, window):
        """Feature Engineering: RMS, Std Dev, and Peak Magnitude."""
        # Check if the window is a DataFrame; if so, grab the 'z' column.
        # Otherwise, assume it's already a slice of the z-axis data.
        if isinstance(window, pd.DataFrame):
            z_raw = window['z'].values
        else:
            # If it's a numpy array, we assume column 3 (index 2) is Z
            # (time=0, x=1, y=2, z=3)
            z_raw = window[:, 3] if window.ndim > 1 else window
            
        z_filt = self._apply_butterworth_highpass(z_raw)
        
        return [
            np.std(z_filt),
            np.max(np.abs(z_filt)),
            np.sqrt(np.mean(z_filt**2)),
            np.ptp(z_filt)
        ]

    def train_model(self, data_windows, labels):
        """
        Trains the Random Forest model on labeled segments.
        Labels: 0 = Smooth Road, 1 = Pothole/Rough Road
        """
        X = [self.extract_features(win) for win in data_windows]
        y = labels
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
        
        self.model.fit(X_train, y_train)
        
        print("--- Model Training Performance ---")
        predictions = self.model.predict(X_test)
        print(classification_report(y_test, predictions))
        
        # Save the model for real-time edge deployment
        joblib.dump(self.model, 'potholenet_v1.pkl')
        print("Model saved as potholenet_v1.pkl")

    def run_inference(self, live_window):
        """
        Used for real-time prediction during a ride.
        """
        features = np.array(self.extract_features(live_window)).reshape(1, -1)
        prediction = self.model.predict(features)
        return "POTHOLE" if prediction[0] == 1 else "SMOOTH"

class SignalIntelligence:
    """
    Signal Intelligence Layer v1.1.0
    Advanced signal processing for road anomaly detection
    """
    
    def __init__(self, sampling_rate=100, gravity_threshold=9.8):
        self.fs = sampling_rate
        self.gravity_threshold = gravity_threshold
        self.window_size_ms = 500  # 500ms sliding window
        self.window_samples = int((self.window_size_ms / 1000) * self.fs)
        self.event_threshold = 15.0  # Impact magnitude threshold
        
        # Sliding window buffer
        self.buffer = deque(maxlen=self.window_samples)
        
    def remove_gravity(self, accel_z):
        """
        High-pass filter to remove gravity (1g) and low-frequency vehicle sway
        Uses a 1Hz high-pass Butterworth filter
        """
        # Simple high-pass: subtract moving average (gravity component)
        if len(self.buffer) < 10:
            return accel_z - self.gravity_threshold
        
        # Calculate moving average for gravity estimation
        gravity_estimate = np.mean(list(self.buffer)[-10:])
        return accel_z - gravity_estimate
    
    def calculate_impact_magnitude(self, accel_x, accel_y, accel_z):
        """
        Calculate Impact Magnitude: M = sqrt(ax^2 + ay^2 + az^2)
        Represents total acceleration force from all axes
        """
        return math.sqrt(accel_x**2 + accel_y**2 + accel_z**2)
    
    def detect_event(self, accel_x, accel_y, accel_z, timestamp=None):
        """
        Sliding window event detection (500ms)
        Returns True if impact magnitude exceeds threshold
        """
        # Calculate impact magnitude
        magnitude = self.calculate_impact_magnitude(accel_x, accel_y, accel_z)
        
        # Add to buffer
        self.buffer.append(magnitude)
        
        # Check if buffer is full
        if len(self.buffer) < self.window_samples:
            return False, magnitude
        
        # Calculate window statistics
        window_data = list(self.buffer)
        max_magnitude = max(window_data)
        avg_magnitude = np.mean(window_data)
        
        # Event detection: peak exceeds threshold
        is_event = max_magnitude > self.event_threshold
        
        return is_event, {
            'magnitude': magnitude,
            'max_magnitude': max_magnitude,
            'avg_magnitude': avg_magnitude,
            'timestamp': timestamp or datetime.now()
        }
    
    def clear_buffer(self):
        """Reset sliding window buffer"""
        self.buffer.clear()

# Global signal intelligence instance
_signal_intel = None

def get_signal_intel():
    """Initialize or return global signal intelligence instance"""
    global _signal_intel
    if _signal_intel is None:
        _signal_intel = SignalIntelligence()
    return _signal_intel

class SpatialIntelligence:
    """
    Spatial Intelligence Layer v1.1.0
    Geospatial clustering and confidence decay for anomaly entities
    """
    
    def __init__(self, cluster_radius_meters=2.0, decay_lambda=0.1):
        self.cluster_radius = cluster_radius_meters
        self.decay_lambda = decay_lambda  # Decay constant per hour
        
    def haversine_distance(self, lat1, lng1, lat2, lng2):
        """
        Calculate Haversine distance between two coordinates in meters
        """
        R = 6371000  # Earth radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_lat / 2) * math.sin(delta_lat / 2) +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lng / 2) * math.sin(delta_lng / 2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    
    def find_nearby_anomaly(self, lat, lng, existing_anomalies):
        """
        Find existing anomaly within cluster radius (2 meters)
        Returns the anomaly ID if found, None otherwise
        """
        for anomaly in existing_anomalies:
            distance = self.haversine_distance(
                lat, lng,
                anomaly['latitude'],
                anomaly['longitude']
            )
            if distance <= self.cluster_radius:
                return anomaly['id']
        return None
    
    def calculate_confidence_score(self, hit_count, last_reported_time):
        """
        Calculate confidence score with exponential decay
        Formula: C = sum(Reports) × e^(-λt)
        where t is time since last report in hours
        """
        if not last_reported_time:
            return float(hit_count)
        
        # Calculate time difference in hours
        time_diff = (datetime.now() - last_reported_time).total_seconds() / 3600.0
        
        # Apply exponential decay
        decay_factor = math.exp(-self.decay_lambda * time_diff)
        
        confidence = hit_count * decay_factor
        
        # Normalize to 0-1 range (assuming max reasonable hits = 10)
        return min(confidence / 10.0, 1.0)
    
    def determine_severity_class(self, impact_magnitude):
        """
        Map impact magnitude to severity class
        1 = Minor, 2 = Moderate, 3 = Major
        """
        if impact_magnitude < 15.0:
            return 1
        elif impact_magnitude < 25.0:
            return 2
        else:
            return 3

# Global spatial intelligence instance
_spatial_intel = None

def get_spatial_intel():
    """Initialize or return global spatial intelligence instance"""
    global _spatial_intel
    if _spatial_intel is None:
        _spatial_intel = SpatialIntelligence()
    return _spatial_intel

class EdgeComputing:
    """
    Edge Computing Layer v1.2.0
    Event-triggered upload logic for "Lean Rider" protocol
    Reduces battery/data usage by only syncing on anomaly events
    """
    
    def __init__(self, pre_trigger_ms=250, post_trigger_ms=250, sampling_rate=100):
        self.pre_trigger_ms = pre_trigger_ms
        self.post_trigger_ms = post_trigger_ms
        self.fs = sampling_rate
        self.pre_trigger_samples = int((pre_trigger_ms / 1000) * self.fs)
        self.post_trigger_samples = int((post_trigger_ms / 1000) * self.fs)
        
        # Circular buffer for pre-trigger data
        self.buffer = deque(maxlen=self.pre_trigger_samples)
        self.event_detected = False
        self.post_trigger_counter = 0
        
    def add_telemetry_point(self, lat, lng, accel_x, accel_y, accel_z, timestamp=None):
        """
        Add a telemetry point to the buffer.
        Returns event window data if event is detected and post-trigger window completes.
        """
        ts = timestamp or datetime.now()
        
        # Add to pre-trigger buffer
        point = {
            'lat': lat,
            'lng': lng,
            'accel_x': accel_x,
            'accel_y': accel_y,
            'accel_z': accel_z,
            'timestamp': ts
        }
        self.buffer.append(point)
        
        # Check if event is in progress
        if self.event_detected:
            self.post_trigger_counter += 1
            if self.post_trigger_counter >= self.post_trigger_samples:
                # Event window complete
                event_window = list(self.buffer)
                self.event_detected = False
                self.post_trigger_counter = 0
                return self._prepare_event_upload(event_window)
        
        return None
    
    def trigger_event(self):
        """
        Trigger an event (called when impact magnitude exceeds threshold).
        Begins post-trigger collection.
        """
        self.event_detected = True
        self.post_trigger_counter = 0
    
    def _prepare_event_upload(self, event_window):
        """
        Prepare event window data for upload to server.
        Returns structured payload with pre/post trigger context.
        """
        if not event_window:
            return None
        
        # Calculate event statistics
        impact_magnitudes = [
            math.sqrt(p['accel_x']**2 + p['accel_y']**2 + p['accel_z']**2)
            for p in event_window
        ]
        
        peak_magnitude = max(impact_magnitudes)
        avg_magnitude = sum(impact_magnitudes) / len(impact_magnitudes)
        
        # Find peak index
        peak_index = impact_magnitudes.index(peak_magnitude)
        peak_point = event_window[peak_index]
        
        return {
            'event_type': 'ANOMALY_DETECTED',
            'peak_magnitude': peak_magnitude,
            'avg_magnitude': avg_magnitude,
            'peak_coordinates': {
                'lat': peak_point['lat'],
                'lng': peak_point['lng']
            },
            'pre_trigger_window': event_window[:peak_index],
            'post_trigger_window': event_window[peak_index:],
            'window_duration_ms': len(event_window) / self.fs * 1000,
            'sampling_rate': self.fs,
            'timestamp': peak_point['timestamp'].isoformat()
        }
    
    def reset(self):
        """Reset the edge computing state"""
        self.buffer.clear()
        self.event_detected = False
        self.post_trigger_counter = 0

# Global edge computing instance
_edge_computing = None

def get_edge_computing():
    """Initialize or return global edge computing instance"""
    global _edge_computing
    if _edge_computing is None:
        _edge_computing = EdgeComputing()
    return _edge_computing

class SignatureAnalysis:
    """
    Signature Analysis Layer v1.3.0
    Synthetic Intelligence for road surface classification and multi-sensor fusion
    """
    
    def __init__(self, sampling_rate=100):
        self.fs = sampling_rate
        self.vibration_floor = 0.0
        self.floor_samples = deque(maxlen=1000)  # 10 seconds of data at 100Hz
        
    def analyze_fft(self, accel_window):
        """
        Perform Fast Fourier Transform on acceleration window.
        Differentiates between impulse (sharp pothole) and periodic (rumble strips) events.
        """
        if not accel_window or len(accel_window) < 10:
            return {
                'dominant_frequency': 0,
                'spectral_centroid': 0,
                'event_type': 'UNKNOWN',
                'frequency_peak': 0
            }
        
        # Extract acceleration magnitude
        magnitudes = []
        for point in accel_window:
            mag = math.sqrt(
                point.get('accel_x', 0)**2 + 
                point.get('accel_y', 0)**2 + 
                point.get('accel_z', 0)**2
            )
            magnitudes.append(mag)
        
        # Remove DC component (subtract mean)
        magnitudes = np.array(magnitudes) - np.mean(magnitudes)
        
        # Apply FFT
        fft_result = np.fft.fft(magnitudes)
        fft_magnitude = np.abs(fft_result)
        fft_freq = np.fft.fftfreq(len(magnitudes), 1/self.fs)
        
        # Find dominant frequency (positive frequencies only)
        positive_freqs = fft_freq[:len(fft_freq)//2]
        positive_mags = fft_magnitude[:len(fft_magnitude)//2]
        
        if len(positive_mags) > 0:
            dominant_idx = np.argmax(positive_mags)
            dominant_frequency = abs(positive_freqs[dominant_idx])
            spectral_centroid = np.sum(positive_freqs * positive_mags) / (np.sum(positive_mags) + 1e-10)
            frequency_peak = positive_mags[dominant_idx]
        else:
            dominant_frequency = 0
            spectral_centroid = 0
            frequency_peak = 0
        
        # Classify event type based on frequency characteristics
        event_type = 'UNKNOWN'
        if dominant_frequency > 20:
            event_type = 'PERIODIC'  # Rumble strips, washboard roads
        elif spectral_centroid < 5 and frequency_peak > 2:
            event_type = 'IMPULSE'  # Sharp pothole impact
        elif dominant_frequency < 2:
            event_type = 'LOW_FREQ'  # Body roll, suspension movement
        
        return {
            'dominant_frequency': dominant_frequency,
            'spectral_centroid': spectral_centroid,
            'event_type': event_type,
            'frequency_peak': frequency_peak
        }
    
    def fuse_gyroscope(self, accel_z, gyro_x, gyro_y, gyro_z):
        """
        Multi-sensor fusion with gyroscope data.
        Calculates leaning angle compensation to avoid false positives during turns.
        """
        # Calculate leaning angle from gyroscope (integrate angular velocity)
        # Simplified: Use instantaneous angular velocity as approximation
        lean_angle_x = math.atan2(gyro_y, gyro_z) if gyro_z != 0 else 0
        lean_angle_y = math.atan2(gyro_x, gyro_z) if gyro_z != 0 else 0
        
        # Total lean angle magnitude
        lean_angle = math.sqrt(lean_angle_x**2 + lean_angle_y**2)
        
        # Correct vertical acceleration for lean angle
        # a_corrected = a_z * cos(θ)
        accel_z_corrected = accel_z * math.cos(lean_angle)
        
        # Calculate correction factor
        correction_factor = abs(math.cos(lean_angle))
        
        return {
            'accel_z_corrected': accel_z_corrected,
            'lean_angle': lean_angle,
            'correction_factor': correction_factor,
            'is_turning': abs(lean_angle) > 0.3  # ~17 degrees threshold
        }
    
    def detect_swerve_pattern(self, gyro_history, anomaly_timestamp):
        """
        Detect "Swerved-to-Avoid" patterns.
        If a high-G turn (gyro spike) immediately precedes a pothole coordinate,
        mark the anomaly as 'Confirmed but Avoidable.'
        """
        if not gyro_history or len(gyro_history) < 5:
            return {'is_avoided': False, 'swerve_magnitude': 0}
        
        # Calculate gyro magnitude for each point
        gyro_magnitudes = []
        for point in gyro_history:
            mag = math.sqrt(
                point.get('gyro_x', 0)**2 + 
                point.get('gyro_y', 0)**2 + 
                point.get('gyro_z', 0)**2
            )
            gyro_magnitudes.append(mag)
        
        # Find maximum gyro magnitude in the window
        max_gyro = max(gyro_magnitudes) if gyro_magnitudes else 0
        
        # Threshold for swerve detection (rad/s)
        swerve_threshold = 2.0
        
        # Check if high-G turn occurred
        is_avoided = max_gyro > swerve_threshold
        
        return {
            'is_avoided': is_avoided,
            'swerve_magnitude': max_gyro
        }
    
    def classify_road_surface(self, accel_window):
        """
        Classify road surface type based on FFT background noise.
        Returns: Gravel, Pavement, Cobblestone, Unknown
        """
        if not accel_window or len(accel_window) < 20:
            return 'UNKNOWN'
        
        fft_result = self.analyze_fft(accel_window)
        
        # Surface classification based on frequency characteristics
        dominant_freq = fft_result['dominant_frequency']
        spectral_centroid = fft_result['spectral_centroid']
        frequency_peak = fft_result['frequency_peak']
        
        if spectral_centroid > 15:
            return 'COBBLESTONE'  # High frequency, irregular
        elif dominant_freq > 10:
            return 'GRAVEL'  # Moderate frequency, rough
        elif spectral_centroid < 5 and frequency_peak < 1:
            return 'PAVEMENT'  # Low frequency, smooth
        else:
            return 'UNKNOWN'
    
    def update_vibration_floor(self, accel_magnitude):
        """
        Update the vibration floor for adaptive gain control.
        If the average vibration floor is high, automatically raise the trigger threshold.
        """
        self.floor_samples.append(accel_magnitude)
        
        if len(self.floor_samples) > 100:
            self.vibration_floor = np.mean(self.floor_samples)
        
        return self.vibration_floor
    
    def calculate_adaptive_threshold(self, base_threshold=15.0):
        """
        Calculate adaptive threshold based on vibration floor.
        Raises threshold in high-vibration environments (off-roading).
        """
        floor = self.vibration_floor
        
        # Adaptive gain: if floor > 5, scale threshold proportionally
        if floor > 5.0:
            adaptive_gain = 1.0 + (floor - 5.0) / 10.0
            return base_threshold * adaptive_gain
        else:
            return base_threshold
    
    def normalize_by_velocity(self, impact_magnitude, velocity):
        """
        Normalize impact magnitude by velocity.
        M_normalized = M / v^2 (since impact force increases with velocity)
        """
        if velocity < 1.0:
            velocity = 1.0  # Prevent division by zero
        
        # Convert velocity to m/s if in km/h (assuming km/h input)
        velocity_ms = velocity / 3.6 if velocity > 10 else velocity
        
        # Normalize: M / v^2
        normalized = impact_magnitude / (velocity_ms ** 2)
        
        return normalized

# Global signature analysis instance
_signature_analysis = None

def get_signature_analysis():
    """Initialize or return global signature analysis instance"""
    global _signature_analysis
    if _signature_analysis is None:
        _signature_analysis = SignatureAnalysis()
    return _signature_analysis

# Global classifier instance
_pothole_classifier = None

def get_classifier():
    """
    Initialize or return the global classifier instance.
    Loads trained model if available, otherwise uses untrained model.
    """
    global _pothole_classifier
    if _pothole_classifier is None:
        _pothole_classifier = PotholeNet()
        # Try to load pre-trained model
        if os.path.exists('potholenet_v1.pkl'):
            _pothole_classifier.model = joblib.load('potholenet_v1.pkl')
            print("Loaded pre-trained PotholeNet model")
        else:
            print("No pre-trained model found, using untrained classifier")
    return _pothole_classifier

def classify_data(sensor_data):
    """
    Classify sensor data as pothole or smooth road with signal intelligence.
    
    Args:
        sensor_data: Dict containing:
            - lat: latitude
            - lng: longitude  
            - accel_x: x-axis acceleration
            - accel_y: y-axis acceleration
            - accel_z: z-axis acceleration
            
    Returns:
        Dict with:
            - classification: "POTHOLE" or "SMOOTH"
            - severity_score: float (0.0-1.0, higher = more severe)
            - confidence: float (0.0-1.0)
            - impact_magnitude: float (M = sqrt(ax^2 + ay^2 + az^2))
            - is_event: bool (exceeded threshold in sliding window)
            - lat: latitude
            - lng: longitude
    """
    classifier = get_classifier()
    signal_intel = get_signal_intel()
    
    try:
        # Handle different input formats
        if isinstance(sensor_data, dict):
            lat = sensor_data.get('lat', 0)
            lng = sensor_data.get('lng', 0)
            accel_x = sensor_data.get('accel_x', 0)
            accel_y = sensor_data.get('accel_y', 0)
            accel_z = sensor_data.get('accel_z', 0)
        else:
            # Assume list/tuple format [lat, lng, accel_x, accel_y, accel_z]
            lat, lng, accel_x, accel_y, accel_z = sensor_data[0], sensor_data[1], sensor_data[2], sensor_data[3], sensor_data[4]
        
        # Apply signal intelligence
        accel_z_filtered = signal_intel.remove_gravity(accel_z)
        impact_magnitude = signal_intel.calculate_impact_magnitude(accel_x, accel_y, accel_z)
        is_event, event_data = signal_intel.detect_event(accel_x, accel_y, accel_z)
        
        # Create window for classification
        window_data = np.array([[0, accel_x, accel_y, accel_z_filtered]])
        
        # Extract features and classify
        features = np.array(classifier.extract_features(window_data)).reshape(1, -1)
        
        # Get prediction and probability
        prediction = classifier.model.predict(features)[0]
        probabilities = classifier.model.predict_proba(features)[0]
        
        classification = "POTHOLE" if prediction == 1 else "SMOOTH"
        severity_score = float(probabilities[1]) if prediction == 1 else float(probabilities[0])
        confidence = float(max(probabilities))
        
        return {
            'classification': classification,
            'severity_score': severity_score,
            'confidence': confidence,
            'impact_magnitude': impact_magnitude,
            'is_event': is_event,
            'event_data': event_data,
            'lat': lat,
            'lng': lng
        }
        
    except Exception as e:
        print(f"Classification error: {e}")
        # Return safe default on error
        return {
            'classification': 'SMOOTH',
            'severity_score': 0.0,
            'confidence': 0.0,
            'impact_magnitude': 0.0,
            'is_event': False,
            'event_data': None,
            'lat': lat if 'lat' in locals() else 0,
            'lng': lng if 'lng' in locals() else 0
        }

if __name__ == "__main__":
    print("PotholeNet Core Engine v1.0")
    print("Waiting for data mission files from 'Shadow'...")
