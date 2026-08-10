import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { getCurrentUser, getSetupStatus, logout as apiLogout, tryForwardLogin } from '../api/auth'
import { setUnauthorizedHandler } from '../api/client'
import type { CurrentUser } from '../api/types'

interface AuthState {
  // undefined enquanto a verificação inicial (GET /users/me) não responde —
  // distingue "ainda não sabemos" de "sabemos que não há sessão" (null).
  user: CurrentUser | null | undefined
  needsSetup: boolean | undefined
  refresh: () => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null | undefined>(undefined)
  const [needsSetup, setNeedsSetup] = useState<boolean | undefined>(undefined)

  async function refresh() {
    const [userResult, statusResult] = await Promise.allSettled([getCurrentUser(), getSetupStatus()])
    let user = userResult.status === 'fulfilled' ? userResult.value : null

    // Sem sessão própria ainda — tenta o login silencioso via forward-auth
    // (produção, atrás do Authentik) antes de assumir que é preciso mostrar
    // a página de login. Best-effort: em dev ou com forward-auth desligado
    // no backend, isto dá sempre 404 e `user` continua null.
    if (!user) {
      const forwarded = await tryForwardLogin()
      if (forwarded) user = await getCurrentUser().catch(() => null)
    }

    setUser(user)
    setNeedsSetup(statusResult.status === 'fulfilled' ? statusResult.value.needs_setup : false)
  }

  useEffect(() => {
    refresh()
    // Sessão expirada a meio do uso (cookie caducado, revogado, etc.) — o
    // interceptor do axios avisa aqui, para deixar de mostrar o utilizador
    // como autenticado sem esperar pelo próximo refresh manual da página.
    setUnauthorizedHandler(() => setUser(null))
    return () => setUnauthorizedHandler(() => {})
  }, [])

  async function logout() {
    await apiLogout()
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, needsSetup, refresh, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth só pode ser usado dentro de AuthProvider')
  return ctx
}
