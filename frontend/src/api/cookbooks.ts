import { api } from './client'
import type { CookbookDetail, CookbookSummary } from './types'

export async function listCookbooks() {
  const { data } = await api.get<CookbookSummary[]>('/cookbooks')
  return data
}

export async function createCookbook(name: string) {
  const { data } = await api.post<CookbookSummary>('/cookbooks', { name })
  return data
}

export async function getCookbook(id: string) {
  const { data } = await api.get<CookbookDetail>(`/cookbooks/${id}`)
  return data
}

export async function deleteCookbook(id: string) {
  await api.delete(`/cookbooks/${id}`)
}

export async function addRecipeToCookbook(cookbookId: string, recipeId: string) {
  const { data } = await api.post<CookbookDetail>(`/cookbooks/${cookbookId}/recipes/${recipeId}`)
  return data
}

export async function removeRecipeFromCookbook(cookbookId: string, recipeId: string) {
  const { data } = await api.delete<CookbookDetail>(`/cookbooks/${cookbookId}/recipes/${recipeId}`)
  return data
}
