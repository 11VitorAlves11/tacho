import { api } from './client'

export interface NutritionEstimate {
  calories_kcal: number | null
  protein_g: number | null
  carbs_g: number | null
  fat_g: number | null
  matched_count: number
  skipped_count: number
}

export async function estimateNutrition(
  ingredients: { name: string; quantity?: number | null; unit?: string | null; is_header?: boolean }[],
  servings: number | null,
) {
  const { data } = await api.post<NutritionEstimate>('/nutrition/estimate', { ingredients, servings })
  return data
}
