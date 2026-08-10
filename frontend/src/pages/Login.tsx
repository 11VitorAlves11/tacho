import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { login } from '../api/auth'
import { AuthLayout } from '../auth/AuthLayout'
import { useAuth } from '../auth/AuthContext'

export function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const { refresh } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const justSetup = (location.state as { justSetup?: boolean } | null)?.justSetup

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
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            className="w-full rounded-lg bg-bg-sage/60 px-3 py-2 text-sm text-text-primary outline-none focus:ring-2 focus:ring-accent-leaf"
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
      </form>
    </AuthLayout>
  )
}
