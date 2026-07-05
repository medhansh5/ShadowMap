import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import pytest
from app import app, db, Anomaly, TelemetryBuffer

@pytest.fixture
def client():
    # Configure app for testing
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' # Use RAM, not disk
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()

def test_upload_valid_data(client):
    """Test uploading a standard road quality reading."""
    payload = {"lat": 28.66, "lng": 77.35, "quality": 0}
    response = client.post('/upload', json=payload)
    
    assert response.status_code == 201
    assert response.get_json()['message'] == "Success"

def test_upload_missing_fields(client):
    """Test that the API rejects incomplete data."""
    payload = {"lat": 28.66} # Missing lng and quality
    response = client.post('/upload', json=payload)
    
    assert response.status_code == 400
    assert "Missing data fields" in response.get_json()['error']

def test_get_roads_returns_list(client):
    """Test that /roads returns a list even if empty."""
    # 1. Test empty state
    response = client.get('/roads')
    assert response.status_code == 200
    assert isinstance(response.get_json(), list)
    assert len(response.get_json()) == 0

    # 2. Add data and check again
    client.post('/upload', json={"lat": 1.0, "lng": 1.0, "quality": 1})
    response = client.get('/roads')
    assert len(response.get_json()) == 1
    assert response.get_json()[0]['lat'] == 1.0

def test_invalid_data_types(client):
    """Test behavior when strings are sent instead of floats."""
    payload = {"lat": "not-a-number", "lng": "somewhere", "quality": "bad"}
    response = client.post('/upload', json=payload)
    
    assert response.status_code == 500

def test_api_event_physics(client):
    """Test v1.4 /api/event endpoint with deep physics fields."""
    payload = {
        "event_type": "ANOMALY_DETECTED",
        "peak_magnitude": 25.0,
        "peak_coordinates": {"lat": 12.9716, "lng": 77.5946},
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
        "estimated_depth": 45.8,
        "rider_id": "pytest_rider",
        "bottom_out": False,
        "heading": 45.5,
        "suspension_travel": 35.2,
        "physics_confidence": 0.85
    }
    response = client.post('/api/event', json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data['status'] == "success"
    
    # Verify saved in db
    with app.app_context():
        anomaly = db.session.query(Anomaly).first()
        assert anomaly is not None
        assert anomaly.estimated_depth == 45.8
        assert anomaly.rider_id == "pytest_rider"
