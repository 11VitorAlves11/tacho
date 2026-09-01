import { Link } from 'react-router-dom'
import { Brand } from './Brand'
import { SunIcon } from './icons'
import { UserMenu } from './UserMenu'
import { applyTheme, getStoredTheme } from '../theme'

export function Header() {
  function toggleTheme() {
    applyTheme(getStoredTheme() === 'dark' ? 'light' : 'dark')
  }
  return (
    <header className="sticky top-0 z-40 hidden h-16 bg-primary-forest text-white lg:block print:hidden">
      <div className="flex h-full items-center justify-between gap-4 px-6 xl:px-8">
        <Link to="/" className="flex h-12 shrink-0 items-center gap-2.5 text-white" aria-label="Tacho — início">
          <Brand compact className="size-[55px] brightness-0 invert" />
          <span className="text-[28px] font-bold tracking-tight">Tacho</span>
        </Link>
        <div className="flex items-center gap-2">
          <button onClick={toggleTheme} className="flex size-11 items-center justify-center rounded-xl text-white transition-colors hover:bg-white/15" aria-label="Alternar tema">
            <SunIcon className="size-5" />
          </button>
          <UserMenu />
        </div>
      </div>
    </header>
  )
}
