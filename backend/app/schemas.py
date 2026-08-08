import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


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
