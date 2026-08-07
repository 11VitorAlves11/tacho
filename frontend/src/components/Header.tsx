import { Link } from 'react-router-dom'
import { PlusIcon, PotIcon } from './icons'
import { UserMenu } from './UserMenu'

export function Header() {
  return (
    <header className="bg-gradient-to-br from-bg-sage-deep-start to-bg-sage-deep-end text-card-white">
      <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-4 sm:px-6">
        <Link to="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <PotIcon className="size-6" />
          <span className="text-lg">Tacho</span>
        </Link>
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
