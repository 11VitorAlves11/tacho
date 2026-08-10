import { useEffect, useState } from 'react'
import { assignMealPlanEntry, listMealPlan, removeMealPlanEntry } from '../api/planning'
import { listRecipes } from '../api/recipes'
import type { MealPlanEntry, MealType, RecipeSummary } from '../api/types'
import { PageShell } from '../components/PageShell'
import { ChevronLeftIcon, XIcon } from '../components/icons'
import { addDays, formatDayShort, formatWeekRange, startOfWeek, toDateKey, weekdayLabel } from '../lib/date'

const MEAL_TYPES: { key: MealType; label: string }[] = [
  { key: 'almoco', label: 'Almoço' },
  { key: 'jantar', label: 'Jantar' },
]

export function MealPlan() {
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date()))
  const [entries, setEntries] = useState<MealPlanEntry[]>([])
  const [recipes, setRecipes] = useState<RecipeSummary[]>([])
  const [error, setError] = useState(false)

  useEffect(() => {
    listRecipes().then(setRecipes).catch(() => {})
  }, [])

  useEffect(() => {
    setError(false)
    const start = toDateKey(weekStart)
    const end = toDateKey(addDays(weekStart, 6))
    listMealPlan(start, end)
      .then(setEntries)
      .catch(() => setError(true))
  }, [weekStart])

  function entryFor(day: string, mealType: MealType) {
    return entries.find((e) => e.day === day && e.meal_type === mealType)
  }

  async function handleAssign(day: string, mealType: MealType, recipeId: string) {
    if (!recipeId) return
    const entry = await assignMealPlanEntry(day, mealType, recipeId)
    setEntries((prev) => [...prev.filter((e) => !(e.day === day && e.meal_type === mealType)), entry])
  }

  async function handleRemove(day: string, mealType: MealType) {
    await removeMealPlanEntry(day, mealType)
    setEntries((prev) => prev.filter((e) => !(e.day === day && e.meal_type === mealType)))
  }

  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i))

  return (
    <PageShell>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-text-primary sm:text-3xl">Planeamento</h1>
      </div>

      <div className="mb-6 flex items-center justify-between rounded-2xl bg-surface p-3 shadow-sm">
        <button
          type="button"
          onClick={() => setWeekStart((w) => addDays(w, -7))}
          className="flex size-9 items-center justify-center rounded-full text-text-secondary transition-colors hover:bg-bg-sage"
          aria-label="Semana anterior"
        >
          <ChevronLeftIcon className="size-5" />
        </button>
        <span className="text-sm font-medium text-text-primary">{formatWeekRange(weekStart)}</span>
        <button
          type="button"
          onClick={() => setWeekStart((w) => addDays(w, 7))}
          className="flex size-9 items-center justify-center rounded-full text-text-secondary transition-colors hover:bg-bg-sage"
          aria-label="Semana seguinte"
        >
          <ChevronLeftIcon className="size-5 rotate-180" />
        </button>
      </div>

      {error && (
        <p className="rounded-xl bg-surface p-4 text-sm text-text-secondary">
          Não foi possível ligar ao backend. Confirma se está a correr em {import.meta.env.VITE_API_URL}.
        </p>
      )}

      <div className="space-y-3">
        {days.map((day) => {
          const dayKey = toDateKey(day)
          return (
            <div key={dayKey} className="rounded-2xl bg-surface p-4 shadow-sm">
              <p className="mb-3 text-sm font-semibold text-text-primary">
                {weekdayLabel((day.getDay() + 6) % 7)} <span className="font-normal text-text-secondary">· {formatDayShort(day)}</span>
              </p>
              <div className="grid gap-2 sm:grid-cols-2">
                {MEAL_TYPES.map((meal) => {
                  const entry = entryFor(dayKey, meal.key)
                  return (
                    <MealSlot
                      key={meal.key}
                      label={meal.label}
                      entry={entry}
                      recipes={recipes}
                      onAssign={(recipeId) => handleAssign(dayKey, meal.key, recipeId)}
                      onRemove={() => handleRemove(dayKey, meal.key)}
                    />
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
    </PageShell>
  )
}

function MealSlot({
  label,
  entry,
  recipes,
  onAssign,
  onRemove,
}: {
  label: string
  entry: MealPlanEntry | undefined
  recipes: RecipeSummary[]
  onAssign: (recipeId: string) => void
  onRemove: () => void
}) {
  return (
    <div className="rounded-xl bg-bg-sage/60 p-3">
      <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-text-secondary">{label}</p>
      {entry ? (
        <div className="flex items-center justify-between gap-2">
          <span className="truncate text-sm font-medium text-text-primary">{entry.recipe.title}</span>
          <button
            type="button"
            onClick={onRemove}
            className="flex size-6 shrink-0 items-center justify-center rounded-full text-text-secondary transition-colors hover:bg-card-white hover:text-text-primary"
            aria-label={`Remover ${entry.recipe.title} de ${label.toLowerCase()}`}
          >
            <XIcon className="size-3.5" />
          </button>
        </div>
      ) : (
        <select
          value=""
          onChange={(e) => onAssign(e.target.value)}
          className="w-full rounded-lg border border-transparent bg-card-white px-2 py-1.5 text-sm text-text-secondary outline-none focus:ring-2 focus:ring-accent-leaf"
        >
          <option value="" disabled>
            + Adicionar receita
          </option>
          {recipes.map((r) => (
            <option key={r.id} value={r.id}>
              {r.title}
            </option>
          ))}
        </select>
      )}
    </div>
  )
}
