import { useEffect, useRef, useState } from 'react'
import { ChevronDownIcon } from './icons'
import { applyTheme, getStoredTheme, type Theme } from '../theme'

const THEME_OPTIONS: { value: Theme; label: string }[] = [
  { value: 'system', label: 'Sistema' },
  { value: 'light', label: 'Claro' },
  { value: 'dark', label: 'Escuro' },
]

// Ainda não há contas nem sessões (v1.2, PRODUCT.md) — este menu mostra o
// agregado real, sem fingir um "sair" ou "definições de conta" que não
// existem.
export function UserMenu() {
  const [open, setOpen] = useState(false)
  const [theme, setTheme] = useState<Theme>(() => getStoredTheme())
  const ref = useRef<HTMLDivElement>(null)

  function handleThemeChange(next: Theme) {
    setTheme(next)
    applyTheme(next)
  }

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

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
          VM
        </span>
        <ChevronDownIcon className={`size-4 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-56 rounded-2xl bg-surface p-3 text-text-primary shadow-[0_10px_30px_-8px_rgba(28,43,31,0.35)]">
          <p className="px-2 text-xs font-medium uppercase tracking-wide text-text-secondary">Agregado</p>
          <p className="mt-1 px-2 text-sm font-semibold">Vítor &amp; Mariana</p>
          <div className="mt-3 border-t border-black/5 pt-3">
            <p className="px-2 text-xs text-text-secondary">Contas individuais chegam na v1.2 — por agora é um espaço só.</p>
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
        </div>
      )}
    </div>
  )
}
