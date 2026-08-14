import { api } from './client'

export interface SkippedIngredient {
  name: string
  reason: string
}

export interface NutritionEstimate {
  calories_kcal: number | null
  protein_g: number | null
  carbs_g: number | null
  fat_g: number | null
  matched_count: number
  skipped_count: number
  skipped_ingredients: SkippedIngredient[]
}

// Único motivo em skipped_ingredients que reflete uma falha real da Open
// Food Facts (rede/timeout) — os outros ("sem quantidade", "unidade não
// reconhecida", "sem correspondência") são recusas legítimas do lado da
// receita, não da API, e não devem ser apresentados como "API em baixo".
export const OFF_UNAVAILABLE_REASON = 'Open Food Facts indisponível'

export async function estimateNutrition(
  ingredients: { name: string; quantity?: number | null; unit?: string | null; is_header?: boolean }[],
  servings: number | null,
) {
  const { data } = await api.post<NutritionEstimate>('/nutrition/estimate', { ingredients, servings })
  return data
}
