import uuid
from datetime import date, datetime
from typing import Annotated

from fastapi_users import schemas as fu_schemas
from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, StringConstraints


class IngredientIn(BaseModel):
    name: str
    quantity: float | None = None
    unit: str | None = None
    is_header: bool = False


class NutritionEstimateRequest(BaseModel):
    ingredients: list[IngredientIn]
    servings: int | None = None


class SkippedIngredient(BaseModel):
    name: str
    reason: str


class NutritionEstimate(BaseModel):
    calories_kcal: int | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None
    # Quantos ingredientes entraram na conta vs. ficaram de fora (sem
    # unidade de massa/volume reconhecida, ou sem correspondência na Open
    # Food Facts) — para o frontend mostrar "estimativa parcial: 3 de 5
    # ingredientes" em vez de fingir precisão que não existe.
    matched_count: int
    skipped_count: int
    # Nome + motivo de cada ingrediente ignorado, para o frontend explicar
    # a falha em vez do texto genérico que culpava a Open Food Facts por
    # omissão mesmo quando o problema era a unidade não reconhecida.
    skipped_ingredients: list[SkippedIngredient] = []


class IngredientOut(IngredientIn):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    position: int


class StepIn(BaseModel):
    instruction: str
    duration_minutes: int | None = None


class StepOut(StepIn):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    position: int


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str | None = Field(default=None, pattern=r"^(breakfast|main|dessert|drink|snack|other)$")


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str | None = Field(default=None, pattern=r"^(breakfast|main|dessert|drink|snack|other)$")


class CategoryOut(CategoryCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID


class TagCreate(BaseModel):
    name: str


class TagOut(TagCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID


class IngredientSubstitutionWrite(BaseModel):
    ingredient_name: str = Field(min_length=1, max_length=160)
    substitute_name: str = Field(min_length=1, max_length=160)
    quantity_ratio: float | None = Field(default=None, gt=0, le=100)
    note: str | None = Field(default=None, max_length=500)
    is_verified: bool = False


class IngredientSubstitutionOut(IngredientSubstitutionWrite):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class RecipeSubstitutionSuggestion(BaseModel):
    ingredient_name: str
    substitution: IngredientSubstitutionOut


class CookbookCreate(BaseModel):
    name: str


class CookbookSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    # Não é coluna — len(cookbook.recipes), anotado por crud.py antes de
    # sair (mesmo padrão do Recipe.is_favorite).
    recipe_count: int


class RecipeCreate(BaseModel):
    title: str
    description: str | None = None
    servings: int | None = None
    prep_minutes: int | None = None
    cook_minutes: int | None = None
    source_url: str | None = None
    notes: str | None = None
    calories_kcal: int | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    estimated_cost: float | None = None
    ingredients: list[IngredientIn] = []
    steps: list[StepIn] = []
    category_ids: list[uuid.UUID] = []
    tag_ids: list[uuid.UUID] = []


class RecipeUpdate(RecipeCreate):
    pass


class RecipeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    servings: int | None
    prep_minutes: int | None
    cook_minutes: int | None
    image_path: str | None
    source_recipe_id: uuid.UUID | None
    is_favorite: bool
    rating: int | None
    categories: list[CategoryOut]
    tags: list[TagOut]
    missing_ingredients: list[str] | None = None
    missing_ingredient_count: int | None = None
    is_makeable: bool | None = None
    dietary_warnings: list[str] = []


class CookbookDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    recipes: list[RecipeSummary]


class RecipeRatingIn(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)


class CookNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str
    created_at: datetime
    cook_history_id: uuid.UUID | None


class CookNoteIn(BaseModel):
    text: str


class CookHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    made_at: datetime


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str
    created_at: datetime
    # Não são colunas — properties em models.Comment que delegam para
    # comment.user (mesmo padrão do Recipe.is_favorite: atributo Python
    # lido por from_attributes, não uma coluna).
    author_name: str | None
    author_email: str


class CommentIn(BaseModel):
    text: str


class RecipeImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    position: int
    is_cover: bool


class ImportRequest(BaseModel):
    url: HttpUrl


class ImportStatus(BaseModel):
    task_id: str
    status: str
    recipe_id: str | None = None


class RecipeExtraction(BaseModel):
    """Rascunho extraído pelo Gemini (fallback de URL ou foto) — nunca
    gravado diretamente, só usado para pré-preencher `RecipeForm.tsx` para
    revisão manual (mesmo princípio da estimativa de nutrição: sugestão,
    nunca escrita automática). Forma próxima de `RecipeCreate`, mas sem os
    campos que não fazem sentido extrair de texto/foto (categorias, tags,
    custo, nutrição)."""

    title: str
    description: str | None = None
    servings: int | None = None
    prep_minutes: int | None = None
    cook_minutes: int | None = None
    ingredients: list[IngredientIn] = []
    steps: list[StepIn] = []


class RecipeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    description: str | None
    servings: int | None
    prep_minutes: int | None
    cook_minutes: int | None
    source_url: str | None
    notes: str | None
    image_path: str | None
    source_recipe_id: uuid.UUID | None
    is_favorite: bool
    rating: int | None
    calories_kcal: int | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None
    estimated_cost: float | None
    created_at: datetime
    updated_at: datetime
    last_made_at: datetime | None
    ingredients: list[IngredientOut]
    steps: list[StepOut]
    categories: list[CategoryOut]
    tags: list[TagOut]
    cook_notes: list[CookNoteOut]
    cook_history: list[CookHistoryOut]
    comments: list[CommentOut]
    images: list[RecipeImageOut]
    dietary_warnings: list[str] = []
    substitution_suggestions: list[RecipeSubstitutionSuggestion] = []


class RecipeShareOut(BaseModel):
    share_url: str
    share_expires_at: datetime


class PublicRecipeOut(BaseModel):
    """Vista pública temporária (link/QR sem autenticação) — deliberadamente
    mais estreita que RecipeOut: sem id, workspace_id, is_favorite, rating,
    notas, custo, comentários, notas pós-confeção nem galeria (decisão do
    utilizador — só o conteúdo da receita em si, nada do uso do agregado)."""

    model_config = ConfigDict(from_attributes=True)

    title: str
    description: str | None
    servings: int | None
    prep_minutes: int | None
    cook_minutes: int | None
    image_path: str | None
    ingredients: list[IngredientOut]
    steps: list[StepOut]
    categories: list[CategoryOut]
    tags: list[TagOut]


class MealPlanEntryIn(BaseModel):
    recipe_id: uuid.UUID


class MealPlanEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    day: date
    meal_type: str
    recipe: RecipeSummary


class ShoppingListItemIn(BaseModel):
    name: str
    quantity: str | None = None


class ShoppingListItemUpdate(BaseModel):
    name: str | None = None
    quantity: str | None = None
    is_checked: bool | None = None


class ShoppingListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    quantity: str | None
    is_checked: bool
    created_at: datetime


class PantryItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    quantity: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=40)
    expires_on: date | None = None
    minimum_quantity: float | None = Field(default=None, ge=0)


class PantryItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    has_it: bool | None = None
    quantity: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=40)
    expires_on: date | None = None
    minimum_quantity: float | None = Field(default=None, ge=0)


class PantryItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    has_it: bool
    quantity: float | None
    unit: str | None
    expires_on: date | None
    minimum_quantity: float | None


class PantryExtraction(BaseModel):
    """Rascunho de artigos reconhecidos numa foto de fatura (Gemini Vision)
    — mesmo princípio de `RecipeExtraction`: nunca grava sozinho, só
    alimenta uma lista pré-marcada no frontend para confirmação num toque
    (`POST /pantry/bulk`)."""

    items: list[str] = []


class PantryBulkIn(BaseModel):
    names: list[str]


class GenerateShoppingListRequest(BaseModel):
    # Segunda-feira da semana a agregar — o frontend calcula-a localmente
    # (ver nota sobre fuso horário em MealPlan.tsx) e envia-a já resolvida.
    week_start: date


class CopyMealPlanWeekRequest(BaseModel):
    source_week_start: date
    target_week_start: date
    overwrite: bool = False


class MealPlanTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    week_start: date


class MealPlanTemplateApply(BaseModel):
    week_start: date
    overwrite: bool = False


class MealPlanTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slots: list[dict]
    created_at: datetime


class MealPlanRecurrenceCreate(BaseModel):
    recipe_id: uuid.UUID
    weekday: int = Field(ge=0, le=6)
    meal_type: str = Field(pattern=r"^(pequeno_almoco|almoco|lanche|jantar)$")
    interval_weeks: int = Field(default=1, ge=1, le=52)
    starts_on: date
    ends_on: date | None = None


class MealPlanRecurrenceOut(MealPlanRecurrenceCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    active: bool


class MealPlanSuggestionItem(BaseModel):
    day: date
    meal_type: str
    recipe: RecipeSummary


class DietaryProfileWrite(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    user_id: uuid.UUID | None = None
    allergies: list[str] = Field(default_factory=list, max_length=50)
    intolerances: list[str] = Field(default_factory=list, max_length=50)
    preferences: list[str] = Field(default_factory=list, max_length=50)


class DietaryProfileOut(DietaryProfileWrite):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class UserRead(fu_schemas.BaseUser[uuid.UUID]):
    name: str | None = None


class UserUpdate(fu_schemas.BaseUserUpdate):
    name: str | None = None


class SetupStatus(BaseModel):
    needs_setup: bool


class OIDCStatus(BaseModel):
    enabled: bool
    display_name: str
    local_login_enabled: bool


class SetupRequest(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]
    email: EmailStr
    password: str = Field(min_length=8)


class MemberInvite(BaseModel):
    email: EmailStr
    password: str


class MemberOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    joined_at: datetime
