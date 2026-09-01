import { useEffect, useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { getOIDCStatus, login, oidcStartUrl } from '../api/auth'
import type { OIDCStatus } from '../api/types'
import { AuthLayout } from '../auth/AuthLayout'
import { useAuth } from '../auth/useAuth'
import { PasswordInput } from '../components/ui'

export function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [oidcStatus, setOIDCStatus] = useState<OIDCStatus | null>(null)
  const { refresh } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const justSetup = (location.state as { justSetup?: boolean } | null)?.justSetup
  const oidcError = new URLSearchParams(location.search).get('oidc_error')

  useEffect(() => {
    getOIDCStatus().then(setOIDCStatus).catch(() => {})
  }, [])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(email, password)
      await refresh()
      navigate('/', { replace: true })
    } catch {
      setError('Email ou password incorretos.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Tacho" subtitle="Inicia sessão para veres as receitas do agregado.">
      {justSetup && <p className="mb-3 text-sm text-accent-leaf">Conta criada. Já podes iniciar sessão.</p>}
      {oidcError && <p role="alert" className="mb-3 rounded-xl bg-accent-orange/10 p-3 text-sm text-accent-orange">{oidcError}</p>}
      {oidcStatus?.enabled && <a href={oidcStartUrl('/')} className="flex min-h-11 w-full items-center justify-center rounded-xl border border-primary-forest bg-primary-soft px-4 text-sm font-semibold text-forest-text">Entrar com {oidcStatus.display_name}</a>}
      {oidcStatus?.enabled && oidcStatus.local_login_enabled && <div className="my-4 flex items-center gap-3 text-xs text-text-secondary"><span className="h-px flex-1 bg-border" /><span>ou</span><span className="h-px flex-1 bg-border" /></div>}
      {(oidcStatus === null || oidcStatus.local_login_enabled) && <form onSubmit={handleSubmit} className="space-y-3">
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-text-secondary">Email</span>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
            className="w-full rounded-lg bg-bg-sage/60 px-3 py-2 text-sm text-text-primary outline-none focus:ring-2 focus:ring-accent-leaf"
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-text-secondary">Password</span>
          <PasswordInput
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>
        {error && <p className="text-sm text-accent-orange">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-full bg-primary-forest px-4 py-2.5 text-sm font-medium text-card-white shadow-[0_10px_30px_-8px_rgba(28,43,31,0.35)] transition-opacity disabled:opacity-60"
        >
          {loading ? 'A entrar…' : 'Entrar'}
        </button>
      </form>}
    </AuthLayout>
  )
}
