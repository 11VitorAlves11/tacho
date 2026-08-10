import uuid
from datetime import date, datetime

from fastapi_users import schemas as fu_schemas
from pydantic import BaseModel, ConfigDict, EmailStr, HttpUrl


class IngredientIn(BaseModel):
    name: str
    quantity: float | None = None
    unit: str | None = None
    is_header: bool = False


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
    name: str


class CategoryOut(CategoryCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID


class TagCreate(BaseModel):
    name: str


class TagOut(TagCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID


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
    is_favorite: bool
    categories: list[CategoryOut]
    tags: list[TagOut]


class CookNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str
    created_at: datetime


class CookNoteIn(BaseModel):
    text: str


class ImportRequest(BaseModel):
    url: HttpUrl


class ImportStatus(BaseModel):
    task_id: str
    status: str
    recipe_id: str | None = None


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
    is_favorite: bool
    calories_kcal: int | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None
    created_at: datetime
    updated_at: datetime
    last_made_at: datetime | None
    ingredients: list[IngredientOut]
    steps: list[StepOut]
    categories: list[CategoryOut]
    tags: list[TagOut]
    cook_notes: list[CookNoteOut]


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


class GenerateShoppingListRequest(BaseModel):
    # Segunda-feira da semana a agregar — o frontend calcula-a localmente
    # (ver nota sobre fuso horário em MealPlan.tsx) e envia-a já resolvida.
    week_start: date


class UserRead(fu_schemas.BaseUser[uuid.UUID]):
    name: str | None = None


class UserUpdate(fu_schemas.BaseUserUpdate):
    name: str | None = None


class SetupStatus(BaseModel):
    needs_setup: bool


class SetupRequest(BaseModel):
    email: EmailStr
    password: str


class MemberInvite(BaseModel):
    email: EmailStr
    password: str


class MemberOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    joined_at: datetime
