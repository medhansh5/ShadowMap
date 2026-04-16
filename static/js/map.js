// Initialize map centered on Ghaziabad
const map = L.map('map').setView([28.6692, 77.3538], 13);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

// Color mapping for road quality
const colors = {
    0: "#2ecc71", // Smooth - Green
    1: "#f1c40f", // Bumpy - Yellow
    2: "#e74c3c"  // Pothole - Red
};

// Fetch data from our API
fetch('/roads')
    .then(response => response.json())
    .then(data => {
        data.forEach(point => {
            L.circle([point.lat, point.lng], {
                color: colors[point.quality],
                fillColor: colors[point.quality],
                fillOpacity: 0.6,
                radius: 20 // Adjust based on zoom
            }).addTo(map);
        });
    });