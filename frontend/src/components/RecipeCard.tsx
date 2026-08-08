import { Link } from 'react-router-dom'
import { recipeImageUrl } from '../api/recipes'
import type { RecipeSummary } from '../api/types'
import { ClockIcon, HeartIcon, PotIcon, ServingsIcon } from './icons'

function totalTime(r: RecipeSummary) {
  const total = (r.prep_minutes ?? 0) + (r.cook_minutes ?? 0)
  return total > 0 ? total : null
}

export function RecipeCard({
  recipe,
  onToggleFavorite,
}: {
  recipe: RecipeSummary
  onToggleFavorite: (id: string) => void
}) {
  const time = totalTime(recipe)

  return (
    <Link
      to={`/receitas/${recipe.id}`}
      className="group relative flex gap-4 rounded-2xl bg-surface p-4 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)] transition-shadow hover:shadow-[0_8px_24px_-4px_rgba(28,43,31,0.22)]"
    >
      <button
        type="button"
        onClick={(e) => {
          e.preventDefault()
          e.stopPropagation()
          onToggleFavorite(recipe.id)
        }}
        aria-label={recipe.is_favorite ? 'Remover dos favoritos' : 'Adicionar aos favoritos'}
        aria-pressed={recipe.is_favorite}
        className={`absolute right-3 top-3 flex size-8 items-center justify-center rounded-full transition-colors ${
          recipe.is_favorite ? 'text-accent-leaf' : 'text-text-secondary/50 hover:text-accent-leaf'
        }`}
      >
        <HeartIcon className="size-5" fill={recipe.is_favorite ? 'currentColor' : 'none'} />
      </button>

      {recipe.image_path ? (
        <img
          src={recipeImageUrl(recipe.image_path)}
          alt=""
          className="size-14 shrink-0 rounded-xl object-cover"
        />
      ) : (
        <div className="flex size-14 shrink-0 items-center justify-center rounded-xl bg-bg-sage text-forest-text">
          <PotIcon className="size-7" />
        </div>
      )}

      <div className="min-w-0 flex-1 pr-8">
        <h3 className="truncate font-semibold text-text-primary group-hover:text-forest-text">
          {recipe.title}
        </h3>

        <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-text-secondary">
          {time && (
            <span className="flex items-center gap-1 font-medium">
              <ClockIcon className="size-4 text-accent-orange" />
              {time} min
            </span>
          )}
          {recipe.servings && (
            <span className="flex items-center gap-1">
              <ServingsIcon className="size-4" />
              {recipe.servings} porções
            </span>
          )}
        </div>

        {(recipe.categories.length > 0 || recipe.tags.length > 0) && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {recipe.categories.map((c) => (
              <span key={c.id} className="rounded-full bg-primary-forest/10 px-2.5 py-0.5 text-xs font-medium text-forest-text">
                {c.name}
              </span>
            ))}
            {recipe.tags.map((t) => (
              <span key={t.id} className="rounded-full bg-accent-leaf/10 px-2.5 py-0.5 text-xs font-medium text-accent-leaf">
                {t.name}
              </span>
            ))}
          </div>
        )}
      </div>
    </Link>
  )
}
