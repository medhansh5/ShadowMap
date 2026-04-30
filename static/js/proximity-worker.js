// ═══════════════════════════════════════════════════════════════════════════
// SHADOWMAP v1.2.0 - PROXIMITY WEB WORKER
// ═══════════════════════════════════════════════════════════════════════════
// WebWorker for proximity checks without blocking the main UI thread
// Runs every 2 seconds to query forward-looking cone for hazards
// ═══════════════════════════════════════════════════════════════════════════

let proximityInterval = null;
let currentPosition = { lat: 28.6692, lng: 77.3538, heading: 0 };

self.onmessage = function(e) {
    const { type, data } = e.data;
    
    switch(type) {
        case 'START_PROXIMITY_CHECKS':
            startProximityChecks(data);
            break;
        case 'STOP_PROXIMITY_CHECKS':
            stopProximityChecks();
            break;
        case 'UPDATE_POSITION':
            updatePosition(data);
            break;
        default:
            console.error('Unknown message type:', type);
    }
};

function startProximityChecks(config) {
    const { interval = 2000, range = 1000 } = config;
    
    if (proximityInterval) {
        clearInterval(proximityInterval);
    }
    
    // Run initial check
    checkProximity(range);
    
    // Set up interval
    proximityInterval = setInterval(() => {
        checkProximity(range);
    }, interval);
    
    self.postMessage({
        type: 'PROXIMITY_STARTED',
        data: { interval, range }
    });
}

function stopProximityChecks() {
    if (proximityInterval) {
        clearInterval(proximityInterval);
        proximityInterval = null;
    }
    
    self.postMessage({
        type: 'PROXIMITY_STOPPED',
        data: {}
    });
}

function updatePosition(position) {
    currentPosition = {
        lat: position.lat,
        lng: position.lng,
        heading: position.heading || 0
    };
}

async function checkProximity(range) {
    try {
        const url = `/api/proximity?lat=${currentPosition.lat}&lng=${currentPosition.lng}&heading=${currentPosition.heading}&range_m=${range}`;
        
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Send results to main thread
        self.postMessage({
            type: 'PROXIMITY_RESULT',
            data: data
        });
        
        // Check for critical alerts
        if (data.critical_alerts && data.critical_alerts.length > 0) {
            self.postMessage({
                type: 'CRITICAL_ALERT',
                data: data.critical_alerts
            });
        }
        
        // Check for warning alerts
        if (data.warning_alerts && data.warning_alerts.length > 0) {
            self.postMessage({
                type: 'WARNING_ALERT',
                data: data.warning_alerts
            });
        }
        
    } catch (error) {
        console.error('Proximity check error:', error);
        self.postMessage({
            type: 'PROXIMITY_ERROR',
            data: { error: error.message }
        });
    }
}
