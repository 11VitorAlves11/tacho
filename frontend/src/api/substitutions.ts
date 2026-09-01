import { api } from './client'
import type { IngredientSubstitution } from './types'

export type SubstitutionPayload = Omit<IngredientSubstitution, 'id' | 'created_at'>

export async function listSubstitutions() {
  const { data } = await api.get<IngredientSubstitution[]>('/ingredient-substitutions')
  return data
}

export async function saveSubstitution(payload: SubstitutionPayload, id?: string) {
  const { data } = id
    ? await api.put<IngredientSubstitution>(`/ingredient-substitutions/${id}`, payload)
    : await api.post<IngredientSubstitution>('/ingredient-substitutions', payload)
  return data
}

export async function deleteSubstitution(id: string) {
  await api.delete(`/ingredient-substitutions/${id}`)
}
