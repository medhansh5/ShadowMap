# 🗺️ ShadowMap v1.0

**ShadowMap** is a crowdsourced road quality mapping platform that transforms motorcycle telemetry data into a live, color-coded map of road conditions using signal processing and machine learning.

The project is an evolution of **PotholeNet**, specifically tuned to filter out the high-vibration profile of a Royal Enfield Classic 350 engine ("Shadow") to detect road anomalies accurately.

## 🚀 Features

* **🔬 Vibration Isolation:** Uses a 4th-order Butterworth High-Pass filter (12Hz) to separate road data from engine noise
* **🤖 Real-time Classification:** Scikit-learn powered classification of road segments (Smooth, Bumpy, Pothole)
* **📡 Live Telemetry API:** RESTful endpoint `/api/telemetry` for real-time sensor data processing
* **🗄️ Intelligent Storage:** Automatic PostgreSQL/SQLite database storage for pothole detections only
* **🎨 Dynamic Visualization:** Interactive Leaflet.js map with severity-based styling and real-time updates
* **🧪 Virtual Test Bench:** Comprehensive testing suite for system validation and calibration

## 🛠️ Tech Stack

* **Backend:** Python, Flask, SQLAlchemy, PostgreSQL/SQLite
* **Frontend:** HTML5, Leaflet.js, JavaScript (ES6)
* **ML/Signal Processing:** Scikit-learn, NumPy, SciPy, Pandas
* **Testing:** Custom test suite with automated validation
* **Deployment:** Render (API), Static hosting (Frontend)

## 📂 Project Structure

```text
shadowmap/
├── app.py              # Flask API with telemetry processing & database logic
├── potholenet.py       # Core ML engine with Butterworth filtering & classification
├── test_shadowmap.py   # Virtual Test Bench - comprehensive testing suite
├── requirements.txt    # Python dependencies
├── static/
│   ├── js/map.js       # Dynamic Leaflet.js map with real-time updates
│   └── README.md       # Static assets documentation
├── templates/
│   └── index.html      # Main map interface
└── potholenet_v1.pkl   # Trained ML model (generated after training)
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL (optional, defaults to SQLite for development)

### Installation

```bash
# Clone and setup
git clone https://github.com/medhansh5/shadowmap.git
cd shadowmap
pip install -r requirements.txt

# Start the Flask server
python app.py
```

### Testing the System

```bash
# Run the Virtual Test Bench (requires Flask server running)
python test_shadowmap.py
```

## 📡 API Endpoints

### POST /api/telemetry
Process real-time telemetry data and classify road quality.

**Request:**
```json
{
  "lat": 28.6692,
  "lng": 77.3538,
  "accel_z": -20.5
}
```

**Response:**
```json
{
  "status": "success",
  "classification": {
    "classification": "POTHOLE",
    "severity_score": 0.9,
    "confidence": 0.85,
    "lat": 28.6692,
    "lng": 77.3538
  },
  "saved_to_db": true,
  "message": "Pothole detected and saved",
  "debug": {
    "coordinates": {"lat": 28.6692, "lng": 77.3538},
    "severity_score": 0.9,
    "confidence": 0.85,
    "database_quality_score": 2
  }
}
```

### GET /roads
Retrieve all stored road quality data for map visualization.

## 🎨 Map Visualization Features

* **Dynamic Styling:** Markers colored by severity (Deep Red >0.8, Orange 0.5-0.8, Yellow <0.5)
* **Size Scaling:** Marker radius dynamically scaled from 3px to 10px based on severity
* **Real-time Updates:** Automatic refresh every 10 seconds with memory-efficient marker management
* **Visual Enhancement:** White stroke borders and 0.9 fill opacity for visibility

## 🧪 Virtual Test Bench

The `test_shadowmap.py` script provides comprehensive system testing:

### Test Scenarios
- **Scenario A:** Major Pothole (`accel_z: -20.5`) → Deep Red marker
- **Scenario B:** Minor Bump (`accel_z: -12.0`) → Orange/Yellow marker
- **Scenario C:** Smooth Road (`accel_z: -9.8`) → No database entry

### Validation Features
- HTTP status code verification
- Classification result validation
- Database commit confirmation
- Log comparison guidance
- Calibration support for PotholeNet tuning

## 🔧 Hardware Setup

**Reference Configuration:**
- **Device:** Oppo F23 5G (Inertial sensors @ 100Hz)
- **Mount:** Royal Enfield Classic 350 ("The Baron")
- **Data Rate:** 100Hz sampling frequency
- **Filter:** 4th-order Butterworth High-Pass at 12Hz

## 📊 Signal Processing Pipeline

1. **Data Collection:** Accelerometer data at 100Hz
2. **Noise Filtering:** Butterworth High-Pass filter removes engine vibrations
3. **Feature Extraction:** RMS, Standard Deviation, Peak Magnitude, Peak-to-Peak
4. **Classification:** Random Forest with probability-based severity scoring
5. **Storage:** Selective database storage for pothole detections only
6. **Visualization:** Real-time map updates with dynamic styling

## 🚀 Live Demo

View the live crowdsourced road quality map:
[https://shadowmap-api.onrender.com](https://shadowmap-api.onrender.com)

## 📝 Development Notes

### Database Schema
```sql
CREATE TABLE road_segment (
    id INTEGER PRIMARY KEY,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    quality_score INTEGER NOT NULL,  -- 0=Smooth, 1=Bumpy, 2=Pothole
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Quality Score Mapping
- **0:** Smooth road (not stored in database)
- **1:** Bumpy road (moderate severity)
- **2:** Pothole (high severity, stored in database)

### Severity Visualization
- **>0.8:** Deep Red (#e63946) - Major Pothole
- **0.5-0.8:** Orange (#f4a261) - Moderate Bump  
- **<0.5:** Yellow (#e9c46a) - Minor Wear

## 🔍 Calibration & Tuning

Use the Virtual Test Bench to calibrate PotholeNet sensitivity:

1. Run `python test_shadowmap.py`
2. Adjust `accel_z` values in test scenarios
3. Monitor classification results and database commits
4. Fine-tune Butterworth filter parameters in `potholenet.py`
5. Verify visual results on the live map

## 📄 License

This project is part of the PotholeNet road quality monitoring initiative under the MIT license.

## 🤝 Contributing

Contributions welcome! Key areas for enhancement:
- Additional sensor fusion (GPS accuracy, speed correlation)
- Advanced ML models (LSTM for temporal patterns)
- Mobile app development for telemetry collection
- Enhanced visualization features

---

**ShadowMap** - Making roads safer, one data point at a time. 🏍️📊
