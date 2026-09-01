import { useEffect, useState, type ReactNode } from 'react'
import { getCurrentUser, getSetupStatus, logout as apiLogout, tryForwardLogin } from '../api/auth'
import { setUnauthorizedHandler } from '../api/client'
import type { CurrentUser, ForwardLoginBlockReason } from '../api/types'
import { AuthContext } from './authContext'

interface ForwardAuthBlock {
  reason: ForwardLoginBlockReason
  email?: string
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null | undefined>(undefined)
  const [needsSetup, setNeedsSetup] = useState<boolean | undefined>(undefined)
  const [forwardAuthBlocked, setForwardAuthBlocked] = useState<ForwardAuthBlock | null>(null)

  async function refresh() {
    const [userResult, statusResult] = await Promise.allSettled([getCurrentUser(), getSetupStatus()])
    let user = userResult.status === 'fulfilled' ? userResult.value : null
    let blocked: ForwardAuthBlock | null = null

    // Sem sessão própria ainda — tenta o login silencioso via forward-auth
    // (produção, atrás de um proxy confiável) antes de assumir que é preciso mostrar
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
    // O carregamento inicial sincroniza este contexto com a sessão e o
    // estado de configuração mantidos pelo backend.
    // oxlint-disable-next-line react/set-state-in-effect
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
