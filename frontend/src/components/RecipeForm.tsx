import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { createCategory, createTag, listCategories, listTags, recipeImageUrl } from '../api/recipes'
import type { Category, Recipe, RecipeInput, Tag } from '../api/types'
import { CameraIcon, PlusIcon, XIcon } from './icons'

interface IngredientRow {
  name: string
  quantity: string
  unit: string
  isHeader: boolean
}

interface StepRow {
  instruction: string
}

function toIngredientRows(recipe?: Recipe): IngredientRow[] {
  if (!recipe || recipe.ingredients.length === 0) return [{ name: '', quantity: '', unit: '', isHeader: false }]
  return recipe.ingredients.map((i) => ({
    name: i.name,
    quantity: i.quantity?.toString() ?? '',
    unit: i.unit ?? '',
    isHeader: i.is_header,
  }))
}

function toStepRows(recipe?: Recipe): StepRow[] {
  if (!recipe || recipe.steps.length === 0) return [{ instruction: '' }]
  return recipe.steps.map((s) => ({ instruction: s.instruction }))
}

export function RecipeForm({
  initial,
  onSubmit,
  submitLabel,
}: {
  initial?: Recipe
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
  const [categoryIds, setCategoryIds] = useState<string[]>(initial?.categories.map((c) => c.id) ?? [])
  const [tagIds, setTagIds] = useState<string[]>(initial?.tags.map((t) => t.id) ?? [])
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

  function updateStep(index: number, instruction: string) {
    setSteps((rows) => rows.map((row, i) => (i === index ? { instruction } : row)))
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
            .map((row) => ({ instruction: row.instruction.trim() })),
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
    'w-full rounded-xl border border-black/10 bg-bg-sage px-3 py-2 text-sm outline-none ring-2 ring-transparent transition-shadow focus:border-accent-leaf focus:ring-accent-leaf/30'

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="rounded-2xl bg-card-white p-5 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]">
        <input
          ref={imageInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          capture="environment"
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
          className={`${fieldClass} mt-1`}
          placeholder="Ex.: Bacalhau à Brás"
        />

        <label className="mt-4 block text-sm font-medium text-text-secondary" htmlFor="description">
          Descrição
        </label>
        <textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className={`${fieldClass} mt-1`}
          rows={2}
        />

        <div className="mt-4 grid grid-cols-3 gap-3">
          <div>
            <label className="block text-sm font-medium text-text-secondary" htmlFor="servings">
              Porções
            </label>
            <input
              id="servings"
              type="number"
              min={0}
              value={servings}
              onChange={(e) => setServings(e.target.value)}
              className={`${fieldClass} mt-1`}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-secondary" htmlFor="prep">
              Preparação (min)
            </label>
            <input
              id="prep"
              type="number"
              min={0}
              value={prepMinutes}
              onChange={(e) => setPrepMinutes(e.target.value)}
              className={`${fieldClass} mt-1`}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-secondary" htmlFor="cook">
              Confeção (min)
            </label>
            <input
              id="cook"
              type="number"
              min={0}
              value={cookMinutes}
              onChange={(e) => setCookMinutes(e.target.value)}
              className={`${fieldClass} mt-1`}
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
          className={`${fieldClass} mt-1`}
          placeholder="https://…"
        />

        <label className="mt-4 block text-sm font-medium text-text-secondary" htmlFor="notes">
          Notas
        </label>
        <textarea
          id="notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className={`${fieldClass} mt-1`}
          rows={2}
        />
      </div>

      <div className="rounded-2xl bg-card-white p-5 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]">
        <h2 className="text-lg font-semibold text-text-primary">Ingredientes</h2>
        <div className="mt-3 space-y-2">
          {ingredients.map((row, i) =>
            row.isHeader ? (
              <div key={i} className="flex gap-2">
                <input
                  value={row.name}
                  onChange={(e) => updateIngredient(i, { name: e.target.value })}
                  placeholder="Nome da secção, ex.: Para o recheio"
                  className={`${fieldClass} font-semibold`}
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
                  className={`${fieldClass} w-16`}
                />
                <input
                  value={row.unit}
                  onChange={(e) => updateIngredient(i, { unit: e.target.value })}
                  placeholder="unidade"
                  className={`${fieldClass} w-24`}
                />
                <input
                  value={row.name}
                  onChange={(e) => updateIngredient(i, { name: e.target.value })}
                  placeholder="ingrediente"
                  className={fieldClass}
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
            className="flex items-center gap-1 text-sm font-medium text-primary-forest"
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

      <div className="rounded-2xl bg-card-white p-5 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]">
        <h2 className="text-lg font-semibold text-text-primary">Preparação</h2>
        <div className="mt-3 space-y-2">
          {steps.map((row, i) => (
            <div key={i} className="flex gap-2">
              <span className="mt-2 flex size-6 shrink-0 items-center justify-center rounded-full bg-bg-sage text-xs font-semibold text-primary-forest">
                {i + 1}
              </span>
              <textarea
                value={row.instruction}
                onChange={(e) => updateStep(i, e.target.value)}
                placeholder={`Passo ${i + 1}`}
                rows={1}
                className={fieldClass}
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
          onClick={() => setSteps((rows) => [...rows, { instruction: '' }])}
          className="mt-3 flex items-center gap-1 text-sm font-medium text-primary-forest"
        >
          <PlusIcon className="size-4" />
          Adicionar passo
        </button>
      </div>

      <div className="rounded-2xl bg-card-white p-5 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]">
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
