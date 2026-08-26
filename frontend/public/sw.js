// Service worker — dois papéis, propositadamente limitados:
// 1) cache-first dos bundles JS/CSS do Vite (/assets/*, hash no nome, seguro
//    cachear indefinidamente) — só para satisfazer o critério de PWA
//    instalável.
// 2) network-first com fallback a cache só da RECEITA ATIVA no Modo Cozinha
//    (CookMode.tsx manda um postMessage a dizer quais URLs guardar assim
//    que a receita carrega) — para a receita continuar visível se a rede
//    cair a meio de cozinhar, mas sem pré-cachear a app toda nem virar um
//    proxy de API genérico. Nunca intercepta navegação nem qualquer outro
//    pedido à API (categorias, plano, despensa, etc.) — este é o mesmo
//    domínio que serve frontend e API em produção (VITE_API_URL="" — ver
//    api/client.ts), sem prefixo /api a distinguir.
const ASSETS_CACHE = 'tacho-assets-v1'
const ACTIVE_RECIPE_CACHE = 'tacho-active-recipe-v1'
const KNOWN_CACHES = new Set([ASSETS_CACHE, ACTIVE_RECIPE_CACHE])

self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => !KNOWN_CACHES.has(k)).map((k) => caches.delete(k)))),
  )
  self.clients.claim()
})

function cacheFirstAssets(request) {
  return caches.match(request).then((cached) => {
    if (cached) return cached
    return fetch(request).then((response) => {
      if (response.ok) {
        const clone = response.clone()
        caches.open(ASSETS_CACHE).then((cache) => cache.put(request, clone))
      }
      return response
    })
  })
}

// Tenta a rede primeiro (nunca serve dados desatualizados enquanto há
// ligação); só recorre à cache da receita ativa se a rede falhar — e só
// para URLs que já lá estavam explicitamente guardadas (CACHE_ACTIVE_RECIPE
// abaixo), nunca para outras receitas ao acaso.
function networkFirstActiveRecipe(request) {
  return caches.open(ACTIVE_RECIPE_CACHE).then((cache) =>
    fetch(request)
      .then((response) => {
        return cache.match(request).then((existing) => {
          if (existing && response.ok) cache.put(request, response.clone())
          return response
        })
      })
      .catch((err) =>
        cache.match(request).then((cached) => {
          if (cached) return cached
          throw err
        }),
      ),
  )
}

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return

  const url = new URL(request.url)
  if (url.origin === self.location.origin && url.pathname.startsWith('/assets/')) {
    event.respondWith(cacheFirstAssets(request))
    return
  }

  if (url.pathname.startsWith('/recipes/') || url.pathname.startsWith('/media/')) {
    event.respondWith(networkFirstActiveRecipe(request))
  }
})

// CookMode.tsx manda isto assim que a receita carrega (a cada receita nova
// substitui a anterior — só uma "receita ativa offline" de cada vez, nunca
// acumula histórico). Best-effort: se algum fetch falhar aqui (já offline
// ao entrar no Modo Cozinha, por exemplo), essa URL fica simplesmente sem
// cache, sem rebentar o resto.
self.addEventListener('message', (event) => {
  if (event.data?.type !== 'CACHE_ACTIVE_RECIPE') return
  const urls = event.data.urls || []
  event.waitUntil(
    caches.open(ACTIVE_RECIPE_CACHE).then(async (cache) => {
      const oldKeys = await cache.keys()
      await Promise.all(oldKeys.map((key) => cache.delete(key)))
      await Promise.all(
        urls.map((url) =>
          fetch(url, { credentials: 'include' })
            .then((response) => {
              if (response.ok) return cache.put(url, response)
            })
            .catch(() => {}),
        ),
      )
    }),
  )
})
