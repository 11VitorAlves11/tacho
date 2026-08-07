import type { ReactNode } from 'react'
import { BottomNav } from './BottomNav'
import { Header } from './Header'

export function PageShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-svh pb-28 sm:pb-10">
      <Header />
      <main className="mx-auto max-w-4xl px-4 py-6 sm:px-6 sm:py-8">{children}</main>
      <BottomNav />
    </div>
  )
}
