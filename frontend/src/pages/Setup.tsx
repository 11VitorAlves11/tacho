import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { getSetupStatus, setup } from '../api/auth'
import { AuthLayout } from '../auth/AuthLayout'
import { useAuth } from '../auth/useAuth'
import { PasswordInput } from '../components/ui'

export function Setup() {
  const [checking, setChecking] = useState(true)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirmation, setPasswordConfirmation] = useState('')
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
    if (password !== passwordConfirmation) {
      setError('As passwords não coincidem.')
      return
    }
    setLoading(true)
    try {
      await setup(name.trim(), email, password)
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
      <form onSubmit={handleSubmit} className="space-y-4">
        <label className="block">
          <span className="mb-1.5 block text-xs font-medium text-text-secondary">Nome de utilizador</span>
          <input
            type="text"
            required
            minLength={2}
            maxLength={80}
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoComplete="name"
            placeholder="Como queres ser tratado?"
            className="min-h-11 w-full rounded-xl border border-border bg-surface px-3 text-sm text-text-primary outline-none focus:border-primary-forest focus:ring-2 focus:ring-primary-forest/15"
          />
        </label>
        <label className="block">
          <span className="mb-1.5 block text-xs font-medium text-text-secondary">Email</span>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
            className="min-h-11 w-full rounded-xl border border-border bg-surface px-3 text-sm text-text-primary outline-none focus:border-primary-forest focus:ring-2 focus:ring-primary-forest/15"
          />
        </label>
        <label className="block">
          <span className="mb-1.5 block text-xs font-medium text-text-secondary">Password</span>
          <PasswordInput
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
          />
        </label>
        <label className="block">
          <span className="mb-1.5 block text-xs font-medium text-text-secondary">Confirmar password</span>
          <PasswordInput
            required
            minLength={8}
            value={passwordConfirmation}
            onChange={(e) => setPasswordConfirmation(e.target.value)}
            autoComplete="new-password"
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
