import type { ReactNode } from 'react'
import { PotIcon } from '../components/icons'

export function AuthLayout({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center bg-bg-sage px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center gap-2 text-center">
          <span className="flex size-12 items-center justify-center rounded-2xl bg-gradient-to-br from-bg-sage-deep-start to-bg-sage-deep-end text-card-white">
            <PotIcon className="size-6" />
          </span>
          <h1 className="text-xl font-bold text-text-primary">{title}</h1>
          <p className="text-sm text-text-secondary">{subtitle}</p>
        </div>
        <div className="rounded-2xl bg-surface p-6 shadow-[0_10px_30px_-8px_rgba(28,43,31,0.35)]">{children}</div>
      </div>
    </div>
  )
}
