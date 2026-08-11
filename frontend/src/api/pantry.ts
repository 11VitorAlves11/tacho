import { api } from './client'
import type { PantryItem } from './types'

export async function listPantryItems() {
  const { data } = await api.get<PantryItem[]>('/pantry')
  return data
}

export async function createPantryItem(name: string) {
  const { data } = await api.post<PantryItem>('/pantry', { name })
  return data
}

export async function setPantryItemHasIt(id: string, hasIt: boolean) {
  const { data } = await api.patch<PantryItem>(`/pantry/${id}`, { has_it: hasIt })
  return data
}

export async function deletePantryItem(id: string) {
  await api.delete(`/pantry/${id}`)
}
