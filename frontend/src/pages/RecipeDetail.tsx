import { useEffect, useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getRecipe, recipeImageUrl } from '../api/recipes'
import type { Recipe } from '../api/types'
import { PageShell } from '../components/PageShell'
import { ClockIcon, FlameIcon, PencilIcon, PlayIcon, ServingsIcon } from '../components/icons'

export function RecipeDetail() {
  const { id } = useParams<{ id: string }>()
  const [recipe, setRecipe] = useState<Recipe | null>(null)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    if (!id) return
    getRecipe(id)
      .then(setRecipe)
      .catch(() => setNotFound(true))
  }, [id])

  if (notFound) {
    return (
      <PageShell>
        <p className="text-text-secondary">Receita não encontrada.</p>
        <Link to="/" className="mt-2 inline-block font-medium text-primary-forest">
          Voltar às receitas
        </Link>
      </PageShell>
    )
  }

  if (!recipe) {
    return (
      <PageShell>
        <p className="text-sm text-text-secondary">A carregar…</p>
      </PageShell>
    )
  }

  const totalMinutes = (recipe.prep_minutes ?? 0) + (recipe.cook_minutes ?? 0)

  return (
    <PageShell>
      <article>
        {recipe.image_path && (
          <img
            src={recipeImageUrl(recipe.image_path)}
            alt=""
            className="aspect-video w-full rounded-2xl object-cover shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]"
          />
        )}

        <div className={`flex items-start justify-between gap-3 ${recipe.image_path ? 'mt-5' : ''}`}>
          <h1 className="text-2xl font-bold text-text-primary sm:text-3xl">{recipe.title}</h1>
          <Link
            to={`/receitas/${recipe.id}/editar`}
            className="flex shrink-0 items-center gap-1.5 rounded-full bg-card-white px-3 py-1.5 text-sm font-medium text-text-secondary shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)] hover:text-primary-forest"
          >
            <PencilIcon className="size-4" />
            <span className="hidden sm:inline">Editar</span>
          </Link>
        </div>
        {recipe.description && <p className="mt-2 text-text-secondary">{recipe.description}</p>}

        <div className="mt-5 flex gap-6 rounded-2xl bg-card-white p-5 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]">
          {totalMinutes > 0 && (
            <HeroStat icon={<ClockIcon className="size-5" />} value={totalMinutes} label="min" tone="orange" />
          )}
          {recipe.servings && (
            <HeroStat icon={<ServingsIcon className="size-5" />} value={recipe.servings} label="porções" tone="forest" />
          )}
          {recipe.calories_kcal != null && (
            <HeroStat icon={<FlameIcon className="size-5" />} value={recipe.calories_kcal} label="kcal/porção" tone="forest" />
          )}
        </div>

        {(recipe.categories.length > 0 || recipe.tags.length > 0) && (
          <div className="mt-4 flex flex-wrap gap-1.5">
            {recipe.categories.map((c) => (
              <span key={c.id} className="rounded-full bg-primary-forest/10 px-2.5 py-0.5 text-xs font-medium text-primary-forest">
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

        <Link
          to={`/receitas/${recipe.id}/cozinhar`}
          className="mt-5 flex items-center justify-center gap-2 rounded-full bg-primary-forest px-5 py-3.5 font-semibold text-card-white shadow-[0_8px_20px_-6px_rgba(45,95,63,0.6)] transition-transform active:scale-[0.98] sm:hidden"
        >
          <PlayIcon className="size-4" />
          Iniciar Modo Cozinha
        </Link>

        <div className="mt-8 grid gap-8 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
          <section>
            <h2 className="text-lg font-semibold text-text-primary">Ingredientes</h2>
            <ul className="mt-3 space-y-2">
              {recipe.ingredients.map((ing) =>
                ing.is_header ? (
                  <li key={ing.id} className="pt-3 text-sm font-semibold text-text-primary first:pt-0">
                    {ing.name}
                  </li>
                ) : (
                  <li key={ing.id} className="flex justify-between gap-3 border-b border-black/5 pb-2 text-sm">
                    <span className="text-text-primary">{ing.name}</span>
                    {(ing.quantity || ing.unit) && (
                      <span className="shrink-0 text-text-secondary">
                        {ing.quantity ?? ''} {ing.unit ?? ''}
                      </span>
                    )}
                  </li>
                ),
              )}
              {recipe.ingredients.length === 0 && (
                <li className="text-sm text-text-secondary">Sem ingredientes registados.</li>
              )}
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-text-primary">Preparação</h2>
            <ol className="mt-3 space-y-4">
              {recipe.steps.map((step, i) => (
                <li key={step.id} className="flex gap-3 text-sm">
                  <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-bg-sage text-xs font-semibold text-primary-forest">
                    {i + 1}
                  </span>
                  <span className="text-text-primary">{step.instruction}</span>
                </li>
              ))}
              {recipe.steps.length === 0 && (
                <li className="text-sm text-text-secondary">Sem passos registados.</li>
              )}
            </ol>
          </section>
        </div>

        {(recipe.protein_g != null || recipe.carbs_g != null || recipe.fat_g != null) && (
          <section className="mt-8 rounded-2xl bg-card-white p-5 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]">
            <h2 className="text-lg font-semibold text-text-primary">Informação nutricional</h2>
            <p className="mt-1 text-xs text-text-secondary">Por porção, entrada manual.</p>
            <div className="mt-3 grid grid-cols-3 gap-3 text-center">
              <MacroStat value={recipe.protein_g} label="Proteína" />
              <MacroStat value={recipe.carbs_g} label="Hidratos" />
              <MacroStat value={recipe.fat_g} label="Gordura" />
            </div>
          </section>
        )}

        {recipe.source_url && (
          <p className="mt-8 text-xs text-text-secondary">
            Fonte:{' '}
            <a href={recipe.source_url} target="_blank" rel="noreferrer" className="underline">
              {recipe.source_url}
            </a>
          </p>
        )}
      </article>
    </PageShell>
  )
}

function MacroStat({ value, label }: { value: number | null; label: string }) {
  return (
    <div className="rounded-xl bg-bg-sage py-3">
      <div className="text-lg font-bold text-text-primary">{value != null ? `${value}g` : '—'}</div>
      <div className="text-xs text-text-secondary">{label}</div>
    </div>
  )
}

function HeroStat({
  icon,
  value,
  label,
  tone,
}: {
  icon: ReactNode
  value: number
  label: string
  tone: 'orange' | 'forest'
}) {
  const iconClass = tone === 'orange' ? 'text-accent-orange' : 'text-primary-forest'
  return (
    <div className="flex items-center gap-2">
      <span className={iconClass}>{icon}</span>
      <div>
        <div className="text-2xl font-bold leading-none text-text-primary sm:text-3xl">{value}</div>
        <div className="text-xs text-text-secondary">{label}</div>
      </div>
    </div>
  )
}
