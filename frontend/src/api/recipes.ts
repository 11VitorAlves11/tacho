import { api } from './client'
import type { Category, ImportStatus, Recipe, RecipeInput, RecipeSummary, Tag } from './types'

export async function listRecipes(params?: { categoryId?: string; tagId?: string; q?: string }) {
  const { data } = await api.get<RecipeSummary[]>('/recipes', {
    params: { category_id: params?.categoryId, tag_id: params?.tagId, q: params?.q },
  })
  return data
}

export async function getRecipe(id: string) {
  const { data } = await api.get<Recipe>(`/recipes/${id}`)
  return data
}

export async function createRecipe(payload: RecipeInput) {
  const { data } = await api.post<Recipe>('/recipes', payload)
  return data
}

export async function updateRecipe(id: string, payload: RecipeInput) {
  const { data } = await api.put<Recipe>(`/recipes/${id}`, payload)
  return data
}

export async function deleteRecipe(id: string) {
  await api.delete(`/recipes/${id}`)
}

export async function uploadRecipeImage(id: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post<Recipe>(`/recipes/${id}/image`, formData)
  return data
}

export function recipeImageUrl(imagePath: string) {
  return `${api.defaults.baseURL}/images/${imagePath}`
}

export async function startImport(url: string) {
  const { data } = await api.post<ImportStatus>('/recipes/import', { url })
  return data
}

export async function getImportStatus(taskId: string) {
  const { data } = await api.get<ImportStatus>(`/recipes/import/${taskId}`)
  return data
}

export async function listCategories() {
  const { data } = await api.get<Category[]>('/categories')
  return data
}

export async function createCategory(name: string) {
  const { data } = await api.post<Category>('/categories', { name })
  return data
}

export async function listTags() {
  const { data } = await api.get<Tag[]>('/tags')
  return data
}

export async function createTag(name: string) {
  const { data } = await api.post<Tag>('/tags', { name })
  return data
}
