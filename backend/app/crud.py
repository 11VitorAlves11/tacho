import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app import models, schemas


def _prefix_tsquery(q: str) -> str | None:
    """Constrói um tsquery de prefixo por palavra (ex. "bacal fri" ->
    "bacal:* & fri:*"), para a pesquisa funcionar enquanto se escreve — um
    plainto_tsquery normal só casa palavras completas. `\\w+` isola só
    caracteres de palavra do input do utilizador, para nunca passar
    sintaxe de tsquery (`&`, `:`, aspas) para o Postgres."""
    words = re.findall(r"\w+", q, re.UNICODE)
    if not words:
        return None
    return " & ".join(f"{word}:*" for word in words)


def _recipe_query(workspace_id: uuid.UUID):
    return (
        select(models.Recipe)
        .where(models.Recipe.workspace_id == workspace_id)
        .options(
            selectinload(models.Recipe.ingredients),
            selectinload(models.Recipe.steps),
            selectinload(models.Recipe.categories),
            selectinload(models.Recipe.tags),
        )
    )


def list_recipes(
    db: Session,
    workspace_id: uuid.UUID,
    category_id: uuid.UUID | None = None,
    tag_id: uuid.UUID | None = None,
    q: str | None = None,
    favorite_only: bool = False,
) -> list[models.Recipe]:
    query = _recipe_query(workspace_id)
    if category_id is not None:
        query = query.where(models.Recipe.categories.any(models.Category.id == category_id))
    if tag_id is not None:
        query = query.where(models.Recipe.tags.any(models.Tag.id == tag_id))
    if favorite_only:
        query = query.where(models.Recipe.is_favorite.is_(True))
    if q:
        tsquery = _prefix_tsquery(q)
        if tsquery is not None:
            query = query.where(
                func.to_tsvector("portuguese", models.Recipe.title).op("@@")(
                    func.to_tsquery("portuguese", tsquery)
                )
            )
    return list(db.scalars(query.order_by(models.Recipe.title)))


def get_recipe(db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID) -> models.Recipe | None:
    query = _recipe_query(workspace_id).where(models.Recipe.id == recipe_id)
    return db.scalars(query).first()


def _resolve_categories(db: Session, workspace_id: uuid.UUID, category_ids: list[uuid.UUID]) -> list[models.Category]:
    if not category_ids:
        return []
    query = select(models.Category).where(
        models.Category.workspace_id == workspace_id, models.Category.id.in_(category_ids)
    )
    return list(db.scalars(query))


def _resolve_tags(db: Session, workspace_id: uuid.UUID, tag_ids: list[uuid.UUID]) -> list[models.Tag]:
    if not tag_ids:
        return []
    query = select(models.Tag).where(models.Tag.workspace_id == workspace_id, models.Tag.id.in_(tag_ids))
    return list(db.scalars(query))


def create_recipe(db: Session, workspace_id: uuid.UUID, payload: schemas.RecipeCreate) -> models.Recipe:
    recipe = models.Recipe(
        workspace_id=workspace_id,
        title=payload.title,
        description=payload.description,
        servings=payload.servings,
        prep_minutes=payload.prep_minutes,
        cook_minutes=payload.cook_minutes,
        source_url=payload.source_url,
        notes=payload.notes,
        calories_kcal=payload.calories_kcal,
        protein_g=payload.protein_g,
        carbs_g=payload.carbs_g,
        fat_g=payload.fat_g,
        ingredients=[
            models.Ingredient(
                position=i, name=ing.name, quantity=ing.quantity, unit=ing.unit, is_header=ing.is_header
            )
            for i, ing in enumerate(payload.ingredients)
        ],
        steps=[
            models.Step(position=i, instruction=step.instruction, duration_minutes=step.duration_minutes)
            for i, step in enumerate(payload.steps)
        ],
        categories=_resolve_categories(db, workspace_id, payload.category_ids),
        tags=_resolve_tags(db, workspace_id, payload.tag_ids),
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


def update_recipe(
    db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID, payload: schemas.RecipeUpdate
) -> models.Recipe | None:
    recipe = get_recipe(db, workspace_id, recipe_id)
    if recipe is None:
        return None

    recipe.title = payload.title
    recipe.description = payload.description
    recipe.servings = payload.servings
    recipe.prep_minutes = payload.prep_minutes
    recipe.cook_minutes = payload.cook_minutes
    recipe.source_url = payload.source_url
    recipe.notes = payload.notes
    recipe.calories_kcal = payload.calories_kcal
    recipe.protein_g = payload.protein_g
    recipe.carbs_g = payload.carbs_g
    recipe.fat_g = payload.fat_g
    recipe.ingredients = [
        models.Ingredient(
            position=i, name=ing.name, quantity=ing.quantity, unit=ing.unit, is_header=ing.is_header
        )
        for i, ing in enumerate(payload.ingredients)
    ]
    recipe.steps = [
        models.Step(position=i, instruction=step.instruction, duration_minutes=step.duration_minutes)
        for i, step in enumerate(payload.steps)
    ]
    recipe.categories = _resolve_categories(db, workspace_id, payload.category_ids)
    recipe.tags = _resolve_tags(db, workspace_id, payload.tag_ids)

    db.commit()
    db.refresh(recipe)
    return recipe


def set_recipe_image(
    db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID, image_path: str
) -> models.Recipe | None:
    recipe = get_recipe(db, workspace_id, recipe_id)
    if recipe is None:
        return None
    recipe.image_path = image_path
    db.commit()
    db.refresh(recipe)
    return recipe


def toggle_recipe_favorite(db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID) -> models.Recipe | None:
    recipe = get_recipe(db, workspace_id, recipe_id)
    if recipe is None:
        return None
    recipe.is_favorite = not recipe.is_favorite
    db.commit()
    db.refresh(recipe)
    return recipe


def mark_recipe_made(db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID) -> models.Recipe | None:
    recipe = get_recipe(db, workspace_id, recipe_id)
    if recipe is None:
        return None
    recipe.last_made_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(recipe)
    return recipe


def add_cook_note(db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID, text: str) -> models.Recipe | None:
    recipe = get_recipe(db, workspace_id, recipe_id)
    if recipe is None:
        return None
    db.add(models.CookNote(recipe_id=recipe.id, text=text))
    db.commit()
    db.refresh(recipe)
    return recipe


def duplicate_recipe(
    db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID, image_path: str | None
) -> models.Recipe | None:
    """Cria uma cópia independente da receita (novo id, sem last_made_at nem
    fonte). `image_path` já vem resolvido pelo router — se a original tem
    foto, o router copia o ficheiro para um nome novo antes de chamar esta
    função, para que apagar uma receita nunca apague a foto da outra."""
    original = get_recipe(db, workspace_id, recipe_id)
    if original is None:
        return None

    copy = models.Recipe(
        workspace_id=workspace_id,
        title=f"{original.title} (cópia)",
        description=original.description,
        servings=original.servings,
        prep_minutes=original.prep_minutes,
        cook_minutes=original.cook_minutes,
        source_url=original.source_url,
        notes=original.notes,
        image_path=image_path,
        calories_kcal=original.calories_kcal,
        protein_g=original.protein_g,
        carbs_g=original.carbs_g,
        fat_g=original.fat_g,
        ingredients=[
            models.Ingredient(
                position=ing.position, name=ing.name, quantity=ing.quantity, unit=ing.unit, is_header=ing.is_header
            )
            for ing in original.ingredients
        ],
        steps=[
            models.Step(position=step.position, instruction=step.instruction, duration_minutes=step.duration_minutes)
            for step in original.steps
        ],
        categories=list(original.categories),
        tags=list(original.tags),
    )
    db.add(copy)
    db.commit()
    db.refresh(copy)
    return copy


def delete_recipe(db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID) -> bool:
    recipe = get_recipe(db, workspace_id, recipe_id)
    if recipe is None:
        return False
    db.delete(recipe)
    db.commit()
    return True


def list_categories(db: Session, workspace_id: uuid.UUID) -> list[models.Category]:
    query = select(models.Category).where(models.Category.workspace_id == workspace_id).order_by(models.Category.name)
    return list(db.scalars(query))


def create_category(db: Session, workspace_id: uuid.UUID, payload: schemas.CategoryCreate) -> models.Category:
    category = models.Category(workspace_id=workspace_id, name=payload.name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, workspace_id: uuid.UUID, category_id: uuid.UUID) -> bool:
    query = select(models.Category).where(
        models.Category.workspace_id == workspace_id, models.Category.id == category_id
    )
    category = db.scalars(query).first()
    if category is None:
        return False
    db.delete(category)
    db.commit()
    return True


def list_tags(db: Session, workspace_id: uuid.UUID) -> list[models.Tag]:
    query = select(models.Tag).where(models.Tag.workspace_id == workspace_id).order_by(models.Tag.name)
    return list(db.scalars(query))


def create_tag(db: Session, workspace_id: uuid.UUID, payload: schemas.TagCreate) -> models.Tag:
    tag = models.Tag(workspace_id=workspace_id, name=payload.name)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def delete_tag(db: Session, workspace_id: uuid.UUID, tag_id: uuid.UUID) -> bool:
    query = select(models.Tag).where(models.Tag.workspace_id == workspace_id, models.Tag.id == tag_id)
    tag = db.scalars(query).first()
    if tag is None:
        return False
    db.delete(tag)
    db.commit()
    return True
