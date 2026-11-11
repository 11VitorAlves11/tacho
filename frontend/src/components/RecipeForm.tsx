import { t } from '../i18n'
import { useEffect, useRef, useState, type ChangeEvent, type FormEvent, type InputHTMLAttributes } from 'react'
import { estimateNutrition, OFF_UNAVAILABLE_REASON, type NutritionEstimate } from '../api/nutrition'
import { createCategory, createTag, listCategories, listTags, recipeImageUrl, updateCategory } from '../api/recipes'
import type { Category, CategoryIcon, RecipeInput, Tag } from '../api/types'
import { CameraIcon, PlusIcon, XIcon } from './icons'
import { CategoryBadge, Chip, Modal } from './ui'

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

const CATEGORY_ICON_OPTIONS: { value: CategoryIcon; symbol: string; label: string }[] = [
  { value: 'breakfast', symbol: '☀', label: 'Pequeno-almoço' },
  { value: 'main', symbol: '🍲', label: 'Prato principal' },
  { value: 'dessert', symbol: '♨', label: 'Sobremesa' },
  { value: 'drink', symbol: '◒', label: 'Bebida' },
  { value: 'snack', symbol: '◇', label: 'Lanche' },
  { value: 'other', symbol: '●', label: 'Outro' },
]

const DEFAULT_CATEGORY_COLOR = '#2F6B45'

// Moldura comum a todos os campos do formulário (altura, raio, borda, fundo),
// para os números do topo, ingredientes e passos lerem como um só sistema.
const FIELD_FRAME =
  'min-h-11 rounded-xl border border-black/10 bg-bg-sage text-sm ring-2 ring-transparent transition-shadow'

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
    initial?.image_path ? recipeImageUrl(initial.image_path, 'medium') : null,
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
  const [managingCategories, setManagingCategories] = useState(false)
  const [categoryError, setCategoryError] = useState('')

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
      const created = await createCategory(name, DEFAULT_CATEGORY_COLOR, 'main')
      setCategories((cats) => [...cats, created])
      setCategoryIds((ids) => [...ids, created.id])
    }
    setNewCategoryName('')
  }

  async function changeCategoryVisual(category: Category, patch: { color?: string | null; icon?: CategoryIcon | null }) {
    setCategoryError('')
    try {
      const updated = await updateCategory(category.id, patch)
      setCategories((current) => current.map((item) => item.id === updated.id ? updated : item))
    } catch {
      setCategoryError(t('Não foi possível guardar a categoria.'))
    }
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
      setEstimateError(t('Não foi possível pedir a estimativa agora. Tenta de novo daqui a pouco.'))
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
      setError(t('Não foi possível guardar a receita.'))
      setSaving(false)
    }
  }

  const fieldFocus = 'outline-none focus:border-accent-leaf focus:ring-accent-leaf/30'
  const fieldClass = `${FIELD_FRAME} px-3 py-2 ${fieldFocus}`
  const compactFieldClass = `${FIELD_FRAME} px-2.5 py-2 ${fieldFocus}`
  const removeRowClass = 'flex w-9 shrink-0 items-center justify-center rounded-xl text-text-secondary hover:bg-bg-sage'

  return (
    <>
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
                {t('Trocar foto')}
              </span>
            </>
          ) : (
            <span className="flex flex-col items-center gap-1.5">
              <CameraIcon className="size-6" />
              <span className="text-sm font-medium">{t('Adicionar foto')}</span>
            </span>
          )}
        </button>

        <label className="mt-4 block text-sm font-medium text-text-secondary" htmlFor="title">
          {t('Título')}
        </label>
        <input
          id="title"
          required
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className={`${fieldClass} w-full mt-1`}
          placeholder={t('Ex.: Bacalhau à Brás')}
        />

        <label className="mt-4 block text-sm font-medium text-text-secondary" htmlFor="description">
          {t('Descrição')}
        </label>
        <textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className={`${fieldClass} w-full mt-1`}
          rows={2}
        />

        <div className="mt-4 grid grid-cols-3 gap-2 sm:gap-3">
          <div>
            <label className="block text-sm font-medium text-text-secondary" htmlFor="servings">
              {t('Porções')}
            </label>
            <input
              id="servings"
              type="number"
              min={0}
              value={servings}
              onChange={(e) => setServings(e.target.value)}
              className={`${fieldClass} mt-1 w-full`}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-secondary" htmlFor="prep">
              {t('Preparação')}<span className="sr-only"> (min)</span>
            </label>
            <UnitInput
              id="prep"
              type="number"
              min={0}
              value={prepMinutes}
              onChange={(e) => setPrepMinutes(e.target.value)}
              unit="min"
              className="mt-1 w-full"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-secondary" htmlFor="cook">
              {t('Confeção')}<span className="sr-only"> (min)</span>
            </label>
            <UnitInput
              id="cook"
              type="number"
              min={0}
              value={cookMinutes}
              onChange={(e) => setCookMinutes(e.target.value)}
              unit="min"
              className="mt-1 w-full"
            />
          </div>
        </div>

        <label className="mt-4 block text-sm font-medium text-text-secondary" htmlFor="source">
          {t('Fonte (opcional)')}
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
          {t('Custo estimado da receita (€, opcional)')}
        </label>
        <input
          id="cost"
          type="number"
          min={0}
          step="0.01"
          value={estimatedCost}
          onChange={(e) => setEstimatedCost(e.target.value)}
          className={`${fieldClass} w-full mt-1`}
          placeholder={t('Ex.: 8.50')}
        />

        <label className="mt-4 block text-sm font-medium text-text-secondary" htmlFor="notes">
          {t('Notas')}
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
        <h2 className="text-lg font-semibold text-text-primary">{t('Ingredientes')}</h2>
        <div className="mt-3 space-y-2">
          {ingredients.map((row, i) =>
            row.isHeader ? (
              <div key={i} className="flex gap-2">
                <input
                  value={row.name}
                  onChange={(e) => updateIngredient(i, { name: e.target.value })}
                  placeholder={t('Nome da secção, ex.: Para o recheio')}
                  className={`${fieldClass} w-full font-semibold`}
                />
                <button
                  type="button"
                  onClick={() => removeIngredient(i)}
                  className={removeRowClass}
                  aria-label={t('Remover secção')}
                >
                  <XIcon className="size-4" />
                </button>
              </div>
            ) : (
              <div key={i} className="flex gap-2">
                <input
                  value={row.quantity}
                  onChange={(e) => updateIngredient(i, { quantity: e.target.value })}
                  placeholder={t('qtd')}
                  inputMode="decimal"
                  aria-label={t('Quantidade do ingrediente {number}', { number: i + 1 })}
                  className={`${compactFieldClass} w-14 shrink-0 sm:w-16`}
                />
                <input
                  value={row.unit}
                  onChange={(e) => updateIngredient(i, { unit: e.target.value })}
                  placeholder={t('unidade')}
                  aria-label={t('Unidade do ingrediente {number}', { number: i + 1 })}
                  className={`${compactFieldClass} w-[4.75rem] shrink-0 sm:w-24`}
                />
                <input
                  value={row.name}
                  onChange={(e) => updateIngredient(i, { name: e.target.value })}
                  placeholder={t('ingrediente')}
                  aria-label={t('Nome do ingrediente {number}', { number: i + 1 })}
                  className={`${fieldClass} min-w-0 flex-1`}
                />
                <button
                  type="button"
                  onClick={() => removeIngredient(i)}
                  className={removeRowClass}
                  aria-label={t('Remover ingrediente')}
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
            {t('Adicionar ingrediente')}
          </button>
          <button
            type="button"
            onClick={() => setIngredients((rows) => [...rows, { name: '', quantity: '', unit: '', isHeader: true }])}
            className="flex items-center gap-1 text-sm font-medium text-text-secondary"
          >
            <PlusIcon className="size-4" />
            {t('Adicionar cabeçalho de secção')}
          </button>
        </div>
      </div>

      <div className="rounded-2xl bg-surface p-5 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]">
        <h2 className="text-lg font-semibold text-text-primary">{t('Preparação')}</h2>
        <div className="mt-3 space-y-2">
          {steps.map((row, i) => (
            <div key={i} className="flex gap-2">
              <span className="mt-2.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-bg-sage text-xs font-semibold text-forest-text">
                {i + 1}
              </span>
              <textarea
                value={row.instruction}
                onChange={(e) => updateStep(i, { instruction: e.target.value })}
                placeholder={t('Passo {number}', { number: i + 1 })}
                aria-label={t('Passo {number}', { number: i + 1 })}
                rows={1}
                className={`${fieldClass} min-w-0 flex-1 field-sizing-content`}
              />
              <UnitInput
                value={row.durationMinutes}
                onChange={(e) => updateStep(i, { durationMinutes: e.target.value })}
                type="number"
                min={0}
                unit="min"
                aria-label={t('Duração do passo {number} em minutos', { number: i + 1 })}
                className="w-[4.5rem] shrink-0 self-start sm:w-24"
              />
              <button
                type="button"
                onClick={() => removeStep(i)}
                className={`${removeRowClass} h-11`}
                aria-label={t('Remover passo')}
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
          {t('Adicionar passo')}
        </button>
      </div>

      <div className="rounded-2xl bg-surface p-5 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]">
        <h2 className="text-lg font-semibold text-text-primary">{t('Categorias e tags')}</h2>

        <div className="mt-3 flex items-center justify-between gap-3">
          <p className="text-sm font-medium text-text-secondary">{t('Categorias')}</p>
          {categories.length > 0 && (
            <button
              type="button"
              onClick={() => setManagingCategories(true)}
              aria-haspopup="dialog"
              className="-my-2 min-h-11 px-1 text-sm font-medium text-forest-text"
            >
              {t('Gerir categorias')}
            </button>
          )}
        </div>
        <div className="mt-1.5 flex flex-wrap items-center gap-2">
          {categories.map((c) => (
            <Chip key={c.id} kind="category" accentColor={c.color} icon={c.icon} active={categoryIds.includes(c.id)} onClick={() => toggleCategory(c.id)}>{c.name}</Chip>
          ))}
          <InlineAdd value={newCategoryName} onChange={setNewCategoryName} onAdd={addNewCategory} placeholder={t('nova categoria')} />
        </div>

        <p className="mt-5 text-sm font-medium text-text-secondary">{t('Tags')}</p>
        <div className="mt-1.5 flex flex-wrap items-center gap-2">
          {tags.map((tag) => (
            <Chip key={tag.id} kind="tag" active={tagIds.includes(tag.id)} onClick={() => toggleTag(tag.id)}>#{tag.name}</Chip>
          ))}
          <InlineAdd value={newTagName} onChange={setNewTagName} onAdd={addNewTag} placeholder={t('nova tag')} />
        </div>
      </div>

      <div className="rounded-2xl bg-surface p-5 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]">
        <h2 className="text-lg font-semibold text-text-primary">{t('Informação nutricional')}</h2>
        <p className="mt-1 text-xs text-text-secondary">{t('Por porção, opcional e à mão.')}</p>

        <button
          type="button"
          onClick={handleEstimateNutrition}
          disabled={estimating}
          className="mt-3 flex items-center gap-1 text-sm font-medium text-forest-text disabled:opacity-50"
        >
          {estimating ? t('A estimar…') : t('Estimar a partir dos ingredientes (Open Food Facts)')}
        </button>

        {estimateError && (
          <div className="mt-2 rounded-xl bg-bg-sage p-3 text-sm text-text-secondary">{estimateError}</div>
        )}

        {nutritionEstimate && (
          <div className="mt-2 rounded-xl bg-bg-sage p-3 text-sm">
            {nutritionEstimate.matched_count === 0 ? (
              <p className="text-text-secondary">
                {t('Não foi possível estimar — nenhum ingrediente entrou na conta. Podes sempre preencher à mão.')}
              </p>
            ) : (
              <>
                <p className="text-text-primary">
                  {t('Estimativa (')}{nutritionEstimate.matched_count} {t('de')}{' '}
                  {nutritionEstimate.matched_count + nutritionEstimate.skipped_count} {t('ingredientes):')} {nutritionEstimate.calories_kcal}{' '}
                  {t('kcal ·')} {nutritionEstimate.protein_g}{t('g proteína ·')} {nutritionEstimate.carbs_g}{t('g hidratos ·')}{' '}
                  {nutritionEstimate.fat_g}{t('g gordura')} </p>
                <p className="mt-1 text-xs text-text-secondary">
                  {t('Aproximada — nem todos os ingredientes/unidades entram na conta, nunca substitui os campos abaixo sem confirmares.')}
                </p>
              </>
            )}
            {nutritionEstimate.skipped_ingredients.length > 0 && (
              <ul className="mt-2 space-y-0.5 text-xs text-text-secondary">
                {nutritionEstimate.skipped_ingredients.map((s, i) => (
                  <li key={i}>
                    {s.name}: {s.reason === OFF_UNAVAILABLE_REASON ? t('a Open Food Facts pode estar em baixo') : s.reason}
                  </li>
                ))}
              </ul>
            )}
            {nutritionEstimate.matched_count > 0 && (
              <div className="mt-2 flex gap-3">
                <button type="button" onClick={applyNutritionEstimate} className="text-sm font-medium text-forest-text">
                  {t('Aplicar')}
                </button>
                <button
                  type="button"
                  onClick={() => setNutritionEstimate(null)}
                  className="text-sm font-medium text-text-secondary"
                >
                  {t('Descartar')}
                </button>
              </div>
            )}
          </div>
        )}

        {nutritionStale && (
          <p className="mt-2 text-xs text-text-secondary">
            {t('Alteraste ingredientes ou porções desde a última estimativa aplicada — os valores abaixo podem estar desactualizados.')}
          </p>
        )}

        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div>
            <label className="block text-sm font-medium text-text-secondary" htmlFor="calories">
              {t('Calorias (kcal)')}
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
              {t('Proteína (g)')}
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
              {t('Hidratos (g)')}
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
              {t('Gordura (g)')}
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
        {saving ? t('A guardar…') : submitLabel}
      </button>
    </form>

    {/* Fora do <form>: os botões do Modal não têm type e submeteriam a receita. */}
    <Modal open={managingCategories} title={t('Gerir categorias')} onClose={() => setManagingCategories(false)}>
      <p className="text-sm text-text-secondary">{t('A cor e o ícone aplicam-se à categoria em todas as receitas.')}</p>
      <ul className="mt-3 max-h-[55svh] space-y-2 overflow-y-auto">
        {categories.map((c) => (
          <li key={c.id} className="flex flex-wrap items-center gap-2 rounded-xl border border-border p-2">
            <span className="w-full min-w-0 sm:w-auto sm:flex-1"><CategoryBadge color={c.color} icon={c.icon} className="max-w-full">{c.name}</CategoryBadge></span>
            <input
              type="color"
              value={c.color ?? DEFAULT_CATEGORY_COLOR}
              onChange={(event) => changeCategoryVisual(c, { color: event.target.value })}
              aria-label={t('Cor de {name}', { name: c.name })}
              className="h-11 w-11 shrink-0 cursor-pointer rounded-xl border border-border bg-surface p-1"
            />
            <select
              value={c.icon ?? ''}
              onChange={(event) => changeCategoryVisual(c, { icon: (event.target.value || null) as CategoryIcon | null })}
              aria-label={t('Ícone de {name}', { name: c.name })}
              className="h-11 min-w-0 flex-1 rounded-xl border border-border bg-surface px-2 text-sm text-text-primary sm:w-40 sm:flex-none"
            >
              <option value="">{t('Sem ícone')}</option>
              {CATEGORY_ICON_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.symbol} {t(option.label)}</option>)}
            </select>
          </li>
        ))}
      </ul>
      {categoryError && <p role="alert" className="mt-2 text-sm text-accent-orange">{categoryError}</p>}
    </Modal>
    </>
  )
}

function UnitInput({ unit, className = '', ...props }: InputHTMLAttributes<HTMLInputElement> & { unit: string }) {
  return (
    <span className={`${FIELD_FRAME} flex items-center pr-3 focus-within:border-accent-leaf focus-within:ring-accent-leaf/30 ${className}`}>
      <input className="min-w-0 flex-1 bg-transparent py-2 pl-3 pr-1 outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none" {...props} />
      <span aria-hidden="true" className="shrink-0 text-text-secondary">{unit}</span>
    </span>
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
    <span className="inline-flex min-h-10 items-center rounded-xl border border-dashed border-border bg-surface ring-2 ring-transparent transition-shadow focus-within:border-accent-leaf focus-within:ring-accent-leaf/30">
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
        aria-label={placeholder}
        className="w-32 bg-transparent py-2 pl-3 text-sm text-text-primary outline-none placeholder:text-text-secondary"
      />
      <button
        type="button"
        onClick={onAdd}
        disabled={!value.trim()}
        className="flex size-10 shrink-0 items-center justify-center rounded-r-xl text-forest-text hover:bg-bg-sage disabled:text-text-secondary disabled:opacity-60"
        aria-label={t('Adicionar {name}', { name: placeholder })}
      >
        <PlusIcon className="size-4" />
      </button>
    </span>
  )
}
