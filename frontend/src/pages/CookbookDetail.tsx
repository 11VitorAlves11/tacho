import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { addRecipeToCookbook, getCookbook, removeRecipeFromCookbook } from '../api/cookbooks'
import { listRecipes, toggleFavorite } from '../api/recipes'
import type { CookbookDetail as CookbookDetailType, RecipeSummary } from '../api/types'
import { PageShell } from '../components/PageShell'
import { RecipeCard } from '../components/RecipeCard'

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
        <p className="text-text-secondary">Coleção não encontrada.</p>
        <Link to="/colecoes" className="mt-2 inline-block font-medium text-forest-text">
          Voltar às coleções
        </Link>
      </PageShell>
    )
  }

  if (!cookbook) {
    return (
      <PageShell>
        <p className="text-sm text-text-secondary">A carregar…</p>
      </PageShell>
    )
  }

  const memberIds = new Set(cookbook.recipes.map((r) => r.id))
  const availableRecipes = allRecipes.filter((r) => !memberIds.has(r.id))

  return (
    <PageShell>
      <Link to="/colecoes" className="text-sm font-medium text-forest-text">
        ← Coleções
      </Link>
      <h1 className="mt-1 text-2xl font-bold text-text-primary sm:text-3xl">{cookbook.name}</h1>

      <div className="mt-4">
        <select
          value=""
          onChange={(e) => handleAdd(e.target.value)}
          disabled={availableRecipes.length === 0}
          className="w-full rounded-xl border border-black/10 bg-bg-sage px-3 py-2 text-sm text-text-secondary outline-none focus:ring-2 focus:ring-accent-leaf disabled:opacity-50 sm:w-auto"
        >
          <option value="" disabled>
            + Adicionar receita a esta coleção
          </option>
          {availableRecipes.map((r) => (
            <option key={r.id} value={r.id}>
              {r.title}
            </option>
          ))}
        </select>
      </div>

      {cookbook.recipes.length === 0 ? (
        <div className="mt-4 rounded-2xl bg-surface p-8 text-center">
          <p className="font-medium text-text-primary">Ainda não há receitas nesta coleção.</p>
          <p className="mt-1 text-sm text-text-secondary">Usa o menu acima para adicionar a primeira.</p>
        </div>
      ) : (
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {cookbook.recipes.map((r) => (
            <div key={r.id}>
              <RecipeCard recipe={r} onToggleFavorite={handleToggleFavorite} />
              <button
                type="button"
                onClick={() => handleRemove(r.id)}
                className="mt-1.5 text-xs font-medium text-text-secondary hover:text-accent-orange"
              >
                Remover da coleção
              </button>
            </div>
          ))}
        </div>
      )}
    </PageShell>
  )
}
