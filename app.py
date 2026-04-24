import os
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
from potholenet import classify_data

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

# 4. Define Database Models
class RoadSegment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    quality_score = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "lat": self.latitude, 
            "lng": self.longitude, 
            "quality": self.quality_score,
            "time": self.timestamp.isoformat()
        }

# 5. Create Database Tables (Run once on startup)
with app.app_context():
    db.create_all()

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
        new_segment = RoadSegment(
            latitude=float(data['lat']),
            longitude=float(data['lng']),
            quality_score=int(data['quality'])
        )
        db.session.add(new_segment)
        db.session.commit()
        return jsonify({"message": "Success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/roads', methods=['GET'])
def get_roads():
    try:
        segments = RoadSegment.query.all()
        return jsonify([s.to_dict() for s in segments])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/telemetry', methods=['POST'])
def process_telemetry():
    """
    Process real-time telemetry data and classify road quality.
    Accepts sensor data, classifies using PotholeNet, and saves pothole detections.
    """
    try:
        # Validate incoming JSON
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
        
        # Required fields validation
        required_fields = ['lat', 'lng', 'accel_z']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {missing_fields}"}), 400
        
        # Validate data types and ranges
        try:
            lat = float(data['lat'])
            lng = float(data['lng'])
            accel_z = float(data['accel_z'])
            
            # Basic coordinate validation
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                return jsonify({"error": "Invalid coordinates"}), 400
                
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid data types for coordinates or acceleration"}), 400
        
        # Classify the sensor data
        classification_result = classify_data(data)
        
        # If pothole detected, save to database
        if classification_result['classification'] == 'POTHOLE':
            try:
                # Map classification to quality score (2 = pothole)
                quality_score = 2
                
                new_segment = RoadSegment(
                    latitude=lat,
                    longitude=lng,
                    quality_score=quality_score
                )
                
                db.session.add(new_segment)
                db.session.commit()
                
                # Detailed logging for verification
                print(f"[DATABASE COMMIT] Pothole saved - Lat: {lat} (type: {type(lat).__name__}), "
                      f"Lng: {lng} (type: {type(lng).__name__}), "
                      f"Severity: {classification_result['severity_score']} (type: {type(classification_result['severity_score']).__name__}), "
                      f"Quality Score: {quality_score}")
                
                return jsonify({
                    "status": "success",
                    "classification": classification_result,
                    "saved_to_db": True,
                    "message": "Pothole detected and saved",
                    "debug": {
                        "coordinates": {"lat": lat, "lng": lng},
                        "severity_score": classification_result['severity_score'],
                        "confidence": classification_result['confidence'],
                        "database_quality_score": quality_score
                    }
                }), 201
                
            except Exception as db_error:
                db.session.rollback()
                print(f"Database error: {db_error}")
                return jsonify({
                    "error": "Failed to save pothole data",
                    "classification": classification_result
                }), 500
        
        # For smooth roads, just return classification without saving
        return jsonify({
            "status": "success",
            "classification": classification_result,
            "saved_to_db": False,
            "message": "Smooth road detected",
            "debug": {
                "coordinates": {"lat": lat, "lng": lng},
                "severity_score": classification_result['severity_score'],
                "confidence": classification_result['confidence'],
                "note": "Not saved to database - only potholes are stored"
            }
        }), 200
        
    except Exception as e:
        print(f"Telemetry processing error: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Use environment PORT for Render compatibility
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
