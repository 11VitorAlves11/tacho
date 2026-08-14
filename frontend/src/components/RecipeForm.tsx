import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { estimateNutrition, OFF_UNAVAILABLE_REASON, type NutritionEstimate } from '../api/nutrition'
import { createCategory, createTag, listCategories, listTags, recipeImageUrl } from '../api/recipes'
import type { Category, RecipeInput, Tag } from '../api/types'
import { CameraIcon, PlusIcon, XIcon } from './icons'

interface IngredientRow {
  name: string
  quantity: string
  unit: string
  isHeader: boolean
}

interface StepRow {
  instruction: string
  durationMinutes: string
}

// Mais fraco do que `Recipe` de propósito — permite pré-preencher o
// formulário a partir de um rascunho que não é (ainda) uma receita
// guardada (ex. RecipeExtraction do import por foto via Gemini,
// AddRecipe.tsx), sem inventar ids/posições/is_favorite/etc. que esse
// rascunho não tem. `Recipe` continua a satisfazer este tipo (é um
// superconjunto estrutural), por isso o modo de edição não muda nada.
interface RecipeFormInitial {
  title?: string
  description?: string | null
  servings?: number | null
  prep_minutes?: number | null
  cook_minutes?: number | null
  source_url?: string | null
  notes?: string | null
  calories_kcal?: number | null
  protein_g?: number | null
  carbs_g?: number | null
  fat_g?: number | null
  estimated_cost?: number | null
  image_path?: string | null
  ingredients?: { name: string; quantity?: number | null; unit?: string | null; is_header?: boolean }[]
  steps?: { instruction: string; duration_minutes?: number | null }[]
  categories?: Category[]
  tags?: Tag[]
}

function toIngredientRows(initial?: RecipeFormInitial): IngredientRow[] {
  const ingredients = initial?.ingredients ?? []
  if (ingredients.length === 0) return [{ name: '', quantity: '', unit: '', isHeader: false }]
  return ingredients.map((i) => ({
    name: i.name,
    quantity: i.quantity?.toString() ?? '',
    unit: i.unit ?? '',
    isHeader: i.is_header ?? false,
  }))
}

function toStepRows(initial?: RecipeFormInitial): StepRow[] {
  const steps = initial?.steps ?? []
  if (steps.length === 0) return [{ instruction: '', durationMinutes: '' }]
  return steps.map((s) => ({ instruction: s.instruction, durationMinutes: s.duration_minutes?.toString() ?? '' }))
}

export function RecipeForm({
  initial,
  onSubmit,
  submitLabel,
}: {
  initial?: RecipeFormInitial
  onSubmit: (payload: RecipeInput, imageFile: File | null) => Promise<void>
  submitLabel: string
}) {
  const [title, setTitle] = useState(initial?.title ?? '')
  const [description, setDescription] = useState(initial?.description ?? '')
  const [servings, setServings] = useState(initial?.servings?.toString() ?? '')
  const [prepMinutes, setPrepMinutes] = useState(initial?.prep_minutes?.toString() ?? '')
  const [cookMinutes, setCookMinutes] = useState(initial?.cook_minutes?.toString() ?? '')
  const [sourceUrl, setSourceUrl] = useState(initial?.source_url ?? '')
  const [notes, setNotes] = useState(initial?.notes ?? '')
  const [caloriesKcal, setCaloriesKcal] = useState(initial?.calories_kcal?.toString() ?? '')
  const [proteinG, setProteinG] = useState(initial?.protein_g?.toString() ?? '')
  const [carbsG, setCarbsG] = useState(initial?.carbs_g?.toString() ?? '')
  const [fatG, setFatG] = useState(initial?.fat_g?.toString() ?? '')
  const [estimatedCost, setEstimatedCost] = useState(initial?.estimated_cost?.toString() ?? '')
  const [nutritionEstimate, setNutritionEstimate] = useState<NutritionEstimate | null>(null)
  const [estimating, setEstimating] = useState(false)
  const [estimateError, setEstimateError] = useState('')
  const [nutritionStale, setNutritionStale] = useState(false)
  const appliedSignatureRef = useRef<string | null>(null)
  const [ingredients, setIngredients] = useState<IngredientRow[]>(toIngredientRows(initial))
  const [steps, setSteps] = useState<StepRow[]>(toStepRows(initial))

  const [imageFile, setImageFile] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(
    initial?.image_path ? recipeImageUrl(initial.image_path) : null,
  )
  const imageInputRef = useRef<HTMLInputElement>(null)

  function handleImageChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setImageFile(file)
    setImagePreview(URL.createObjectURL(file))
  }

  const [categories, setCategories] = useState<Category[]>([])
  const [tags, setTags] = useState<Tag[]>([])
  const [categoryIds, setCategoryIds] = useState<string[]>(initial?.categories?.map((c) => c.id) ?? [])
  const [tagIds, setTagIds] = useState<string[]>(initial?.tags?.map((t) => t.id) ?? [])
  const [newCategoryName, setNewCategoryName] = useState('')
  const [newTagName, setNewTagName] = useState('')

  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    listCategories().then(setCategories).catch(() => {})
    listTags().then(setTags).catch(() => {})
  }, [])

  function updateIngredient(index: number, patch: Partial<IngredientRow>) {
    setIngredients((rows) => rows.map((row, i) => (i === index ? { ...row, ...patch } : row)))
  }

  function removeIngredient(index: number) {
    setIngredients((rows) => (rows.length > 1 ? rows.filter((_, i) => i !== index) : rows))
  }

  function updateStep(index: number, patch: Partial<StepRow>) {
    setSteps((rows) => rows.map((row, i) => (i === index ? { ...row, ...patch } : row)))
  }

  function removeStep(index: number) {
    setSteps((rows) => (rows.length > 1 ? rows.filter((_, i) => i !== index) : rows))
  }

  function toggleCategory(id: string) {
    setCategoryIds((ids) => (ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]))
  }

  function toggleTag(id: string) {
    setTagIds((ids) => (ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]))
  }

  async function addNewCategory() {
    const name = newCategoryName.trim()
    if (!name) return
    const existing = categories.find((c) => c.name.toLowerCase() === name.toLowerCase())
    if (existing) {
      if (!categoryIds.includes(existing.id)) setCategoryIds((ids) => [...ids, existing.id])
    } else {
      const created = await createCategory(name)
      setCategories((cats) => [...cats, created])
      setCategoryIds((ids) => [...ids, created.id])
    }
    setNewCategoryName('')
  }

  async function addNewTag() {
    const name = newTagName.trim()
    if (!name) return
    const existing = tags.find((t) => t.name.toLowerCase() === name.toLowerCase())
    if (existing) {
      if (!tagIds.includes(existing.id)) setTagIds((ids) => [...ids, existing.id])
    } else {
      const created = await createTag(name)
      setTags((ts) => [...ts, created])
      setTagIds((ids) => [...ids, created.id])
    }
    setNewTagName('')
  }

  async function handleEstimateNutrition() {
    if (estimating) return
    setEstimating(true)
    setNutritionEstimate(null)
    setEstimateError('')
    try {
      const result = await estimateNutrition(
        ingredients
          .filter((row) => !row.isHeader && row.name.trim())
          .map((row) => ({ name: row.name, quantity: row.quantity ? Number(row.quantity) : null, unit: row.unit || null })),
        servings ? Number(servings) : null,
      )
      setNutritionEstimate(result)
    } catch {
      // Falha ao chamar o próprio endpoint (rede local, 5xx) — distinto de
      // um 200 com matched_count:0, que já traz skipped_ingredients a
      // explicar cada ingrediente ignorado.
      setEstimateError('Não foi possível pedir a estimativa agora. Tenta de novo daqui a pouco.')
    } finally {
      setEstimating(false)
    }
  }

  function applyNutritionEstimate() {
    if (!nutritionEstimate) return
    if (nutritionEstimate.calories_kcal != null) setCaloriesKcal(nutritionEstimate.calories_kcal.toString())
    if (nutritionEstimate.protein_g != null) setProteinG(nutritionEstimate.protein_g.toString())
    if (nutritionEstimate.carbs_g != null) setCarbsG(nutritionEstimate.carbs_g.toString())
    if (nutritionEstimate.fat_g != null) setFatG(nutritionEstimate.fat_g.toString())
    setNutritionEstimate(null)
    setNutritionStale(false)
    appliedSignatureRef.current = JSON.stringify({ servings, ingredients })
  }

  // Os valores nutricionais aplicados ficam gravados como números fixos,
  // não recalculam sozinhos — avisa quando ingredientes/porções mudam
  // depois de uma estimativa já aplicada, para não passar por actualizados
  // sem estar.
  useEffect(() => {
    if (appliedSignatureRef.current === null) return
    setNutritionStale(JSON.stringify({ servings, ingredients }) !== appliedSignatureRef.current)
  }, [servings, ingredients])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await onSubmit(
        {
          title: title.trim(),
          description: description.trim() || null,
          servings: servings ? Number(servings) : null,
          prep_minutes: prepMinutes ? Number(prepMinutes) : null,
          cook_minutes: cookMinutes ? Number(cookMinutes) : null,
          source_url: sourceUrl.trim() || null,
          notes: notes.trim() || null,
          calories_kcal: caloriesKcal ? Number(caloriesKcal) : null,
          protein_g: proteinG ? Number(proteinG) : null,
          carbs_g: carbsG ? Number(carbsG) : null,
          fat_g: fatG ? Number(fatG) : null,
          estimated_cost: estimatedCost ? Number(estimatedCost) : null,
          ingredients: ingredients
            .filter((row) => row.name.trim())
            .map((row) => ({
              name: row.name.trim(),
              quantity: row.isHeader ? null : row.quantity ? Number(row.quantity) : null,
              unit: row.isHeader ? null : row.unit.trim() || null,
              is_header: row.isHeader,
            })),
          steps: steps
            .filter((row) => row.instruction.trim())
            .map((row) => ({
              instruction: row.instruction.trim(),
              duration_minutes: row.durationMinutes ? Number(row.durationMinutes) : null,
            })),
          category_ids: categoryIds,
          tag_ids: tagIds,
        },
        imageFile,
      )
    } catch {
      setError('Não foi possível guardar a receita.')
      setSaving(false)
    }
  }

  const fieldClass =
    'rounded-xl border border-black/10 bg-bg-sage px-3 py-2 text-sm outline-none ring-2 ring-transparent transition-shadow focus:border-accent-leaf focus:ring-accent-leaf/30'

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="rounded-2xl bg-surface p-5 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]">
        <input
          ref={imageInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={handleImageChange}
          className="hidden"
        />
        <button
          type="button"
          onClick={() => imageInputRef.current?.click()}
          className="relative flex aspect-video w-full items-center justify-center overflow-hidden rounded-xl bg-bg-sage text-text-secondary"
        >
          {imagePreview ? (
            <>
              <img src={imagePreview} alt="" className="size-full object-cover" />
              <span className="absolute bottom-2 right-2 flex items-center gap-1 rounded-full bg-primary-forest/90 px-3 py-1.5 text-xs font-medium text-card-white">
                <CameraIcon className="size-3.5" />
                Trocar foto
              </span>
            </>
          ) : (
            <span className="flex flex-col items-center gap-1.5">
              <CameraIcon className="size-6" />
              <span className="text-sm font-medium">Adicionar foto</span>
            </span>
          )}
        </button>

        <label className="mt-4 block text-sm font-medium text-text-secondary" htmlFor="title">
          Título
        </label>
        <input
          id="title"
          required
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className={`${fieldClass} w-full mt-1`}
          placeholder="Ex.: Bacalhau à Brás"
        />

        <label className="mt-4 block text-sm font-medium text-text-secondary" htmlFor="description">
          Descrição
        </label>
        <textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className={`${fieldClass} w-full mt-1`}
          rows={2}
        />

        <div className="mt-4 grid grid-cols-3 gap-3">
          <div>
            <label className="block min-h-10 text-sm font-medium text-text-secondary" htmlFor="servings">
              Porções (und)
            </label>
            <input
              id="servings"
              type="number"
              min={0}
              value={servings}
              onChange={(e) => setServings(e.target.value)}
              className={`${fieldClass} w-full mt-1`}
            />
          </div>
          <div>
            <label className="block min-h-10 text-sm font-medium text-text-secondary" htmlFor="prep">
              Preparação (min)
            </label>
            <input
              id="prep"
              type="number"
              min={0}
              value={prepMinutes}
              onChange={(e) => setPrepMinutes(e.target.value)}
              className={`${fieldClass} w-full mt-1`}
            />
          </div>
          <div>
            <label className="block min-h-10 text-sm font-medium text-text-secondary" htmlFor="cook">
              Confeção (min)
            </label>
            <input
              id="cook"
              type="number"
              min={0}
              value={cookMinutes}
              onChange={(e) => setCookMinutes(e.target.value)}
              className={`${fieldClass} w-full mt-1`}
            />
          </div>
        </div>

        <label className="mt-4 block text-sm font-medium text-text-secondary" htmlFor="source">
          Fonte (opcional)
        </label>
        <input
          id="source"
          type="url"
          value={sourceUrl}
          onChange={(e) => setSourceUrl(e.target.value)}
          className={`${fieldClass} w-full mt-1`}
          placeholder="https://…"
        />

        <label className="mt-4 block text-sm font-medium text-text-secondary" htmlFor="cost">
          Custo estimado da receita (€, opcional)
        </label>
        <input
          id="cost"
          type="number"
          min={0}
          step="0.01"
          value={estimatedCost}
          onChange={(e) => setEstimatedCost(e.target.value)}
          className={`${fieldClass} w-full mt-1`}
          placeholder="Ex.: 8.50"
        />

        <label className="mt-4 block text-sm font-medium text-text-secondary" htmlFor="notes">
          Notas
        </label>
        <textarea
          id="notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className={`${fieldClass} w-full mt-1`}
          rows={2}
        />
      </div>

      <div className="rounded-2xl bg-surface p-5 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]">
        <h2 className="text-lg font-semibold text-text-primary">Ingredientes</h2>
        <div className="mt-3 space-y-2">
          {ingredients.map((row, i) =>
            row.isHeader ? (
              <div key={i} className="flex gap-2">
                <input
                  value={row.name}
                  onChange={(e) => updateIngredient(i, { name: e.target.value })}
                  placeholder="Nome da secção, ex.: Para o recheio"
                  className={`${fieldClass} w-full font-semibold`}
                />
                <button
                  type="button"
                  onClick={() => removeIngredient(i)}
                  className="shrink-0 rounded-full p-2 text-text-secondary hover:bg-bg-sage"
                  aria-label="Remover secção"
                >
                  <XIcon className="size-4" />
                </button>
              </div>
            ) : (
              <div key={i} className="flex gap-2">
                <input
                  value={row.quantity}
                  onChange={(e) => updateIngredient(i, { quantity: e.target.value })}
                  placeholder="qtd"
                  inputMode="decimal"
                  className={`${fieldClass} w-16 shrink-0`}
                />
                <input
                  value={row.unit}
                  onChange={(e) => updateIngredient(i, { unit: e.target.value })}
                  placeholder="unidade"
                  className={`${fieldClass} w-24 shrink-0`}
                />
                <input
                  value={row.name}
                  onChange={(e) => updateIngredient(i, { name: e.target.value })}
                  placeholder="ingrediente"
                  className={`${fieldClass} min-w-0 flex-1`}
                />
                <button
                  type="button"
                  onClick={() => removeIngredient(i)}
                  className="shrink-0 rounded-full p-2 text-text-secondary hover:bg-bg-sage"
                  aria-label="Remover ingrediente"
                >
                  <XIcon className="size-4" />
                </button>
              </div>
            ),
          )}
        </div>
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2">
          <button
            type="button"
            onClick={() => setIngredients((rows) => [...rows, { name: '', quantity: '', unit: '', isHeader: false }])}
            className="flex items-center gap-1 text-sm font-medium text-forest-text"
          >
            <PlusIcon className="size-4" />
            Adicionar ingrediente
          </button>
          <button
            type="button"
            onClick={() => setIngredients((rows) => [...rows, { name: '', quantity: '', unit: '', isHeader: true }])}
            className="flex items-center gap-1 text-sm font-medium text-text-secondary"
          >
            <PlusIcon className="size-4" />
            Adicionar cabeçalho de secção
          </button>
        </div>
      </div>

      <div className="rounded-2xl bg-surface p-5 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]">
        <h2 className="text-lg font-semibold text-text-primary">Preparação</h2>
        <div className="mt-3 space-y-2">
          {steps.map((row, i) => (
            <div key={i} className="flex gap-2">
              <span className="mt-2 flex size-6 shrink-0 items-center justify-center rounded-full bg-bg-sage text-xs font-semibold text-forest-text">
                {i + 1}
              </span>
              <textarea
                value={row.instruction}
                onChange={(e) => updateStep(i, { instruction: e.target.value })}
                placeholder={`Passo ${i + 1}`}
                rows={1}
                className={`${fieldClass} min-w-0 flex-1`}
              />
              <input
                value={row.durationMinutes}
                onChange={(e) => updateStep(i, { durationMinutes: e.target.value })}
                type="number"
                min={0}
                placeholder="min"
                aria-label={`Duração do passo ${i + 1} em minutos`}
                className={`${fieldClass} w-16 shrink-0 text-center`}
              />
              <button
                type="button"
                onClick={() => removeStep(i)}
                className="shrink-0 rounded-full p-2 text-text-secondary hover:bg-bg-sage"
                aria-label="Remover passo"
              >
                <XIcon className="size-4" />
              </button>
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={() => setSteps((rows) => [...rows, { instruction: '', durationMinutes: '' }])}
          className="mt-3 flex items-center gap-1 text-sm font-medium text-forest-text"
        >
          <PlusIcon className="size-4" />
          Adicionar passo
        </button>
      </div>

      <div className="rounded-2xl bg-surface p-5 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]">
        <h2 className="text-lg font-semibold text-text-primary">Categorias e tags</h2>

        <p className="mt-3 text-sm font-medium text-text-secondary">Categorias</p>
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
          {categories.map((c) => (
            <Chip key={c.id} label={c.name} active={categoryIds.includes(c.id)} onClick={() => toggleCategory(c.id)} tone="forest" />
          ))}
          <InlineAdd value={newCategoryName} onChange={setNewCategoryName} onAdd={addNewCategory} placeholder="nova categoria" />
        </div>

        <p className="mt-4 text-sm font-medium text-text-secondary">Tags</p>
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
          {tags.map((t) => (
            <Chip key={t.id} label={t.name} active={tagIds.includes(t.id)} onClick={() => toggleTag(t.id)} tone="leaf" />
          ))}
          <InlineAdd value={newTagName} onChange={setNewTagName} onAdd={addNewTag} placeholder="nova tag" />
        </div>
      </div>

      <div className="rounded-2xl bg-surface p-5 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]">
        <h2 className="text-lg font-semibold text-text-primary">Informação nutricional</h2>
        <p className="mt-1 text-xs text-text-secondary">Por porção, opcional e à mão.</p>

        <button
          type="button"
          onClick={handleEstimateNutrition}
          disabled={estimating}
          className="mt-3 flex items-center gap-1 text-sm font-medium text-forest-text disabled:opacity-50"
        >
          {estimating ? 'A estimar…' : 'Estimar a partir dos ingredientes (Open Food Facts)'}
        </button>

        {estimateError && (
          <div className="mt-2 rounded-xl bg-bg-sage p-3 text-sm text-text-secondary">{estimateError}</div>
        )}

        {nutritionEstimate && (
          <div className="mt-2 rounded-xl bg-bg-sage p-3 text-sm">
            {nutritionEstimate.matched_count === 0 ? (
              <p className="text-text-secondary">
                Não foi possível estimar — nenhum ingrediente entrou na conta. Podes sempre preencher à mão.
              </p>
            ) : (
              <>
                <p className="text-text-primary">
                  Estimativa ({nutritionEstimate.matched_count} de{' '}
                  {nutritionEstimate.matched_count + nutritionEstimate.skipped_count} ingredientes): {nutritionEstimate.calories_kcal}{' '}
                  kcal · {nutritionEstimate.protein_g}g proteína · {nutritionEstimate.carbs_g}g hidratos ·{' '}
                  {nutritionEstimate.fat_g}g gordura
                </p>
                <p className="mt-1 text-xs text-text-secondary">
                  Aproximada — nem todos os ingredientes/unidades entram na conta, nunca substitui os campos abaixo
                  sem confirmares.
                </p>
              </>
            )}
            {nutritionEstimate.skipped_ingredients.length > 0 && (
              <ul className="mt-2 space-y-0.5 text-xs text-text-secondary">
                {nutritionEstimate.skipped_ingredients.map((s, i) => (
                  <li key={i}>
                    {s.name}: {s.reason === OFF_UNAVAILABLE_REASON ? 'a Open Food Facts pode estar em baixo' : s.reason}
                  </li>
                ))}
              </ul>
            )}
            {nutritionEstimate.matched_count > 0 && (
              <div className="mt-2 flex gap-3">
                <button type="button" onClick={applyNutritionEstimate} className="text-sm font-medium text-forest-text">
                  Aplicar
                </button>
                <button
                  type="button"
                  onClick={() => setNutritionEstimate(null)}
                  className="text-sm font-medium text-text-secondary"
                >
                  Descartar
                </button>
              </div>
            )}
          </div>
        )}

        {nutritionStale && (
          <p className="mt-2 text-xs text-text-secondary">
            Alteraste ingredientes ou porções desde a última estimativa aplicada — os valores abaixo podem estar
            desactualizados.
          </p>
        )}

        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div>
            <label className="block text-sm font-medium text-text-secondary" htmlFor="calories">
              Calorias (kcal)
            </label>
            <input
              id="calories"
              type="number"
              min={0}
              value={caloriesKcal}
              onChange={(e) => setCaloriesKcal(e.target.value)}
              className={`${fieldClass} w-full mt-1`}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-secondary" htmlFor="protein">
              Proteína (g)
            </label>
            <input
              id="protein"
              type="number"
              min={0}
              step="0.1"
              value={proteinG}
              onChange={(e) => setProteinG(e.target.value)}
              className={`${fieldClass} w-full mt-1`}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-secondary" htmlFor="carbs">
              Hidratos (g)
            </label>
            <input
              id="carbs"
              type="number"
              min={0}
              step="0.1"
              value={carbsG}
              onChange={(e) => setCarbsG(e.target.value)}
              className={`${fieldClass} w-full mt-1`}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-secondary" htmlFor="fat">
              Gordura (g)
            </label>
            <input
              id="fat"
              type="number"
              min={0}
              step="0.1"
              value={fatG}
              onChange={(e) => setFatG(e.target.value)}
              className={`${fieldClass} w-full mt-1`}
            />
          </div>
        </div>
      </div>

      {error && <p className="text-sm text-accent-orange">{error}</p>}

      <button
        type="submit"
        disabled={saving}
        className="w-full rounded-full bg-primary-forest py-3.5 font-semibold text-card-white transition-opacity disabled:opacity-60"
      >
        {saving ? 'A guardar…' : submitLabel}
      </button>
    </form>
  )
}

function Chip({
  label,
  active,
  onClick,
  tone,
}: {
  label: string
  active: boolean
  onClick: () => void
  tone: 'forest' | 'leaf'
}) {
  const activeClass = tone === 'forest' ? 'bg-primary-forest text-card-white' : 'bg-accent-leaf text-card-white'
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
        active ? activeClass : 'bg-bg-sage text-text-secondary hover:bg-bg-sage/70'
      }`}
    >
      {label}
    </button>
  )
}

function InlineAdd({
  value,
  onChange,
  onAdd,
  placeholder,
}: {
  value: string
  onChange: (v: string) => void
  onAdd: () => void
  placeholder: string
}) {
  return (
    <span className="flex items-center gap-1 rounded-full border border-dashed border-black/15 pl-2.5 pr-1 py-0.5">
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault()
            onAdd()
          }
        }}
        placeholder={placeholder}
        className="w-24 bg-transparent text-xs outline-none placeholder:text-text-secondary"
      />
      <button
        type="button"
        onClick={onAdd}
        className="flex size-5 shrink-0 items-center justify-center rounded-full text-text-secondary hover:bg-bg-sage"
        aria-label={`Adicionar ${placeholder}`}
      >
        <PlusIcon className="size-3.5" />
      </button>
    </span>
  )
}
