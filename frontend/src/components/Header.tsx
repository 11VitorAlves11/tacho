import { NavLink, Link } from 'react-router-dom'
import { CalendarIcon, CartIcon, PlusIcon, PotIcon } from './icons'
import { UserMenu } from './UserMenu'

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-1.5 rounded-full px-3 py-2 text-sm font-medium transition-colors ${
    isActive ? 'bg-card-white/20' : 'text-card-white/85 hover:bg-card-white/10'
  }`

export function Header() {
  return (
    <header className="bg-gradient-to-br from-bg-sage-deep-start to-bg-sage-deep-end text-card-white print:hidden">
      <div className="mx-auto flex max-w-4xl items-center justify-between gap-3 px-4 py-4 sm:px-6">
        <div className="flex items-center gap-5">
          <Link to="/" className="flex shrink-0 items-center gap-2 font-semibold tracking-tight">
            <PotIcon className="size-6" />
            <span className="text-lg">Tacho</span>
          </Link>
          {/* Equivalente desktop do BottomNav (sm:hidden) — em ecrã pequeno a
              navegação vive só no BottomNav, para não duplicar destinos.
              Agrupado com o logótipo (em vez de centrado sozinho no meio do
              header) para ler como uma barra de navegação normal — marca +
              destinos à esquerda, ações à direita. */}
          <nav className="hidden items-center gap-1 sm:flex" aria-label="Navegação principal">
            <NavLink to="/lista-compras" className={navLinkClass}>
              <CartIcon className="size-4" />
              Lista
            </NavLink>
            <NavLink to="/planeamento" className={navLinkClass}>
              <CalendarIcon className="size-4" />
              Plano
            </NavLink>
          </nav>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/adicionar"
            className="hidden items-center gap-1.5 rounded-full bg-card-white/15 px-4 py-2 text-sm font-medium transition-colors hover:bg-card-white/25 sm:flex"
          >
            <PlusIcon className="size-4" />
            Adicionar receita
          </Link>
          <UserMenu />
        </div>
      </div>
    </header>
  )
}
