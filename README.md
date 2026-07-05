# 🗺️ ShadowMap v1.5.0 — Crowdsourced Road Quality Mapping & Cyberpunk Rider HUD

**ShadowMap** is an advanced crowdsourced road quality mapping platform that transforms motorcycle telemetry data into a live, color-coded map of road conditions. Using real-time signal processing, Kalman filtering, suspension physics modeling, synthetic intelligence (FFT analysis), and multi-sensor fusion, ShadowMap delivers proactive rider alerts and comprehensive mission analytics.

The project is an evolution of **PotholeNet**, specifically tuned to filter out the high-vibration profile of a Royal Enfield Classic 350 engine ("The Baron") to detect road anomalies with spatial confidence scoring, predictive hazard warnings, and signature-based classification.

---

## 🌟 What's New in v1.5.0 & v1.4.0

* **🌌 Cyberpunk Rider HUD v1.5.0:** High-contrast neon-glow interface styled with Google Fonts (`Orbitron`, `Share Tech Mono`), glassmorphism overlays, glitch animations, and dynamic SVG grip/lean meters.
* **🔊 Web Audio API Synthesizer & Haptics:** Real-time on-device acoustic alarms and customized haptic pulse patterns (`navigator.vibrate`) differentiating road bumps from severe bottom-out suspension events.
* **⚡ Mission Control Analytics Drawer:** Live in-HUD dashboard tracking **Total Hits**, **Max Suspension Depth (mm)**, and **Max G-Force (g)** in real time.
* **📥 One-Click GeoJSON Export:** Instant compilation and download of Kalman-filtered rider trajectories and anomaly markers into standard GeoJSON FeatureCollections (`shadowmap_mission_<timestamp>.geojson`).
* **🏍️ Suspension Physics Modeling (v1.4.0):** Double integration of Z-axis acceleration to estimate physical pothole depth (mm) and calculate suspension travel percentage.
* **💥 Bottom-Out Detection (v1.4.0):** Immediate alert triggering when estimated pothole depth exceeds maximum suspension travel thresholds.
* **🛰️ Kalman Filtered GPS Tracking (v1.4.0):** State-space smoothing for latitude, longitude, velocity, and heading to eliminate GPS jitter.
* **🧪 Master Test Suite Runner (`test_suite_all.py`):** Unified automated testing across mathematical, database, and API layers.

---

## 🚀 Core Features

* **🔬 Signal Intelligence:** 4th-order Butterworth High-Pass filter removes gravity (1g) and low-frequency vehicle sway from Z-axis data.
* **⚡ Impact Magnitude:** Calculates total acceleration force: M = √(ax² + ay² + az²).
* **🪟 Sliding Window Detection:** 500ms event detection window for real-time anomaly identification.
* **🗺️ Spatial Clustering:** Groups nearby telemetry points within a 2-meter radius into single anomaly entities.
* **📈 Confidence Scoring:** Exponential decay formula: C = Σ(Reports) × e^(-λt) for temporal intelligence.
* **🤖 Real-Time ML Classification:** Scikit-learn powered classification with severity classes (Minor/Moderate/Major).
* **📡 Live Telemetry API:** RESTful endpoints (`/api/telemetry`, `/api/event`, `/api/telemetry/batch`) with rate limiting and UTF-8 encoding protection.
* **🗄️ Intelligent Storage:** SQLAlchemy 2.0 compliant PostgreSQL/SQLite database with anomaly clustering and confidence tracking.
* **🎨 Confidence Heatmaps:** Leaflet.js visualization shifting from Sharp Red (high confidence) to Faded Amber (decaying).
* **⚠️ Proximity Alerts:** WebWorker-powered forward-looking cone (1km range, ±45° heading) with audio/visual warnings.
* **🎵 Signature Analysis:** FFT-based frequency domain analysis to differentiate impulse vs periodic events and classify road surfaces (Pavement, Gravel, Cobblestone).
* **🔄 Multi-Sensor Fusion:** Gyroscope integration with leaning angle compensation (a_corrected = a_z × cos(θ)) and swerve avoidance detection.

---

## 🛠️ Tech Stack

* **Backend:** Python 3.10+, Flask, SQLAlchemy 2.0, PostgreSQL/SQLite, Flask-CORS
* **Frontend:** HTML5, CSS3 Glassmorphism, Leaflet.js, JavaScript (ES6), Web Audio API, Service Worker PWA
* **ML/Signal Processing:** Scikit-learn, NumPy, SciPy, Pandas
* **Testing:** PyTest, Custom Virtual Test Bench, Master Test Runner (`test_suite_all.py`)
* **Deployment:** Render (API), Static hosting / Flask-served PWA

---

## 📂 Project Structure

```text
shadowmap/
├── app.py              # Flask API with signal/suspension intelligence, clustering, rate limiting
├── potholenet.py       # Signal Intelligence + ML + Kalman Filter + Suspension Physics (v1.4/v1.5)
├── test_suite_all.py   # Master Test Runner executing all unit & integration suites (v1.5.0)
├── test_shadowmap.py   # Virtual Test Bench - live simulation & scenario testing
├── test_physics.py     # Mathematical verification for Kalman filtering & suspension physics
├── test_v14_api.py     # API integration tests for v1.4+ telemetry endpoints
├── test_v14_simple.py  # Direct database and simple physics integration tests
├── requirements.txt    # Python dependencies
├── sw.js               # Service Worker for PWA caching (v1.5.0)
├── manifest.json       # Web App Manifest for mobile installation
├── static/
│   ├── js/map.js       # Confidence heatmaps + Rider HUD + Proximity WebWorker
│   └── js/proximity-worker.js # WebWorker for background hazard queries
├── templates/
│   └── index.html      # Cyberpunk Rider HUD v1.5.0 & Leaflet map interface
├── tests/
│   └── test.py         # Core PyTest test suite
└── potholenet_v1.pkl   # Trained Scikit-Learn ML classification model
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/medhansh5/shadowmap.git
cd shadowmap

# Install dependencies
pip install -r requirements.txt

# Start the Flask server
python app.py
```

Visit `http://127.0.0.1:5000` in your web browser or mobile device to open the Cyberpunk Rider HUD!

---

## 🧪 Automated Testing

ShadowMap includes a comprehensive automated test suite. Run all unit, mathematical, and integration tests with a single command:

```bash
python test_suite_all.py
```

### Expected Output:
```text
============================================================
🚀 SHADOWMAP v1.5.0 MASTER TEST RUNNER
============================================================
   ✅ Physics Mathematical Suite: PASSED
   ✅ Core PyTest Suite: PASSED
   ✅ v1.4 Simple Integration Suite: PASSED
   ✅ v1.4 API Integration Suite: PASSED
============================================================
🎉 ALL TEST SUITES PASSED SUCCESSFULLY! SHADOWMAP v1.5.0 IS READY FOR DEPLOYMENT.
```

To run individual test suites:
```bash
# Physics & Suspension Math
python test_physics.py

# Core PyTest Suite
pytest tests/test.py -v

# Live Server Virtual Test Bench (requires app.py running)
python test_shadowmap.py
```

---

## 📡 API Reference

### POST `/api/telemetry`
Process real-time 3-axis telemetry data with signal intelligence, Kalman filtering, and spatial clustering.
**Rate Limit:** 30 req/min

**Request Body:**
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

### POST `/api/event`
Process event-triggered uploads from edge computing devices with pre/post trigger windows, FFT signature analysis, and suspension depth modeling.
**Rate Limit:** 20 req/min

### POST `/api/telemetry/batch` (v1.5.0)
High-throughput batch ingestion endpoint allowing offline-to-online bulk telemetry synchronization.

### GET `/api/stats` (v1.5.0)
Returns global mission statistics including total anomalies recorded, average impact magnitude, and maximum severity encountered.

### GET `/api/rider/<rider_id>` (v1.5.0)
Retrieves the complete anomaly history and recorded trajectory trail for a specific rider ID.

---

## 📊 Signal & Physics Pipeline (v1.5.0)

1. **Inertial Collection:** 3-axis accelerometer (100Hz) + gyroscope + GPS velocity.
2. **Kalman Smoothing:** State-space filtering removes GPS jitter and interpolates trajectory.
3. **Gravity Removal:** Butterworth high-pass filter eliminates static 1G gravity bias.
4. **Multi-Sensor Fusion:** Leaning angle compensation (`a_corrected = a_z × cos(θ)`).
5. **Suspension Modeling:** Double integration of Z-axis acceleration estimates physical pothole depth in millimeters.
6. **Bottom-Out Alerting:** Triggers immediate audio/haptic alarms if estimated depth exceeds suspension travel limits.
7. **FFT Signature Analysis:** Frequency domain analysis classifies impulse vs periodic vibrations and detects road surface type.
8. **Spatial Clustering:** Groups proximate reports within a 2-meter radius into unified database entities.
9. **Temporal Decay:** Confidences decay over time (`C = Σ(Reports) × e^(-λt)`) unless reinforced by new riders.

---

## 📄 License

This project is part of the ShadowMap road quality monitoring initiative under the MIT license.

---

**ShadowMap** — Making roads safer, one data point at a time. 🏍️⚡🗺️
