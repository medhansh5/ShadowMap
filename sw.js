const CACHE_NAME = 'shadowmap-lite-v1.3.0';
const STATIC_CACHE = 'shadowmap-static-v1.3.0';
const MAP_CACHE = 'shadowmap-maps-v1.3.0';

// Core assets to cache for offline functionality
const STATIC_ASSETS = [
  '/',
  '/index.html',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
];

// Map tile patterns for caching (local region)
const MAP_TILE_PATTERNS = [
  'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing ShadowMap Lite service worker');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        console.log('[SW] Static assets cached successfully');
        return self.skipWaiting();
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating ShadowMap Lite service worker');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((cacheName) => {
              return cacheName !== STATIC_CACHE && 
                     cacheName !== MAP_CACHE &&
                     cacheName !== CACHE_NAME;
            })
            .map((cacheName) => {
              console.log('[SW] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            })
        );
      })
      .then(() => {
        console.log('[SW] Service worker activated');
        return self.clients.claim();
      })
  );
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Handle different request types
  if (request.method === 'GET') {
    // Static assets - cache first strategy
    if (STATIC_ASSETS.some(asset => request.url.includes(asset)) || 
        request.url.includes('leaflet')) {
      event.respondWith(
        caches.open(STATIC_CACHE)
          .then((cache) => {
            return cache.match(request)
              .then((response) => {
                if (response) {
                  // Serve from cache
                  return response;
                }
                
                // Fetch and cache new resource
                return fetch(request)
                  .then((fetchResponse) => {
                    if (fetchResponse.ok) {
                      cache.put(request, fetchResponse.clone());
                    }
                    return fetchResponse;
                  })
                  .catch(() => {
                    // Return cached version if available
                    return cache.match(request);
                  });
              });
          })
      );
      return;
    }
    
    // Map tiles - cache first with network fallback
    if (url.hostname.includes('basemaps.cartocdn.com')) {
      event.respondWith(
        caches.open(MAP_CACHE)
          .then((cache) => {
            return cache.match(request)
              .then((response) => {
                if (response) {
                  // Serve cached tile immediately
                  return response;
                }
                
                // Fetch and cache new tile
                return fetch(request)
                  .then((fetchResponse) => {
                    if (fetchResponse.ok) {
                      cache.put(request, fetchResponse.clone());
                    }
                    return fetchResponse;
                  })
                  .catch(() => {
                    // Return a placeholder tile or error
                    return new Response('Map tile unavailable', {
                      status: 404,
                      statusText: 'Map tile unavailable'
                    });
                  });
              });
          })
      );
      return;
    }
    
    // API calls - network first with cache fallback
    if (url.pathname.includes('/api/')) {
      event.respondWith(
        fetch(request)
          .then((response) => {
            if (response.ok) {
              // Cache successful API responses
              const responseClone = response.clone();
              caches.open(CACHE_NAME)
                .then((cache) => {
                  cache.put(request, responseClone);
                });
            }
            return response;
          })
          .catch(() => {
            // Try to serve from cache
            return caches.match(request)
              .then((cachedResponse) => {
                if (cachedResponse) {
                  return cachedResponse;
                }
                
                // Return offline response for API calls
                return new Response(JSON.stringify({
                  error: 'Offline - data will sync when connection is restored',
                  offline: true
                }), {
                  status: 503,
                  headers: {
                    'Content-Type': 'application/json'
                  }
                });
              });
          })
      );
      return;
    }
  }
  
  // Handle POST requests for telemetry data
  if (request.method === 'POST' && url.pathname.includes('/api/event')) {
    event.respondWith(
      handleTelemetrySync(request)
    );
    return;
  }
});

// Handle telemetry sync with background sync
async function handleTelemetrySync(request) {
  try {
    const response = await fetch(request);
    
    if (response.ok) {
      console.log('[SW] Telemetry synced successfully');
      return response;
    } else {
      throw new Error('Server error during telemetry sync');
    }
  } catch (error) {
    console.log('[SW] Telemetry sync failed, storing for background sync:', error.message);
    
    // Store request data for background sync
    const requestData = await request.clone().json();
    
    // Store in IndexedDB for background sync
    await storeForBackgroundSync('telemetry-sync', {
      url: request.url,
      method: request.method,
      headers: Object.fromEntries(request.headers.entries()),
      body: requestData,
      timestamp: Date.now()
    });
    
    // Register background sync if available
    if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
      await self.registration.sync.register('telemetry-sync');
    }
    
    return new Response(JSON.stringify({
      status: 'queued',
      message: 'Telemetry queued for background sync'
    }), {
      status: 202,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }
}

// Background sync event
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync event:', event.tag);
  
  if (event.tag === 'telemetry-sync') {
    event.waitUntil(
      performTelemetryBackgroundSync()
    );
  }
});

// Perform background sync for queued telemetry
async function performTelemetryBackgroundSync() {
  try {
    const queuedItems = await getStoredItems('telemetry-sync');
    
    if (queuedItems.length === 0) {
      console.log('[SW] No telemetry items to sync');
      return;
    }
    
    console.log(`[SW] Syncing ${queuedItems.length} telemetry items`);
    
    for (const item of queuedItems) {
      try {
        const response = await fetch(item.url, {
          method: item.method,
          headers: item.headers,
          body: JSON.stringify(item.body)
        });
        
        if (response.ok) {
          console.log('[SW] Telemetry item synced successfully');
          await removeStoredItem('telemetry-sync', item.id);
        } else {
          console.log('[SW] Telemetry sync failed, will retry later');
        }
      } catch (error) {
        console.log('[SW] Error syncing telemetry item:', error.message);
      }
    }
  } catch (error) {
    console.error('[SW] Background sync error:', error);
  }
}

// IndexedDB helpers for background sync storage
async function storeForBackgroundSync(storeName, data) {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('ShadowMapSyncDB', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      const db = request.result;
      const transaction = db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      
      data.id = Date.now().toString() + Math.random().toString(36).substr(2, 9);
      const addRequest = store.add(data);
      
      addRequest.onsuccess = () => resolve(addRequest.result);
      addRequest.onerror = () => reject(addRequest.error);
    };
    
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(storeName)) {
        const store = db.createObjectStore(storeName, { keyPath: 'id' });
        store.createIndex('timestamp', 'timestamp', { unique: false });
      }
    };
  });
}

async function getStoredItems(storeName) {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('ShadowMapSyncDB', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      const db = request.result;
      const transaction = db.transaction([storeName], 'readonly');
      const store = transaction.objectStore(storeName);
      const getRequest = store.getAll();
      
      getRequest.onsuccess = () => resolve(getRequest.result);
      getRequest.onerror = () => reject(getRequest.error);
    };
    
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(storeName)) {
        const store = db.createObjectStore(storeName, { keyPath: 'id' });
        store.createIndex('timestamp', 'timestamp', { unique: false });
      }
    };
  });
}

async function removeStoredItem(storeName, id) {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('ShadowMapSyncDB', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      const db = request.result;
      const transaction = db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      const deleteRequest = store.delete(id);
      
      deleteRequest.onsuccess = () => resolve(deleteRequest.result);
      deleteRequest.onerror = () => reject(deleteRequest.error);
    };
    
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(storeName)) {
        const store = db.createObjectStore(storeName, { keyPath: 'id' });
        store.createIndex('timestamp', 'timestamp', { unique: false });
      }
    };
  });
}

// Push notification for critical alerts (optional)
self.addEventListener('push', (event) => {
  if (event.data) {
    const data = event.data.json();
    
    if (data.type === 'critical-anomaly') {
      event.waitUntil(
        self.registration.showNotification('ShadowMap Alert', {
          body: `Critical anomaly detected: ${data.magnitude.toFixed(2)} m/s²`,
          icon: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iOTYiIGhlaWdodD0iOTYiIHZpZXdCb3g9IjAgMCA5NiA5NiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9Ijk2IiBoZWlnaHQ9Ijk2IiBmaWxsPSIjMDAwMDAwIi8+CjxjaXJjbGUgY3g9IjQ4IiBjeT0iNDgiIHI9IjIwIiBmaWxsPSIjZmYwMDAwIiBvcGFjaXR5PSIwLjMiLz4KPHRleHQgeD0iNDgiIHk9IjU0IiBmb250LWZhbWlseT0iQ291cmllciBOZXcsIG1vbm9zcGFjZSIgZm9udC1zaXplPSIyNCIgZmlsbD0iI2ZmMDAwMCIgdGV4dC1hbmNob3I9Im1pZGRsZSI+ITwvdGV4dD4KPC9zdmc+Cg==',
          badge: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMTIiIGN5PSIxMiIgcj0iMTAiIGZpbGw9IiNmZjAwMDAiLz4KPC9zdmc+Cg==',
          vibrate: [200, 100, 200],
          tag: 'shadowmap-anomaly',
          requireInteraction: true
        })
      );
    }
  }
});

// Message handling for communication with main app
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

console.log('[SW] ShadowMap Lite service worker loaded');
