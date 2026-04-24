// 1. Initialize the map centered on Ghaziabad
const map = L.map('map').setView([28.6692, 77.3538], 13);

// 2. Add OpenStreetMap tiles
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: ' OpenStreetMap'
}).addTo(map);

// 3. Status overlay elements
const statusText = document.getElementById('status-text');

// 4. Marker management
let markers = [];
let lastUpdateTime = 0;

// 5. Dynamic color mapping based on severity
function getColorBySeverity(severity) {
    if (severity > 0.8) {
        return "#e63946"; // Deep Red - Major Pothole
    } else if (severity >= 0.5) {
        return "#f4a261"; // Orange - Moderate Bump
    } else {
        return "#e9c46a"; // Yellow - Minor Wear
    }
}

// 6. Dynamic radius scaling based on severity
function getRadiusBySeverity(severity) {
    // Scale from 3px (minimum) to 10px (maximum)
    const minRadius = 3;
    const maxRadius = 10;
    return minRadius + (severity * (maxRadius - minRadius));
}

// 7. Clear existing markers
function clearMarkers() {
    markers.forEach(marker => {
        map.removeLayer(marker);
    });
    markers = [];
}

// 8. Update map with fresh data
function updateMap() {
    const currentTime = Date.now();
    console.log('[MAP UPDATE] Fetching fresh road data...');

    fetch('/roads')
        .then(response => {
            if (response.ok) {
                statusText.innerHTML = " ShadowMap Live";
                statusText.style.color = "#2ecc71";
                // Hide the status box after 5 seconds to clear the screen
                setTimeout(() => {
                    document.getElementById('status-overlay').style.opacity = '0';
                    setTimeout(() => {
                        document.getElementById('status-overlay').style.display = 'none';
                    }, 500);
                }, 5000);
            }
            return response.json();
        })
        .then(data => {
            // Clear old markers to prevent memory buildup
            clearMarkers();

            // Add new markers with dynamic styling
            data.forEach(point => {
                // Use quality as a proxy for severity (0=smooth, 1=bumpy, 2=pothole)
                // Map to severity scale: 0 -> 0.1, 1 -> 0.5, 2 -> 0.9
                const severity = point.quality === 2 ? 0.9 : (point.quality === 1 ? 0.5 : 0.1);

                const marker = L.circle([point.lat, point.lng], {
                    color: '#ffffff',
                    fillColor: getColorBySeverity(severity),
                    fillOpacity: 0.9,
                    radius: getRadiusBySeverity(severity),
                    weight: 1
                }).addTo(map);

                markers.push(marker);
            });

            lastUpdateTime = currentTime;
            console.log(`[MAP UPDATE] Added ${markers.length} markers`);
        })
        .catch(err => {
            console.error('Fetch error:', err);
            statusText.innerHTML = " Server Offline (Waking up...)";
            statusText.style.color = "#e74c3c";
        });
}

// 9. Initial map load
updateMap();

// 10. Real-time updates every 10 seconds
setInterval(updateMap, 10000);
