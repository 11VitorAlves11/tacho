// Espelha backend/app/schemas.py — manter em sincronia manualmente (sem
// codegen ainda; considerar mais tarde se o schema crescer muito).

export interface Category {
  id: string
  name: string
}

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
  is_favorite: boolean
  rating: number | null
  categories: Category[]
  tags: Tag[]
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
  is_favorite: boolean
  rating: number | null
  calories_kcal: number | null
  protein_g: number | null
  carbs_g: number | null
  fat_g: number | null
  created_at: string
  updated_at: string
  last_made_at: string | null
  ingredients: Ingredient[]
  steps: Step[]
  categories: Category[]
  tags: Tag[]
  cook_notes: CookNote[]
  comments: Comment[]
}

export interface PantryItem {
  id: string
  name: string
  has_it: boolean
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
  ingredients: { name: string; quantity?: number | null; unit?: string | null; is_header?: boolean }[]
  steps: { instruction: string; duration_minutes?: number | null }[]
  category_ids: string[]
  tag_ids: string[]
}

export interface ImportStatus {
  task_id: string
  status: 'pending' | 'done' | string
  recipe_id: string | null
}

export type MealType = 'almoco' | 'jantar'

export interface MealPlanEntry {
  id: string
  day: string
  meal_type: MealType
  recipe: RecipeSummary
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
