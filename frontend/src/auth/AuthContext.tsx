import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { getCurrentUser, getSetupStatus, logout as apiLogout, tryForwardLogin } from '../api/auth'
import { setUnauthorizedHandler } from '../api/client'
import type { CurrentUser, ForwardLoginBlockReason } from '../api/types'

interface ForwardAuthBlock {
  reason: ForwardLoginBlockReason
  email?: string
}

interface AuthState {
  // undefined enquanto a verificação inicial (GET /users/me) não responde —
  // distingue "ainda não sabemos" de "sabemos que não há sessão" (null).
  user: CurrentUser | null | undefined
  needsSetup: boolean | undefined
  // Authentik já identificou esta pessoa via forward-auth, mas falta ação
  // do admin do lado do Tacho (conta inexistente/inativa/sem agregado) —
  // `App.tsx` mostra uma página de erro em vez do ecrã de login.
  forwardAuthBlocked: ForwardAuthBlock | null
  refresh: () => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null | undefined>(undefined)
  const [needsSetup, setNeedsSetup] = useState<boolean | undefined>(undefined)
  const [forwardAuthBlocked, setForwardAuthBlocked] = useState<ForwardAuthBlock | null>(null)

  async function refresh() {
    const [userResult, statusResult] = await Promise.allSettled([getCurrentUser(), getSetupStatus()])
    let user = userResult.status === 'fulfilled' ? userResult.value : null
    let blocked: ForwardAuthBlock | null = null

    // Sem sessão própria ainda — tenta o login silencioso via forward-auth
    // (produção, atrás do Authentik) antes de assumir que é preciso mostrar
    // a página de login. Best-effort: em dev ou com forward-auth desligado
    // no backend, isto dá sempre `not_applicable` e `user` continua null.
    if (!user) {
      const forwarded = await tryForwardLogin()
      if (forwarded.status === 'ok') {
        user = await getCurrentUser().catch(() => null)
      } else if (forwarded.status === 'blocked') {
        blocked = { reason: forwarded.reason, email: forwarded.email }
      }
    }

    setUser(user)
    setForwardAuthBlocked(blocked)
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

  return (
    <AuthContext.Provider value={{ user, needsSetup, forwardAuthBlocked, refresh, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth só pode ser usado dentro de AuthProvider')
  return ctx
}
