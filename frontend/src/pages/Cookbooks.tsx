import { t } from '../i18n'
import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { createCookbook, deleteCookbook, listCookbooks } from '../api/cookbooks'
import { recipeImageUrl } from '../api/recipes'
import type { CookbookSummary } from '../api/types'
import { BrandFallback } from '../components/Brand'
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
      <h1 className="text-2xl font-bold text-text-primary sm:text-3xl">{t('Coleções')}</h1>

      {error && <p className="mt-4 text-sm text-text-secondary">{t('Não foi possível ligar ao backend.')}</p>}

      {!error && cookbooks === null && <p className="mt-4 text-sm text-text-secondary">{t('A carregar…')}</p>}

      {cookbooks && cookbooks.length === 0 && (
        <div className="mt-4 rounded-2xl bg-surface p-8 text-center">
          <p className="font-medium text-text-primary">{t('Ainda não há coleções.')}</p>
          <p className="mt-1 text-sm text-text-secondary">{t('Cria a primeira em baixo — ex. "Sobremesas de Natal".')}</p>
        </div>
      )}

      {cookbooks && cookbooks.length > 0 && (
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {cookbooks.map((c) => (
            <div key={c.id} className="relative">
              <Link
                to={`/colecoes/${c.id}`}
                className="group block overflow-hidden rounded-2xl border border-border bg-surface transition duration-200 hover:-translate-y-0.5 hover:border-primary-forest/25 hover:shadow-[0_8px_25px_rgba(20,30,24,0.08)]"
              >
                <CoverCollage paths={c.cover_image_paths} />
                <div className="p-4 pr-14">
                  <h3 className="truncate font-semibold text-text-primary group-hover:text-forest-text">{c.name}</h3>
                  <p className="text-sm text-text-secondary">
                    {c.recipe_count} {t('receita')}{c.recipe_count !== 1 ? 's' : ''}
                  </p>
                </div>
              </Link>
              <button
                type="button"
                onClick={() => setDeleteId(c.id)}
                className="absolute bottom-3 right-2 flex size-11 items-center justify-center rounded-xl text-text-secondary transition-colors hover:bg-muted hover:text-accent-orange"
                aria-label={t('Apagar coleção {name}', { name: c.name })}
              >
                <TrashIcon className="size-5" />
              </button>
            </div>
          ))}
        </div>
      )}

      <form onSubmit={handleCreate} className="mt-6 flex gap-2">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder={t('Nome da nova coleção…')}
          aria-label={t('Nome da nova coleção…')}
          className="min-w-0 flex-1 min-h-11 rounded-xl border border-border bg-surface px-3 text-sm text-text-primary outline-none focus:border-primary-forest focus:ring-2 focus:ring-primary-forest/15"
        />
        <button
          type="submit"
          disabled={!newName.trim() || creating}
          className="flex shrink-0 items-center gap-1 rounded-xl bg-primary-forest px-4 py-2 text-sm font-medium text-card-white disabled:opacity-50"
        >
          <PlusIcon className="size-4" />
          {t('Criar')}
        </button>
      </form>
      <ConfirmDialog open={deleteId !== null} title={t('Apagar coleção?')} description={t('As receitas da coleção não serão apagadas.')} confirmLabel={t('Apagar')} onCancel={() => setDeleteId(null)} onConfirm={handleDelete} />
    </PageShell>
  )
}

const COLLAGE_TILE_CLASS: Record<number, string[]> = {
  1: ['col-span-2 row-span-2'],
  2: ['row-span-2', 'row-span-2'],
  3: ['row-span-2', '', ''],
  4: ['', '', '', ''],
}

function CoverCollage({ paths }: { paths: string[] }) {
  const covers = paths.slice(0, 4)
  return (
    <div aria-hidden="true" className="grid aspect-[16/9] grid-cols-2 grid-rows-2 gap-0.5 overflow-hidden bg-muted">
      {covers.length === 0 ? (
        <div className="col-span-2 row-span-2 flex items-center justify-center bg-primary-soft">
          <BrandFallback className="size-16 opacity-70" />
        </div>
      ) : (
        covers.map((path, index) => (
          <img key={path} src={recipeImageUrl(path, 'thumb')} loading="lazy" decoding="async" alt="" className={`size-full min-h-0 object-cover ${COLLAGE_TILE_CLASS[covers.length][index]}`} />
        ))
      )}
    </div>
  )
}
