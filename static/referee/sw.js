const CACHE_NAME = 'referee-v1.0.0';
const urlsToCache = [
  '/referee',
  '/static/referee/manifest.json',
  '/static/referee/court.jpg',
  '/static/referee/img_01.png',
  '/static/referee/img_02.png',
  '/static/referee/icon-192.png',
  '/static/referee/icon-512.png'
];

// Установка Service Worker
self.addEventListener('install', function(event) {
  console.log('Service Worker: Установка...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('Service Worker: Кэширование файлов');
        return cache.addAll(urlsToCache);
      })
      .catch(function(error) {
        console.log('Service Worker: Ошибка кэширования', error);
      })
  );
});

// Активация Service Worker
self.addEventListener('activate', function(event) {
  console.log('Service Worker: Активация...');
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          if (cacheName !== CACHE_NAME) {
            console.log('Service Worker: Удаление старого кэша', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Перехват запросов
self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        // Возвращаем кэшированную версию или загружаем из сети
        if (response) {
          console.log('Service Worker: Загрузка из кэша', event.request.url);
          return response;
        }
        
        console.log('Service Worker: Загрузка из сети', event.request.url);
        return fetch(event.request).then(function(response) {
          // Проверяем, что ответ валидный
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }

          // Клонируем ответ
          var responseToCache = response.clone();

          caches.open(CACHE_NAME)
            .then(function(cache) {
              cache.put(event.request, responseToCache);
            });

          return response;
        });
      })
  );
});

// Обработка сообщений от основного потока
self.addEventListener('message', function(event) {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// Уведомления
self.addEventListener('notificationclick', function(event) {
  console.log('Service Worker: Клик по уведомлению');
  event.notification.close();
  
  event.waitUntil(
    clients.openWindow('/referee')
  );
});
