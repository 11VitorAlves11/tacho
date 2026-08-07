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
}

export interface RecipeSummary {
  id: string
  title: string
  servings: number | null
  prep_minutes: number | null
  cook_minutes: number | null
  image_path: string | null
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
  created_at: string
  updated_at: string
  ingredients: Ingredient[]
  steps: Step[]
  categories: Category[]
  tags: Tag[]
}

export interface RecipeInput {
  title: string
  description?: string | null
  servings?: number | null
  prep_minutes?: number | null
  cook_minutes?: number | null
  source_url?: string | null
  notes?: string | null
  ingredients: { name: string; quantity?: number | null; unit?: string | null; is_header?: boolean }[]
  steps: { instruction: string }[]
  category_ids: string[]
  tag_ids: string[]
}

export interface ImportStatus {
  task_id: string
  status: 'pending' | 'done' | string
  recipe_id: string | null
}
