import pytest
from app import app, db, RoadSegment

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
    assert response.get_json()['message'] == "Data received successfully"

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
    # Flask-SQLAlchemy/SQLite might try to cast strings, 
    # but sending completely garbage data should be handled.
    payload = {"lat": "not-a-number", "lng": "somewhere", "quality": "bad"}
    response = client.post('/upload', json=payload)
    
    # This will likely trigger the 'except' block in our app.py
    assert response.status_code == 500
