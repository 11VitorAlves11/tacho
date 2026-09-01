import { api } from './client'
import type { PantryExtraction, PantryItem, PantryItemInput } from './types'

export async function listPantryItems() {
  const { data } = await api.get<PantryItem[]>('/pantry')
  return data
}

export async function createPantryItem(payload: PantryItemInput & { name: string }) {
  const { data } = await api.post<PantryItem>('/pantry', payload)
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
  return updatePantryItem(id, { has_it: hasIt })
}

export async function updatePantryItem(id: string, patch: PantryItemInput) {
  const { data } = await api.patch<PantryItem>(`/pantry/${id}`, patch)
  return data
}

export async function deletePantryItem(id: string) {
  await api.delete(`/pantry/${id}`)
}
