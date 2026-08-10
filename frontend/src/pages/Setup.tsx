import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { getSetupStatus, setup } from '../api/auth'
import { AuthLayout } from '../auth/AuthLayout'
import { useAuth } from '../auth/AuthContext'

export function Setup() {
  const [checking, setChecking] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { refresh } = useAuth()

  useEffect(() => {
    getSetupStatus()
      .then((status) => {
        if (!status.needs_setup) {
          navigate('/login', { replace: true })
          return
        }
        setChecking(false)
      })
      .catch(() => setChecking(false))
  }, [navigate])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await setup(email, password)
      // O guard de rotas em App.tsx decide entre /setup e /login com base
      // no `needsSetup` do AuthContext — sem atualizá-lo aqui primeiro, o
      // guard continuava a achar que a configuração inicial ainda faltava
      // e devolvia sempre a /setup, mesmo depois deste navigate.
      await refresh()
      navigate('/login', { replace: true, state: { justSetup: true } })
    } catch {
      setError('Não foi possível criar a conta. Tenta outra vez.')
    } finally {
      setLoading(false)
    }
  }

  if (checking) return null

  return (
    <AuthLayout title="Configuração inicial" subtitle="Cria a primeira conta do agregado para começar a usar o Tacho.">
      <form onSubmit={handleSubmit} className="space-y-3">
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
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            className="w-full rounded-lg bg-bg-sage/60 px-3 py-2 text-sm text-text-primary outline-none focus:ring-2 focus:ring-accent-leaf"
          />
        </label>
        {error && <p className="text-sm text-accent-orange">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-full bg-primary-forest px-4 py-2.5 text-sm font-medium text-card-white shadow-[0_10px_30px_-8px_rgba(28,43,31,0.35)] transition-opacity disabled:opacity-60"
        >
          {loading ? 'A criar…' : 'Criar conta'}
        </button>
      </form>
    </AuthLayout>
  )
}
