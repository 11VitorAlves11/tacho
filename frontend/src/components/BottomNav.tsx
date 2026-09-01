import { NavLink } from 'react-router-dom'
import { CalendarIcon, CartIcon, HomeIcon, PantryIcon, PlusIcon } from './icons'

const linkBase =
  'flex min-h-12 flex-1 flex-col items-center justify-center gap-0.5 text-[11px] font-medium transition-colors'

export function BottomNav() {
  return (
    <nav
      className="fixed inset-x-4 bottom-[calc(0.75rem+env(safe-area-inset-bottom))] z-40 grid grid-cols-5 items-center rounded-[1.75rem] border border-border bg-surface/95 px-2 py-1.5 shadow-[0_10px_35px_rgba(20,30,24,0.14)] backdrop-blur lg:hidden print:hidden"
      aria-label="Navegação principal"
    >
      <NavLink
        to="/"
        end
        className={({ isActive }) => `${linkBase} ${isActive ? 'text-primary-forest' : 'text-text-secondary'}`}
      >
        <HomeIcon className="size-5" />
        Início
      </NavLink>
      <NavLink
        to="/planeamento"
        className={({ isActive }) => `${linkBase} ${isActive ? 'text-primary-forest' : 'text-text-secondary'}`}
      >
        <CalendarIcon className="size-5" />
        Refeições
      </NavLink>
      <NavLink
        to="/adicionar"
        className="relative -top-5 flex flex-col items-center gap-1 text-[11px] font-semibold text-primary-forest"
      >
        <span className="flex size-14 items-center justify-center rounded-full border-4 border-surface bg-primary-forest text-white shadow-lg"><PlusIcon className="size-7" /></span>
        Adicionar
      </NavLink>
      <NavLink to="/lista-compras" className={({ isActive }) => `${linkBase} ${isActive ? 'text-primary-forest' : 'text-text-secondary'}`}>
        <CartIcon className="size-5" />
        Lista
      </NavLink>
      <NavLink to="/despensa" className={({ isActive }) => `${linkBase} ${isActive ? 'text-primary-forest' : 'text-text-secondary'}`}>
        <PantryIcon className="size-5" />
        Despensa
      </NavLink>
    </nav>
  )
}
