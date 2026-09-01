import { Link } from 'react-router-dom'
import { recipeImageUrl } from '../api/recipes'
import type { RecipeSummary } from '../api/types'
import { BrandFallback } from './Brand'
import { ClockIcon, HeartIcon, ServingsIcon } from './icons'
import { CategoryBadge, TagBadge } from './ui'

function totalTime(recipe: RecipeSummary) {
  const total = (recipe.prep_minutes ?? 0) + (recipe.cook_minutes ?? 0)
  return total > 0 ? total : null
}

export function RecipeCard({ recipe, onToggleFavorite }: { recipe: RecipeSummary; onToggleFavorite: (id: string) => void }) {
  const time = totalTime(recipe)
  const category = recipe.categories[0]
  const tag = recipe.categories.length === 0 ? recipe.tags[0] : undefined
  return (
    <Link to={`/receitas/${recipe.id}`} className="group relative grid min-h-[112px] grid-cols-[112px_minmax(0,1fr)] overflow-hidden rounded-2xl border border-border bg-surface transition duration-200 hover:-translate-y-0.5 hover:border-primary-forest/25 hover:shadow-[0_8px_25px_rgba(20,30,24,0.08)] sm:flex sm:min-h-0 sm:flex-col">
      <div className="relative h-full min-h-[112px] overflow-hidden bg-muted sm:aspect-[4/3] sm:min-h-0 sm:w-full">
        {recipe.image_path ? <img src={recipeImageUrl(recipe.image_path)} alt="" className="size-full object-cover transition-transform duration-300 group-hover:scale-[1.025]" /> : <div className="flex size-full items-center justify-center bg-primary-soft"><BrandFallback className="size-14 opacity-70 sm:size-20" /></div>}
        <button type="button" onClick={(event) => { event.preventDefault(); event.stopPropagation(); onToggleFavorite(recipe.id) }} aria-label={recipe.is_favorite ? 'Remover dos favoritos' : 'Adicionar aos favoritos'} aria-pressed={recipe.is_favorite} className="absolute right-2.5 top-2.5 flex size-10 items-center justify-center rounded-full border border-white/60 bg-white/90 text-neutral-600 shadow-sm transition hover:scale-105 hover:text-primary-forest sm:size-9">
          <HeartIcon className={`size-5 ${recipe.is_favorite ? 'text-primary-forest' : ''}`} fill={recipe.is_favorite ? 'currentColor' : 'none'} />
        </button>
      </div>
      <div className="flex min-w-0 flex-col justify-center p-3.5 sm:block sm:p-4">
        <h3 className="line-clamp-2 text-sm font-semibold leading-snug text-text-primary sm:truncate sm:text-base">{recipe.title}</h3>
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-text-secondary">
          {time && <span className="flex items-center gap-1"><ClockIcon className="size-3.5" />{time} min</span>}
          {recipe.servings && <span className="flex items-center gap-1"><ServingsIcon className="size-3.5" />{recipe.servings} doses</span>}
        </div>
        {(category || tag) && <div className="mt-2">{category ? <CategoryBadge color={category.color} icon={category.icon} className="px-2 py-0.5 text-[11px]">{category.name}</CategoryBadge> : <TagBadge className="px-2 py-0.5 text-[11px]">{tag?.name}</TagBadge>}</div>}
        {recipe.is_makeable === true && <p className="mt-2 text-xs font-semibold text-forest-text">Tens todos os ingredientes</p>}
        {recipe.missing_ingredient_count !== null && recipe.missing_ingredient_count > 0 && <p className="mt-2 line-clamp-2 text-xs text-text-secondary">Faltam {recipe.missing_ingredient_count}: {recipe.missing_ingredients?.slice(0, 3).join(', ')}</p>}
        {recipe.dietary_warnings?.length > 0 && <div className="mt-2 rounded-lg bg-danger/10 px-2.5 py-2 text-xs font-semibold text-danger" role="note">Atenção: {recipe.dietary_warnings.slice(0, 2).join(' · ')}</div>}
      </div>
    </Link>
  )
}
