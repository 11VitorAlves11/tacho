import { api } from './client'
import type { DietaryProfile } from './types'

export type DietaryProfilePayload = Omit<DietaryProfile, 'id' | 'created_at'>

export async function listDietaryProfiles() {
  const { data } = await api.get<DietaryProfile[]>('/dietary-profiles')
  return data
}

export async function saveDietaryProfile(payload: DietaryProfilePayload, id?: string) {
  const { data } = id
    ? await api.put<DietaryProfile>(`/dietary-profiles/${id}`, payload)
    : await api.post<DietaryProfile>('/dietary-profiles', payload)
  return data
}

export async function deleteDietaryProfile(id: string) {
  await api.delete(`/dietary-profiles/${id}`)
}
