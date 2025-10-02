/**
 * Service Worker for Depanku Application
 * Handles caching strategies and offline functionality
 */

const CACHE_NAME = 'depanku-v1';
const API_CACHE_NAME = 'depanku-api-v1';
const STATIC_CACHE_NAME = 'depanku-static-v1';

// URLs to cache on install
const URLS_TO_CACHE = [
    '/',
    '/static/css/design-system.css',
    '/static/css/design-system-accessibility.css',
    '/static/css/landing.css',
    '/static/js/auth.js',
    '/static/js/performance.js',
    '/static/images/favicon.ico',
    '/static/images/hero-illustration.svg'
];

// API endpoints to cache
const API_ENDPOINTS = [
    '/api/organizations',
    '/api/auth/current-user',
    '/api/ai/analysis'
];

// Install event - cache static assets
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(STATIC_CACHE_NAME)
            .then(cache => {
                console.log('Opened cache');
                return cache.addAll(URLS_TO_CACHE);
            })
            .then(() => self.skipWaiting())
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME && 
                        cacheName !== API_CACHE_NAME && 
                        cacheName !== STATIC_CACHE_NAME) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch event - handle requests with appropriate caching strategy
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);
    
    // Don't cache chrome-extension:// URLs
    if (url.protocol === 'chrome-extension:') {
        return;
    }

    // Handle API requests with network-first strategy
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    // Don't cache non-successful responses
                    if (!response.ok) {
                        return response;
                    }
                    
                    // Clone the response since it can only be consumed once
                    const responseToCache = response.clone();
                    
                    caches.open(API_CACHE_NAME)
                        .then(cache => {
                            cache.put(event.request, responseToCache);
                        });
                    
                    return response;
                })
                .catch(() => {
                    // If network fails, try to get from cache
                    return caches.match(event.request);
                })
        );
        return;
    }

    // Handle static assets with cache-first strategy
    if (event.request.destination === 'script' || 
        event.request.destination === 'style' ||
        event.request.destination === 'image' ||
        event.request.destination === 'font') {
        event.respondWith(
            caches.match(event.request)
                .then(response => {
                    // Cache hit - return response
                    if (response) {
                        return response;
                    }
                    
                    // Cache miss - fetch from network
                    return fetch(event.request).then(response => {
                        // Don't cache non-successful responses
                        if (!response || response.status !== 200 || response.type !== 'basic') {
                            return response;
                        }
                        
                        // Clone the response
                        const responseToCache = response.clone();
                        
                        caches.open(STATIC_CACHE_NAME)
                            .then(cache => {
                                cache.put(event.request, responseToCache);
                            });
                        
                        return response;
                    });
                })
        );
        return;
    }

    // Handle HTML pages with network-first strategy
    if (event.request.headers.get('accept').includes('text/html')) {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    // Don't cache non-successful responses
                    if (!response || response.status !== 200 || response.type !== 'basic') {
                        return response;
                    }
                    
                    // Clone the response
                    const responseToCache = response.clone();
                    
                    caches.open(CACHE_NAME)
                        .then(cache => {
                            cache.put(event.request, responseToCache);
                        });
                    
                    return response;
                })
                .catch(() => {
                    // If network fails, try to get from cache
                    return caches.match(event.request);
                })
        );
        return;
    }

    // For all other requests, use network-first strategy
    event.respondWith(
        fetch(event.request)
            .catch(() => {
                // If network fails, try to get from cache
                return caches.match(event.request);
            })
    );
});

// Handle background sync
self.addEventListener('sync', event => {
    if (event.tag === 'sync-form-data') {
        event.waitUntil(
            // Sync form data in background
            syncFormData()
        );
    }
});

// Handle push notifications
self.addEventListener('push', event => {
    if (event.data) {
        const options = {
            body: event.data.text(),
            icon: '/static/images/favicon.ico',
            badge: '/static/images/badge.png',
            vibrate: [100, 50, 100],
            data: {
                dateOfArrival: Date.now(),
                primaryKey: 1
            }
        };
        
        event.waitUntil(
            self.registration.showNotification('Depanku', options)
        );
    }
});

// Handle notification click
self.addEventListener('notificationclick', event => {
    event.notification.close();
    
    if (event.notification.data && event.notification.data.url) {
        event.waitUntil(
            clients.openWindow(event.notification.data.url)
        );
    }
});

// Background sync function
async function syncFormData() {
    try {
        // Get pending form data from IndexedDB
        const pendingData = await getPendingFormData();
        
        if (pendingData.length > 0) {
            // Send data to server
            for (const data of pendingData) {
                const response = await fetch('/api/sync', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });
                
                if (response.ok) {
                    // Remove from pending data
                    await removePendingFormData(data.id);
                }
            }
        }
    } catch (error) {
        console.error('Background sync failed:', error);
    }
}

// Helper functions for IndexedDB operations
async function getPendingFormData() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('depanku-pending-data', 1);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const transaction = db.transaction(['pending'], 'readonly');
            const store = transaction.objectStore('pending');
            const getAll = store.getAll();
            
            getAll.onsuccess = () => resolve(getAll.result);
            getAll.onerror = () => reject(getAll.error);
        };
        
        request.onupgradeneeded = () => {
            const db = request.result;
            if (!db.objectStoreNames.contains('pending')) {
                db.createObjectStore('pending', { keyPath: 'id' });
            }
        };
    });
}

async function removePendingFormData(id) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('depanku-pending-data', 1);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const transaction = db.transaction(['pending'], 'readwrite');
            const store = transaction.objectStore('pending');
            const deleteRequest = store.delete(id);
            
            deleteRequest.onsuccess = () => resolve();
            deleteRequest.onerror = () => reject(deleteRequest.error);
        };
    });
}

// Handle message events
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data && event.data.type === 'CACHE_URLS') {
        event.waitUntil(
            caches.open(STATIC_CACHE_NAME)
                .then(cache => cache.addAll(event.data.urls))
        );
    }
});