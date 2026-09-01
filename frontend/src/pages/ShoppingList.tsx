import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import {
  addShoppingListItem,
  deleteShoppingListItem,
  generateShoppingList,
  listShoppingList,
  updateShoppingListItem,
} from '../api/planning'
import type { ShoppingListItem } from '../api/types'
import { PageShell } from '../components/PageShell'
import { PlusIcon, TrashIcon } from '../components/icons'
import { startOfWeek, toDateKey } from '../lib/date'

export function ShoppingList() {
  const [items, setItems] = useState<ShoppingListItem[] | null>(null)
  const [error, setError] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [newName, setNewName] = useState('')
  const [newQuantity, setNewQuantity] = useState('')

  useEffect(() => {
    listShoppingList()
      .then(setItems)
      .catch(() => setError(true))
  }, [])

  async function handleGenerate() {
    setGenerating(true)
    try {
      const weekStart = toDateKey(startOfWeek(new Date()))
      const updated = await generateShoppingList(weekStart)
      setItems(updated)
    } catch {
      setError(true)
    } finally {
      setGenerating(false)
    }
  }

  async function handleToggle(item: ShoppingListItem) {
    const updated = await updateShoppingListItem(item.id, { is_checked: !item.is_checked })
    setItems((prev) => prev?.map((i) => (i.id === item.id ? updated : i)) ?? prev)
  }

  async function handleDelete(id: string) {
    await deleteShoppingListItem(id)
    setItems((prev) => prev?.filter((i) => i.id !== id) ?? prev)
  }

  async function handleAdd(e: FormEvent) {
    e.preventDefault()
    if (!newName.trim()) return
    const item = await addShoppingListItem(newName.trim(), newQuantity.trim() || null)
    setItems((prev) => [...(prev ?? []), item])
    setNewName('')
    setNewQuantity('')
  }

  const unchecked = items?.filter((i) => !i.is_checked) ?? []
  const checked = items?.filter((i) => i.is_checked) ?? []
  const progress = items?.length ? Math.round((checked.length / items.length) * 100) : 0

  return (
    <PageShell wide>
      <div className="mb-1 flex items-center justify-between gap-3">
        <div><h1 className="text-2xl font-bold tracking-tight text-text-primary sm:text-3xl">Lista de compras</h1>{items && items.length > 0 && <p className="mt-1 text-sm text-text-secondary">{checked.length} de {items.length} concluídos</p>}</div>
        <button
          type="button"
          onClick={handleGenerate}
          disabled={generating}
          className="shrink-0 rounded-full bg-primary-forest px-4 py-2 text-sm font-medium text-card-white shadow-[0_10px_30px_-8px_rgba(28,43,31,0.35)] transition-opacity disabled:opacity-60"
        >
          {generating ? 'A gerar…' : 'Gerar da semana'}
        </button>
      </div>

      <Link to="/despensa" className="mb-6 inline-block text-sm font-medium text-forest-text">
        Despensa →
      </Link>

      {items && items.length > 0 && <div className="mb-6 h-2 overflow-hidden rounded-full bg-muted" aria-label={`${progress}% da lista concluída`} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}><div className="h-full rounded-full bg-primary-forest transition-[width]" style={{ width: `${progress}%` }} /></div>}

      {error && (
        <p className="mb-4 rounded-xl bg-surface p-4 text-sm text-text-secondary">
          Não foi possível ligar ao backend. Confirma se está a correr em {import.meta.env.VITE_API_URL}.
        </p>
      )}

      <form onSubmit={handleAdd} className="mb-6 flex gap-2 rounded-2xl border border-border bg-surface p-3">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="Adicionar item…"
          className="min-w-0 flex-1 rounded-lg bg-muted px-3 py-2 text-sm text-text-primary outline-none placeholder:text-text-secondary focus:ring-2 focus:ring-accent-leaf"
        />
        <input
          value={newQuantity}
          onChange={(e) => setNewQuantity(e.target.value)}
          placeholder="Qtd."
          className="w-20 rounded-lg bg-muted px-3 py-2 text-sm text-text-primary outline-none placeholder:text-text-secondary focus:ring-2 focus:ring-accent-leaf"
        />
        <button
          type="submit"
          className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary-forest text-card-white transition-opacity hover:opacity-90"
          aria-label="Adicionar item"
        >
          <PlusIcon className="size-4" />
        </button>
      </form>

      {!error && items === null && <p className="text-sm text-text-secondary">A carregar…</p>}

      {items !== null && items.length === 0 && (
        <div className="rounded-2xl bg-surface p-8 text-center">
          <p className="font-medium text-text-primary">A lista está vazia.</p>
          <p className="mt-1 text-sm text-text-secondary">
            Usa "Gerar da semana" para juntar os ingredientes do plano, ou adiciona itens à mão.
          </p>
        </div>
      )}

      {items !== null && items.length > 0 && (
        <ul className="grid gap-2 lg:grid-cols-2">
          {[...unchecked, ...checked].map((item) => (
            <ShoppingListRow key={item.id} item={item} onToggle={() => handleToggle(item)} onDelete={() => handleDelete(item.id)} />
          ))}
        </ul>
      )}
    </PageShell>
  )
}

function ShoppingListRow({
  item,
  onToggle,
  onDelete,
}: {
  item: ShoppingListItem
  onToggle: () => void
  onDelete: () => void
}) {
  return (
    <li className="flex min-h-14 items-center gap-3 rounded-xl border border-border bg-surface p-3">
      <button
        type="button"
        onClick={onToggle}
        aria-pressed={item.is_checked}
        aria-label={item.is_checked ? `Desmarcar ${item.name}` : `Marcar ${item.name} como comprado`}
        className={`size-6 shrink-0 rounded-md border-2 transition-colors ${
          item.is_checked ? 'border-accent-leaf bg-accent-leaf' : 'border-text-secondary/40'
        }`}
      />
      <div className={`min-w-0 flex-1 ${item.is_checked ? 'opacity-50' : ''}`}>
        <span className={`text-sm font-medium text-text-primary ${item.is_checked ? 'line-through' : ''}`}>
          {item.name}
        </span>
        {item.quantity && <span className="ml-2 text-xs text-text-secondary">{item.quantity}</span>}
      </div>
      <button
        type="button"
        onClick={onDelete}
        className="flex size-7 shrink-0 items-center justify-center rounded-full text-text-secondary transition-colors hover:bg-bg-sage hover:text-text-primary"
        aria-label={`Remover ${item.name}`}
      >
        <TrashIcon className="size-4" />
      </button>
    </li>
  )
}
