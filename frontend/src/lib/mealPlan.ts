import type { MealPlanEntry, MealType } from '../api/types'

export interface DayMeals {
  filled: { meal: MealType; entry: MealPlanEntry }[]
  empty: MealType[]
}

// Divide as refeições de um dia em ocupadas e livres, pela ordem de `meals`,
// para a vista móvel mostrar só as ocupadas como linhas e as livres como chips.
export function splitDayMeals(entries: MealPlanEntry[], day: string, meals: readonly MealType[]): DayMeals {
  const byMeal = new Map(entries.filter((entry) => entry.day === day).map((entry) => [entry.meal_type, entry]))
  const result: DayMeals = { filled: [], empty: [] }
  for (const meal of meals) {
    const entry = byMeal.get(meal)
    if (entry) result.filled.push({ meal, entry })
    else result.empty.push(meal)
  }
  return result
}
