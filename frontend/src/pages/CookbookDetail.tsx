import { t } from '../i18n'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { addRecipeToCookbook, getCookbook, removeRecipeFromCookbook } from '../api/cookbooks'
import { listRecipes, toggleFavorite } from '../api/recipes'
import type { CookbookDetail as CookbookDetailType, RecipeSummary } from '../api/types'
import { PageShell } from '../components/PageShell'
import { RecipeCard } from '../components/RecipeCard'
import { XIcon } from '../components/icons'
import { EmptyState } from '../components/ui'

export function CookbookDetail() {
  const { id } = useParams<{ id: string }>()
  const [cookbook, setCookbook] = useState<CookbookDetailType | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [allRecipes, setAllRecipes] = useState<RecipeSummary[]>([])

  useEffect(() => {
    if (!id) return
    getCookbook(id)
      .then(setCookbook)
      .catch(() => setNotFound(true))
    listRecipes().then(setAllRecipes).catch(() => {})
  }, [id])

  async function handleToggleFavorite(recipeId: string) {
    const updated = await toggleFavorite(recipeId)
    setCookbook((prev) =>
      prev
        ? { ...prev, recipes: prev.recipes.map((r) => (r.id === recipeId ? { ...r, is_favorite: updated.is_favorite } : r)) }
        : prev,
    )
  }

  async function handleAdd(recipeId: string) {
    if (!id || !recipeId) return
    const updated = await addRecipeToCookbook(id, recipeId)
    setCookbook(updated)
  }

  async function handleRemove(recipeId: string) {
    if (!id) return
    const updated = await removeRecipeFromCookbook(id, recipeId)
    setCookbook(updated)
  }

  if (notFound) {
    return (
      <PageShell>
        <p className="text-text-secondary">{t('Coleção não encontrada.')}</p>
        <Link to="/colecoes" className="mt-2 inline-block font-medium text-forest-text">
          {t('Voltar às coleções')}
        </Link>
      </PageShell>
    )
  }

  if (!cookbook) {
    return (
      <PageShell>
        <p className="text-sm text-text-secondary">{t('A carregar…')}</p>
      </PageShell>
    )
  }

  const memberIds = new Set(cookbook.recipes.map((r) => r.id))
  const availableRecipes = allRecipes.filter((r) => !memberIds.has(r.id))

  return (
    <PageShell>
      <Link to="/colecoes" className="text-sm font-medium text-forest-text">
        {t('← Coleções')}
      </Link>
      <h1 className="mt-1 text-2xl font-bold text-text-primary sm:text-3xl">{cookbook.name}</h1>

      <div className="mt-4">
        <select
          value=""
          onChange={(e) => handleAdd(e.target.value)}
          disabled={availableRecipes.length === 0}
          aria-label={t('+ Adicionar receita a esta coleção')}
          className="w-full min-h-11 rounded-xl border border-border bg-surface px-3 text-sm text-text-primary outline-none focus:border-primary-forest focus:ring-2 focus:ring-primary-forest/15 disabled:opacity-50 sm:w-auto"
        >
          <option value="" disabled>
            {t('+ Adicionar receita a esta coleção')}
          </option>
          {availableRecipes.map((r) => (
            <option key={r.id} value={r.id}>
              {r.title}
            </option>
          ))}
        </select>
      </div>

      {cookbook.recipes.length === 0 ? (
        <div className="mt-4">
          <EmptyState title={t('Ainda não há receitas nesta coleção.')} description={t('Usa o menu acima para adicionar a primeira.')} />
        </div>
      ) : (
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
          {cookbook.recipes.map((r) => (
            <div key={r.id} className="relative">
              <RecipeCard recipe={r} onToggleFavorite={handleToggleFavorite} />
              <button
                type="button"
                onClick={() => handleRemove(r.id)}
                title={t('Remover da coleção')}
                aria-label={t('Remover {name} da coleção', { name: r.title })}
                className="absolute bottom-2.5 left-2.5 flex size-10 items-center justify-center rounded-full border border-white/60 bg-white/90 text-neutral-600 shadow-sm transition hover:scale-105 hover:text-accent-orange sm:bottom-auto sm:left-2.5 sm:top-2.5 sm:size-9"
              >
                <XIcon className="size-5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </PageShell>
  )
}
