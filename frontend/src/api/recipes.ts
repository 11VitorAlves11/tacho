import { api } from './client'
import type {
  Category,
  ImportStatus,
  Recipe,
  RecipeExtraction,
  RecipeInput,
  RecipeShare,
  RecipeSummary,
  ShoppingListItem,
  Tag,
} from './types'

export async function listRecipes(params?: {
  categoryId?: string
  tagIds?: string[]
  q?: string
  ingredient?: string
  ratingMin?: number
  maxTotalMinutes?: number
  favorite?: boolean
  makeable?: boolean
  pantrySuggestions?: boolean
  safeForAll?: boolean
  profileIds?: string[]
}) {
  const { data } = await api.get<RecipeSummary[]>('/recipes', {
    params: {
      category_id: params?.categoryId,
      tag_ids: params?.tagIds?.join(','),
      q: params?.q,
      ingredient: params?.ingredient,
      rating_min: params?.ratingMin,
      max_total_minutes: params?.maxTotalMinutes,
      favorite: params?.favorite,
      makeable: params?.makeable,
      pantry_suggestions: params?.pantrySuggestions,
      safe_for_all: params?.safeForAll,
      profile_ids: params?.profileIds?.join(','),
    },
  })
  return data
}

export async function exportWorkspaceRecipes() {
  const { data } = await api.get('/recipes/export')
  return data as { format: string; version: number; recipes: unknown[] }
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

export async function duplicateRecipe(id: string) {
  const { data } = await api.post<Recipe>(`/recipes/${id}/duplicate`)
  return data
}

// Gera/renova o link público temporário (5h) — POST de novo antes de
// expirar estica a janela em vez de a substituir por outra em separado.
export async function shareRecipe(id: string) {
  const { data } = await api.post<RecipeShare>(`/recipes/${id}/share`)
  return data
}

export async function markRecipeMade(id: string) {
  const { data } = await api.post<Recipe>(`/recipes/${id}/mark-made`)
  return data
}

export async function addRecipeToShoppingList(id: string) {
  const { data } = await api.post<ShoppingListItem[]>(`/recipes/${id}/shopping-list`)
  return data
}

export async function addMissingRecipeIngredientsToShoppingList(id: string) {
  const { data } = await api.post<ShoppingListItem[]>(`/recipes/${id}/shopping-list/missing`)
  return data
}

export async function toggleFavorite(id: string) {
  const { data } = await api.post<Recipe>(`/recipes/${id}/favorite`)
  return data
}

export async function setRecipeRating(id: string, rating: number | null) {
  const { data } = await api.patch<Recipe>(`/recipes/${id}/rating`, { rating })
  return data
}

export async function addCookNote(id: string, text: string) {
  const { data } = await api.post<Recipe>(`/recipes/${id}/notes`, { text })
  return data
}

export async function addComment(id: string, text: string) {
  const { data } = await api.post<Recipe>(`/recipes/${id}/comments`, { text })
  return data
}

export async function deleteComment(id: string, commentId: string) {
  await api.delete(`/recipes/${id}/comments/${commentId}`)
}

export async function uploadRecipeImage(id: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post<Recipe>(`/recipes/${id}/image`, formData)
  return data
}

export function recipeImageUrl(imagePath: string) {
  return `${api.defaults.baseURL}/media/${imagePath}`
}

export async function addRecipeGalleryImage(id: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post<Recipe>(`/recipes/${id}/images`, formData)
  return data
}

export async function deleteRecipeGalleryImage(id: string, imageId: string) {
  const { data } = await api.delete<Recipe>(`/recipes/${id}/images/${imageId}`)
  return data
}

export async function setRecipeGalleryCover(id: string, imageId: string) {
  const { data } = await api.post<Recipe>(`/recipes/${id}/images/${imageId}/cover`)
  return data
}

export async function startImport(url: string) {
  const { data } = await api.post<ImportStatus>('/recipes/import', { url })
  return data
}

export async function getImportStatus(taskId: string) {
  const { data } = await api.get<ImportStatus>(`/recipes/import/${taskId}`)
  return data
}

// Importação por foto (Gemini Vision) — 1-3 fotos, devolve um rascunho
// para rever/completar no formulário, nunca uma receita já criada. Sem
// GEMINI_API_KEY no backend, dá 422 (ver AddRecipe.tsx).
export async function importRecipeFromPhotos(files: File[]) {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))
  const { data } = await api.post<RecipeExtraction>('/recipes/import/photo', formData)
  return data
}

export async function listCategories() {
  const { data } = await api.get<Category[]>('/categories')
  return data
}

export async function createCategory(name: string, color?: string | null, icon?: Category['icon']) {
  const { data } = await api.post<Category>('/categories', { name, color: color ?? null, icon: icon ?? null })
  return data
}

export async function updateCategory(id: string, patch: { name?: string; color?: string | null; icon?: Category['icon'] }) {
  const { data } = await api.patch<Category>(`/categories/${id}`, patch)
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
