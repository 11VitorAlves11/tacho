import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { createPantryItem, deletePantryItem, listPantryItems, setPantryItemHasIt } from '../api/pantry'
import type { PantryItem } from '../api/types'
import { PageShell } from '../components/PageShell'
import { PlusIcon, XIcon } from '../components/icons'

export function Pantry() {
  const [items, setItems] = useState<PantryItem[] | null>(null)
  const [error, setError] = useState(false)
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    listPantryItems().then(setItems).catch(() => setError(true))
  }, [])

  async function handleCreate(e: FormEvent) {
    e.preventDefault()
    const name = newName.trim()
    if (!name || creating) return
    setCreating(true)
    try {
      const item = await createPantryItem(name)
      setItems((prev) => [...(prev ?? []), item])
      setNewName('')
    } finally {
      setCreating(false)
    }
  }

  async function handleToggle(item: PantryItem) {
    const updated = await setPantryItemHasIt(item.id, !item.has_it)
    setItems((prev) => prev?.map((i) => (i.id === item.id ? updated : i)) ?? prev)
  }

  async function handleDelete(id: string) {
    await deletePantryItem(id)
    setItems((prev) => prev?.filter((i) => i.id !== id) ?? prev)
  }

  return (
    <PageShell>
      <Link to="/lista-compras" className="text-sm font-medium text-forest-text">
        ← Lista de Compras
      </Link>
      <h1 className="mt-1 text-2xl font-bold text-text-primary sm:text-3xl">Despensa</h1>
      <p className="mt-1 text-sm text-text-secondary">
        Marca o que tens em casa — usado no filtro "Dá para fazer" das receitas.
      </p>

      {error && <p className="mt-4 text-sm text-text-secondary">Não foi possível ligar ao backend.</p>}

      {items && items.length === 0 && (
        <div className="mt-4 rounded-2xl bg-surface p-8 text-center">
          <p className="font-medium text-text-primary">A despensa está vazia.</p>
          <p className="mt-1 text-sm text-text-secondary">Adiciona os ingredientes que costumas ter em casa.</p>
        </div>
      )}

      {items && items.length > 0 && (
        <ul className="mt-4 space-y-2">
          {items.map((item) => (
            <li
              key={item.id}
              className="flex items-center justify-between gap-2 rounded-xl bg-surface p-3 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]"
            >
              <label className="flex min-w-0 flex-1 items-center gap-3">
                <input
                  type="checkbox"
                  checked={item.has_it}
                  onChange={() => handleToggle(item)}
                  className="size-5 shrink-0 accent-accent-leaf"
                />
                <span className={`truncate text-sm ${item.has_it ? 'text-text-primary' : 'text-text-secondary line-through'}`}>
                  {item.name}
                </span>
              </label>
              <button
                type="button"
                onClick={() => handleDelete(item.id)}
                className="shrink-0 rounded-full p-1.5 text-text-secondary hover:bg-bg-sage"
                aria-label={`Remover ${item.name} da despensa`}
              >
                <XIcon className="size-4" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={handleCreate} className="mt-6 flex gap-2">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="Adicionar ingrediente…"
          className="min-w-0 flex-1 rounded-xl border border-black/10 bg-bg-sage px-3 py-2 text-sm outline-none ring-2 ring-transparent transition-shadow focus:border-accent-leaf focus:ring-accent-leaf/30"
        />
        <button
          type="submit"
          disabled={!newName.trim() || creating}
          className="flex shrink-0 items-center gap-1 rounded-xl bg-primary-forest px-4 py-2 text-sm font-medium text-card-white disabled:opacity-50"
        >
          <PlusIcon className="size-4" />
          Adicionar
        </button>
      </form>
    </PageShell>
  )
}
