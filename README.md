# 🗺️ ShadowMap

**ShadowMap** is a crowdsourced road quality mapping platform. It transforms motorcycle telemetry data into a live, color-coded map of road conditions using signal processing and machine learning.

The project is an evolution of **PotholeNet**, specifically tuned to filter out the high-vibration profile of a Royal Enfield Classic 350 engine to detect road anomalies accurately.

## 🚀 Features
* **Vibration Isolation:** Uses a 4th-order Butterworth High-Pass filter ($12\text{Hz}$) to separate road data from engine noise.
* **Real-time Classification:** Scikit-learn powered classification of road segments (Smooth, Bumpy, Pothole).
* **Live Crowdsourcing:** Mobile telemetry is POSTed to a central Flask API and stored in a PostgreSQL/SQLite database.
* **Interactive Visualization:** A Leaflet.js frontend renders road quality overlays globally.

## 🛠️ Tech Stack
* **Backend:** Python, Flask, SQLAlchemy
* **Frontend:** HTML5, Leaflet.js, JavaScript (ES6)
* **ML/Signal Processing:** Scikit-learn, NumPy, SciPy
* **Deployment:** Render (API), GitHub Pages (Static Frontend)

## 📂 Project Structure
```text
shadowmap/
├── app.py              # Flask API & Backend logic
├── potholenet.py       # Mobile telemetry & ML processing script
├── requirements.txt    # Python dependencies
├── static/
│   ├── js/map.js       # Leaflet.js map logic
│   └── css/style.css   # Custom styling
├── templates/
│   └── index.html      # Main map interface
└── tests/
    └── test_api.py     # Pytest suite for API validation
```

## 🚀 Live Demo
You can view the live crowdsourced road quality map here:
[https://shadowmap-api.onrender.com](https://shadowmap-api.onrender.com)
