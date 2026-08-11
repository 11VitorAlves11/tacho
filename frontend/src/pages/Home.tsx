import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listCategories, listRecipes, listTags, toggleFavorite } from '../api/recipes'
import type { Category, RecipeSummary, Tag } from '../api/types'
import { PageShell } from '../components/PageShell'
import { RecipeCard } from '../components/RecipeCard'
import { CartIcon, HeartIcon, SearchIcon } from '../components/icons'

export function Home() {
  const [recipes, setRecipes] = useState<RecipeSummary[] | null>(null)
  const [categories, setCategories] = useState<Category[]>([])
  const [tags, setTags] = useState<Tag[]>([])
  const [q, setQ] = useState('')
  const [categoryId, setCategoryId] = useState<string | null>(null)
  const [tagId, setTagId] = useState<string | null>(null)
  const [favoriteOnly, setFavoriteOnly] = useState(false)
  const [makeableOnly, setMakeableOnly] = useState(false)
  const [error, setError] = useState(false)

  useEffect(() => {
    listCategories().then(setCategories).catch(() => {})
    listTags().then(setTags).catch(() => {})
  }, [])

  useEffect(() => {
    const handle = setTimeout(() => {
      setError(false)
      listRecipes({
        q: q || undefined,
        categoryId: categoryId ?? undefined,
        tagId: tagId ?? undefined,
        favorite: favoriteOnly || undefined,
        makeable: makeableOnly || undefined,
      })
        .then(setRecipes)
        .catch(() => setError(true))
    }, 250)
    return () => clearTimeout(handle)
  }, [q, categoryId, tagId, favoriteOnly, makeableOnly])

  async function handleToggleFavorite(id: string) {
    const updated = await toggleFavorite(id)
    setRecipes((prev) => {
      if (!prev) return prev
      // Na vista "Favoritos", desfavoritar remove logo da lista.
      if (favoriteOnly && !updated.is_favorite) {
        return prev.filter((r) => r.id !== id)
      }
      return prev.map((r) => (r.id === id ? { ...r, is_favorite: updated.is_favorite } : r))
    })
  }

  const hasCategoryOrTagFilters = categories.length > 0 || tags.length > 0

  return (
    <PageShell>
      <section className="-mx-4 -mt-6 mb-6 rounded-b-3xl bg-gradient-to-br from-bg-sage-deep-start to-bg-sage-deep-end px-4 pb-6 pt-2 text-card-white sm:mx-0 sm:mt-0 sm:rounded-3xl sm:p-6">
        <h1 className="text-2xl font-bold sm:text-3xl">As receitas do agregado</h1>
        <p className="mt-1 text-sm text-card-white/80">
          Tudo o que hoje está no Tandoor, agora num sítio só — e teu.
        </p>

        <label className="mt-4 flex items-center gap-2 rounded-full bg-card-white px-4 py-3 text-text-primary shadow-inner ring-2 ring-transparent transition-shadow focus-within:ring-accent-leaf">
          <SearchIcon className="size-5 shrink-0 text-text-secondary" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            type="search"
            placeholder="Procurar receitas…"
            className="w-full bg-transparent text-sm outline-none placeholder:text-text-secondary"
          />
        </label>

        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setFavoriteOnly((v) => !v)}
            aria-pressed={favoriteOnly}
            className={`flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              favoriteOnly ? 'bg-card-white text-accent-leaf' : 'bg-card-white/15 text-card-white hover:bg-card-white/25'
            }`}
          >
            <HeartIcon className="size-3.5" fill={favoriteOnly ? 'currentColor' : 'none'} />
            Favoritos
          </button>
          <button
            type="button"
            onClick={() => setMakeableOnly((v) => !v)}
            aria-pressed={makeableOnly}
            className={`flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              makeableOnly ? 'bg-card-white text-accent-leaf' : 'bg-card-white/15 text-card-white hover:bg-card-white/25'
            }`}
          >
            <CartIcon className="size-3.5" />
            Dá para fazer
          </button>
          {hasCategoryOrTagFilters && (
            <>
              <FilterChip label="Todas" active={!categoryId && !tagId} onClick={() => { setCategoryId(null); setTagId(null) }} />
              {categories.map((c) => (
                <FilterChip
                  key={c.id}
                  label={c.name}
                  active={categoryId === c.id}
                  onClick={() => { setCategoryId(categoryId === c.id ? null : c.id); setTagId(null) }}
                />
              ))}
              {tags.map((t) => (
                <FilterChip
                  key={t.id}
                  label={`#${t.name}`}
                  active={tagId === t.id}
                  onClick={() => { setTagId(tagId === t.id ? null : t.id); setCategoryId(null) }}
                />
              ))}
            </>
          )}
        </div>

        <Link to="/colecoes" className="mt-3 inline-block text-sm font-medium text-card-white/80 hover:text-card-white">
          Coleções →
        </Link>
      </section>

      {error && (
        <p className="rounded-xl bg-surface p-4 text-sm text-text-secondary">
          Não foi possível ligar ao backend. Confirma se está a correr em {import.meta.env.VITE_API_URL}.
        </p>
      )}

      {!error && recipes === null && <p className="text-sm text-text-secondary">A carregar…</p>}

      {!error && recipes !== null && recipes.length === 0 && (
        <div className="rounded-2xl bg-surface p-8 text-center">
          {favoriteOnly ? (
            <p className="font-medium text-text-primary">Ainda não marcaste nenhuma receita como favorita.</p>
          ) : makeableOnly ? (
            <>
              <p className="font-medium text-text-primary">Nenhuma receita dá para fazer com o que tens na despensa.</p>
              <Link to="/despensa" className="mt-1 inline-block text-sm text-forest-text">
                Atualizar a despensa →
              </Link>
            </>
          ) : (
            <>
              <p className="font-medium text-text-primary">Ainda não há receitas por aqui.</p>
              <p className="mt-1 text-sm text-text-secondary">
                Usa o botão "Adicionar" para importar a primeira por URL.
              </p>
            </>
          )}
        </div>
      )}

      {recipes && recipes.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2">
          {recipes.map((r) => (
            <RecipeCard key={r.id} recipe={r} onToggleFavorite={handleToggleFavorite} />
          ))}
        </div>
      )}
    </PageShell>
  )
}

function FilterChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
        active ? 'bg-card-white text-primary-forest' : 'bg-card-white/15 text-card-white hover:bg-card-white/25'
      }`}
    >
      {label}
    </button>
  )
}
