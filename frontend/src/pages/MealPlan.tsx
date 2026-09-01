import { useEffect, useState } from 'react'
import { applyMealPlanTemplate, assignMealPlanEntry, copyMealPlanWeek, createMealPlanRecurrence, listMealPlan, listMealPlanTemplates, removeMealPlanEntry, saveMealPlanTemplate, suggestMealPlan } from '../api/planning'
import { listRecipes, recipeImageUrl } from '../api/recipes'
import type { MealPlanEntry, MealPlanSuggestionItem, MealPlanTemplate, MealType, RecipeSummary } from '../api/types'
import { PageShell } from '../components/PageShell'
import { ChevronLeftIcon, PlusIcon, XIcon } from '../components/icons'
import { Modal, SearchInput } from '../components/ui'
import { addDays, formatDayShort, formatWeekRange, startOfWeek, toDateKey, weekdayLabel } from '../lib/date'

const MEALS: { key: MealType; label: string }[] = [
  { key: 'pequeno_almoco', label: 'Pequeno-almoço' },
  { key: 'almoco', label: 'Almoço' },
  { key: 'lanche', label: 'Lanche' },
  { key: 'jantar', label: 'Jantar' },
]

export function MealPlan() {
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date()))
  const [entries, setEntries] = useState<MealPlanEntry[]>([])
  const [recipes, setRecipes] = useState<RecipeSummary[]>([])
  const [error, setError] = useState(false)
  const [templates, setTemplates] = useState<MealPlanTemplate[]>([])
  const [selectedTemplateId, setSelectedTemplateId] = useState('')
  const [planFeedback, setPlanFeedback] = useState('')
  const [planActionBusy, setPlanActionBusy] = useState(false)
  const [suggestions, setSuggestions] = useState<MealPlanSuggestionItem[]>([])
  const [suggestionOpen, setSuggestionOpen] = useState(false)
  const [suggestionBusy, setSuggestionBusy] = useState(false)
  const [draggedMeal, setDraggedMeal] = useState<{ day: string; meal: MealType; recipeId: string } | null>(null)

  useEffect(() => { listRecipes().then(setRecipes).catch(() => {}) }, [])
  useEffect(() => { listMealPlanTemplates().then(setTemplates).catch(() => {}) }, [])
  useEffect(() => {
    listMealPlan(toDateKey(weekStart), toDateKey(addDays(weekStart, 6)))
      .then((loadedEntries) => {
        setEntries(loadedEntries)
        setError(false)
      })
      .catch(() => setError(true))
  }, [weekStart])

  function entryFor(day: string, mealType: MealType) { return entries.find((entry) => entry.day === day && entry.meal_type === mealType) }
  async function assign(day: string, meal: MealType, recipeId: string) {
    if (!recipeId) return
    const entry = await assignMealPlanEntry(day, meal, recipeId)
    setEntries((current) => [...current.filter((item) => !(item.day === day && item.meal_type === meal)), entry])
  }
  async function remove(day: string, meal: MealType) {
    await removeMealPlanEntry(day, meal)
    setEntries((current) => current.filter((item) => !(item.day === day && item.meal_type === meal)))
  }
  async function moveMeal(targetDay: string, targetMeal: MealType) {
    if (!draggedMeal || (draggedMeal.day === targetDay && draggedMeal.meal === targetMeal)) return
    try {
      await assign(targetDay, targetMeal, draggedMeal.recipeId)
      await remove(draggedMeal.day, draggedMeal.meal)
    } catch {
      setError(true)
    } finally {
      setDraggedMeal(null)
    }
  }

  const days = Array.from({ length: 7 }, (_, index) => addDays(weekStart, index))
  const todayKey = toDateKey(new Date())

  function goToCurrentWeek() {
    const today = new Date()
    setWeekStart(startOfWeek(today))
  }

  async function copyPreviousWeek() {
    setPlanActionBusy(true)
    try {
      const currentKey = toDateKey(weekStart)
      setEntries(await copyMealPlanWeek(toDateKey(addDays(weekStart, -7)), currentKey))
      setPlanFeedback('Semana anterior copiada. As refeições existentes foram preservadas.')
    } catch {
      setPlanFeedback('Não foi possível copiar a semana anterior.')
    } finally {
      setPlanActionBusy(false)
    }
  }

  async function saveCurrentWeekAsTemplate() {
    const name = window.prompt('Nome do modelo semanal:')?.trim()
    if (!name) return
    setPlanActionBusy(true)
    try {
      const template = await saveMealPlanTemplate(name, toDateKey(weekStart))
      setTemplates((current) => [...current.filter((item) => item.id !== template.id), template].sort((a, b) => a.name.localeCompare(b.name, 'pt-PT')))
      setSelectedTemplateId(template.id)
      setPlanFeedback(`Modelo “${template.name}” guardado.`)
    } catch {
      setPlanFeedback('Não foi possível guardar o modelo.')
    } finally {
      setPlanActionBusy(false)
    }
  }

  async function applySelectedTemplate() {
    if (!selectedTemplateId) return
    setPlanActionBusy(true)
    try {
      setEntries(await applyMealPlanTemplate(selectedTemplateId, toDateKey(weekStart)))
      setPlanFeedback('Modelo aplicado. As refeições existentes foram preservadas.')
    } catch {
      setPlanFeedback('Não foi possível aplicar o modelo.')
    } finally {
      setPlanActionBusy(false)
    }
  }

  async function previewSuggestions() {
    setSuggestionBusy(true)
    setPlanFeedback('')
    try {
      setSuggestions(await suggestMealPlan(toDateKey(weekStart)))
      setSuggestionOpen(true)
    } catch {
      setPlanFeedback('Não foi possível criar uma sugestão para esta semana.')
    } finally {
      setSuggestionBusy(false)
    }
  }

  async function applySuggestions() {
    setSuggestionBusy(true)
    try {
      for (const suggestion of suggestions) {
        await assign(suggestion.day, suggestion.meal_type, suggestion.recipe.id)
      }
      setSuggestionOpen(false)
      setPlanFeedback(`${suggestions.length} sugestões adicionadas ao planeamento.`)
    } catch {
      setPlanFeedback('A sugestão foi aplicada apenas parcialmente. Confirma os espaços antes de tentar novamente.')
      setSuggestionOpen(false)
    } finally {
      setSuggestionBusy(false)
    }
  }

  return <PageShell wide>
    <div className="flex flex-wrap items-center justify-between gap-4">
      <div><h1 className="text-2xl font-bold tracking-tight text-text-primary sm:text-3xl">Planeamento de Refeições</h1><p className="mt-1 text-sm text-text-secondary">Organiza todas as refeições da semana.</p></div>
      <WeekNavigation label={formatWeekRange(weekStart)} previous={() => setWeekStart((date) => addDays(date, -7))} next={() => setWeekStart((date) => addDays(date, 7))} current={goToCurrentWeek} />
    </div>
    {error && <p role="alert" className="mt-5 rounded-xl border border-danger/20 bg-danger/5 p-4 text-sm text-text-secondary">Não foi possível carregar o planeamento.</p>}
    <div className="mt-5 flex flex-wrap items-end gap-2 rounded-2xl border border-border bg-surface p-3"><button type="button" disabled={planActionBusy || suggestionBusy} onClick={previewSuggestions} className="min-h-10 rounded-xl bg-primary-forest px-4 text-sm font-semibold text-white disabled:opacity-50">{suggestionBusy ? 'A preparar…' : 'Sugerir semana'}</button><button type="button" disabled={planActionBusy} onClick={copyPreviousWeek} className="min-h-10 rounded-xl border border-border px-3 text-sm font-semibold text-forest-text disabled:opacity-50">Copiar semana anterior</button><button type="button" disabled={planActionBusy} onClick={saveCurrentWeekAsTemplate} className="min-h-10 rounded-xl border border-border px-3 text-sm font-semibold text-forest-text disabled:opacity-50">Guardar como modelo</button><label className="min-w-48 flex-1 text-xs font-semibold text-text-secondary">Modelo semanal<select value={selectedTemplateId} onChange={(event) => setSelectedTemplateId(event.target.value)} className="mt-1 min-h-10 w-full rounded-xl border border-border bg-surface px-3 text-sm text-text-primary"><option value="">Escolher modelo…</option>{templates.map((template) => <option key={template.id} value={template.id}>{template.name} ({template.slots.length} refeições)</option>)}</select></label><button type="button" disabled={!selectedTemplateId || planActionBusy} onClick={applySelectedTemplate} className="min-h-10 rounded-xl bg-primary-forest px-4 text-sm font-semibold text-white disabled:opacity-50">Aplicar</button></div>
    {planFeedback && <p role="status" className="mt-2 text-sm text-text-secondary">{planFeedback}</p>}

    <div className="mt-6 space-y-6 lg:hidden">
      {days.map((day, dayIndex) => {
        const dayKey = toDateKey(day)
        const isToday = dayKey === todayKey
        return <section key={dayKey} className={`rounded-2xl border p-3 ${isToday ? 'border-primary-forest bg-primary-soft/40' : 'border-border bg-muted/30'}`}><h2 className="mb-3 flex items-baseline justify-between gap-3 px-1 text-lg font-bold text-text-primary"><span>{weekdayLabel(dayIndex)}</span><span className={`text-sm font-semibold ${isToday ? 'text-forest-text' : 'text-text-secondary'}`}>{isToday ? 'Hoje · ' : ''}{formatDayShort(day)}</span></h2><div className="space-y-3">{MEALS.map((meal) => <MobileMeal key={meal.key} label={meal.label} entry={entryFor(dayKey, meal.key)} recipes={recipes} days={days} onAssign={(id) => assign(dayKey, meal.key, id)} onRepeat={(targetDay, targetMeal, recipeId) => assign(targetDay, targetMeal, recipeId)} onRemove={() => remove(dayKey, meal.key)} />)}</div></section>
      })}
    </div>

    <div className="mt-7 hidden overflow-hidden rounded-2xl border border-border bg-surface lg:block">
      <div className="grid grid-cols-[120px_repeat(7,minmax(110px,1fr))] border-b border-border bg-muted/70">
        <div className="p-4" />
        {days.map((day, index) => <div key={toDateKey(day)} className={`border-l border-border p-3 text-center ${toDateKey(day) === todayKey ? 'bg-primary-soft' : ''}`}><p className="text-xs font-bold uppercase tracking-wide text-text-secondary">{weekdayLabel(index).slice(0, 3)}</p><p className="mt-0.5 text-sm font-semibold text-text-primary">{formatDayShort(day)}</p></div>)}
      </div>
      {MEALS.map((meal) => <div key={meal.key} className="grid min-h-36 grid-cols-[120px_repeat(7,minmax(110px,1fr))] border-b border-border last:border-0"><div className="p-4 text-sm font-bold text-text-primary">{meal.label}</div>{days.map((day) => { const dayKey = toDateKey(day); return <DesktopMeal key={dayKey} entry={entryFor(dayKey, meal.key)} recipes={recipes} days={days} isDragging={draggedMeal !== null} onAssign={(id) => assign(dayKey, meal.key, id)} onRepeat={(targetDay, targetMeal, recipeId) => assign(targetDay, targetMeal, recipeId)} onRemove={() => remove(dayKey, meal.key)} onDragStart={(recipeId) => setDraggedMeal({ day: dayKey, meal: meal.key, recipeId })} onDragEnd={() => setDraggedMeal(null)} onDrop={() => moveMeal(dayKey, meal.key)} /> })}</div>)}
    </div>
    <Modal open={suggestionOpen} title="Sugestão para a semana" onClose={() => !suggestionBusy && setSuggestionOpen(false)}>
      <p className="text-sm text-text-secondary">Revê a proposta antes de a aplicar. Podes retirar refeições; os espaços já ocupados não são alterados.</p>
      {suggestions.length > 0 ? <div className="mt-4 max-h-[55svh] space-y-2 overflow-y-auto pr-1">{suggestions.map((suggestion) => {
        const suggestionDate = new Date(`${suggestion.day}T00:00:00`)
        const mealLabel = MEALS.find((meal) => meal.key === suggestion.meal_type)?.label ?? suggestion.meal_type
        return <div key={`${suggestion.day}-${suggestion.meal_type}`} className="flex items-center gap-3 rounded-xl border border-border p-2"><RecipePhoto recipe={suggestion.recipe} className="size-16 shrink-0 rounded-lg" /><div className="min-w-0 flex-1"><p className="font-semibold text-text-primary">{suggestion.recipe.title}</p><p className="text-xs text-text-secondary">{weekdayLabel((suggestionDate.getDay() + 6) % 7)}, {formatDayShort(suggestionDate)} · {mealLabel}</p></div><button type="button" onClick={() => setSuggestions((current) => current.filter((item) => item !== suggestion))} disabled={suggestionBusy} aria-label={`Retirar ${suggestion.recipe.title} da sugestão`} className="flex size-9 shrink-0 items-center justify-center rounded-xl text-text-secondary hover:bg-muted"><XIcon className="size-5" /></button></div>
      })}</div> : <p className="mt-6 rounded-xl bg-muted p-4 text-center text-sm text-text-secondary">Não há espaços livres para sugerir almoços ou jantares nesta semana.</p>}
      <div className="mt-5 flex justify-end gap-2"><button type="button" disabled={suggestionBusy} onClick={() => setSuggestionOpen(false)} className="min-h-11 rounded-xl border border-border px-4 text-sm font-semibold text-text-primary">Cancelar</button><button type="button" disabled={suggestionBusy || suggestions.length === 0} onClick={applySuggestions} className="min-h-11 rounded-xl bg-primary-forest px-4 text-sm font-semibold text-white disabled:opacity-50">{suggestionBusy ? 'A aplicar…' : `Aplicar ${suggestions.length} sugestões`}</button></div>
    </Modal>
  </PageShell>
}

function WeekNavigation({ label, previous, next, current }: { label: string; previous: () => void; next: () => void; current: () => void }) {
  return <div className="flex flex-wrap items-center justify-end gap-2"><button onClick={current} className="min-h-10 rounded-xl border border-border bg-surface px-3 text-sm font-semibold text-forest-text hover:bg-primary-soft">Hoje</button><div className="flex items-center gap-1 rounded-xl border border-border bg-surface p-1"><button onClick={previous} className="flex size-10 items-center justify-center rounded-lg text-text-secondary hover:bg-muted" aria-label="Semana anterior"><ChevronLeftIcon className="size-5" /></button><span className="min-w-32 text-center text-sm font-semibold text-text-primary">{label}</span><button onClick={next} className="flex size-10 items-center justify-center rounded-lg text-text-secondary hover:bg-muted" aria-label="Semana seguinte"><ChevronLeftIcon className="size-5 rotate-180" /></button></div></div>
}

function RecipePicker({ recipes, onAssign, variant = 'add' }: { recipes: RecipeSummary[]; onAssign: (id: string) => void; variant?: 'add' | 'replace' }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [saving, setSaving] = useState(false)
  const [pickerError, setPickerError] = useState(false)
  const filteredRecipes = recipes.filter((recipe) => recipe.title.toLocaleLowerCase('pt-PT').includes(query.trim().toLocaleLowerCase('pt-PT')))

  async function choose(recipeId: string) {
    setSaving(true)
    setPickerError(false)
    try {
      await onAssign(recipeId)
      setOpen(false)
      setQuery('')
    } catch {
      setPickerError(true)
    } finally {
      setSaving(false)
    }
  }

  const triggerClass = variant === 'replace'
    ? 'rounded-lg bg-white/90 px-2.5 py-1.5 text-xs font-semibold text-neutral-700 shadow-sm hover:bg-white'
    : 'flex min-h-11 w-full items-center justify-center gap-1.5 rounded-xl border border-dashed border-border text-xs font-semibold text-text-secondary hover:border-primary-forest hover:bg-primary-soft hover:text-forest-text'
  return <><button type="button" onClick={() => setOpen(true)} className={triggerClass}>{variant === 'add' && <PlusIcon className="size-4" />}<span>{variant === 'replace' ? 'Trocar' : 'Adicionar'}</span></button><Modal open={open} title={variant === 'replace' ? 'Trocar receita' : 'Escolher receita'} onClose={() => setOpen(false)}><SearchInput value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Pesquisar receitas…" autoFocus /><div className="mt-4 grid max-h-[55svh] grid-cols-2 gap-3 overflow-y-auto pr-1">{filteredRecipes.map((recipe) => <button type="button" key={recipe.id} disabled={saving} onClick={() => choose(recipe.id)} className="overflow-hidden rounded-xl border border-border bg-surface text-left transition hover:border-primary-forest hover:shadow-md disabled:opacity-60"><RecipePhoto recipe={recipe} className="h-24 w-full rounded-none" /><span className="block p-2.5 text-sm font-semibold leading-snug text-text-primary">{recipe.title}</span></button>)}</div>{recipes.length === 0 && <p className="py-8 text-center text-sm text-text-secondary">Ainda não existem receitas para adicionar.</p>}{recipes.length > 0 && filteredRecipes.length === 0 && <p className="py-8 text-center text-sm text-text-secondary">Nenhuma receita encontrada.</p>}{pickerError && <p role="alert" className="mt-3 text-sm text-danger">Não foi possível adicionar esta receita.</p>}</Modal></>
}

function RecipePhoto({ recipe, className = '' }: { recipe: RecipeSummary; className?: string }) {
  return recipe.image_path
    ? <img src={recipeImageUrl(recipe.image_path)} alt="" className={`object-cover ${className}`} />
    : <div aria-hidden="true" className={`flex items-center justify-center bg-primary-soft text-2xl text-forest-text/40 ${className}`}>♨</div>
}

function RepeatMeal({ recipe, days, onRepeat }: { recipe: RecipeSummary; days: Date[]; onRepeat: (day: string, meal: MealType, recipeId: string) => Promise<void> }) {
  const [open, setOpen] = useState(false)
  const [target, setTarget] = useState(`${toDateKey(days[0])}|almoco`)
  const [saving, setSaving] = useState(false)
  const [repeatError, setRepeatError] = useState(false)
  const [recurring, setRecurring] = useState(false)
  const [intervalWeeks, setIntervalWeeks] = useState(1)
  const [endsOn, setEndsOn] = useState('')

  async function repeat() {
    const [day, meal] = target.split('|') as [string, MealType]
    setSaving(true)
    setRepeatError(false)
    try {
      await onRepeat(day, meal, recipe.id)
      if (recurring) {
        const selectedDate = new Date(`${day}T00:00:00`)
        await createMealPlanRecurrence(recipe.id, (selectedDate.getDay() + 6) % 7, meal, day, intervalWeeks, endsOn || null)
      }
      setOpen(false)
    } catch {
      setRepeatError(true)
    } finally {
      setSaving(false)
    }
  }

  return <><button type="button" onClick={() => setOpen(true)} className="rounded-lg bg-white/90 px-2.5 py-1.5 text-xs font-semibold text-neutral-700 shadow-sm hover:bg-white">Repetir</button><Modal open={open} title={`Repetir ${recipe.title}`} onClose={() => setOpen(false)}><label className="block text-sm font-medium text-text-primary">Destino<select value={target} onChange={(event) => setTarget(event.target.value)} className="mt-2 min-h-11 w-full rounded-xl border border-border bg-surface px-3 text-text-primary outline-none focus:border-primary-forest">{days.flatMap((day, dayIndex) => MEALS.map((meal) => <option key={`${toDateKey(day)}-${meal.key}`} value={`${toDateKey(day)}|${meal.key}`}>{weekdayLabel(dayIndex)}, {formatDayShort(day)} · {meal.label}</option>))}</select></label><label className="mt-4 flex items-center gap-2 text-sm font-medium text-text-primary"><input type="checkbox" checked={recurring} onChange={(event) => setRecurring(event.target.checked)} className="size-4 accent-primary-forest" />Repetir automaticamente</label>{recurring && <div className="mt-3 grid grid-cols-2 gap-2"><label className="text-xs font-semibold text-text-secondary">Intervalo<select value={intervalWeeks} onChange={(event) => setIntervalWeeks(Number(event.target.value))} className="mt-1 min-h-11 w-full rounded-xl border border-border bg-surface px-2 text-sm text-text-primary"><option value="1">Todas as semanas</option><option value="2">A cada 2 semanas</option><option value="4">A cada 4 semanas</option></select></label><label className="text-xs font-semibold text-text-secondary">Termina em<input type="date" value={endsOn} onChange={(event) => setEndsOn(event.target.value)} className="mt-1 min-h-11 w-full rounded-xl border border-border bg-surface px-2 text-sm text-text-primary" /></label></div>}{repeatError && <p role="alert" className="mt-3 text-sm text-danger">Não foi possível repetir esta refeição.</p>}<button type="button" disabled={saving} onClick={repeat} className="mt-5 min-h-11 w-full rounded-xl bg-primary-forest px-4 text-sm font-semibold text-white disabled:opacity-60">{saving ? 'A repetir…' : recurring ? 'Criar repetição' : 'Repetir refeição'}</button></Modal></>
}

function DesktopMeal({ entry, recipes, days, isDragging, onAssign, onRepeat, onRemove, onDragStart, onDragEnd, onDrop }: { entry?: MealPlanEntry; recipes: RecipeSummary[]; days: Date[]; isDragging: boolean; onAssign: (id: string) => Promise<void>; onRepeat: (day: string, meal: MealType, recipeId: string) => Promise<void>; onRemove: () => void; onDragStart: (recipeId: string) => void; onDragEnd: () => void; onDrop: () => void }) {
  return <div onDragOver={(event) => { if (isDragging) event.preventDefault() }} onDrop={(event) => { event.preventDefault(); onDrop() }} className={`min-w-0 border-l border-border p-2 transition-colors ${isDragging ? 'bg-primary-soft/50' : ''}`}>{entry ? <div draggable onDragStart={() => onDragStart(entry.recipe.id)} onDragEnd={onDragEnd} className="group relative h-full min-h-32 cursor-grab overflow-hidden rounded-xl bg-muted active:cursor-grabbing"><RecipePhoto recipe={entry.recipe} className="absolute inset-0 size-full" /><div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/85 via-black/55 to-transparent px-2 pb-2 pt-8"><p className="text-xs font-semibold leading-snug text-white">{entry.recipe.title}</p></div><div className="absolute left-1.5 top-1.5 flex flex-col gap-1 opacity-100 xl:opacity-0 xl:group-hover:opacity-100"><RecipePicker recipes={recipes} onAssign={onAssign} variant="replace" /><RepeatMeal recipe={entry.recipe} days={days} onRepeat={onRepeat} /></div><button onClick={onRemove} aria-label={`Remover ${entry.recipe.title}`} className="absolute right-1.5 top-1.5 flex size-8 items-center justify-center rounded-full bg-white/90 text-neutral-600 opacity-100 shadow-sm xl:opacity-0 xl:group-hover:opacity-100"><XIcon className="size-4" /></button></div> : <RecipePicker recipes={recipes} onAssign={onAssign} />}</div>
}

function MobileMeal({ label, entry, recipes, days, onAssign, onRepeat, onRemove }: { label: string; entry?: MealPlanEntry; recipes: RecipeSummary[]; days: Date[]; onAssign: (id: string) => Promise<void>; onRepeat: (day: string, meal: MealType, recipeId: string) => Promise<void>; onRemove: () => void }) {
  return <section className="rounded-2xl border border-border bg-surface p-4"><h3 className="mb-3 text-xs font-bold uppercase tracking-wide text-text-secondary">{label}</h3>{entry ? <div className="flex items-center gap-3"><RecipePhoto recipe={entry.recipe} className="size-20 shrink-0 rounded-xl" /><p className="min-w-0 flex-1 font-semibold text-text-primary">{entry.recipe.title}</p><div className="flex flex-col items-end gap-1"><RecipePicker recipes={recipes} onAssign={onAssign} variant="replace" /><RepeatMeal recipe={entry.recipe} days={days} onRepeat={onRepeat} /><button onClick={onRemove} className="flex size-9 items-center justify-center rounded-xl text-text-secondary hover:bg-muted" aria-label={`Remover ${entry.recipe.title}`}><XIcon className="size-5" /></button></div></div> : <RecipePicker recipes={recipes} onAssign={onAssign} />}</section>
}
