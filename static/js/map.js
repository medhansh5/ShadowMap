// ═══════════════════════════════════════════════════════════════════════════
// SHADOWMAP v1.1.0 - INTELLIGENCE LAYER
// ═══════════════════════════════════════════════════════════════════════════

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

// 5. Confidence-based color mapping (v1.1.0)
// High Confidence = Sharp Red, Decaying = Faded Amber
function getColorByConfidence(confidence) {
    if (confidence > 0.7) {
        return "#e63946"; // Sharp Red - High Confidence
    } else if (confidence > 0.4) {
        return "#f4a261"; // Orange - Medium Confidence
    } else if (confidence > 0.2) {
        return "#e9c46a"; // Amber - Low Confidence
    } else {
        return "#8d99ae"; // Faded Gray - Very Low Confidence
    }
}

// 6. Dynamic radius scaling based on confidence
function getRadiusByConfidence(confidence) {
    // Scale from 3px (minimum) to 12px (maximum)
    const minRadius = 3;
    const maxRadius = 12;
    return minRadius + (confidence * (maxRadius - minRadius));
}

// 7. Fill opacity based on confidence (decay visualization)
function getOpacityByConfidence(confidence) {
    // Higher confidence = more opaque
    return 0.3 + (confidence * 0.6);
}

// 8. Clear existing markers
function clearMarkers() {
    markers.forEach(marker => {
        map.removeLayer(marker);
    });
    markers = [];
}

// 9. Rider HUD Overlay (500m ahead view)
function createRiderHUD() {
    const hud = L.control({ position: 'bottomleft' });
    
    hud.onAdd = function(map) {
        const div = L.DomUtil.create('div', 'rider-hud');
        div.innerHTML = `
            <div style="
                background: rgba(0, 0, 0, 0.85);
                color: #00ff00;
                padding: 15px;
                border-radius: 8px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                border: 1px solid #00ff00;
                box-shadow: 0 0 10px rgba(0, 255, 0, 0.3);
                min-width: 240px;
            ">
                <div style="border-bottom: 1px solid #00ff00; padding-bottom: 8px; margin-bottom: 8px;">
                    <strong>RIDER HUD v1.3.0</strong>
                </div>
                <div id="hud-status">SCANNING...</div>
                <div id="hud-proximity" style="margin-top: 8px; color: #ffff00;">NO HAZARDS AHEAD</div>
                <div id="hud-surface" style="margin-top: 8px; color: #00ffff;">SURFACE: UNKNOWN</div>
                <div id="hud-anomalies" style="margin-top: 8px;">ANOMALIES: 0</div>
                <div id="hud-confidence" style="margin-top: 4px;">AVG CONFIDENCE: 0.00</div>
                <div id="hud-range" style="margin-top: 4px; color: #ffff00;">RANGE: 1000m</div>
            </div>
        `;
        return div;
    };
    
    hud.addTo(map);
    return hud;
}

// 10. Update HUD with current statistics
function updateHUD(anomalies) {
    const hudStatus = document.getElementById('hud-status');
    const hudAnomalies = document.getElementById('hud-anomalies');
    const hudConfidence = document.getElementById('hud-confidence');
    const hudSurface = document.getElementById('hud-surface');
    
    if (!hudStatus) return;
    
    const activeAnomalies = anomalies.filter(a => a.confidence > 0.3);
    const avgConfidence = activeAnomalies.length > 0 
        ? (activeAnomalies.reduce((sum, a) => sum + a.confidence, 0) / activeAnomalies.length).toFixed(2)
        : '0.00';
    
    // Determine road surface type based on anomaly data (v1.3.0)
    const surfaceTypes = {};
    activeAnomalies.forEach(a => {
        const surface = a.road_surface || 'UNKNOWN';
        surfaceTypes[surface] = (surfaceTypes[surface] || 0) + 1;
    });
    
    // Get most common surface type
    let dominantSurface = 'UNKNOWN';
    let maxCount = 0;
    for (const [surface, count] of Object.entries(surfaceTypes)) {
        if (count > maxCount) {
            maxCount = count;
            dominantSurface = surface;
        }
    }
    
    // Surface color coding
    const surfaceColors = {
        'PAVEMENT': '#00ff00',
        'GRAVEL': '#ffaa00',
        'COBBLESTONE': '#ff00ff',
        'UNKNOWN': '#888888'
    };
    
    hudStatus.innerHTML = activeAnomalies.length > 0 
        ? '<span style="color: #ff0000;">⚠ THREATS DETECTED</span>' 
        : '<span style="color: #00ff00;">✓ CLEAR</span>';
    
    hudSurface.innerHTML = `SURFACE: <span style="color: ${surfaceColors[dominantSurface] || '#00ffff'};">${dominantSurface}</span>`;
    hudAnomalies.innerHTML = `ANOMALIES: ${activeAnomalies.length}`;
    hudConfidence.innerHTML = `AVG CONFIDENCE: ${avgConfidence}`;
}

// 11. Proximity WebWorker Integration (v1.2.0)
let proximityWorker = null;
let currentRiderPosition = { lat: 28.6692, lng: 77.3538, heading: 0 };

function initProximityWorker() {
    if (typeof Worker !== 'undefined') {
        try {
            proximityWorker = new Worker('/static/js/proximity-worker.js');
            
            proximityWorker.onmessage = function(e) {
                const { type, data } = e.data;
                
                switch(type) {
                    case 'PROXIMITY_RESULT':
                        handleProximityResult(data);
                        break;
                    case 'CRITICAL_ALERT':
                        handleCriticalAlert(data);
                        break;
                    case 'WARNING_ALERT':
                        handleWarningAlert(data);
                        break;
                    case 'PROXIMITY_ERROR':
                        console.error('Proximity worker error:', data.error);
                        break;
                    default:
                        console.log('Worker message:', type, data);
                }
            };
            
            // Start proximity checks
            proximityWorker.postMessage({
                type: 'START_PROXIMITY_CHECKS',
                data: { interval: 2000, range: 1000 }
            });
            
            console.log('[PROXIMITY] Worker initialized');
            
        } catch (error) {
            console.error('Failed to initialize proximity worker:', error);
        }
    } else {
        console.warn('Web Workers not supported in this browser');
    }
}

function updateRiderPosition(lat, lng, heading) {
    currentRiderPosition = { lat, lng, heading };
    
    if (proximityWorker) {
        proximityWorker.postMessage({
            type: 'UPDATE_POSITION',
            data: currentRiderPosition
        });
    }
}

function handleProximityResult(data) {
    console.log('[PROXIMITY] Alerts in range:', data.alerts.length);
    
    // Update HUD with proximity info
    const hudStatus = document.getElementById('hud-status');
    const hudProximity = document.getElementById('hud-proximity');
    
    if (hudStatus && hudProximity) {
        if (data.critical_alerts.length > 0) {
            hudStatus.innerHTML = '<span style="color: #ff0000; animation: blink 0.5s infinite;">🚨 CRITICAL HAZARD</span>';
            hudProximity.innerHTML = `CRITICAL: ${data.critical_alerts.length} (${data.critical_alerts[0].distance_m}m)`;
        } else if (data.warning_alerts.length > 0) {
            hudStatus.innerHTML = '<span style="color: #ff9900;">⚠ WARNING</span>';
            hudProximity.innerHTML = `WARNING: ${data.warning_alerts.length} (${data.warning_alerts[0].distance_m}m)`;
        } else if (data.alerts.length > 0) {
            hudStatus.innerHTML = '<span style="color: #ffff00;">⚡ CAUTION</span>';
            hudProximity.innerHTML = `ANOMALIES: ${data.alerts.length} (${data.alerts[0].distance_m}m)`;
        } else {
            hudStatus.innerHTML = '<span style="color: #00ff00;">✓ CLEAR</span>';
            hudProximity.innerHTML = 'NO HAZARDS AHEAD';
        }
    }
}

function handleCriticalAlert(alerts) {
    console.error('[CRITICAL ALERT]', alerts);
    
    // Play audio alert (if browser allows)
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 800;
        oscillator.type = 'square';
        gainNode.gain.value = 0.3;
        
        oscillator.start();
        oscillator.stop(audioContext.currentTime + 0.2);
        
        // Repeat alarm
        setTimeout(() => {
            oscillator.start();
            oscillator.stop(audioContext.currentTime + 0.2);
        }, 300);
        
    } catch (error) {
        console.warn('Audio alert not available:', error);
    }
    
    // Flash screen red
    const flashOverlay = document.createElement('div');
    flashOverlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(255, 0, 0, 0.3);
        z-index: 9999;
        pointer-events: none;
        animation: flash 0.5s ease-out;
    `;
    document.body.appendChild(flashOverlay);
    setTimeout(() => flashOverlay.remove(), 500);
}

function handleWarningAlert(alerts) {
    console.warn('[WARNING ALERT]', alerts);
    
    // Play softer warning tone
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 600;
        oscillator.type = 'sine';
        gainNode.gain.value = 0.2;
        
        oscillator.start();
        oscillator.stop(audioContext.currentTime + 0.15);
        
    } catch (error) {
        console.warn('Audio warning not available:', error);
    }
}

// 11. Update map with fresh data (v1.1.0 confidence-based)
function updateMap() {
    const currentTime = Date.now();
    console.log('[MAP UPDATE] Fetching anomaly intelligence data...');

    fetch('/roads')
        .then(response => {
            if (response.ok) {
                statusText.innerHTML = " ShadowMap v1.3.0 Live";
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

            // Add new markers with confidence-based styling
            data.forEach(point => {
                const confidence = point.confidence || 0.1;
                const severity = point.severity || 1;
                
                // Confidence-based color heatmap
                const marker = L.circle([point.lat, point.lng], {
                    color: '#ffffff',
                    fillColor: getColorByConfidence(confidence),
                    fillOpacity: getOpacityByConfidence(confidence),
                    radius: getRadiusByConfidence(confidence),
                    weight: 1
                }).addTo(map);

                // Add popup with anomaly details
                marker.bindPopup(`
                    <div style="font-family: Arial, sans-serif; font-size: 12px;">
                        <strong>Anomaly #${point.id}</strong><br>
                        Confidence: ${(confidence * 100).toFixed(1)}%<br>
                        Severity: ${severity}/3<br>
                        Hits: ${point.hit_count || 1}<br>
                        Impact: ${(point.impact_magnitude || 0).toFixed(2)} m/s²
                    </div>
                `);

                markers.push(marker);
            });

            // Update HUD
            updateHUD(data);

            lastUpdateTime = currentTime;
            console.log(`[MAP UPDATE] Added ${markers.length} anomaly markers`);
        })
        .catch(err => {
            console.error('Fetch error:', err);
            statusText.innerHTML = " Server Offline (Waking up...)";
            statusText.style.color = "#e74c3c";
        });
}

// 12. Initialize HUD
createRiderHUD();

// 13. Initialize Proximity Worker (v1.2.0)
initProximityWorker();

// 14. Initial map load
updateMap();

// 15. Real-time updates every 10 seconds
setInterval(updateMap, 10000);
