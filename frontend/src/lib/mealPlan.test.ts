import { describe, expect, it } from 'vitest'

import type { MealPlanEntry, MealType, RecipeSummary } from '../api/types'
import { splitDayMeals } from './mealPlan'

const MEALS: MealType[] = ['pequeno_almoco', 'almoco', 'lanche', 'jantar']

function entry(day: string, meal_type: MealType, title: string): MealPlanEntry {
  return { id: `${day}-${meal_type}`, day, meal_type, recipe: { id: title, title } as RecipeSummary }
}

describe('splitDayMeals', () => {
  it('leaves every meal empty when the day has no entries', () => {
    expect(splitDayMeals([], '2026-11-09', MEALS)).toEqual({ filled: [], empty: MEALS })
  })

  it('keeps the meal order regardless of entry order and ignores other days', () => {
    const dinner = entry('2026-11-09', 'jantar', 'Caril')
    const lunch = entry('2026-11-09', 'almoco', 'Arroz de pato')
    const otherDay = entry('2026-11-10', 'pequeno_almoco', 'Panquecas')

    const result = splitDayMeals([dinner, otherDay, lunch], '2026-11-09', MEALS)

    expect(result.filled).toEqual([{ meal: 'almoco', entry: lunch }, { meal: 'jantar', entry: dinner }])
    expect(result.empty).toEqual(['pequeno_almoco', 'lanche'])
  })

  it('reports no empty meals when the day is full', () => {
    const entries = MEALS.map((meal) => entry('2026-11-09', meal, meal))

    const result = splitDayMeals(entries, '2026-11-09', MEALS)

    expect(result.filled.map((item) => item.meal)).toEqual(MEALS)
    expect(result.empty).toEqual([])
  })
})
