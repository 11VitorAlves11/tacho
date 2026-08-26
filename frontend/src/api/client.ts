import axios from 'axios'

// Em dev, o Vite corre no host e o backend é outro container/porta — sem
// reverse proxy is optional and deployment-specific,
// por isso a base URL vem de uma env var com fallback ao localhost:8000.
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
  // Necessário para o cookie de sessão (app/auth.py, httpOnly) viajar em
  // pedidos entre origens diferentes (frontend :5173, backend :8000 em
  // dev) — sem isto o browser guarda o Set-Cookie do login mas nunca o
  // reenvia nos pedidos seguintes.
  withCredentials: true,
})

let onUnauthorized: (() => void) | null = null

export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && onUnauthorized) {
      onUnauthorized()
    }
    return Promise.reject(error)
  },
)
