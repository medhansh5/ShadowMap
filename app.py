import os
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Database Configuration
# Use DATABASE_URL environment variable for PostgreSQL on Render later
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///shadowmap.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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
            "quality": self.quality_score
        }

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
    try:
        new_segment = RoadSegment(
            latitude=data['lat'],
            longitude=data['lng'],
            quality_score=data['quality']
        )
        db.session.add(new_segment)
        db.session.commit()
        return jsonify({"message": "Success"}), 201
    except:
        return jsonify({"error": "Invalid data"}), 400

@app.route('/roads', methods=['GET'])
def get_roads():
    segments = RoadSegment.query.all()
    return jsonify([s.to_dict() for s in segments])

if __name__ == '__main__':
    app.run(debug=True)
