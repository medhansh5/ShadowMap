import os
import math
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
from functools import wraps
from potholenet import classify_data, get_spatial_intel, get_signature_analysis

# 1. Initialize the Flask App object FIRST
app = Flask(__name__)
CORS(app)

# 2. Database Configuration Logic
# Get URL from environment, or default to local SQLite for development
uri = os.environ.get('DATABASE_URL', 'sqlite:///shadowmap.db')

# Fix for Render/Heroku which might provide 'postgres://' (SQLAlchemy needs 'postgresql://')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 3. Initialize SQLAlchemy with the app
db = SQLAlchemy(app)

# 4. Define Database Models (v1.1.0 Anomaly Intelligence)
class Anomaly(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    confidence_score = db.Column(db.Float, nullable=False, default=0.0)
    hit_count = db.Column(db.Integer, nullable=False, default=1)
    first_reported = db.Column(db.DateTime, default=datetime.utcnow)
    last_reported = db.Column(db.DateTime, default=datetime.utcnow)
    impact_magnitude = db.Column(db.Float, nullable=True)
    severity_class = db.Column(db.Integer, nullable=False, default=1)
    cluster_radius = db.Column(db.Float, default=2.0)
    is_active = db.Column(db.Boolean, default=True)
    frequency_peak = db.Column(db.Float, nullable=True)  # v1.3.0: FFT frequency peak
    is_avoided = db.Column(db.Boolean, default=False)  # v1.3.0: Swerve-to-avoid detection
    road_surface = db.Column(db.String(50), nullable=True)  # v1.3.0: Pavement, Gravel, Cobblestone

    def to_dict(self):
        return {
            "id": self.id,
            "lat": self.latitude,
            "lng": self.longitude,
            "confidence": self.confidence_score,
            "hit_count": self.hit_count,
            "impact_magnitude": self.impact_magnitude,
            "severity": self.severity_class,
            "first_reported": self.first_reported.isoformat(),
            "last_reported": self.last_reported.isoformat(),
            "is_active": self.is_active,
            "frequency_peak": self.frequency_peak,
            "is_avoided": self.is_avoided,
            "road_surface": self.road_surface
        }

class TelemetryBuffer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    accel_x = db.Column(db.Float, nullable=False)
    accel_y = db.Column(db.Float, nullable=False)
    accel_z = db.Column(db.Float, nullable=False)
    impact_magnitude = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_processed = db.Column(db.Boolean, default=False)

# 5. Create Database Tables (Run once on startup)
with app.app_context():
    db.create_all()

# 6. Rate Limiting (v1.2.0)
# Simple in-memory rate limiter for production use
# For production, consider using Redis-based rate limiting
rate_limit_storage = {}

def rate_limit(max_requests=10, window_seconds=60):
    """
    Simple rate limiter decorator.
    Limits requests to max_requests per window_seconds per IP.
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            client_ip = request.remote_addr
            current_time = datetime.utcnow().timestamp()
            
            # Clean up old entries
            if client_ip in rate_limit_storage:
                rate_limit_storage[client_ip] = [
                    timestamp for timestamp in rate_limit_storage[client_ip]
                    if current_time - timestamp < window_seconds
                ]
            else:
                rate_limit_storage[client_ip] = []
            
            # Check if limit exceeded
            if len(rate_limit_storage[client_ip]) >= max_requests:
                return jsonify({
                    "error": "Rate limit exceeded",
                    "limit": max_requests,
                    "window": window_seconds
                }), 429
            
            # Add current request timestamp
            rate_limit_storage[client_ip].append(current_time)
            
            return f(*args, **kwargs)
        return wrapped
    return decorator

# --- WEB ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

# --- API ROUTES ---

@app.route('/upload', methods=['POST'])
def upload_data():
    data = request.get_json()
    
    if not data or not all(k in data for k in ("lat", "lng", "quality")):
        return jsonify({"error": "Missing data fields"}), 400

    try:
        new_anomaly = Anomaly(
            latitude=float(data['lat']),
            longitude=float(data['lng']),
            severity_class=int(data['quality'])
        )
        db.session.add(new_anomaly)
        db.session.commit()
        return jsonify({"message": "Success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/roads', methods=['GET'])
def get_roads():
    try:
        anomalies = Anomaly.query.filter_by(is_active=True).all()
        return jsonify([a.to_dict() for a in anomalies])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/telemetry', methods=['POST'])
@rate_limit(max_requests=30, window_seconds=60)
def process_telemetry():
    """
    Process real-time telemetry data with signal intelligence and spatial clustering.
    v1.3.0: Integrates signature analysis, gyroscope fusion, and dynamic thresholding.
    """
    try:
        # Validate incoming JSON
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
        
        # Required fields validation (v1.3.0: 3-axis accel + optional gyro + velocity)
        required_fields = ['lat', 'lng', 'accel_x', 'accel_y', 'accel_z']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {missing_fields}"}), 400
        
        # Validate data types and ranges
        try:
            lat = float(data['lat'])
            lng = float(data['lng'])
            accel_x = float(data['accel_x'])
            accel_y = float(data['accel_y'])
            accel_z = float(data['accel_z'])
            
            # Optional v1.3.0 fields
            gyro_x = float(data.get('gyro_x', 0))
            gyro_y = float(data.get('gyro_y', 0))
            gyro_z = float(data.get('gyro_z', 0))
            velocity = float(data.get('velocity', 20.0))  # Default 20 km/h
            
            # Basic coordinate validation
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                return jsonify({"error": "Invalid coordinates"}), 400
                
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid data types for coordinates or acceleration"}), 400
        
        # Get signature analysis instance
        signature_intel = get_signature_analysis()
        
        # Apply gyroscope fusion for leaning angle compensation
        gyro_fusion = signature_intel.fuse_gyroscope(accel_z, gyro_x, gyro_y, gyro_z)
        accel_z_corrected = gyro_fusion['accel_z_corrected']
        
        # Update data with corrected acceleration
        data['accel_z'] = accel_z_corrected
        
        # Calculate impact magnitude
        impact_magnitude = math.sqrt(accel_x**2 + accel_y**2 + accel_z_corrected**2)
        
        # Normalize by velocity (M_normalized = M / v^2)
        impact_normalized = signature_intel.normalize_by_velocity(impact_magnitude, velocity)
        
        # Update vibration floor for adaptive thresholding
        signature_intel.update_vibration_floor(impact_magnitude)
        adaptive_threshold = signature_intel.calculate_adaptive_threshold(base_threshold=15.0)
        
        # Classify with signal intelligence
        classification_result = classify_data(data)
        
        # Override event detection with adaptive threshold
        if impact_normalized < adaptive_threshold:
            classification_result['is_event'] = False
            classification_result['note'] = f"Below adaptive threshold: {adaptive_threshold:.2f}"
        
        # Signature analysis for FFT and road surface classification
        signature_data = {
            'dominant_frequency': 0,
            'spectral_centroid': 0,
            'event_type': 'UNKNOWN',
            'frequency_peak': 0,
            'road_surface': 'UNKNOWN'
        }
        
        # If event detected, perform spatial clustering with signature analysis
        if classification_result['classification'] == 'POTHOLE' and classification_result['is_event']:
            try:
                spatial_intel = get_spatial_intel()
                
                # Find nearby anomalies within 2-meter radius
                existing_anomalies = Anomaly.query.filter_by(is_active=True).all()
                anomaly_list = [{'id': a.id, 'latitude': a.latitude, 'longitude': a.longitude} 
                               for a in existing_anomalies]
                
                nearby_id = spatial_intel.find_nearby_anomaly(lat, lng, anomaly_list)
                
                if nearby_id:
                    # Update existing anomaly
                    existing = Anomaly.query.get(nearby_id)
                    if existing:
                        existing.hit_count += 1
                        existing.last_reported = datetime.utcnow()
                        existing.impact_magnitude = max(
                            existing.impact_magnitude or 0,
                            impact_magnitude
                        )
                        existing.severity_class = spatial_intel.determine_severity_class(
                            impact_magnitude
                        )
                        existing.confidence_score = spatial_intel.calculate_confidence_score(
                            existing.hit_count,
                            existing.last_reported
                        )
                        
                        db.session.commit()
                        
                        print(f"[CLUSTER UPDATE] Anomaly #{nearby_id} updated - Hits: {existing.hit_count}, "
                              f"Confidence: {existing.confidence_score:.3f}")
                        
                        return jsonify({
                            "status": "success",
                            "classification": classification_result,
                            "signature": signature_data,
                            "saved_to_db": True,
                            "clustered": True,
                            "anomaly_id": nearby_id,
                            "message": "Pothole detected and clustered with existing anomaly",
                            "debug": {
                                "coordinates": {"lat": lat, "lng": lng},
                                "impact_magnitude": impact_magnitude,
                                "impact_normalized": impact_normalized,
                                "adaptive_threshold": adaptive_threshold,
                                "gyro_correction": gyro_fusion,
                                "severity_score": classification_result['severity_score'],
                                "confidence": classification_result['confidence'],
                                "cluster_hit_count": existing.hit_count,
                                "cluster_confidence": existing.confidence_score
                            }
                        }), 201
                else:
                    # Create new anomaly entity with signature data
                    severity_class = spatial_intel.determine_severity_class(impact_magnitude)
                    
                    new_anomaly = Anomaly(
                        latitude=lat,
                        longitude=lng,
                        confidence_score=0.1,
                        hit_count=1,
                        impact_magnitude=impact_magnitude,
                        severity_class=severity_class,
                        first_reported=datetime.utcnow(),
                        last_reported=datetime.utcnow(),
                        frequency_peak=signature_data['frequency_peak'],
                        road_surface=signature_data['road_surface']
                    )
                    
                    db.session.add(new_anomaly)
                    db.session.commit()
                    
                    print(f"[NEW ANOMALY] Created #{new_anomaly.id} - Impact: {impact_magnitude:.2f}, "
                          f"Surface: {signature_data['road_surface']}")
                    
                    return jsonify({
                        "status": "success",
                        "classification": classification_result,
                        "signature": signature_data,
                        "saved_to_db": True,
                        "clustered": False,
                        "anomaly_id": new_anomaly.id,
                        "message": "New anomaly entity created",
                        "debug": {
                            "coordinates": {"lat": lat, "lng": lng},
                            "impact_magnitude": impact_magnitude,
                            "impact_normalized": impact_normalized,
                            "adaptive_threshold": adaptive_threshold,
                            "gyro_correction": gyro_fusion,
                            "severity_class": severity_class
                        }
                    }), 201
                
            except Exception as db_error:
                db.session.rollback()
                print(f"Database error: {db_error}")
                return jsonify({
                    "error": "Failed to save anomaly data",
                    "classification": classification_result,
                    "signature": signature_data
                }), 500
        
        # For non-events, return classification without saving
        return jsonify({
            "status": "success",
            "classification": classification_result,
            "signature": signature_data,
            "saved_to_db": False,
            "message": "Event threshold not exceeded",
            "debug": {
                "coordinates": {"lat": lat, "lng": lng},
                "impact_magnitude": impact_magnitude,
                "impact_normalized": impact_normalized,
                "adaptive_threshold": adaptive_threshold,
                "gyro_correction": gyro_fusion,
                "note": classification_result.get('note', 'Not saved - event threshold not exceeded')
            }
        }), 200
        
    except Exception as e:
        print(f"Telemetry processing error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/event', methods=['POST'])
@rate_limit(max_requests=20, window_seconds=60)
def process_event():
    """
    Process event-triggered upload from edge computing layer.
    v1.3.0: Accepts pre/post trigger windows with FFT signature analysis.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
        
        # Validate required fields
        required_fields = ['event_type', 'peak_magnitude', 'peak_coordinates', 
                          'pre_trigger_window', 'post_trigger_window']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {missing_fields}"}), 400
        
        event_type = data.get('event_type')
        peak_magnitude = data.get('peak_magnitude')
        peak_coords = data.get('peak_coordinates', {})
        pre_window = data.get('pre_trigger_window', [])
        post_window = data.get('post_trigger_window', [])
        
        # Optional v1.3.0 fields
        gyro_history = data.get('gyro_history', [])
        velocity = float(data.get('velocity', 20.0))
        
        lat = float(peak_coords.get('lat', 0))
        lng = float(peak_coords.get('lng', 0))
        
        # Basic coordinate validation
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            return jsonify({"error": "Invalid coordinates"}), 400
        
        # Get signature analysis instance
        signature_intel = get_signature_analysis()
        
        # Combine pre and post windows for FFT analysis
        full_window = pre_window + post_window
        
        # Perform FFT signature analysis
        fft_result = signature_intel.analyze_fft(full_window)
        
        # Classify road surface
        road_surface = signature_intel.classify_road_surface(full_window)
        
        # Detect swerve-to-avoid pattern
        swerve_result = signature_intel.detect_swerve_pattern(gyro_history, datetime.utcnow())
        
        # Normalize impact by velocity
        impact_normalized = signature_intel.normalize_by_velocity(peak_magnitude, velocity)
        
        # Classify the peak point
        peak_data = {
            'lat': lat,
            'lng': lng,
            'accel_x': 0,  # Will be extracted from window
            'accel_y': 0,
            'accel_z': 0
        }
        
        # Extract peak acceleration from post_window (first point is peak)
        if post_window:
            peak_point = post_window[0]
            peak_data['accel_x'] = peak_point.get('accel_x', 0)
            peak_data['accel_y'] = peak_point.get('accel_y', 0)
            peak_data['accel_z'] = peak_point.get('accel_z', 0)
        
        # Classify with signal intelligence
        classification_result = classify_data(peak_data)
        
        # If event detected, perform spatial clustering
        if classification_result['classification'] == 'POTHOLE' and classification_result['is_event']:
            try:
                spatial_intel = get_spatial_intel()
                
                # Find nearby anomalies within 2-meter radius
                existing_anomalies = Anomaly.query.filter_by(is_active=True).all()
                anomaly_list = [{'id': a.id, 'latitude': a.latitude, 'longitude': a.longitude} 
                               for a in existing_anomalies]
                
                nearby_id = spatial_intel.find_nearby_anomaly(lat, lng, anomaly_list)
                
                if nearby_id:
                    # Update existing anomaly
                    existing = Anomaly.query.get(nearby_id)
                    if existing:
                        existing.hit_count += 1
                        existing.last_reported = datetime.utcnow()
                        existing.impact_magnitude = max(
                            existing.impact_magnitude or 0,
                            peak_magnitude
                        )
                        existing.severity_class = spatial_intel.determine_severity_class(
                            peak_magnitude
                        )
                        existing.confidence_score = spatial_intel.calculate_confidence_score(
                            existing.hit_count,
                            existing.last_reported
                        )
                        existing.frequency_peak = fft_result['frequency_peak']
                        existing.is_avoided = swerve_result['is_avoided']
                        if not existing.road_surface:
                            existing.road_surface = road_surface
                        
                        db.session.commit()
                        
                        print(f"[EVENT CLUSTER] Anomaly #{nearby_id} updated via event upload - Hits: {existing.hit_count}, "
                              f"Surface: {road_surface}, Avoided: {swerve_result['is_avoided']}")
                        
                        return jsonify({
                            "status": "success",
                            "event_processed": True,
                            "clustered": True,
                            "anomaly_id": nearby_id,
                            "message": "Event processed and clustered with existing anomaly",
                            "signature": {
                                "fft_result": fft_result,
                                "road_surface": road_surface,
                                "swerve_detected": swerve_result
                            },
                            "window_stats": {
                                "pre_samples": len(pre_window),
                                "post_samples": len(post_window),
                                "peak_magnitude": peak_magnitude,
                                "impact_normalized": impact_normalized
                            }
                        }), 201
                else:
                    # Create new anomaly entity with signature data
                    severity_class = spatial_intel.determine_severity_class(peak_magnitude)
                    
                    new_anomaly = Anomaly(
                        latitude=lat,
                        longitude=lng,
                        confidence_score=0.1,
                        hit_count=1,
                        impact_magnitude=peak_magnitude,
                        severity_class=severity_class,
                        first_reported=datetime.utcnow(),
                        last_reported=datetime.utcnow(),
                        frequency_peak=fft_result['frequency_peak'],
                        is_avoided=swerve_result['is_avoided'],
                        road_surface=road_surface
                    )
                    
                    db.session.add(new_anomaly)
                    db.session.commit()
                    
                    print(f"[NEW EVENT ANOMALY] Created #{new_anomaly.id} - Impact: {peak_magnitude:.2f}, "
                          f"Surface: {road_surface}, Avoided: {swerve_result['is_avoided']}")
                    
                    return jsonify({
                        "status": "success",
                        "event_processed": True,
                        "clustered": False,
                        "anomaly_id": new_anomaly.id,
                        "message": "New anomaly entity created from event",
                        "signature": {
                            "fft_result": fft_result,
                            "road_surface": road_surface,
                            "swerve_detected": swerve_result
                        },
                        "window_stats": {
                            "pre_samples": len(pre_window),
                            "post_samples": len(post_window),
                            "peak_magnitude": peak_magnitude,
                            "impact_normalized": impact_normalized
                        }
                    }), 201
                
            except Exception as db_error:
                db.session.rollback()
                print(f"Database error: {db_error}")
                return jsonify({
                    "error": "Failed to save event data",
                    "classification": classification_result,
                    "signature": {
                        "fft_result": fft_result,
                        "road_surface": road_surface
                    }
                }), 500
        
        # For non-events, return classification without saving
        return jsonify({
            "status": "success",
            "event_processed": True,
            "saved_to_db": False,
            "message": "Event threshold not reached",
            "signature": {
                "fft_result": fft_result,
                "road_surface": road_surface
            },
            "window_stats": {
                "pre_samples": len(pre_window),
                "post_samples": len(post_window),
                "peak_magnitude": peak_magnitude
            }
        }), 200
        
    except Exception as e:
        print(f"Event processing error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/export/geojson', methods=['GET'])
def export_geojson():
    """
    Export anomalies as GeoJSON for offline navigation apps.
    v1.2.0: Lightweight export for external use.
    """
    try:
        anomalies = Anomaly.query.filter_by(is_active=True).all()
        
        features = []
        for anomaly in anomalies:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [anomaly.longitude, anomaly.latitude]
                },
                "properties": {
                    "id": anomaly.id,
                    "confidence": anomaly.confidence_score,
                    "hit_count": anomaly.hit_count,
                    "severity": anomaly.severity_class,
                    "impact_magnitude": anomaly.impact_magnitude,
                    "last_reported": anomaly.last_reported.isoformat()
                }
            })
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        return jsonify(geojson), 200
        
    except Exception as e:
        print(f"GeoJSON export error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/proximity', methods=['GET'])
def get_proximity_alerts():
    """
    Query for anomalies within a forward-looking cone (1km range).
    v1.2.0: Proximity Engine for proactive rider alerts.
    
    Query parameters:
    - lat: Current latitude
    - lng: Current longitude
    - heading: Vehicle heading in degrees (0-360)
    - range_m: Search range in meters (default: 1000)
    """
    try:
        lat = float(request.args.get('lat', 0))
        lng = float(request.args.get('lng', 0))
        heading = float(request.args.get('heading', 0))
        range_m = float(request.args.get('range_m', 1000))
        
        # Basic validation
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            return jsonify({"error": "Invalid coordinates"}), 400
        
        if not (0 <= heading <= 360):
            return jsonify({"error": "Invalid heading (must be 0-360)"}), 400
        
        # Get all active anomalies
        anomalies = Anomaly.query.filter_by(is_active=True).all()
        
        # Filter by distance and heading (forward-looking cone)
        # Cone angle: +/- 45 degrees from heading
        cone_angle = 45
        min_heading = (heading - cone_angle) % 360
        max_heading = (heading + cone_angle) % 360
        
        proximity_alerts = []
        for anomaly in anomalies:
            # Calculate distance using Haversine approximation
            lat1_rad = math.radians(lat)
            lat2_rad = math.radians(anomaly.latitude)
            delta_lat = math.radians(anomaly.latitude - lat)
            delta_lng = math.radians(anomaly.longitude - lng)
            
            a = (math.sin(delta_lat / 2) * math.sin(delta_lat / 2) +
                 math.cos(lat1_rad) * math.cos(lat2_rad) *
                 math.sin(delta_lng / 2) * math.sin(delta_lng / 2))
            
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            distance = 6371000 * c  # Earth radius in meters
            
            if distance <= range_m:
                # Calculate bearing to anomaly
                y = math.sin(delta_lng) * math.cos(lat2_rad)
                x = (math.cos(lat1_rad) * math.sin(lat2_rad) -
                     math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lng))
                bearing = math.degrees(math.atan2(y, x)) % 360
                
                # Check if within forward-looking cone
                in_cone = False
                if min_heading < max_heading:
                    in_cone = min_heading <= bearing <= max_heading
                else:  # Crossing 0/360 boundary
                    in_cone = bearing >= min_heading or bearing <= max_heading
                
                if in_cone:
                    # Determine alert level based on severity and distance
                    alert_level = "INFO"
                    if anomaly.severity_class == 3 and distance < 100:
                        alert_level = "CRITICAL"
                    elif anomaly.severity_class == 3 and distance < 200:
                        alert_level = "WARNING"
                    elif anomaly.severity_class == 2 and distance < 50:
                        alert_level = "WARNING"
                    
                    proximity_alerts.append({
                        "anomaly_id": anomaly.id,
                        "lat": anomaly.latitude,
                        "lng": anomaly.longitude,
                        "distance_m": round(distance, 1),
                        "bearing": round(bearing, 1),
                        "severity": anomaly.severity_class,
                        "confidence": anomaly.confidence_score,
                        "impact_magnitude": anomaly.impact_magnitude,
                        "alert_level": alert_level
                    })
        
        # Sort by distance (closest first)
        proximity_alerts.sort(key=lambda x: x['distance_m'])
        
        return jsonify({
            "current_position": {"lat": lat, "lng": lng, "heading": heading},
            "search_range_m": range_m,
            "cone_angle": cone_angle,
            "alerts": proximity_alerts,
            "critical_alerts": [a for a in proximity_alerts if a['alert_level'] == 'CRITICAL'],
            "warning_alerts": [a for a in proximity_alerts if a['alert_level'] == 'WARNING']
        }), 200
        
    except Exception as e:
        print(f"Proximity query error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Use environment PORT for Render compatibility
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
