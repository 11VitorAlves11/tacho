import { useState, type ButtonHTMLAttributes, type HTMLAttributes, type InputHTMLAttributes, type ReactNode } from 'react'
import type { CategoryIcon } from '../api/types'
import { EyeIcon, EyeOffIcon, SearchIcon } from './icons'

export function Button({
  variant = 'primary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' | 'danger' }) {
  const variants = {
    primary: 'bg-primary-forest text-white hover:brightness-95',
    secondary: 'border border-border bg-surface text-text-primary hover:bg-muted',
    ghost: 'text-text-secondary hover:bg-muted hover:text-text-primary',
    danger: 'bg-danger text-white hover:brightness-95',
  }
  return (
    <button
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition duration-200 disabled:pointer-events-none disabled:opacity-50 ${variants[variant]} ${className}`}
      {...props}
    />
  )
}

export function IconButton({ className = '', ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={`inline-flex size-11 shrink-0 items-center justify-center rounded-xl text-text-secondary transition-colors hover:bg-muted hover:text-text-primary disabled:opacity-50 ${className}`}
      {...props}
    />
  )
}

export function Card({ className = '', ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={`rounded-2xl border border-border bg-surface ${className}`} {...props} />
}

export function Chip({
  active = false,
  kind = 'default',
  accentColor,
  icon,
  className = '',
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { active?: boolean; kind?: 'default' | 'category' | 'tag'; accentColor?: string | null; icon?: CategoryIcon | null }) {
  const kindClass = kind === 'category'
    ? 'border-primary-forest/35 bg-primary-soft text-forest-text hover:border-primary-forest/60'
    : kind === 'tag'
      ? 'border-dashed border-accent-orange/40 bg-accent-orange/10 text-accent-orange hover:border-accent-orange/70 hover:bg-accent-orange/15'
      : 'border-border bg-surface text-text-primary hover:border-primary-forest/40 hover:bg-primary-soft'
  return (
    <button
      type="button"
      aria-pressed={active}
      style={!active && kind === 'category' && accentColor ? { borderColor: `${accentColor}66`, backgroundColor: `${accentColor}18` } : undefined}
      className={`inline-flex min-h-10 shrink-0 items-center gap-1.5 rounded-xl border px-3.5 py-2 text-sm font-medium transition-colors ${
        active
          ? kind === 'tag'
            ? 'border-accent-orange bg-accent-orange text-white'
            : 'border-primary-forest bg-primary-forest text-white'
          : kindClass
      } ${className}`}
      {...props}
    >
      {kind === 'category' && icon && <span aria-hidden="true" style={accentColor ? { color: accentColor } : undefined}>{CATEGORY_ICONS[icon]}</span>}
      {children}
    </button>
  )
}

const CATEGORY_ICONS: Record<CategoryIcon, string> = {
  breakfast: '☀',
  main: '🍲',
  dessert: '♨',
  drink: '◒',
  snack: '◇',
  other: '●',
}

export function CategoryBadge({ children, className = '', color, icon }: { children: ReactNode; className?: string; color?: string | null; icon?: CategoryIcon | null }) {
  const style = color ? { borderColor: `${color}66`, backgroundColor: `${color}18` } : undefined
  return <span style={style} className={`inline-flex w-fit items-center gap-1.5 rounded-lg border border-primary-forest/30 bg-primary-soft px-2.5 py-1 text-xs font-semibold text-forest-text ${className}`}><span aria-hidden="true" style={color ? { color } : undefined} className={icon ? 'text-sm leading-none' : 'size-1.5 rounded-full bg-primary-forest'}>{icon ? CATEGORY_ICONS[icon] : ''}</span>{children}</span>
}

export function TagBadge({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <span className={`inline-flex w-fit items-center rounded-full border border-dashed border-accent-orange/40 bg-accent-orange/10 px-2.5 py-1 text-xs font-medium text-accent-orange ${className}`}><span aria-hidden="true" className="mr-0.5 opacity-70">#</span>{children}</span>
}

export function SearchInput({ className = '', ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className={`flex min-h-12 min-w-0 items-center gap-2.5 rounded-xl border border-border bg-surface px-3 min-[380px]:px-4 transition focus-within:border-primary-forest focus-within:ring-2 focus-within:ring-primary-forest/15 ${className}`}>
      <SearchIcon className="size-5 shrink-0 text-text-secondary" />
      <input
        type="search"
        className="min-w-0 flex-1 bg-transparent text-sm text-text-primary outline-none placeholder:text-text-secondary"
        {...props}
      />
    </label>
  )
}

export function PasswordInput({ className = '', ...props }: Omit<InputHTMLAttributes<HTMLInputElement>, 'type'>) {
  const [visible, setVisible] = useState(false)
  return <div className={`relative ${className}`}><input type={visible ? 'text' : 'password'} className="min-h-11 w-full rounded-xl border border-border bg-surface py-2 pl-3 pr-12 text-sm text-text-primary outline-none transition focus:border-primary-forest focus:ring-2 focus:ring-primary-forest/15" {...props} /><button type="button" onClick={() => setVisible((value) => !value)} aria-label={visible ? 'Ocultar password' : 'Mostrar password'} aria-pressed={visible} className="absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-r-xl text-text-secondary transition-colors hover:text-text-primary"><span className="flex size-5 items-center justify-center">{visible ? <EyeOffIcon className="block size-5" /> : <EyeIcon className="block size-5" />}</span></button></div>
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div aria-hidden="true" className={`animate-pulse rounded-xl bg-muted ${className}`} />
}

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <Card className="p-8 text-center">
      <p className="font-semibold text-text-primary">{title}</p>
      {description && <p className="mx-auto mt-1 max-w-md text-sm text-text-secondary">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </Card>
  )
}

export function ErrorState({ children }: { children: ReactNode }) {
  return (
    <div role="alert" className="rounded-xl border border-danger/20 bg-danger/5 p-4 text-sm text-text-secondary">
      {children}
    </div>
  )
}

export function BottomSheet({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
}) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-labelledby="sheet-title">
      <button className="absolute inset-0 bg-black/35" onClick={onClose} aria-label="Fechar" />
      <section className="absolute inset-x-0 bottom-0 max-h-[85svh] overflow-y-auto rounded-t-3xl border-t border-border bg-surface px-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))] pt-3 shadow-2xl">
        <div className="mx-auto mb-4 h-1 w-10 rounded-full bg-border" />
        <div className="flex items-center justify-between gap-3">
          <h2 id="sheet-title" className="text-lg font-bold text-text-primary">{title}</h2>
          <button onClick={onClose} className="min-h-11 px-2 text-sm font-semibold text-forest-text">Fechar</button>
        </div>
        <div className="mt-4">{children}</div>
      </section>
    </div>
  )
}

export function Modal({ open, title, onClose, children }: { open: boolean; title: string; onClose: () => void; children: ReactNode }) {
  if (!open) return null
  return <div className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-4" role="dialog" aria-modal="true" aria-labelledby="modal-title"><button className="absolute inset-0 bg-black/40" onClick={onClose} aria-label="Fechar" /><section className="relative w-full rounded-t-3xl border border-border bg-surface p-5 shadow-2xl sm:max-w-md sm:rounded-2xl"><div className="flex items-center justify-between gap-3"><h2 id="modal-title" className="text-lg font-bold text-text-primary">{title}</h2><button onClick={onClose} className="min-h-11 px-2 text-sm font-semibold text-forest-text">Fechar</button></div><div className="mt-3">{children}</div></section></div>
}

export function ConfirmDialog({ open, title, description, confirmLabel = 'Confirmar', onCancel, onConfirm }: { open: boolean; title: string; description: string; confirmLabel?: string; onCancel: () => void; onConfirm: () => void }) {
  return <Modal open={open} title={title} onClose={onCancel}><p className="text-sm leading-relaxed text-text-secondary">{description}</p><div className="mt-5 flex justify-end gap-2"><Button variant="ghost" onClick={onCancel}>Cancelar</Button><Button variant="danger" onClick={onConfirm}>{confirmLabel}</Button></div></Modal>
}

export function Toast({ children, onDismiss }: { children: ReactNode; onDismiss?: () => void }) {
  return <div role="status" className="fixed inset-x-4 bottom-28 z-[60] mx-auto flex max-w-sm items-center gap-3 rounded-xl border border-border bg-surface p-4 text-sm font-medium text-text-primary shadow-xl lg:bottom-6">{children}{onDismiss && <button onClick={onDismiss} className="ml-auto text-xs font-semibold text-forest-text">Fechar</button>}</div>
}
