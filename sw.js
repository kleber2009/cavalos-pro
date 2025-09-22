const CACHE_NAME = 'cavalos-hibrido-v2.0';
const STATIC_CACHE = 'static-v2.0';
const DYNAMIC_CACHE = 'dynamic-v2.0';

const STATIC_FILES = [
  '/',
  '/static/icons/icon.svg',
  '/manifest.json',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
  'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
];

// Install event - cache static files
self.addEventListener('install', event => {
  console.log('[SW] Installing...');
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('[SW] Caching static files');
        return cache.addAll(STATIC_FILES);
      })
      .then(() => {
        console.log('[SW] Skip waiting');
        return self.skipWaiting();
      })
  );
});

// Activate event - clean old caches
self.addEventListener('activate', event => {
  console.log('[SW] Activating...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('[SW] Claiming clients');
      return self.clients.claim();
    })
  );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Handle API requests differently
  if (url.pathname.startsWith('/analisar')) {
    event.respondWith(
      fetch(request)
        .then(response => {
          // Clone response for caching
          const responseClone = response.clone();
          caches.open(DYNAMIC_CACHE)
            .then(cache => {
              cache.put(request, responseClone);
            });
          return response;
        })
        .catch(() => {
          // Return cached version if available
          return caches.match(request)
            .then(cachedResponse => {
              if (cachedResponse) {
                return cachedResponse;
              }
              // Return offline page or error
              return new Response(
                JSON.stringify({
                  error: 'Sem conexão. Dados em cache não disponíveis.',
                  offline: true
                }),
                {
                  status: 503,
                  headers: { 'Content-Type': 'application/json' }
                }
              );
            });
        })
    );
    return;
  }

  // Handle static files
  event.respondWith(
    caches.match(request)
      .then(cachedResponse => {
        if (cachedResponse) {
          return cachedResponse;
        }
        
        return fetch(request)
          .then(response => {
            // Don't cache non-successful responses
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }

            // Clone response for caching
            const responseToCache = response.clone();
            caches.open(DYNAMIC_CACHE)
              .then(cache => {
                cache.put(request, responseToCache);
              });

            return response;
          })
          .catch(() => {
            // Return offline fallback for HTML pages
            if (request.headers.get('accept').includes('text/html')) {
              return caches.match('/');
            }
          });
      })
  );
});

// Background sync for offline actions
self.addEventListener('sync', event => {
  console.log('[SW] Background sync:', event.tag);
  if (event.tag === 'background-sync') {
    event.waitUntil(
      // Handle background sync logic here
      console.log('[SW] Performing background sync')
    );
  }
});

// Push notifications (for future use)
self.addEventListener('push', event => {
  console.log('[SW] Push received');
  const options = {
    body: event.data ? event.data.text() : 'Nova análise disponível!',
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/icon.svg',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'Ver Análise',
        icon: '/static/icons/icon.svg'
      },
      {
        action: 'close',
        title: 'Fechar'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('Cavalos Pro', options)
  );
});

// Clique em notificação
self.addEventListener('notificationclick', function(event) {
  console.log('[Service Worker] Clique em notificação:', event);
  
  event.notification.close();
  
  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});