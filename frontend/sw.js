/**
 * LetsGoal Service Worker
 * Provides offline support, caching strategies, and PWA functionality
 */

const CACHE_VERSION = 'v1';
const CACHE_NAMES = {
  static: `letsgoal-static-${CACHE_VERSION}`,
  images: `letsgoal-images-${CACHE_VERSION}`,
  fonts: `letsgoal-fonts-${CACHE_VERSION}`,
  api: `letsgoal-api-${CACHE_VERSION}`,
  cdn: `letsgoal-cdn-${CACHE_VERSION}`
};

// Assets to pre-cache on install
const PRECACHE_ASSETS = [
  '/',
  '/login',
  '/dashboard',
  '/offline.html',
  '/css/styles.css',
  '/js/auth.js',
  '/js/dashboard.js',
  '/manifest.json',
  '/assets/icons/icon-192x192.png',
  '/assets/icons/icon-512x512.png',
  '/assets/icons/apple-touch-icon.png'
];

// CDN resources to cache
const CDN_RESOURCES = [
  'https://cdn.tailwindcss.com',
  'https://cdn.jsdelivr.net/npm/chart.js',
  'https://cdn.jsdelivr.net/npm/sortablejs@1.15.2/Sortable.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
];

// Routes that should NEVER be cached (auth endpoints)
const NEVER_CACHE = [
  '/api/auth/login',
  '/api/auth/logout',
  '/api/auth/register',
  '/api/auth/check'
];

// Install event - pre-cache critical assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');

  event.waitUntil(
    caches.open(CACHE_NAMES.static)
      .then((cache) => {
        console.log('[SW] Pre-caching static assets');
        // Use addAll for critical assets, but don't fail if some are missing
        return cache.addAll(PRECACHE_ASSETS).catch((error) => {
          console.warn('[SW] Some pre-cache assets failed:', error);
          // Try to cache what we can individually
          return Promise.allSettled(
            PRECACHE_ASSETS.map(url =>
              cache.add(url).catch(e => console.warn(`[SW] Failed to cache ${url}:`, e))
            )
          );
        });
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');

  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => {
              // Delete caches that don't match current version
              return name.startsWith('letsgoal-') &&
                     !Object.values(CACHE_NAMES).includes(name);
            })
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => self.clients.claim())
  );
});

// Fetch event - handle all network requests
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Never cache auth endpoints
  if (NEVER_CACHE.some(path => url.pathname.startsWith(path))) {
    event.respondWith(fetch(request));
    return;
  }

  // Determine caching strategy based on request type
  if (url.pathname.startsWith('/api/')) {
    // API requests: Network-first with cache fallback
    event.respondWith(networkFirstStrategy(request, CACHE_NAMES.api));
  } else if (isGoogleFont(url)) {
    // Google Fonts: Cache-first (long-term)
    event.respondWith(cacheFirstStrategy(request, CACHE_NAMES.fonts, 365 * 24 * 60 * 60));
  } else if (isCDNResource(url)) {
    // CDN resources: Stale-while-revalidate
    event.respondWith(staleWhileRevalidateStrategy(request, CACHE_NAMES.cdn));
  } else if (isImageRequest(request, url)) {
    // Images/Icons: Cache-first
    event.respondWith(cacheFirstStrategy(request, CACHE_NAMES.images));
  } else if (isStaticAsset(url)) {
    // Local CSS/JS: Cache-first
    event.respondWith(cacheFirstStrategy(request, CACHE_NAMES.static));
  } else {
    // HTML pages: Network-first
    event.respondWith(networkFirstStrategy(request, CACHE_NAMES.static));
  }
});

// Caching Strategies

/**
 * Cache-first strategy: Return cached version if available, fallback to network
 */
async function cacheFirstStrategy(request, cacheName, maxAgeSeconds = null) {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);

  if (cachedResponse) {
    // Check if cache is still valid (optional max age)
    if (maxAgeSeconds) {
      const cachedDate = new Date(cachedResponse.headers.get('date'));
      const now = new Date();
      if ((now - cachedDate) / 1000 < maxAgeSeconds) {
        return cachedResponse;
      }
    } else {
      return cachedResponse;
    }
  }

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.warn('[SW] Network request failed, returning cached:', request.url);
    return cachedResponse || createOfflineResponse(request);
  }
}

/**
 * Network-first strategy: Try network, fallback to cache
 */
async function networkFirstStrategy(request, cacheName) {
  const cache = await caches.open(cacheName);

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.warn('[SW] Network failed, trying cache:', request.url);
    const cachedResponse = await cache.match(request);

    if (cachedResponse) {
      return cachedResponse;
    }

    // Return offline page for navigation requests
    return createOfflineResponse(request);
  }
}

/**
 * Stale-while-revalidate: Return cached immediately, update in background
 */
async function staleWhileRevalidateStrategy(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);

  // Fetch in background
  const fetchPromise = fetch(request)
    .then((networkResponse) => {
      if (networkResponse.ok) {
        cache.put(request, networkResponse.clone());
      }
      return networkResponse;
    })
    .catch((error) => {
      console.warn('[SW] Background fetch failed:', request.url);
      return null;
    });

  // Return cached immediately, or wait for network
  return cachedResponse || fetchPromise;
}

// Helper Functions

function isGoogleFont(url) {
  return url.hostname === 'fonts.googleapis.com' ||
         url.hostname === 'fonts.gstatic.com';
}

function isCDNResource(url) {
  return url.hostname === 'cdn.tailwindcss.com' ||
         url.hostname === 'cdn.jsdelivr.net' ||
         url.hostname === 'cdnjs.cloudflare.com';
}

function isImageRequest(request, url) {
  const acceptHeader = request.headers.get('Accept') || '';
  const isImage = acceptHeader.includes('image');
  const isIconPath = url.pathname.includes('/assets/icons/') ||
                     url.pathname.includes('/favicon');
  return isImage || isIconPath;
}

function isStaticAsset(url) {
  return url.pathname.endsWith('.css') ||
         url.pathname.endsWith('.js') ||
         url.pathname.endsWith('.json') ||
         url.pathname.startsWith('/css/') ||
         url.pathname.startsWith('/js/');
}

/**
 * Create appropriate offline response based on request type
 */
async function createOfflineResponse(request) {
  const url = new URL(request.url);
  const acceptHeader = request.headers.get('Accept') || '';

  // For navigation requests, return offline page
  if (acceptHeader.includes('text/html')) {
    const offlinePage = await caches.match('/offline.html');
    if (offlinePage) {
      return offlinePage;
    }
    return new Response(
      '<html><body><h1>Offline</h1><p>Please check your internet connection.</p></body></html>',
      { headers: { 'Content-Type': 'text/html' } }
    );
  }

  // For API requests, return JSON error
  if (url.pathname.startsWith('/api/')) {
    return new Response(
      JSON.stringify({ error: 'Offline', message: 'No internet connection' }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }

  // Default offline response
  return new Response('Offline', { status: 503 });
}

// Message handling for communication with main thread
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data && event.data.type === 'GET_VERSION') {
    event.ports[0].postMessage({ version: CACHE_VERSION });
  }

  if (event.data && event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches.keys().then((names) =>
        Promise.all(names.map((name) => caches.delete(name)))
      )
    );
  }
});

// Background sync for offline actions (future enhancement)
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-goals') {
    console.log('[SW] Background sync triggered');
    // TODO: Implement offline goal sync
  }
});

console.log('[SW] Service worker loaded, version:', CACHE_VERSION);
