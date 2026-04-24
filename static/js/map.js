// Initialize the map
let map;
let markers = [];
let refreshInterval;

// Initialize map when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeMap();
    createLegend();
    createLoadingIndicator();
    updateMap();
    
    // Set up auto-refresh every 10 seconds
    refreshInterval = setInterval(updateMap, 10000);
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
            color: '#e63946',
            fillColor: '#e63946',
            fillOpacity: 0.7,
            radius: 10,
            weight: 2
        };
    } else if (severity >= 0.5) {
        return {
            color: '#f4a261',
            fillColor: '#f4a261',
            fillOpacity: 0.7,
            radius: 6,
            weight: 2
        };
    } else {
        return {
            color: '#e9c46a',
            fillColor: '#e9c46a',
            fillOpacity: 0.7,
            radius: 3,
            weight: 1
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

async function updateMap() {
    showLoading(true);
    
    try {
        // Fetch demo data from local JSON file
        const response = await fetch('./static/js/demo_data.json');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Clear existing markers
        markers.forEach(marker => {
            map.removeLayer(marker);
        });
        markers = [];
        
        // Add new markers
        data.forEach(pothole => {
            const style = getSeverityStyle(pothole.severity);
            
            const marker = L.circleMarker([pothole.lat, pothole.lng], style)
                .addTo(map);
            
            // Create popup content
            const popupContent = `
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                    <strong style="color: ${style.color}; font-size: 14px;">
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
        
        console.log(`Updated map with ${data.length} potholes`);
        
    } catch (error) {
        console.error('Error updating map:', error);
        
        // Show error message to user
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.style.cssText = `
            position: absolute;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background-color: rgba(220, 38, 38, 0.9);
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 14px;
            z-index: 1000;
            backdrop-filter: blur(10px);
        `;
        errorDiv.textContent = 'Failed to load pothole data';
        document.body.appendChild(errorDiv);
        
        // Remove error message after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.parentNode.removeChild(errorDiv);
            }
        }, 5000);
    } finally {
        showLoading(false);
    }
}

function createLegend() {
    const legend = L.control({ position: 'bottomleft' });
    
    legend.onAdd = function(map) {
        const div = L.DomUtil.create('div', 'severity-legend');
        div.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 8px; font-size: 13px;">Severity Levels</div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #e63946;"></div>
                <span>Critical (>80%)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #f4a261;"></div>
                <span>Moderate (50-80%)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #e9c46a;"></div>
                <span>Low (<50%)</span>
            </div>
            <div style="margin-top: 8px; font-size: 10px; color: #666;">
                Auto-refresh: 10s
            </div>
        `;
        return div;
    };
    
    legend.addTo(map);
}

function createLoadingIndicator() {
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'loading-indicator';
    loadingDiv.className = 'loading-indicator';
    loadingDiv.style.display = 'none';
    loadingDiv.textContent = 'Updating data...';
    document.body.appendChild(loadingDiv);
}

function showLoading(show) {
    const loadingIndicator = document.getElementById('loading-indicator');
    if (loadingIndicator) {
        loadingIndicator.style.display = show ? 'block' : 'none';
    }
}

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});
