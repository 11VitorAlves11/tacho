import { api } from './client'
import type { PantryExtraction, PantryItem } from './types'

export async function listPantryItems() {
  const { data } = await api.get<PantryItem[]>('/pantry')
  return data
}

export async function createPantryItem(name: string) {
  const { data } = await api.post<PantryItem>('/pantry', { name })
  return data
}

export async function importPantryFromReceipt(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post<PantryExtraction>('/pantry/import/receipt', formData)
  return data
}

export async function bulkCreatePantryItems(names: string[]) {
  const { data } = await api.post<PantryItem[]>('/pantry/bulk', { names })
  return data
}

export async function setPantryItemHasIt(id: string, hasIt: boolean) {
  const { data } = await api.patch<PantryItem>(`/pantry/${id}`, { has_it: hasIt })
  return data
}

export async function deletePantryItem(id: string) {
  await api.delete(`/pantry/${id}`)
}
