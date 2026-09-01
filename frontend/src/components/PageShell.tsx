import type { ReactNode } from 'react'
import { BottomNav } from './BottomNav'
import { Header } from './Header'
import { Sidebar } from './Sidebar'

export function PageShell({ children, wide = false }: { children: ReactNode; wide?: boolean }) {
  return (
    <div className="min-h-svh overflow-x-hidden bg-bg-sage pb-28 lg:pb-0 print:min-h-0 print:pb-0">
      <Header />
      <div className="flex">
        <Sidebar />
        <main className={`min-w-0 flex-1 px-3 py-5 min-[380px]:px-4 sm:px-6 sm:py-8 lg:px-8 xl:px-10 print:p-0 ${wide ? '2xl:px-12' : ''}`}>
          <div className={`mx-auto w-full ${wide ? 'max-w-[1500px]' : 'max-w-6xl'}`}>{children}</div>
        </main>
      </div>
      <BottomNav />
    </div>
  )
}
