// Initialize the map
let map;
let markers = [];

// Demo data constant - potholes around Ghaziabad
const demoData = [
    {
        "lat": 28.6692,
        "lng": 77.4538,
        "severity": 0.92,
        "timestamp": "2026-04-24T18:30:00Z"
    },
    {
        "lat": 28.6715,
        "lng": 77.4521,
        "severity": 0.65,
        "timestamp": "2026-04-24T18:32:15Z"
    },
    {
        "lat": 28.6678,
        "lng": 77.4556,
        "severity": 0.35,
        "timestamp": "2026-04-24T18:35:42Z"
    },
    {
        "lat": 28.6701,
        "lng": 77.4512,
        "severity": 0.81,
        "timestamp": "2026-04-24T18:38:20Z"
    },
    {
        "lat": 28.6689,
        "lng": 77.4567,
        "severity": 0.42,
        "timestamp": "2026-04-24T18:41:05Z"
    },
    {
        "lat": 28.6723,
        "lng": 77.4545,
        "severity": 0.73,
        "timestamp": "2026-04-24T18:43:30Z"
    },
    {
        "lat": 28.6665,
        "lng": 77.4529,
        "severity": 0.28,
        "timestamp": "2026-04-24T18:45:18Z"
    },
    {
        "lat": 28.6712,
        "lng": 77.4578,
        "severity": 0.87,
        "timestamp": "2026-04-24T18:47:45Z"
    },
    {
        "lat": 28.6746,
        "lng": 77.4503,
        "severity": 0.55,
        "timestamp": "2026-04-24T18:50:12Z"
    },
    {
        "lat": 28.6658,
        "lng": 77.4591,
        "severity": 0.18,
        "timestamp": "2026-04-24T18:52:38Z"
    },
    {
        "lat": 28.6762,
        "lng": 77.4487,
        "severity": 0.76,
        "timestamp": "2026-04-24T18:55:21Z"
    },
    {
        "lat": 28.6641,
        "lng": 77.4615,
        "severity": 0.31,
        "timestamp": "2026-04-24T18:57:48Z"
    }
];

// Initialize map when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeMap();
    createLegend();
    updateMap();
});

function initializeMap() {
    // Create map centered on Ghaziabad, India
    map = L.map('map').setView([28.6692, 77.4538], 14);
    
    // Add dark tile layer (CartoDB Dark Matter)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);
}

function getSeverityStyle(severity) {
    if (severity > 0.8) {
        return {
            color: '#ff4d4d',
            fillColor: '#ff4d4d',
            fillOpacity: 0.8,
            radius: 12,
            weight: 2,
            className: 'neon-marker-high'
        };
    } else if (severity >= 0.5) {
        return {
            color: '#f4a261',
            fillColor: '#f4a261',
            fillOpacity: 0.8,
            radius: 8,
            weight: 2,
            className: 'neon-marker-moderate'
        };
    } else {
        return {
            color: '#00d4ff',
            fillColor: '#00d4ff',
            fillOpacity: 0.8,
            radius: 5,
            weight: 2,
            className: 'neon-marker-low'
        };
    }
}

function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function updateMap() {
    // Clear existing markers
    markers.forEach(marker => {
        map.removeLayer(marker);
    });
    markers = [];
    
    // Add new markers from demo data
    demoData.forEach(pothole => {
        const style = getSeverityStyle(pothole.severity);
        
        const marker = L.circleMarker([pothole.lat, pothole.lng], style)
            .addTo(map);
        
        // Create popup content
        const popupContent = `
            <div style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                <strong style="color: ${style.color}; font-size: 14px; font-weight: 600;">
                    Severity: ${(pothole.severity * 100).toFixed(0)}%
                </strong><br>
                <span style="color: #888; font-size: 12px;">
                    ${formatTimestamp(pothole.timestamp)}
                </span><br>
                <span style="color: #aaa; font-size: 11px;">
                    ${pothole.lat.toFixed(6)}, ${pothole.lng.toFixed(6)}
                </span>
            </div>
        `;
        
        marker.bindPopup(popupContent);
        markers.push(marker);
    });
    
    console.log(`Map updated with ${demoData.length} potholes from demo data`);
}


function createLegend() {
    const legend = L.control({ position: 'bottomleft' });
    
    legend.onAdd = function(map) {
        const div = L.DomUtil.create('div', 'severity-legend');
        div.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 12px; font-size: 13px;">Severity Levels</div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #ff4d4d; box-shadow: 0 0 10px rgba(255, 77, 77, 0.6);"></div>
                <span>Critical (>80%)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #f4a261; box-shadow: 0 0 8px rgba(244, 162, 97, 0.6);"></div>
                <span>Moderate (50-80%)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #00d4ff; box-shadow: 0 0 6px rgba(0, 212, 255, 0.6);"></div>
                <span>Low (<50%)</span>
            </div>
                    `;
        return div;
    };
    
    legend.addTo(map);
}

