import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  addComment,
  deleteComment,
  duplicateRecipe,
  getRecipe,
  recipeImageUrl,
  setRecipeRating,
  toggleFavorite,
} from '../api/recipes'
import type { Recipe } from '../api/types'
import { PageShell } from '../components/PageShell'
import {
  ClockIcon,
  CopyIcon,
  FlameIcon,
  HeartIcon,
  MinusIcon,
  PencilIcon,
  PlayIcon,
  PlusIcon,
  ServingsIcon,
  StarIcon,
  XIcon,
} from '../components/icons'

// Recalcula a quantidade para o número de porções escolhido, sem persistir
// nada — padrão Mealie (PRD/TODO: "sem mudanças no backend").
function scaleQuantity(quantity: number, originalServings: number, desiredServings: number): number {
  return quantity * (desiredServings / originalServings)
}

function formatQuantity(quantity: number): string {
  const rounded = Math.round(quantity * 100) / 100
  return rounded.toFixed(2).replace(/\.?0+$/, '')
}

function formatLastMade(iso: string): string {
  return new Date(iso).toLocaleDateString('pt-PT', { day: 'numeric', month: 'long', year: 'numeric' })
}

export function RecipeDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [recipe, setRecipe] = useState<Recipe | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [desiredServings, setDesiredServings] = useState<number | null>(null)
  const [duplicating, setDuplicating] = useState(false)
  const [commentText, setCommentText] = useState('')
  const [postingComment, setPostingComment] = useState(false)

  useEffect(() => {
    if (!id) return
    getRecipe(id)
      .then((r) => {
        setRecipe(r)
        setDesiredServings(r.servings)
      })
      .catch(() => setNotFound(true))
  }, [id])

  async function handleDuplicate() {
    if (!id || duplicating) return
    setDuplicating(true)
    try {
      const copy = await duplicateRecipe(id)
      navigate(`/receitas/${copy.id}/editar`)
    } finally {
      setDuplicating(false)
    }
  }

  async function handleToggleFavorite() {
    if (!id) return
    const updated = await toggleFavorite(id)
    setRecipe((prev) => (prev ? { ...prev, is_favorite: updated.is_favorite } : prev))
  }

  async function handleAddComment(e: FormEvent) {
    e.preventDefault()
    const text = commentText.trim()
    if (!id || !text || postingComment) return
    setPostingComment(true)
    try {
      const updated = await addComment(id, text)
      setRecipe((prev) => (prev ? { ...prev, comments: updated.comments } : prev))
      setCommentText('')
    } finally {
      setPostingComment(false)
    }
  }

  async function handleDeleteComment(commentId: string) {
    if (!id) return
    await deleteComment(id, commentId)
    setRecipe((prev) => (prev ? { ...prev, comments: prev.comments.filter((c) => c.id !== commentId) } : prev))
  }

  async function handleSetRating(value: number) {
    if (!id || !recipe) return
    const nextRating = recipe.rating === value ? null : value
    const updated = await setRecipeRating(id, nextRating)
    setRecipe((prev) => (prev ? { ...prev, rating: updated.rating } : prev))
  }

  if (notFound) {
    return (
      <PageShell>
        <p className="text-text-secondary">Receita não encontrada.</p>
        <Link to="/" className="mt-2 inline-block font-medium text-forest-text">
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
          <div className="flex shrink-0 gap-2">
            <button
              type="button"
              onClick={handleToggleFavorite}
              aria-pressed={recipe.is_favorite}
              aria-label={recipe.is_favorite ? 'Remover dos favoritos' : 'Adicionar aos favoritos'}
              className={`flex items-center gap-1.5 rounded-full bg-surface px-3 py-1.5 text-sm font-medium shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)] ${
                recipe.is_favorite ? 'text-accent-leaf' : 'text-text-secondary hover:text-accent-leaf'
              }`}
            >
              <HeartIcon className="size-4" fill={recipe.is_favorite ? 'currentColor' : 'none'} />
              <span className="hidden sm:inline">Favorito</span>
            </button>
            <button
              type="button"
              onClick={handleDuplicate}
              disabled={duplicating}
              className="flex items-center gap-1.5 rounded-full bg-surface px-3 py-1.5 text-sm font-medium text-text-secondary shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)] hover:text-forest-text disabled:opacity-50"
            >
              <CopyIcon className="size-4" />
              <span className="hidden sm:inline">Duplicar</span>
            </button>
            <Link
              to={`/receitas/${recipe.id}/editar`}
              className="flex items-center gap-1.5 rounded-full bg-surface px-3 py-1.5 text-sm font-medium text-text-secondary shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)] hover:text-forest-text"
            >
              <PencilIcon className="size-4" />
              <span className="hidden sm:inline">Editar</span>
            </Link>
          </div>
        </div>
        {recipe.description && <p className="mt-2 text-text-secondary">{recipe.description}</p>}

        <div className="mt-2 flex items-center gap-0.5" role="radiogroup" aria-label="Avaliação por estrelas">
          {[1, 2, 3, 4, 5].map((value) => {
            const filled = recipe.rating != null && value <= recipe.rating
            return (
              <button
                key={value}
                type="button"
                onClick={() => handleSetRating(value)}
                aria-pressed={filled}
                aria-label={`${value} estrela${value > 1 ? 's' : ''}`}
                className={`p-0.5 ${filled ? 'text-accent-leaf' : 'text-text-secondary hover:text-accent-leaf'}`}
              >
                <StarIcon className="size-5" fill={filled ? 'currentColor' : 'none'} />
              </button>
            )
          })}
        </div>

        <div className="mt-5 flex gap-6 rounded-2xl bg-surface p-5 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]">
          {totalMinutes > 0 && (
            <HeroStat icon={<ClockIcon className="size-5" />} value={totalMinutes} label="min" tone="orange" />
          )}
          {recipe.servings != null && desiredServings != null && (
            <div className="flex items-center gap-2">
              <span className="text-forest-text">
                <ServingsIcon className="size-5" />
              </span>
              <div>
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => setDesiredServings((s) => Math.max(1, (s ?? 1) - 1))}
                    className="flex size-6 shrink-0 items-center justify-center rounded-full bg-bg-sage text-forest-text"
                    aria-label="Menos uma porção"
                  >
                    <MinusIcon className="size-3.5" />
                  </button>
                  <span className="min-w-[1.5ch] text-center text-2xl font-bold leading-none text-text-primary sm:text-3xl">
                    {desiredServings}
                  </span>
                  <button
                    type="button"
                    onClick={() => setDesiredServings((s) => (s ?? 1) + 1)}
                    className="flex size-6 shrink-0 items-center justify-center rounded-full bg-bg-sage text-forest-text"
                    aria-label="Mais uma porção"
                  >
                    <PlusIcon className="size-3.5" />
                  </button>
                </div>
                <div className="text-xs text-text-secondary">
                  porções{desiredServings !== recipe.servings ? ` (original: ${recipe.servings})` : ''}
                </div>
              </div>
            </div>
          )}
          {recipe.calories_kcal != null && (
            <HeroStat icon={<FlameIcon className="size-5" />} value={recipe.calories_kcal} label="kcal/porção" tone="forest" />
          )}
        </div>

        {/* O hero number mostra sempre o tempo total (DESIGN.md, "Hierarchy" —
            um único hero number por métrica); a repartição prep/confeção fica
            como legenda secundária, só quando ambos os tempos são conhecidos. */}
        {recipe.prep_minutes != null && recipe.cook_minutes != null && (
          <p className="mt-2 text-xs text-text-secondary">
            Preparação: {recipe.prep_minutes} min · Confeção: {recipe.cook_minutes} min
          </p>
        )}

        {recipe.last_made_at && (
          <p className="mt-2 text-xs text-text-secondary">Feita pela última vez em {formatLastMade(recipe.last_made_at)}.</p>
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
                        {ing.quantity != null
                          ? recipe.servings && desiredServings
                            ? formatQuantity(scaleQuantity(ing.quantity, recipe.servings, desiredServings))
                            : ing.quantity
                          : ''}{' '}
                        {ing.unit ?? ''}
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
                  <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-bg-sage text-xs font-semibold text-forest-text">
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
          <section className="mt-8 rounded-2xl bg-surface p-5 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]">
            <h2 className="text-lg font-semibold text-text-primary">Informação nutricional</h2>
            <p className="mt-1 text-xs text-text-secondary">Por porção, entrada manual.</p>
            <div className="mt-3 grid grid-cols-3 gap-3 text-center">
              <MacroStat value={recipe.protein_g} label="Proteína" />
              <MacroStat value={recipe.carbs_g} label="Hidratos" />
              <MacroStat value={recipe.fat_g} label="Gordura" />
            </div>
          </section>
        )}

        {recipe.cook_notes.length > 0 && (
          <section className="mt-8">
            <h2 className="text-lg font-semibold text-text-primary">Notas</h2>
            <ul className="mt-3 space-y-3">
              {recipe.cook_notes.map((note) => (
                <li key={note.id} className="rounded-2xl bg-surface p-4 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]">
                  <p className="text-sm text-text-primary">{note.text}</p>
                  <p className="mt-1 text-xs text-text-secondary">{formatLastMade(note.created_at)}</p>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className="mt-8">
          <h2 className="text-lg font-semibold text-text-primary">Comentários</h2>
          {recipe.comments.length > 0 && (
            <ul className="mt-3 space-y-3">
              {recipe.comments.map((comment) => (
                <li
                  key={comment.id}
                  className="flex items-start justify-between gap-2 rounded-2xl bg-surface p-4 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]"
                >
                  <div>
                    <p className="text-sm text-text-primary">{comment.text}</p>
                    <p className="mt-1 text-xs text-text-secondary">
                      {comment.author_name ?? comment.author_email} · {formatLastMade(comment.created_at)}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDeleteComment(comment.id)}
                    className="shrink-0 rounded-full p-1.5 text-text-secondary hover:bg-bg-sage"
                    aria-label="Apagar comentário"
                  >
                    <XIcon className="size-4" />
                  </button>
                </li>
              ))}
            </ul>
          )}
          <form onSubmit={handleAddComment} className="mt-3 flex gap-2">
            <input
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              placeholder="Escreve um comentário…"
              className="min-w-0 flex-1 rounded-xl border border-black/10 bg-bg-sage px-3 py-2 text-sm outline-none ring-2 ring-transparent transition-shadow focus:border-accent-leaf focus:ring-accent-leaf/30"
            />
            <button
              type="submit"
              disabled={!commentText.trim() || postingComment}
              className="shrink-0 rounded-xl bg-primary-forest px-4 py-2 text-sm font-medium text-card-white disabled:opacity-50"
            >
              Enviar
            </button>
          </form>
        </section>

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
  const iconClass = tone === 'orange' ? 'text-accent-orange' : 'text-forest-text'
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
