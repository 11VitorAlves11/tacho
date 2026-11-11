import { api } from './client'
import type {
  PantryItem,
  PantryItemInput,
  PantryPriceEntry,
  PantryPriceEntryInput,
  PantryPriceHistory,
  ReceiptConfirmInput,
  ReceiptConfirmResult,
  ReceiptExtraction,
} from './types'

export async function listPantryItems() {
  const { data } = await api.get<PantryItem[]>('/pantry')
  return data
}

export async function createPantryItem(payload: PantryItemInput & { name: string }) {
  const { data } = await api.post<PantryItem>('/pantry', payload)
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

export async function listPriceEntries(itemId: string) {
  const { data } = await api.get<PantryPriceEntry[]>(`/pantry/${itemId}/prices`)
  return data
}

export async function createPriceEntry(itemId: string, payload: PantryPriceEntryInput) {
  const { data } = await api.post<PantryPriceEntry>(`/pantry/${itemId}/prices`, payload)
  return data
}

export async function deletePriceEntry(itemId: string, entryId: string) {
  await api.delete(`/pantry/${itemId}/prices/${entryId}`)
}

export async function getPriceHistory(months = 12) {
  const { data } = await api.get<PantryPriceHistory>('/pantry/prices/history', { params: { months } })
  return data
}

/** Returns a draft for review only; nothing is saved until `confirmReceipt`. */
export async function readReceipt(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post<ReceiptExtraction>('/pantry/receipt', formData)
  return data
}

export async function confirmReceipt(payload: ReceiptConfirmInput) {
  const { data } = await api.post<ReceiptConfirmResult>('/pantry/receipt/confirm', payload)
  return data
}
