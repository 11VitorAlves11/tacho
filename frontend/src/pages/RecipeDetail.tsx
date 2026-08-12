import { useEffect, useRef, useState, type ChangeEvent, type FormEvent, type ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import QRCode from 'qrcode'
import {
  addComment,
  addRecipeGalleryImage,
  deleteComment,
  deleteRecipeGalleryImage,
  duplicateRecipe,
  getRecipe,
  recipeImageUrl,
  setRecipeGalleryCover,
  setRecipeRating,
  toggleFavorite,
} from '../api/recipes'
import type { Recipe } from '../api/types'
import { PageShell } from '../components/PageShell'
import {
  CameraIcon,
  ClockIcon,
  CopyIcon,
  EuroIcon,
  FlameIcon,
  HeartIcon,
  MinusIcon,
  PencilIcon,
  PlayIcon,
  PlusIcon,
  PotIcon,
  PrinterIcon,
  ServingsIcon,
  StarIcon,
  XIcon,
} from '../components/icons'

// Recalcula a quantidade para o número de porções escolhido, sem persistir
// nada — padrão Mealie (PRD/TODO: "sem mudanças no backend").
function scaleQuantity(quantity: number, originalServings: number, desiredServings: number): number {
  return quantity * (desiredServings / originalServings)
}

// Frações comuns de cozinha como glifo unicode em vez de decimal — "½
// chávena" em vez de "0.5 chávena" (TODO.md). Tolerância cobre o
// arredondamento próprio do parser de importação (backend/app/tasks.py::
// _parse_quantity arredonda a 2 casas: 1/3 vira 0.33, não 0.333…) e o erro
// de vírgula flutuante ao escalar porções.
const FRACTION_GLYPHS: [number, string][] = [
  [0.125, '⅛'],
  [0.25, '¼'],
  [1 / 3, '⅓'],
  [0.375, '⅜'],
  [0.5, '½'],
  [0.625, '⅝'],
  [2 / 3, '⅔'],
  [0.75, '¾'],
  [0.875, '⅞'],
]

function formatQuantity(quantity: number): string {
  const rounded = Math.round(quantity * 1000) / 1000
  const whole = Math.floor(rounded)
  const fraction = rounded - whole
  const match = FRACTION_GLYPHS.find(([value]) => Math.abs(fraction - value) < 0.02)
  if (match) {
    const [, glyph] = match
    return whole > 0 ? `${whole} ${glyph}` : glyph
  }
  return (Math.round(quantity * 100) / 100).toFixed(2).replace(/\.?0+$/, '')
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
  const [uploadingGalleryImage, setUploadingGalleryImage] = useState(false)
  const galleryInputRef = useRef<HTMLInputElement>(null)
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    getRecipe(id)
      .then((r) => {
        setRecipe(r)
        setDesiredServings(r.servings)
      })
      .catch(() => setNotFound(true))
  }, [id])

  // Só para a folha de estilo de impressão (print:...) — gerado já aqui em
  // vez de só ao clicar "Imprimir" para não haver atraso nem flash entre o
  // clique e o diálogo de impressão do browser.
  useEffect(() => {
    if (!recipe) return
    QRCode.toDataURL(window.location.href, { margin: 1, width: 160 })
      .then(setQrDataUrl)
      .catch(() => setQrDataUrl(null))
  }, [recipe?.id])

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

  async function handleAddGalleryImage(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!id || !file || uploadingGalleryImage) return
    setUploadingGalleryImage(true)
    try {
      const updated = await addRecipeGalleryImage(id, file)
      setRecipe((prev) => (prev ? { ...prev, images: updated.images } : prev))
    } finally {
      setUploadingGalleryImage(false)
    }
  }

  async function handleDeleteGalleryImage(imageId: string) {
    if (!id) return
    const updated = await deleteRecipeGalleryImage(id, imageId)
    setRecipe((prev) => (prev ? { ...prev, images: updated.images } : prev))
  }

  async function handleSetGalleryCover(imageId: string) {
    if (!id) return
    const updated = await setRecipeGalleryCover(id, imageId)
    setRecipe((prev) => (prev ? { ...prev, images: updated.images } : prev))
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
        {/* Só na folha impressa — a app troca o cabeçalho normal (nav,
            avatar) por um mastro pequeno, para a folha ter identidade
            própria sem trazer chrome que só faz sentido no ecrã. */}
        <div className="hidden items-center gap-1.5 border-b border-black/10 pb-3 text-xs font-semibold uppercase tracking-wide text-text-secondary print:mb-4 print:flex">
          <PotIcon className="size-3.5 text-forest-text" />
          Tacho
        </div>

        {recipe.image_path && (
          <img
            src={recipeImageUrl(recipe.image_path)}
            alt=""
            className="aspect-video w-full rounded-2xl object-cover shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]"
          />
        )}

        <div className={`flex items-start justify-between gap-3 ${recipe.image_path ? 'mt-5' : ''}`}>
          <h1 className="text-2xl font-bold text-text-primary sm:text-3xl">{recipe.title}</h1>
          <div className="flex shrink-0 gap-2 print:hidden">
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
            <button
              type="button"
              onClick={() => window.print()}
              className="flex items-center gap-1.5 rounded-full bg-surface px-3 py-1.5 text-sm font-medium text-text-secondary shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)] hover:text-forest-text"
            >
              <PrinterIcon className="size-4" />
              <span className="hidden sm:inline">Imprimir</span>
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

        <div className="mt-5 flex gap-6 rounded-2xl bg-surface p-5 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)] print:break-inside-avoid print:border print:border-black/15 print:shadow-none">
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
                    className="flex size-6 shrink-0 items-center justify-center rounded-full bg-bg-sage text-forest-text print:hidden"
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
                    className="flex size-6 shrink-0 items-center justify-center rounded-full bg-bg-sage text-forest-text print:hidden"
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
          {recipe.estimated_cost != null && recipe.servings != null && recipe.servings > 0 && (
            <HeroStat
              icon={<EuroIcon className="size-5" />}
              value={Math.round((recipe.estimated_cost / recipe.servings) * 100) / 100}
              label="€/porção"
              tone="forest"
            />
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
          className="mt-5 flex items-center justify-center gap-2 rounded-full bg-primary-forest px-5 py-3.5 font-semibold text-card-white shadow-[0_8px_20px_-6px_rgba(45,95,63,0.6)] transition-transform active:scale-[0.98] print:hidden sm:inline-flex sm:w-auto sm:px-6"
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
                    <span className="flex items-center gap-2 text-text-primary">
                      {/* Só na folha impressa — dá para riscar à mão os
                          ingredientes já separados, mesma lógica do check
                          da Lista de Compras, mas em papel. */}
                      <span
                        aria-hidden="true"
                        className="hidden size-3 shrink-0 rounded-[3px] border border-black/40 print:inline-block"
                      />
                      {ing.name}
                    </span>
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
          <section className="mt-8 rounded-2xl bg-surface p-5 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)] print:break-inside-avoid print:border print:border-black/15 print:shadow-none">
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
                <li
                  key={note.id}
                  className="rounded-2xl bg-surface p-4 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)] print:border print:border-black/15 print:shadow-none"
                >
                  <p className="text-sm text-text-primary">{note.text}</p>
                  <p className="mt-1 text-xs text-text-secondary">{formatLastMade(note.created_at)}</p>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className="mt-8 print:hidden">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-text-primary">Galeria</h2>
            <button
              type="button"
              onClick={() => galleryInputRef.current?.click()}
              disabled={uploadingGalleryImage}
              className="flex items-center gap-1 text-sm font-medium text-forest-text disabled:opacity-50"
            >
              <CameraIcon className="size-4" />
              {uploadingGalleryImage ? 'A enviar…' : 'Adicionar foto'}
            </button>
            <input
              ref={galleryInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              capture="environment"
              onChange={handleAddGalleryImage}
              className="hidden"
            />
          </div>

          {recipe.images.length === 0 ? (
            <p className="mt-2 text-sm text-text-secondary">Ainda não há fotos extra desta receita.</p>
          ) : (
            <div className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-4">
              {recipe.images.map((image) => (
                <div key={image.id} className="group relative aspect-square overflow-hidden rounded-xl bg-bg-sage">
                  <img src={recipeImageUrl(image.filename)} alt="" className="size-full object-cover" />
                  {image.is_cover && (
                    <span className="absolute left-1.5 top-1.5 rounded-full bg-card-white/90 px-2 py-0.5 text-[10px] font-medium text-forest-text">
                      Capa
                    </span>
                  )}
                  <div className="absolute inset-x-0 bottom-0 flex justify-end gap-1 bg-gradient-to-t from-black/50 to-transparent p-1.5">
                    {!image.is_cover && (
                      <button
                        type="button"
                        onClick={() => handleSetGalleryCover(image.id)}
                        aria-label="Tornar capa da galeria"
                        className="flex size-6 items-center justify-center rounded-full bg-card-white/90 text-forest-text"
                      >
                        <StarIcon className="size-3.5" />
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => handleDeleteGalleryImage(image.id)}
                      aria-label="Apagar foto da galeria"
                      className="flex size-6 items-center justify-center rounded-full bg-card-white/90 text-accent-orange"
                    >
                      <XIcon className="size-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="mt-8 print:hidden">
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

        {qrDataUrl && (
          <div className="hidden items-center gap-3 border-t border-black/10 pt-4 print:mt-8 print:flex">
            <img src={qrDataUrl} alt="" className="size-24" />
            <p className="text-xs text-text-secondary">
              Ver esta receita online, com fotos e comentários:
              <br />
              {window.location.href}
            </p>
          </div>
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
