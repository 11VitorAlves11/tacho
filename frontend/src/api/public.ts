import { api } from './client'
import type { PublicRecipe } from './types'

// Sem sessão de propósito — consumido por pages/PublicRecipe.tsx, a única
// página que não vive atrás do AuthProvider (ver App.tsx).
export async function getPublicRecipe(token: string) {
  const { data } = await api.get<PublicRecipe>(`/public/recipes/${token}`)
  return data
}
