import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getPublicRecipe, publicRecipeImageUrl } from '../api/public'
import type { PublicRecipe as PublicRecipeType } from '../api/types'
import { ClockIcon, PotIcon, ServingsIcon } from '../components/icons'
import { formatQuantity } from '../lib/quantity'

// Página pública, sem sessão — o link/QR gerado em RecipeDetail.tsx
// ("Partilhar") aponta para aqui. Ao contrário do Detalhe normal, é só
// leitura: sem editar, favoritar, comentar, nem qualquer chrome da app
// (Header/BottomNav pressupõem sessão). Ver App.tsx — esta é a única rota
// que não vive atrás do gate de autenticação.
export function PublicRecipe() {
  const { token } = useParams<{ token: string }>()
  const [recipe, setRecipe] = useState<PublicRecipeType | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!token) return
    getPublicRecipe(token)
      .then(setRecipe)
      .catch(() => setError(true))
  }, [token])

  if (error) {
    return (
      <div className="flex min-h-svh flex-col items-center justify-center bg-bg-sage px-4 text-center">
        <PotIcon className="size-8 text-forest-text" />
        <h1 className="mt-3 text-lg font-semibold text-text-primary">Link expirado</h1>
        <p className="mt-1 max-w-xs text-sm text-text-secondary">
          Este link de partilha já não é válido — os links do Tacho duram 5 horas. Pede a quem partilhou contigo
          para gerar um novo.
        </p>
      </div>
    )
  }

  if (!recipe) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-bg-sage">
        <p className="text-sm text-text-secondary">A carregar…</p>
      </div>
    )
  }

  const totalMinutes = (recipe.prep_minutes ?? 0) + (recipe.cook_minutes ?? 0)

  return (
    <div className="min-h-svh bg-bg-sage pb-10">
      <div className="mx-auto flex max-w-4xl items-center gap-1.5 px-4 py-4 text-sm font-semibold text-forest-text sm:px-6">
        <PotIcon className="size-5" />
        Tacho
        <span className="font-normal text-text-secondary">· receita partilhada</span>
      </div>

      <main className="mx-auto max-w-4xl px-4 sm:px-6">
        <article className="rounded-2xl bg-surface p-5 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)] sm:p-8">
          {recipe.image_path && (
            <img
              src={publicRecipeImageUrl(token!)}
              alt=""
              className="aspect-video w-full rounded-2xl object-cover"
            />
          )}

          <h1 className={`text-2xl font-bold text-text-primary sm:text-3xl ${recipe.image_path ? 'mt-5' : ''}`}>
            {recipe.title}
          </h1>
          {recipe.description && <p className="mt-2 text-text-secondary">{recipe.description}</p>}

          {(totalMinutes > 0 || recipe.servings != null) && (
            <div className="mt-5 flex gap-6 rounded-2xl bg-bg-sage p-5">
              {totalMinutes > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-accent-orange">
                    <ClockIcon className="size-5" />
                  </span>
                  <div>
                    <div className="text-2xl font-bold leading-none text-text-primary sm:text-3xl">
                      {totalMinutes}
                    </div>
                    <div className="text-xs text-text-secondary">min</div>
                  </div>
                </div>
              )}
              {recipe.servings != null && (
                <div className="flex items-center gap-2">
                  <span className="text-forest-text">
                    <ServingsIcon className="size-5" />
                  </span>
                  <div>
                    <div className="text-2xl font-bold leading-none text-text-primary sm:text-3xl">
                      {recipe.servings}
                    </div>
                    <div className="text-xs text-text-secondary">porções</div>
                  </div>
                </div>
              )}
            </div>
          )}

          {(recipe.categories.length > 0 || recipe.tags.length > 0) && (
            <div className="mt-4 flex flex-wrap gap-1.5">
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
                          {ing.quantity != null ? formatQuantity(ing.quantity) : ''} {ing.unit ?? ''}
                        </span>
                      )}
                    </li>
                  ),
                )}
              </ul>
            </section>

            <section>
              <h2 className="text-lg font-semibold text-text-primary">Preparação</h2>
              <ol className="mt-3 space-y-4">
                {recipe.steps.map((step, i) => (
                  <li key={step.id} className="flex gap-3 text-sm">
                    <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-bg-sage text-xs font-semibold text-forest-text">
                      {i + 1}
                    </span>
                    <span className="text-text-primary">{step.instruction}</span>
                  </li>
                ))}
              </ol>
            </section>
          </div>
        </article>

        <p className="mt-4 text-center text-xs text-text-secondary">
          Partilhado a partir do Tacho — este link deixa de funcionar 5 horas depois de gerado.
        </p>
      </main>
    </div>
  )
}
