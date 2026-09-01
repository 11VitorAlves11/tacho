import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { createCookbook, deleteCookbook, listCookbooks } from '../api/cookbooks'
import type { CookbookSummary } from '../api/types'
import { PageShell } from '../components/PageShell'
import { PlusIcon, TrashIcon } from '../components/icons'
import { ConfirmDialog } from '../components/ui'

export function Cookbooks() {
  const [cookbooks, setCookbooks] = useState<CookbookSummary[] | null>(null)
  const [error, setError] = useState(false)
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)

  useEffect(() => {
    listCookbooks().then(setCookbooks).catch(() => setError(true))
  }, [])

  async function handleCreate(e: FormEvent) {
    e.preventDefault()
    const name = newName.trim()
    if (!name || creating) return
    setCreating(true)
    try {
      const cookbook = await createCookbook(name)
      setCookbooks((prev) => [...(prev ?? []), cookbook])
      setNewName('')
    } finally {
      setCreating(false)
    }
  }

  async function handleDelete() {
    if (!deleteId) return
    await deleteCookbook(deleteId)
    setCookbooks((prev) => prev?.filter((c) => c.id !== deleteId) ?? prev)
    setDeleteId(null)
  }

  return (
    <PageShell>
      <h1 className="text-2xl font-bold text-text-primary sm:text-3xl">Coleções</h1>

      {error && <p className="mt-4 text-sm text-text-secondary">Não foi possível ligar ao backend.</p>}

      {!error && cookbooks === null && <p className="mt-4 text-sm text-text-secondary">A carregar…</p>}

      {cookbooks && cookbooks.length === 0 && (
        <div className="mt-4 rounded-2xl bg-surface p-8 text-center">
          <p className="font-medium text-text-primary">Ainda não há coleções.</p>
          <p className="mt-1 text-sm text-text-secondary">Cria a primeira em baixo — ex. "Sobremesas de Natal".</p>
        </div>
      )}

      {cookbooks && cookbooks.length > 0 && (
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {cookbooks.map((c) => (
            <div
              key={c.id}
              className="flex items-center justify-between gap-2 rounded-2xl bg-surface p-4 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]"
            >
              <Link to={`/colecoes/${c.id}`} className="min-w-0 flex-1">
                <h3 className="truncate font-semibold text-text-primary hover:text-forest-text">{c.name}</h3>
                <p className="text-sm text-text-secondary">
                  {c.recipe_count} receita{c.recipe_count !== 1 ? 's' : ''}
                </p>
              </Link>
              <button
                type="button"
                onClick={() => setDeleteId(c.id)}
                className="shrink-0 rounded-full p-2 text-text-secondary hover:bg-bg-sage hover:text-accent-orange"
                aria-label={`Apagar coleção ${c.name}`}
              >
                <TrashIcon className="size-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      <form onSubmit={handleCreate} className="mt-6 flex gap-2">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="Nome da nova coleção…"
          className="min-w-0 flex-1 rounded-xl border border-black/10 bg-bg-sage px-3 py-2 text-sm outline-none ring-2 ring-transparent transition-shadow focus:border-accent-leaf focus:ring-accent-leaf/30"
        />
        <button
          type="submit"
          disabled={!newName.trim() || creating}
          className="flex shrink-0 items-center gap-1 rounded-xl bg-primary-forest px-4 py-2 text-sm font-medium text-card-white disabled:opacity-50"
        >
          <PlusIcon className="size-4" />
          Criar
        </button>
      </form>
      <ConfirmDialog open={deleteId !== null} title="Apagar coleção?" description="As receitas da coleção não serão apagadas." confirmLabel="Apagar" onCancel={() => setDeleteId(null)} onConfirm={handleDelete} />
    </PageShell>
  )
}
