// 1. Initialize the map centered on Ghaziabad
const map = L.map('map').setView([28.6692, 77.3538], 13);

// 2. Add OpenStreetMap tiles
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap'
}).addTo(map);

// 3. Status overlay elements
const statusText = document.getElementById('status-text');

// 4. Color mapping for road quality
const colors = {
    0: "#2ecc71", // Smooth - Green
    1: "#f1c40f", // Bumpy - Yellow
    2: "#e74c3c"  // Pothole - Red
};

// 5. Fetch data and handle the "Wake-up"
// Make sure this URL matches your Render service link!
fetch('/roads')
    .then(response => {
        if (response.ok) {
            statusText.innerHTML = "🟢 ShadowMap Live";
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
        // 6. Loop through coordinates and draw circles
        data.forEach(point => {
            L.circle([point.lat, point.lng], {
                color: colors[point.quality],
                fillColor: colors[point.quality],
                fillOpacity: 0.6,
                radius: 15 
            }).addTo(map);
        });
    })
    .catch(err => {
        console.error('Fetch error:', err);
        statusText.innerHTML = "🔴 Server Offline (Waking up...)";
        statusText.style.color = "#e74c3c";
    });
