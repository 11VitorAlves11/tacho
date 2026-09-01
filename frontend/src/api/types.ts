// Espelha backend/app/schemas.py — manter em sincronia manualmente (sem
// codegen ainda; considerar mais tarde se o schema crescer muito).

export interface Category {
  id: string
  name: string
  color: string | null
  icon: CategoryIcon | null
}

export type CategoryIcon = 'breakfast' | 'main' | 'dessert' | 'drink' | 'snack' | 'other'

export interface Tag {
  id: string
  name: string
}

export interface Ingredient {
  id: string
  position: number
  name: string
  quantity: number | null
  unit: string | null
  is_header: boolean
}

export interface Step {
  id: string
  position: number
  instruction: string
  duration_minutes: number | null
}

export interface CookNote {
  id: string
  text: string
  created_at: string
  cook_history_id: string | null
}

export interface CookHistoryEntry {
  id: string
  made_at: string
}

export interface RecipeImage {
  id: string
  filename: string
  position: number
  is_cover: boolean
}

export interface Comment {
  id: string
  text: string
  created_at: string
  author_name: string | null
  author_email: string
}

export interface RecipeSummary {
  id: string
  title: string
  servings: number | null
  prep_minutes: number | null
  cook_minutes: number | null
  image_path: string | null
  source_recipe_id: string | null
  is_favorite: boolean
  rating: number | null
  categories: Category[]
  tags: Tag[]
  missing_ingredients: string[] | null
  missing_ingredient_count: number | null
  is_makeable: boolean | null
  dietary_warnings: string[]
}

export interface Recipe {
  id: string
  workspace_id: string
  title: string
  description: string | null
  servings: number | null
  prep_minutes: number | null
  cook_minutes: number | null
  source_url: string | null
  notes: string | null
  image_path: string | null
  source_recipe_id: string | null
  is_favorite: boolean
  rating: number | null
  calories_kcal: number | null
  protein_g: number | null
  carbs_g: number | null
  fat_g: number | null
  estimated_cost: number | null
  created_at: string
  updated_at: string
  last_made_at: string | null
  ingredients: Ingredient[]
  steps: Step[]
  categories: Category[]
  tags: Tag[]
  cook_notes: CookNote[]
  cook_history: CookHistoryEntry[]
  comments: Comment[]
  images: RecipeImage[]
  dietary_warnings: string[]
  substitution_suggestions: RecipeSubstitutionSuggestion[]
}

export interface IngredientSubstitution {
  id: string
  ingredient_name: string
  substitute_name: string
  quantity_ratio: number | null
  note: string | null
  is_verified: boolean
  created_at: string
}

export interface RecipeSubstitutionSuggestion {
  ingredient_name: string
  substitution: IngredientSubstitution
}

export interface RecipeShare {
  share_url: string
  share_expires_at: string
}

// Vista pública temporária (link/QR sem autenticação) — deliberadamente
// mais estreita que Recipe, espelha PublicRecipeOut do backend.
export interface PublicRecipe {
  title: string
  description: string | null
  servings: number | null
  prep_minutes: number | null
  cook_minutes: number | null
  image_path: string | null
  ingredients: Ingredient[]
  steps: Step[]
  categories: Category[]
  tags: Tag[]
}

export interface PantryItem {
  id: string
  name: string
  has_it: boolean
  quantity: number | null
  unit: string | null
  expires_on: string | null
  minimum_quantity: number | null
}

export interface PantryItemInput {
  name?: string
  has_it?: boolean
  quantity?: number | null
  unit?: string | null
  expires_on?: string | null
  minimum_quantity?: number | null
}

export interface PantryExtraction {
  items: string[]
}

export interface CookbookSummary {
  id: string
  name: string
  recipe_count: number
}

export interface CookbookDetail {
  id: string
  name: string
  recipes: RecipeSummary[]
}

export interface RecipeInput {
  title: string
  description?: string | null
  servings?: number | null
  prep_minutes?: number | null
  cook_minutes?: number | null
  source_url?: string | null
  notes?: string | null
  calories_kcal?: number | null
  protein_g?: number | null
  carbs_g?: number | null
  fat_g?: number | null
  estimated_cost?: number | null
  ingredients: { name: string; quantity?: number | null; unit?: string | null; is_header?: boolean }[]
  steps: { instruction: string; duration_minutes?: number | null }[]
  category_ids: string[]
  tag_ids: string[]
}

export interface RecipeExtraction {
  title: string
  description: string | null
  servings: number | null
  prep_minutes: number | null
  cook_minutes: number | null
  ingredients: { name: string; quantity: number | null; unit: string | null; is_header: boolean }[]
  steps: { instruction: string; duration_minutes: number | null }[]
}

export interface ImportStatus {
  task_id: string
  status: 'pending' | 'done' | string
  recipe_id: string | null
}

export type MealType = 'pequeno_almoco' | 'almoco' | 'lanche' | 'jantar'

export interface MealPlanEntry {
  id: string
  day: string
  meal_type: MealType
  recipe: RecipeSummary
}

export interface MealPlanTemplate {
  id: string
  name: string
  slots: { day_offset: number; meal_type: MealType; recipe_id: string }[]
  created_at: string
}

export interface MealPlanRecurrence {
  id: string
  recipe_id: string
  weekday: number
  meal_type: MealType
  interval_weeks: number
  starts_on: string
  ends_on: string | null
  active: boolean
}

export interface MealPlanSuggestionItem {
  day: string
  meal_type: MealType
  recipe: RecipeSummary
}

export interface DietaryProfile {
  id: string
  name: string
  user_id: string | null
  allergies: string[]
  intolerances: string[]
  preferences: string[]
  created_at: string
}

export interface ShoppingListItem {
  id: string
  name: string
  quantity: string | null
  is_checked: boolean
  created_at: string
}

export interface CurrentUser {
  id: string
  email: string
  name: string | null
  is_active: boolean
  is_superuser: boolean
  is_verified: boolean
}

export interface WorkspaceMember {
  id: string
  email: string
  name: string | null
  joined_at: string
}

export interface SetupStatus {
  needs_setup: boolean
}

export interface OIDCStatus {
  enabled: boolean
  display_name: string
  local_login_enabled: boolean
}

export type ForwardLoginBlockReason = 'no_account' | 'inactive' | 'no_membership'

export type ForwardLoginResult =
  | { status: 'ok' }
  | { status: 'blocked'; reason: ForwardLoginBlockReason; email?: string }
  | { status: 'not_applicable' }
