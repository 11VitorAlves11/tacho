import { api } from './client'
import type { MealPlanEntry, MealType, ShoppingListItem } from './types'

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
