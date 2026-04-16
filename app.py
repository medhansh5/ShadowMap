import os
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime

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

if __name__ == '__main__':
    # Use environment PORT for Render compatibility
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
