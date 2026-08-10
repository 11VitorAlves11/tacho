import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { addWorkspaceMember, listWorkspaceMembers } from '../api/auth'
import type { WorkspaceMember } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { applyTheme, getStoredTheme, type Theme } from '../theme'
import { ChevronDownIcon, PlusIcon } from './icons'

const THEME_OPTIONS: { value: Theme; label: string }[] = [
  { value: 'system', label: 'Sistema' },
  { value: 'light', label: 'Claro' },
  { value: 'dark', label: 'Escuro' },
]

function initials(email: string) {
  return email.slice(0, 2).toUpperCase()
}

export function UserMenu() {
  const [open, setOpen] = useState(false)
  const [theme, setTheme] = useState<Theme>(() => getStoredTheme())
  const [members, setMembers] = useState<WorkspaceMember[] | null>(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [newEmail, setNewEmail] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [addError, setAddError] = useState<string | null>(null)
  const [adding, setAdding] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (open && members === null) {
      listWorkspaceMembers().then(setMembers).catch(() => {})
    }
  }, [open, members])

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  function handleThemeChange(next: Theme) {
    setTheme(next)
    applyTheme(next)
  }

  async function handleAddMember(e: FormEvent) {
    e.preventDefault()
    setAddError(null)
    setAdding(true)
    try {
      const member = await addWorkspaceMember(newEmail, newPassword)
      setMembers((prev) => [...(prev ?? []), member])
      setNewEmail('')
      setNewPassword('')
      setShowAddForm(false)
    } catch {
      setAddError('Não foi possível criar a conta (email já existe?).')
    } finally {
      setAdding(false)
    }
  }

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  if (!user) return null

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="true"
        className="flex items-center gap-1.5 rounded-full bg-card-white/15 py-1.5 pl-1.5 pr-2.5 text-sm font-medium transition-colors hover:bg-card-white/25"
      >
        <span className="flex size-7 items-center justify-center rounded-full bg-card-white text-xs font-semibold text-primary-forest">
          {initials(user.email)}
        </span>
        <ChevronDownIcon className={`size-4 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute right-0 top-full z-30 mt-2 max-h-[calc(100vh-5rem)] w-64 overflow-y-auto rounded-2xl bg-surface p-3 text-text-primary shadow-[0_10px_30px_-8px_rgba(28,43,31,0.35)]">
          <p className="px-2 text-xs font-medium uppercase tracking-wide text-text-secondary">Sessão</p>
          <p className="mt-1 px-2 text-sm font-semibold">{user.email}</p>

          <div className="mt-3 border-t border-black/5 pt-3">
            <p className="px-2 text-xs font-medium uppercase tracking-wide text-text-secondary">Agregado</p>
            <ul className="mt-1 space-y-0.5">
              {members?.map((m) => (
                <li key={m.id} className="px-2 py-0.5 text-sm text-text-primary">
                  {m.email}
                </li>
              ))}
            </ul>
            {!showAddForm ? (
              <button
                type="button"
                onClick={() => setShowAddForm(true)}
                className="mt-2 flex w-full items-center gap-1.5 rounded-lg px-2 py-1.5 text-sm text-text-secondary transition-colors hover:bg-bg-sage hover:text-text-primary"
              >
                <PlusIcon className="size-3.5" />
                Adicionar pessoa
              </button>
            ) : (
              <form onSubmit={handleAddMember} className="mt-2 space-y-2 px-2">
                <input
                  type="email"
                  required
                  placeholder="Email"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  className="w-full rounded-lg bg-bg-sage/60 px-2.5 py-1.5 text-sm outline-none focus:ring-2 focus:ring-accent-leaf"
                />
                <input
                  type="password"
                  required
                  minLength={8}
                  placeholder="Password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full rounded-lg bg-bg-sage/60 px-2.5 py-1.5 text-sm outline-none focus:ring-2 focus:ring-accent-leaf"
                />
                {addError && <p className="text-xs text-accent-orange">{addError}</p>}
                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={adding}
                    className="flex-1 rounded-full bg-primary-forest px-3 py-1.5 text-xs font-medium text-card-white disabled:opacity-60"
                  >
                    {adding ? 'A criar…' : 'Criar conta'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowAddForm(false)}
                    className="rounded-full px-3 py-1.5 text-xs font-medium text-text-secondary hover:bg-bg-sage"
                  >
                    Cancelar
                  </button>
                </div>
              </form>
            )}
          </div>

          <div className="mt-3 border-t border-black/5 pt-3">
            <p className="px-2 text-xs font-medium uppercase tracking-wide text-text-secondary">Tema</p>
            <div className="mt-2 flex gap-1 rounded-full bg-bg-sage p-1">
              {THEME_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => handleThemeChange(opt.value)}
                  aria-pressed={theme === opt.value}
                  className={`flex-1 rounded-full py-1 text-xs font-medium transition-colors ${
                    theme === opt.value ? 'bg-primary-forest text-card-white' : 'text-text-secondary'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-3 border-t border-black/5 pt-3">
            <button
              type="button"
              onClick={handleLogout}
              className="w-full rounded-lg px-2 py-1.5 text-left text-sm font-medium text-accent-orange transition-colors hover:bg-accent-orange/10"
            >
              Sair
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
