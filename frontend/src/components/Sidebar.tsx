import { NavLink } from 'react-router-dom'
import { CalendarIcon, CartIcon, FolderIcon, HomeIcon, PantryIcon, PlusIcon } from './icons'

const items = [
  { to: '/', label: 'Receitas', icon: HomeIcon, end: true },
  { to: '/adicionar', label: 'Adicionar receita', icon: PlusIcon },
  { to: '/planeamento', label: 'Planeamento de Refeições', icon: CalendarIcon },
  { to: '/lista-compras', label: 'Lista de compras', icon: CartIcon },
  { to: '/colecoes', label: 'Coleções', icon: FolderIcon },
  { to: '/despensa', label: 'Despensa', icon: PantryIcon },
  { to: '/perfis-alimentares', label: 'Perfis alimentares', icon: HomeIcon },
  { to: '/substituicoes', label: 'Substituições', icon: PantryIcon },
]

export function Sidebar() {
  return (
    <aside className="sticky top-16 hidden h-[calc(100svh-4rem)] w-60 shrink-0 border-r border-border bg-surface px-4 py-6 lg:block print:hidden">
      <nav aria-label="Navegação principal" className="space-y-1">
        {items.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => `flex min-h-11 items-center gap-3 rounded-xl px-3.5 text-sm font-medium transition-colors ${
              isActive ? 'bg-primary-soft text-forest-text' : 'text-text-secondary hover:bg-muted hover:text-text-primary'
            }`}
          >
            <Icon className="size-5" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="absolute inset-x-4 bottom-6 rounded-2xl border border-border bg-muted/60 p-4">
        <img src="/tacho-symbol.svg" alt="" className="size-8" />
        <p className="mt-2 text-sm font-semibold text-text-primary">O teu livro de receitas</p>
        <p className="mt-0.5 text-xs leading-relaxed text-text-secondary">Planeia, compra e cozinha num só lugar.</p>
      </div>
    </aside>
  )
}
