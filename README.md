# 🗺️ ShadowMap v1.3.0

**ShadowMap** is a crowdsourced road quality mapping platform that transforms motorcycle telemetry data into a live, color-coded map of road conditions using advanced signal processing, spatial intelligence, synthetic intelligence (FFT analysis), and multi-sensor fusion for proactive rider alerts.

The project is an evolution of **PotholeNet**, specifically tuned to filter out the high-vibration profile of a Royal Enfield Classic 350 engine ("The Baron") to detect road anomalies with spatial confidence scoring, predictive hazard warnings, and signature-based classification.

## 🚀 Features

* **🔬 Signal Intelligence:** High-pass filter removes gravity (1g) and low-frequency vehicle sway from Z-axis data
* **⚡ Impact Magnitude:** Calculates total acceleration force: M = √(ax² + ay² + az²)
* **🪟 Sliding Window Detection:** 500ms event detection window for real-time anomaly identification
* **🗺️ Spatial Clustering:** Groups nearby telemetry points within 2-meter radius into single anomaly entities
* **📈 Confidence Scoring:** Exponential decay formula: C = Σ(Reports) × e^(-λt) for temporal intelligence
* **🤖 Real-time Classification:** Scikit-learn powered classification with severity classes (Minor/Moderate/Major)
* **📡 Live Telemetry API:** RESTful endpoint `/api/telemetry` for 3-axis accelerometer data processing
* **🗄️ Intelligent Storage:** PostgreSQL/SQLite with anomaly clustering and confidence tracking
* **🎨 Confidence Heatmaps:** Leaflet.js visualization with Sharp Red (high confidence) to Faded Amber (decaying)
* **🎯 Rider HUD v3:** High-contrast overlay with proximity alerts, hazard detection, road surface type, and 1000m range
* **📲 Edge Computing:** Event-triggered uploads with 250ms pre/post trigger windows for battery/data efficiency
* **⚠️ Proximity Alerts:** Forward-looking cone (1km) with heading-based hazard detection
* **🔊 Critical Warnings:** Audio and visual alerts for hazards within 100m of trajectory
* **📄 GeoJSON Export:** Lightweight export for offline navigation app integration
* **🛡️ Rate Limiting:** API protection against abuse (30 req/min for telemetry, 20 req/min for events)
* **🧪 Virtual Test Bench:** Comprehensive testing suite for signal intelligence validation
* **🎵 Signature Analysis (v1.3.0):** FFT-based frequency domain analysis to differentiate impulse vs periodic events
* **🔄 Multi-Sensor Fusion (v1.3.0):** Gyroscope integration with leaning angle compensation (a_corrected = a_z × cos(θ))
* **🚗 Swerve Detection (v1.3.0):** Detects "Swerved-to-Avoid" patterns with high-G turn analysis
* **📊 Adaptive Thresholding (v1.3.0):** Dynamic gain control based on vibration floor for off-road conditions
* **🏃 Velocity Scaling (v1.3.0):** Normalizes impact by velocity: M_normalized = M / v²
* **🛣️ Road Surface Classification (v1.3.0):** Classifies surface type (Pavement, Gravel, Cobblestone) via FFT background noise

## 🛠️ Tech Stack

* **Backend:** Python, Flask, SQLAlchemy, PostgreSQL/SQLite
* **Frontend:** HTML5, Leaflet.js, JavaScript (ES6)
* **ML/Signal Processing:** Scikit-learn, NumPy, SciPy, Pandas
* **Testing:** Custom test suite with automated validation
* **Deployment:** Render (API), Static hosting (Frontend)

## 📂 Project Structure

```text
shadowmap/
├── app.py              # Flask API with signal intelligence, spatial clustering, rate limiting
├── potholenet.py       # Signal Intelligence + ML + Edge Computing + SignatureAnalysis (v1.3.0)
├── test_shadowmap.py   # Virtual Test Bench v1.3.0 - signal intelligence + proximity + signature tests
├── requirements.txt    # Python dependencies
├── migrations/
│   └── 001_create_anomalies_table.sql  # Database migration for v1.1.0
├── static/
│   ├── js/map.js       # Confidence heatmaps + Rider HUD v3 + Proximity WebWorker
│   ├── js/proximity-worker.js  # WebWorker for proximity checks (2s interval)
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
Process real-time 3-axis telemetry data with signal intelligence and spatial clustering.
**Rate Limited:** 30 requests per minute

**Request (v1.3.0):**
```json
{
  "lat": 28.6692,
  "lng": 77.3538,
  "accel_x": 2.5,
  "accel_y": 1.8,
  "accel_z": -25.0,
  "gyro_x": 0.1,
  "gyro_y": 0.1,
  "gyro_z": 0.1,
  "velocity": 20.0
}
```

**Response (v1.3.0):**
```json
{
  "status": "success",
  "classification": {
    "classification": "POTHOLE",
    "severity_score": 0.9,
    "confidence": 0.85,
    "impact_magnitude": 25.2,
    "is_event": true,
    "lat": 28.6692,
    "lng": 77.3538
  },
  "signature": {
    "dominant_frequency": 15.5,
    "spectral_centroid": 8.2,
    "event_type": "IMPULSE",
    "frequency_peak": 3.2,
    "road_surface": "PAVEMENT"
  },
  "saved_to_db": true,
  "clustered": false,
  "anomaly_id": 1,
  "message": "New anomaly entity created",
  "debug": {
    "coordinates": {"lat": 28.6692, "lng": 77.3538},
    "impact_magnitude": 25.2,
    "impact_normalized": 2.52,
    "adaptive_threshold": 15.0,
    "gyro_correction": {
      "accel_z_corrected": -24.8,
      "lean_angle": 0.1,
      "correction_factor": 0.99,
      "is_turning": false
    }
  }
}
```

### POST /api/event (v1.3.0)
Process event-triggered upload from edge computing layer with pre/post trigger windows and signature analysis.
**Rate Limited:** 20 requests per minute

**Request (v1.3.0):**
```json
{
  "event_type": "ANOMALY_DETECTED",
  "peak_magnitude": 25.0,
  "peak_coordinates": {
    "lat": 28.6692,
    "lng": 77.3538
  },
  "pre_trigger_window": [
    {"lat": 28.6692, "lng": 77.3538, "accel_x": 0.1, "accel_y": 0.1, "accel_z": -9.8, "timestamp": "2026-04-30T14:30:00"},
    {"lat": 28.6692, "lng": 77.3538, "accel_x": 0.2, "accel_y": 0.2, "accel_z": -10.0, "timestamp": "2026-04-30T14:30:01"}
  ],
  "post_trigger_window": [
    {"lat": 28.6692, "lng": 77.3538, "accel_x": 2.5, "accel_y": 1.8, "accel_z": -25.0, "timestamp": "2026-04-30T14:30:02"},
    {"lat": 28.6692, "lng": 77.3538, "accel_x": 2.3, "accel_y": 1.6, "accel_z": -22.0, "timestamp": "2026-04-30T14:30:03"}
  ],
  "gyro_history": [
    {"gyro_x": 0.1, "gyro_y": 0.1, "gyro_z": 0.1, "timestamp": "2026-04-30T14:30:00"},
    {"gyro_x": 0.1, "gyro_y": 0.1, "gyro_z": 0.1, "timestamp": "2026-04-30T14:30:01"}
  ],
  "velocity": 20.0,
  "window_duration_ms": 40,
  "sampling_rate": 100
}
```

**Response (v1.3.0):**
```json
{
  "status": "success",
  "event_processed": true,
  "clustered": false,
  "anomaly_id": 1,
  "message": "New anomaly entity created from event",
  "signature": {
    "fft_result": {
      "dominant_frequency": 15.5,
      "spectral_centroid": 8.2,
      "event_type": "IMPULSE",
      "frequency_peak": 3.2
    },
    "road_surface": "PAVEMENT",
    "swerve_detected": {
      "is_avoided": false,
      "swerve_magnitude": 0.14
    }
  },
  "window_stats": {
    "pre_samples": 2,
    "post_samples": 2,
    "peak_magnitude": 25.0,
    "impact_normalized": 2.52
  }
}
```

### GET /api/proximity (v1.2.0)
Query for anomalies within a forward-looking cone (1km range) for proactive rider alerts.

**Query Parameters:**
- `lat`: Current latitude
- `lng`: Current longitude
- `heading`: Vehicle heading in degrees (0-360)
- `range_m`: Search range in meters (default: 1000)

**Response (v1.2.0):**
```json
{
  "current_position": {"lat": 28.6692, "lng": 77.3538, "heading": 45},
  "search_range_m": 1000,
  "cone_angle": 45,
  "alerts": [
    {
      "anomaly_id": 1,
      "lat": 28.6695,
      "lng": 77.3542,
      "distance_m": 85.3,
      "bearing": 47.2,
      "severity": 3,
      "confidence": 0.85,
      "impact_magnitude": 25.0,
      "alert_level": "CRITICAL"
    }
  ],
  "critical_alerts": [...],
  "warning_alerts": [...]
}
```

### GET /api/export/geojson (v1.2.0)
Export anomalies as GeoJSON for offline navigation apps.

**Response (v1.2.0):**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [77.3538, 28.6692]
      },
      "properties": {
        "id": 1,
        "confidence": 0.85,
        "hit_count": 3,
        "severity": 3,
        "impact_magnitude": 25.0,
        "last_reported": "2026-04-30T14:30:00"
      }
    }
  ]
}
```

### GET /roads
Retrieve all active anomalies with confidence scores for heatmap visualization.

## 🎨 Map Visualization Features (v1.3.0)

* **Confidence Heatmaps:** Sharp Red (>0.7 confidence) to Faded Amber (<0.2) for temporal decay visualization
* **Dynamic Opacity:** Higher confidence = more opaque (0.3-0.9 range)
* **Size Scaling:** Marker radius dynamically scaled from 3px to 12px based on confidence
* **Rider HUD v3:** High-contrast overlay with proximity alerts, hazard detection, road surface type, and 1000m range
* **Proximity Engine:** WebWorker-based forward-looking cone (1km, ±45° heading) for proactive alerts
* **Critical Warnings:** Audio alerts and screen flash for hazards within 100m
* **Warning Alerts:** Softer audio tones for hazards within 200m
* **Real-time Updates:** Automatic refresh every 10 seconds with memory-efficient marker management
* **Interactive Popups:** Click markers to view anomaly ID, confidence %, severity class, hit count, impact magnitude, road surface, and swerve status
* **Road Surface Display:** HUD shows dominant surface type (Pavement, Gravel, Cobblestone) with color coding

## 🧪 Virtual Test Bench

The `test_shadowmap.py` script provides comprehensive system testing:

### Test Scenarios (v1.3.0)
- **Scenario A:** Major Pothole (3-axis high impact + Gyro) → New anomaly entity created
- **Scenario B:** Same Location (Clustering test) → Updates existing anomaly, increases hit count
- **Scenario C:** Sharp Turn (Gyro Compensation test) → Gyro fusion reduces false positives during turns
- **Scenario D:** Smooth Road → Classification returned, not saved
- **Event A:** Event-Triggered Upload (Signature Analysis) → FFT analysis + road surface classification
- **Proximity Test:** Forward-looking cone query → Hazard detection within 1km
- **GeoJSON Export:** Data export → Offline navigation app integration

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

## 📊 Signal Processing Pipeline (v1.3.0)

1. **Data Collection:** 3-axis accelerometer data at 100Hz (ax, ay, az) + gyroscope data (ωx, ωy, ωz) + velocity
2. **Gravity Removal:** High-pass filter removes 1g gravity and low-frequency vehicle sway
3. **Impact Magnitude:** Calculate M = √(ax² + ay² + az²) for total acceleration force
4. **Multi-Sensor Fusion:** Gyroscope fusion with leaning angle compensation (a_corrected = a_z × cos(θ))
5. **Velocity Scaling:** Normalize impact by velocity (M_normalized = M / v²) since impact force increases with velocity
6. **Sliding Window Detection:** 500ms window identifies events exceeding threshold
7. **Adaptive Thresholding:** Dynamic gain control based on vibration floor (raises threshold in high-vibration environments)
8. **Edge Computing:** Event-triggered uploads with 250ms pre/post trigger windows (battery/data efficiency)
9. **Signature Analysis:** FFT frequency domain analysis to differentiate impulse vs periodic events
10. **Road Surface Classification:** Classifies surface type (Pavement, Gravel, Cobblestone) via FFT background noise
11. **Swerve Detection:** Detects "Swerved-to-Avoid" patterns with high-G turn analysis
12. **Feature Extraction:** RMS, Standard Deviation, Peak Magnitude, Peak-to-Peak from filtered data
13. **Classification:** Random Forest with severity classes (Minor/Moderate/Major)
14. **Spatial Clustering:** Groups nearby points within 2-meter radius into anomaly entities
15. **Confidence Scoring:** Exponential decay C = Σ(Reports) × e^(-λt) for temporal intelligence
16. **Storage:** PostgreSQL/SQLite with hit counts, confidence scores, impact magnitudes, frequency peaks, road surface, and swerve status
17. **Proximity Engine:** Forward-looking cone (1km, ±45°) with heading-based hazard detection
18. **Proactive Alerts:** WebWorker-based checks every 2 seconds with audio/visual warnings
19. **Visualization:** Confidence-based heatmaps with Rider HUD v3 overlay

## 🚀 Live Demo

View the live crowdsourced road quality map:
[https://shadowmap-api.onrender.com](https://shadowmap-api.onrender.com)

## 📝 Development Notes

### Database Schema (v1.1.0)
```sql
CREATE TABLE anomalies (
    id SERIAL PRIMARY KEY,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    confidence_score FLOAT NOT NULL DEFAULT 0.0,
    hit_count INTEGER NOT NULL DEFAULT 1,
    first_reported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_reported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    impact_magnitude FLOAT,
    severity_class INTEGER NOT NULL DEFAULT 1,  -- 1=Minor, 2=Moderate, 3=Major
    cluster_radius FLOAT DEFAULT 2.0,
    is_active BOOLEAN DEFAULT TRUE
);
```

### Severity Class Mapping
- **1:** Minor (Impact < 15.0 m/s²)
- **2:** Moderate (Impact 15.0-25.0 m/s²)
- **3:** Major (Impact > 25.0 m/s²)

### Confidence Visualization
- **>0.7:** Sharp Red (#e63946) - High Confidence
- **0.4-0.7:** Orange (#f4a261) - Medium Confidence
- **0.2-0.4:** Amber (#e9c46a) - Low Confidence
- **<0.2:** Faded Gray (#8d99ae) - Very Low Confidence

## 🔍 Calibration & Tuning (v1.3.0)

Use the Virtual Test Bench to calibrate signal intelligence parameters:

1. Run `python test_shadowmap.py`
2. Adjust 3-axis acceleration values (ax, ay, az) to test signal intelligence
3. Verify spatial clustering (Scenario B should cluster with Scenario A)
4. Monitor confidence decay over time (λ = 0.1 per hour)
5. Fine-tune event threshold in `SignalIntelligence` class (default: 15.0 m/s²)
6. Adjust clustering radius in `SpatialIntelligence` class (default: 2.0 meters)
7. Verify confidence-based heatmaps on the live map
8. Check Rider HUD displays correct hazard statistics
9. Test event-triggered uploads with pre/post trigger windows (250ms)
10. Adjust proximity cone angle (default: ±45°) and range (default: 1000m)
11. Calibrate alert thresholds (Critical: <100m, Warning: <200m)
12. Verify GeoJSON export works for offline navigation apps
13. Test gyroscope fusion for leaning angle compensation (a_corrected = a_z × cos(θ))
14. Verify FFT signature analysis classifies impulse vs periodic events
15. Check adaptive thresholding adjusts for vibration floor (off-road conditions)
16. Validate velocity-based magnitude scaling (M_normalized = M / v²)
17. Test swerve-to-avoid detection with high-G turns (threshold: 2.0 rad/s)
18. Verify road surface classification (Pavement, Gravel, Cobblestone) via FFT background noise

## 📄 License

This project is part of the PotholeNet road quality monitoring initiative under the MIT license.

## 🤝 Contributing

Contributions welcome! Key areas for enhancement:
- Additional sensor fusion (GPS accuracy, speed correlation, gyroscope)
- Advanced ML models (LSTM for temporal patterns, Transformer architectures)
- Mobile app development for event-triggered telemetry collection
- Enhanced WebWorker optimization for proximity checks
- PostGIS spatial indexing for faster proximity queries
- Offline-first architecture with local anomaly caching
- Real-time WebSocket updates for live hazard tracking
- Integration with navigation APIs (Google Maps, Mapbox)

---

**ShadowMap** - Making roads safer, one data point at a time. 🏍️📊
