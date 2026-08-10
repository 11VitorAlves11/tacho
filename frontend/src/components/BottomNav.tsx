import { NavLink } from 'react-router-dom'
import { CalendarIcon, CartIcon, PlusIcon, PotIcon } from './icons'

const linkBase =
  'flex flex-1 flex-col items-center gap-1 rounded-full py-2 text-xs font-medium transition-colors'

export function BottomNav() {
  return (
    <nav
      className="fixed inset-x-4 bottom-4 z-20 flex gap-1 rounded-full bg-surface/95 p-1.5 shadow-[0_10px_30px_-8px_rgba(28,43,31,0.35)] backdrop-blur sm:hidden"
      aria-label="Navegação principal"
    >
      <NavLink
        to="/"
        end
        className={({ isActive }) =>
          `${linkBase} ${isActive ? 'bg-primary-forest text-card-white' : 'text-text-secondary'}`
        }
      >
        <PotIcon className="size-5" />
        Receitas
      </NavLink>
      <NavLink
        to="/lista-compras"
        className={({ isActive }) =>
          `${linkBase} ${isActive ? 'bg-primary-forest text-card-white' : 'text-text-secondary'}`
        }
      >
        <CartIcon className="size-5" />
        Lista
      </NavLink>
      <NavLink
        to="/planeamento"
        className={({ isActive }) =>
          `${linkBase} ${isActive ? 'bg-primary-forest text-card-white' : 'text-text-secondary'}`
        }
      >
        <CalendarIcon className="size-5" />
        Plano
      </NavLink>
      <NavLink
        to="/adicionar"
        className={({ isActive }) =>
          `${linkBase} ${isActive ? 'bg-primary-forest text-card-white' : 'text-text-secondary'}`
        }
      >
        <PlusIcon className="size-5" />
        Adicionar
      </NavLink>
    </nav>
  )
}
