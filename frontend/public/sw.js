// Service worker básico — só para satisfazer o critério de instalabilidade
// e dar cache-first aos bundles JS/CSS do Vite (hash no nome do ficheiro,
// por isso é seguro cachear indefinidamente). Nunca intercepta pedidos à
// API do backend nem navegação — este é o mesmo domínio que serve tanto
// o frontend como a API em produção (VITE_API_URL="" — ver api/client.ts),
// não há prefixo /api a distinguir, por isso o critério é explícito: só
// /assets/*.
const CACHE_NAME = 'tacho-assets-v1'

self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))),
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return

  const url = new URL(request.url)
  if (url.origin !== self.location.origin || !url.pathname.startsWith('/assets/')) return

  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached
      return fetch(request).then((response) => {
        if (response.ok) {
          const clone = response.clone()
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone))
        }
        return response
      })
    }),
  )
})
