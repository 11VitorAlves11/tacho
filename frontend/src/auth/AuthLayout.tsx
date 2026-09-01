import type { ReactNode } from 'react'
import { Brand } from '../components/Brand'

export function AuthLayout({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center bg-bg-sage px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center gap-2 text-center">
          <Brand compact className="size-16" />
          <h1 className="text-xl font-bold text-text-primary">{title}</h1>
          <p className="text-sm text-text-secondary">{subtitle}</p>
        </div>
        <div className="rounded-2xl border border-border bg-surface p-6 shadow-[0_12px_35px_rgba(20,30,24,0.08)]">{children}</div>
      </div>
    </div>
  )
}
