// Formato de `GET /recipes/export`, aceite de volta por `POST /recipes/import-file`.
export const RECIPE_EXPORT_FORMAT = 'tacho.recipe-export'
export const RECIPE_EXPORT_VERSION = 1
export const MAX_IMPORTED_RECIPES = 500

export type RecipeExportDocument = { format: typeof RECIPE_EXPORT_FORMAT; version: typeof RECIPE_EXPORT_VERSION; recipes: unknown[] }

export type RecipeExportError = 'invalid_json' | 'wrong_format' | 'unsupported_version' | 'no_recipes' | 'too_many'

// Validação no browser antes de enviar — o backend repete-a, isto só evita
// mandar um ficheiro qualquer e dá uma mensagem mais imediata.
export function parseRecipeExport(text: string): { document: RecipeExportDocument } | { error: RecipeExportError } {
  let value: unknown
  try {
    value = JSON.parse(text)
  } catch {
    return { error: 'invalid_json' }
  }
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return { error: 'wrong_format' }
  const candidate = value as Record<string, unknown>
  if (candidate.format !== RECIPE_EXPORT_FORMAT) return { error: 'wrong_format' }
  if (candidate.version !== RECIPE_EXPORT_VERSION) return { error: 'unsupported_version' }
  if (!Array.isArray(candidate.recipes) || candidate.recipes.length === 0) return { error: 'no_recipes' }
  if (candidate.recipes.length > MAX_IMPORTED_RECIPES) return { error: 'too_many' }
  return { document: { format: RECIPE_EXPORT_FORMAT, version: RECIPE_EXPORT_VERSION, recipes: candidate.recipes } }
}
