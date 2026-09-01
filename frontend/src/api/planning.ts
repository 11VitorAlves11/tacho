import { api } from './client'
import type { MealPlanEntry, MealPlanRecurrence, MealPlanSuggestionItem, MealPlanTemplate, MealType, ShoppingListItem } from './types'

export async function listMealPlan(start: string, end: string) {
  const { data } = await api.get<MealPlanEntry[]>('/meal-plan', { params: { start, end } })
  return data
}

export async function assignMealPlanEntry(day: string, mealType: MealType, recipeId: string) {
  const { data } = await api.put<MealPlanEntry>(`/meal-plan/${day}/${mealType}`, { recipe_id: recipeId })
  return data
}

export async function removeMealPlanEntry(day: string, mealType: MealType) {
  await api.delete(`/meal-plan/${day}/${mealType}`)
}

export async function copyMealPlanWeek(sourceWeekStart: string, targetWeekStart: string, overwrite = false) {
  const { data } = await api.post<MealPlanEntry[]>('/meal-plan/copy-week', {
    source_week_start: sourceWeekStart,
    target_week_start: targetWeekStart,
    overwrite,
  })
  return data
}

export async function listMealPlanTemplates() {
  const { data } = await api.get<MealPlanTemplate[]>('/meal-plan-templates')
  return data
}

export async function saveMealPlanTemplate(name: string, weekStart: string) {
  const { data } = await api.post<MealPlanTemplate>('/meal-plan-templates', { name, week_start: weekStart })
  return data
}

export async function applyMealPlanTemplate(templateId: string, weekStart: string, overwrite = false) {
  const { data } = await api.post<MealPlanEntry[]>(`/meal-plan-templates/${templateId}/apply`, {
    week_start: weekStart,
    overwrite,
  })
  return data
}

export async function createMealPlanRecurrence(
  recipeId: string,
  weekday: number,
  mealType: MealType,
  startsOn: string,
  intervalWeeks = 1,
  endsOn?: string | null,
) {
  const { data } = await api.post<MealPlanRecurrence>('/meal-plan-recurrences', {
    recipe_id: recipeId,
    weekday,
    meal_type: mealType,
    starts_on: startsOn,
    interval_weeks: intervalWeeks,
    ends_on: endsOn ?? null,
  })
  return data
}

export async function suggestMealPlan(weekStart: string) {
  const { data } = await api.get<MealPlanSuggestionItem[]>('/meal-plan-suggestion', {
    params: { week_start: weekStart },
  })
  return data
}

export async function listShoppingList() {
  const { data } = await api.get<ShoppingListItem[]>('/shopping-list')
  return data
}

export async function generateShoppingList(weekStart: string) {
  const { data } = await api.post<ShoppingListItem[]>('/shopping-list/generate', { week_start: weekStart })
  return data
}

export async function addShoppingListItem(name: string, quantity?: string | null) {
  const { data } = await api.post<ShoppingListItem>('/shopping-list', { name, quantity: quantity ?? null })
  return data
}

export async function updateShoppingListItem(
  id: string,
  payload: { name?: string; quantity?: string | null; is_checked?: boolean },
) {
  const { data } = await api.patch<ShoppingListItem>(`/shopping-list/${id}`, payload)
  return data
}

export async function deleteShoppingListItem(id: string) {
  await api.delete(`/shopping-list/${id}`)
}
