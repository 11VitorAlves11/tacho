import re
import secrets
import unicodedata
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app import models, schemas


def _normalize(text: str) -> str:
    """Minúsculas e sem acentos, para comparar nomes de ingredientes com
    nomes de itens da despensa sem depender de escrita exata (ex. "Farinha"
    == "farinha", "açúcar" == "acucar")."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return without_accents.lower().strip()


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
            selectinload(models.Recipe.comments).selectinload(models.Comment.user),
            selectinload(models.Recipe.images),
        )
    )


def _favorited_recipe_ids(db: Session, user_id: uuid.UUID, recipe_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    if not recipe_ids:
        return set()
    query = select(models.recipe_favorites.c.recipe_id).where(
        models.recipe_favorites.c.user_id == user_id,
        models.recipe_favorites.c.recipe_id.in_(recipe_ids),
    )
    return set(db.scalars(query))


def _annotate_favorites(db: Session, user_id: uuid.UUID, recipes: list[models.Recipe]) -> list[models.Recipe]:
    """`Recipe.is_favorite` não é coluna (ver models.py) — marcada aqui como
    atributo Python antes de sair para o schema, sempre relativa a quem fez
    o pedido. Todas as funções deste módulo que devolvem Recipe(s) à API
    passam por aqui antes de devolver."""
    favorited = _favorited_recipe_ids(db, user_id, [r.id for r in recipes])
    for recipe in recipes:
        recipe.is_favorite = recipe.id in favorited
    return recipes


def _is_makeable(recipe: models.Recipe, normalized_pantry: list[str]) -> bool:
    ingredients = [i for i in recipe.ingredients if not i.is_header]
    if not ingredients:
        return False
    return all(
        any(pantry_name in _normalize(ingredient.name) for pantry_name in normalized_pantry)
        for ingredient in ingredients
    )


def list_recipes(
    db: Session,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    category_id: uuid.UUID | None = None,
    tag_id: uuid.UUID | None = None,
    q: str | None = None,
    favorite_only: bool = False,
    makeable_only: bool = False,
) -> list[models.Recipe]:
    query = _recipe_query(workspace_id)
    if category_id is not None:
        query = query.where(models.Recipe.categories.any(models.Category.id == category_id))
    if tag_id is not None:
        query = query.where(models.Recipe.tags.any(models.Tag.id == tag_id))
    if favorite_only:
        query = query.where(
            models.Recipe.id.in_(
                select(models.recipe_favorites.c.recipe_id).where(models.recipe_favorites.c.user_id == user_id)
            )
        )
    if q:
        tsquery = _prefix_tsquery(q)
        if tsquery is not None:
            query = query.where(
                func.to_tsvector("portuguese", models.Recipe.title).op("@@")(func.to_tsquery("portuguese", tsquery))
            )
    recipes = list(db.scalars(query.order_by(models.Recipe.title)))
    if makeable_only:
        # Correspondência em Python, não em SQL: precisa de comparar contra
        # todos os ingredientes de cada receita (já carregados por
        # selectinload em _recipe_query) e a lista de despensa é tipicamente
        # pequena — não vale a pena um JOIN/subquery SQL para isto.
        pantry_query = select(models.PantryItem.name).where(
            models.PantryItem.workspace_id == workspace_id, models.PantryItem.has_it.is_(True)
        )
        normalized_pantry = [_normalize(name) for name in db.scalars(pantry_query)]
        recipes = [r for r in recipes if _is_makeable(r, normalized_pantry)]
    return _annotate_favorites(db, user_id, recipes)


def get_recipe(
    db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID, user_id: uuid.UUID | None = None
) -> models.Recipe | None:
    """`user_id` só é preciso quando a receita devolvida vai direta para o
    schema da API (que exige `is_favorite`) — chamadas internas que só
    verificam existência ou copiam campos (`duplicate_recipe`,
    `delete_recipe`) podem omiti-lo."""
    query = _recipe_query(workspace_id).where(models.Recipe.id == recipe_id)
    recipe = db.scalars(query).first()
    if recipe is None:
        return None
    if user_id is not None:
        recipe = _annotate_favorites(db, user_id, [recipe])[0]
    return recipe


def create_recipe_share(db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID) -> models.Recipe | None:
    """Gera (ou renova) o link público temporário — 5h a partir de agora,
    pedir de novo antes de expirar simplesmente estica a janela. Nunca
    reutiliza `Recipe.id` como token (imprevisível de propósito, sem
    revelar o uuid interno num link partilhado fora do agregado)."""
    recipe = db.scalars(
        select(models.Recipe).where(models.Recipe.workspace_id == workspace_id, models.Recipe.id == recipe_id)
    ).first()
    if recipe is None:
        return None
    recipe.share_token = secrets.token_urlsafe(24)
    recipe.share_expires_at = datetime.now(UTC) + timedelta(hours=5)
    db.commit()
    db.refresh(recipe)
    return recipe


def get_recipe_by_share_token(db: Session, token: str) -> models.Recipe | None:
    """Sem `workspace_id` — o token já é a única credencial aqui, o
    pedido nunca vem de uma sessão autenticada. `selectinload` deliberado
    e mais estreito que `_recipe_query`: a vista pública nunca mostra
    comentários, notas pós-confeção nem a galeria de fotos extra (decisão
    do utilizador — só o conteúdo da receita em si)."""
    query = (
        select(models.Recipe)
        .where(models.Recipe.share_token == token)
        .options(
            selectinload(models.Recipe.ingredients),
            selectinload(models.Recipe.steps),
            selectinload(models.Recipe.categories),
            selectinload(models.Recipe.tags),
        )
    )
    recipe = db.scalars(query).first()
    if recipe is None or recipe.share_expires_at is None or recipe.share_expires_at < datetime.now(UTC):
        return None
    return recipe


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
        estimated_cost=payload.estimated_cost,
        ingredients=[
            models.Ingredient(position=i, name=ing.name, quantity=ing.quantity, unit=ing.unit, is_header=ing.is_header)
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
    recipe.is_favorite = False  # receita nova, ninguém a favoritou ainda
    return recipe


def update_recipe(
    db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID, user_id: uuid.UUID, payload: schemas.RecipeUpdate
) -> models.Recipe | None:
    recipe = get_recipe(db, workspace_id, recipe_id, user_id)
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
    recipe.estimated_cost = payload.estimated_cost
    recipe.ingredients = [
        models.Ingredient(position=i, name=ing.name, quantity=ing.quantity, unit=ing.unit, is_header=ing.is_header)
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
    db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID, user_id: uuid.UUID, image_path: str
) -> models.Recipe | None:
    recipe = get_recipe(db, workspace_id, recipe_id, user_id)
    if recipe is None:
        return None
    recipe.image_path = image_path
    db.commit()
    db.refresh(recipe)
    return recipe


def set_recipe_rating(
    db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID, user_id: uuid.UUID, rating: int | None
) -> models.Recipe | None:
    recipe = get_recipe(db, workspace_id, recipe_id, user_id)
    if recipe is None:
        return None
    recipe.rating = rating
    db.commit()
    db.refresh(recipe)
    return recipe


def toggle_recipe_favorite(
    db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID, user_id: uuid.UUID
) -> models.Recipe | None:
    recipe = get_recipe(db, workspace_id, recipe_id)  # existência só, is_favorite calculado abaixo
    if recipe is None:
        return None
    already_favorited = recipe.id in _favorited_recipe_ids(db, user_id, [recipe.id])
    if already_favorited:
        db.execute(
            models.recipe_favorites.delete().where(
                models.recipe_favorites.c.recipe_id == recipe.id, models.recipe_favorites.c.user_id == user_id
            )
        )
    else:
        db.execute(models.recipe_favorites.insert().values(recipe_id=recipe.id, user_id=user_id))
    db.commit()
    db.refresh(recipe)
    recipe.is_favorite = not already_favorited
    return recipe


def mark_recipe_made(
    db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID, user_id: uuid.UUID
) -> models.Recipe | None:
    recipe = get_recipe(db, workspace_id, recipe_id, user_id)
    if recipe is None:
        return None
    recipe.last_made_at = datetime.now(UTC)
    db.commit()
    db.refresh(recipe)
    return recipe


def add_cook_note(
    db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID, user_id: uuid.UUID, text: str
) -> models.Recipe | None:
    recipe = get_recipe(db, workspace_id, recipe_id, user_id)
    if recipe is None:
        return None
    db.add(models.CookNote(recipe_id=recipe.id, text=text))
    db.commit()
    db.refresh(recipe)
    return recipe


def add_comment(
    db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID, user_id: uuid.UUID, text: str
) -> models.Recipe | None:
    recipe = get_recipe(db, workspace_id, recipe_id, user_id)
    if recipe is None:
        return None
    db.add(models.Comment(recipe_id=recipe.id, user_id=user_id, text=text))
    db.commit()
    db.refresh(recipe)
    return recipe


def delete_comment(db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID, comment_id: uuid.UUID) -> bool:
    query = select(models.Comment).where(
        models.Comment.id == comment_id,
        models.Comment.recipe_id == recipe_id,
        models.Comment.recipe.has(models.Recipe.workspace_id == workspace_id),
    )
    comment = db.scalars(query).first()
    if comment is None:
        return False
    db.delete(comment)
    db.commit()
    return True


def add_recipe_image(
    db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID, user_id: uuid.UUID, filename: str
) -> models.Recipe | None:
    recipe = get_recipe(db, workspace_id, recipe_id, user_id)
    if recipe is None:
        return None
    image = models.RecipeImage(
        recipe_id=recipe.id,
        filename=filename,
        position=len(recipe.images),
        # Primeira foto da galeria é capa da galeria por omissão — mas só
        # quando a receita ainda não tem foto de capa própria
        # (Recipe.image_path); com capa já definida, o badge "Capa" numa
        # foto da galeria diferente ficava a contradizer a capa real
        # mostrada no card/hero. Sem capa própria, continua a fazer
        # sentido destacar logo a primeira foto da galeria.
        is_cover=len(recipe.images) == 0 and recipe.image_path is None,
    )
    db.add(image)
    db.commit()
    db.refresh(recipe)
    return recipe


def get_recipe_image(
    db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID, image_id: uuid.UUID
) -> models.RecipeImage | None:
    query = select(models.RecipeImage).where(
        models.RecipeImage.id == image_id,
        models.RecipeImage.recipe_id == recipe_id,
        models.RecipeImage.recipe.has(models.Recipe.workspace_id == workspace_id),
    )
    return db.scalars(query).first()


def delete_recipe_image_row(
    db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID, image_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[models.Recipe, str] | None:
    """Devolve (receita atualizada, nome do ficheiro apagado) para o router
    poder também remover o ficheiro do disco — só a linha da BD é
    responsabilidade deste módulo."""
    image = get_recipe_image(db, workspace_id, recipe_id, image_id)
    if image is None:
        return None
    filename = image.filename
    was_cover = image.is_cover
    db.delete(image)
    db.commit()

    recipe = get_recipe(db, workspace_id, recipe_id, user_id)
    if recipe is None:
        return None
    # Se a foto apagada era a capa, a próxima (por posição) herda o papel —
    # nunca deixar a galeria sem capa enquanto tiver pelo menos uma foto.
    if was_cover and recipe.images:
        recipe.images[0].is_cover = True
        db.commit()
        db.refresh(recipe)
        recipe = get_recipe(db, workspace_id, recipe_id, user_id)
    return (recipe, filename)


def set_recipe_image_cover(
    db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID, image_id: uuid.UUID, user_id: uuid.UUID
) -> models.Recipe | None:
    image = get_recipe_image(db, workspace_id, recipe_id, image_id)
    if image is None:
        return None
    for other in image.recipe.images:
        other.is_cover = other.id == image.id
    db.commit()
    return get_recipe(db, workspace_id, recipe_id, user_id)


def duplicate_recipe(
    db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID, image_path: str | None, new_id: uuid.UUID
) -> models.Recipe | None:
    """Cria uma cópia independente da receita (novo id, sem last_made_at nem
    fonte). `image_path` já vem resolvido pelo router — se a original tem
    foto, o router copia o ficheiro para um nome novo antes de chamar esta
    função, para que apagar uma receita nunca apague a foto da outra.
    `new_id` também já vem gerado pelo router — o ficheiro da foto (se
    houver) já foi copiado para a pasta `receitas/<new_id>/` antes desta
    receita existir na BD, por isso o id do INSERT tem de ser este mesmo,
    não um gerado aqui."""
    original = get_recipe(db, workspace_id, recipe_id)
    if original is None:
        return None

    copy = models.Recipe(
        id=new_id,
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
        estimated_cost=original.estimated_cost,
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
    copy.is_favorite = False  # cópia nova, não herda favoritos da original
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


def list_cookbooks(db: Session, workspace_id: uuid.UUID) -> list[models.Cookbook]:
    query = (
        select(models.Cookbook)
        .where(models.Cookbook.workspace_id == workspace_id)
        .options(selectinload(models.Cookbook.recipes))
        .order_by(models.Cookbook.name)
    )
    cookbooks = list(db.scalars(query))
    for cookbook in cookbooks:
        cookbook.recipe_count = len(cookbook.recipes)  # não é coluna, ver schemas.CookbookSummary
    return cookbooks


def create_cookbook(db: Session, workspace_id: uuid.UUID, payload: schemas.CookbookCreate) -> models.Cookbook:
    cookbook = models.Cookbook(workspace_id=workspace_id, name=payload.name)
    db.add(cookbook)
    db.commit()
    db.refresh(cookbook)
    cookbook.recipe_count = 0
    return cookbook


def _cookbook_query(workspace_id: uuid.UUID):
    return (
        select(models.Cookbook)
        .where(models.Cookbook.workspace_id == workspace_id)
        .options(
            selectinload(models.Cookbook.recipes).selectinload(models.Recipe.categories),
            selectinload(models.Cookbook.recipes).selectinload(models.Recipe.tags),
        )
    )


def get_cookbook(
    db: Session, workspace_id: uuid.UUID, cookbook_id: uuid.UUID, user_id: uuid.UUID
) -> models.Cookbook | None:
    query = _cookbook_query(workspace_id).where(models.Cookbook.id == cookbook_id)
    cookbook = db.scalars(query).first()
    if cookbook is None:
        return None
    _annotate_favorites(db, user_id, cookbook.recipes)  # CookbookDetail.recipes é RecipeSummary, exige is_favorite
    return cookbook


def delete_cookbook(db: Session, workspace_id: uuid.UUID, cookbook_id: uuid.UUID) -> bool:
    query = select(models.Cookbook).where(
        models.Cookbook.workspace_id == workspace_id, models.Cookbook.id == cookbook_id
    )
    cookbook = db.scalars(query).first()
    if cookbook is None:
        return False
    db.delete(cookbook)
    db.commit()
    return True


def add_recipe_to_cookbook(
    db: Session, workspace_id: uuid.UUID, cookbook_id: uuid.UUID, recipe_id: uuid.UUID, user_id: uuid.UUID
) -> models.Cookbook | None:
    cookbook = get_cookbook(db, workspace_id, cookbook_id, user_id)
    if cookbook is None:
        return None
    recipe = get_recipe(db, workspace_id, recipe_id)
    if recipe is None:
        return None
    if recipe.id not in {r.id for r in cookbook.recipes}:
        cookbook.recipes.append(recipe)
        db.commit()
        db.refresh(cookbook)
        _annotate_favorites(db, user_id, cookbook.recipes)
    return cookbook


def remove_recipe_from_cookbook(
    db: Session, workspace_id: uuid.UUID, cookbook_id: uuid.UUID, recipe_id: uuid.UUID, user_id: uuid.UUID
) -> models.Cookbook | None:
    cookbook = get_cookbook(db, workspace_id, cookbook_id, user_id)
    if cookbook is None:
        return None
    cookbook.recipes = [r for r in cookbook.recipes if r.id != recipe_id]
    db.commit()
    db.refresh(cookbook)
    _annotate_favorites(db, user_id, cookbook.recipes)
    return cookbook


def _meal_plan_query(workspace_id: uuid.UUID):
    return (
        select(models.MealPlanEntry)
        .where(models.MealPlanEntry.workspace_id == workspace_id)
        .options(
            selectinload(models.MealPlanEntry.recipe).selectinload(models.Recipe.categories),
            selectinload(models.MealPlanEntry.recipe).selectinload(models.Recipe.tags),
        )
    )


def list_meal_plan_entries(
    db: Session, workspace_id: uuid.UUID, user_id: uuid.UUID, start: date, end: date
) -> list[models.MealPlanEntry]:
    query = _meal_plan_query(workspace_id).where(models.MealPlanEntry.day >= start, models.MealPlanEntry.day <= end)
    entries = list(db.scalars(query).unique())
    # MealPlanEntryOut.recipe é um RecipeSummary — exige is_favorite, que só
    # existe depois de anotado (ver models.py/_annotate_favorites).
    _annotate_favorites(db, user_id, [e.recipe for e in entries])
    return entries


def upsert_meal_plan_entry(
    db: Session, workspace_id: uuid.UUID, user_id: uuid.UUID, day: date, meal_type: str, recipe_id: uuid.UUID
) -> models.MealPlanEntry | None:
    """Atribui uma receita a um dia/refeição — substitui o que lá estivesse
    (um slot só tem uma receita). `recipe_id` é validado como pertencente ao
    workspace antes de gravar; devolve None se a receita não existir aqui."""
    recipe = get_recipe(db, workspace_id, recipe_id)
    if recipe is None:
        return None

    query = select(models.MealPlanEntry).where(
        models.MealPlanEntry.workspace_id == workspace_id,
        models.MealPlanEntry.day == day,
        models.MealPlanEntry.meal_type == meal_type,
    )
    entry = db.scalars(query).first()
    if entry is None:
        entry = models.MealPlanEntry(workspace_id=workspace_id, day=day, meal_type=meal_type, recipe_id=recipe_id)
        db.add(entry)
    else:
        entry.recipe_id = recipe_id
    db.commit()

    result_query = _meal_plan_query(workspace_id).where(models.MealPlanEntry.id == entry.id)
    result = db.scalars(result_query).first()
    if result is not None:
        _annotate_favorites(db, user_id, [result.recipe])
    return result


def delete_meal_plan_entry(db: Session, workspace_id: uuid.UUID, day: date, meal_type: str) -> bool:
    query = select(models.MealPlanEntry).where(
        models.MealPlanEntry.workspace_id == workspace_id,
        models.MealPlanEntry.day == day,
        models.MealPlanEntry.meal_type == meal_type,
    )
    entry = db.scalars(query).first()
    if entry is None:
        return False
    db.delete(entry)
    db.commit()
    return True


def list_shopping_list_items(db: Session, workspace_id: uuid.UUID) -> list[models.ShoppingListItem]:
    query = (
        select(models.ShoppingListItem)
        .where(models.ShoppingListItem.workspace_id == workspace_id)
        .order_by(models.ShoppingListItem.created_at)
    )
    return list(db.scalars(query))


def create_shopping_list_item(
    db: Session, workspace_id: uuid.UUID, payload: schemas.ShoppingListItemIn
) -> models.ShoppingListItem:
    item = models.ShoppingListItem(workspace_id=workspace_id, name=payload.name, quantity=payload.quantity)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_shopping_list_item(
    db: Session, workspace_id: uuid.UUID, item_id: uuid.UUID, payload: schemas.ShoppingListItemUpdate
) -> models.ShoppingListItem | None:
    query = select(models.ShoppingListItem).where(
        models.ShoppingListItem.workspace_id == workspace_id, models.ShoppingListItem.id == item_id
    )
    item = db.scalars(query).first()
    if item is None:
        return None
    if payload.name is not None:
        item.name = payload.name
    if payload.quantity is not None:
        item.quantity = payload.quantity
    if payload.is_checked is not None:
        item.is_checked = payload.is_checked
    db.commit()
    db.refresh(item)
    return item


def delete_shopping_list_item(db: Session, workspace_id: uuid.UUID, item_id: uuid.UUID) -> bool:
    query = select(models.ShoppingListItem).where(
        models.ShoppingListItem.workspace_id == workspace_id, models.ShoppingListItem.id == item_id
    )
    item = db.scalars(query).first()
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True


def list_pantry_items(db: Session, workspace_id: uuid.UUID) -> list[models.PantryItem]:
    query = (
        select(models.PantryItem).where(models.PantryItem.workspace_id == workspace_id).order_by(models.PantryItem.name)
    )
    return list(db.scalars(query))


def bulk_upsert_pantry_items(db: Session, workspace_id: uuid.UUID, names: list[str]) -> list[models.PantryItem]:
    """Usado pela importação de fatura (`extract_pantry_items_from_image`
    + confirmação no frontend): insere os nomes novos e marca `has_it=True`
    nos que já existiam (por nome normalizado, mesma comparação de
    `_normalize` usada no filtro "dá para fazer") em vez de um `create_pantry_item`
    por item — evitava rebentar a meio com `IntegrityError` da constraint
    `uq_pantry_item_workspace_name` assim que a fatura repetisse um artigo
    já na despensa."""
    cleaned: list[str] = []
    seen_keys: set[str] = set()
    for raw_name in names:
        name = raw_name.strip()
        if not name:
            continue
        key = _normalize(name)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        cleaned.append(name)
    if not cleaned:
        return []

    existing = list(db.scalars(select(models.PantryItem).where(models.PantryItem.workspace_id == workspace_id)))
    existing_by_key = {_normalize(item.name): item for item in existing}

    result: list[models.PantryItem] = []
    for name in cleaned:
        item = existing_by_key.get(_normalize(name))
        if item is not None:
            item.has_it = True
        else:
            item = models.PantryItem(workspace_id=workspace_id, name=name)
            db.add(item)
        result.append(item)

    db.commit()
    for item in result:
        db.refresh(item)
    return result


def create_pantry_item(db: Session, workspace_id: uuid.UUID, payload: schemas.PantryItemIn) -> models.PantryItem:
    item = models.PantryItem(workspace_id=workspace_id, name=payload.name)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_pantry_item(
    db: Session, workspace_id: uuid.UUID, item_id: uuid.UUID, payload: schemas.PantryItemUpdate
) -> models.PantryItem | None:
    query = select(models.PantryItem).where(
        models.PantryItem.workspace_id == workspace_id, models.PantryItem.id == item_id
    )
    item = db.scalars(query).first()
    if item is None:
        return None
    item.has_it = payload.has_it
    db.commit()
    db.refresh(item)
    return item


def delete_pantry_item(db: Session, workspace_id: uuid.UUID, item_id: uuid.UUID) -> bool:
    query = select(models.PantryItem).where(
        models.PantryItem.workspace_id == workspace_id, models.PantryItem.id == item_id
    )
    item = db.scalars(query).first()
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True


def _format_quantity(quantity, unit: str | None) -> str | None:
    parts = []
    if quantity is not None:
        parts.append(f"{float(quantity):g}")
    if unit:
        parts.append(unit)
    return " ".join(parts) if parts else None


def generate_shopping_list(db: Session, workspace_id: uuid.UUID, week_start: date) -> list[models.ShoppingListItem]:
    """Agrega os ingredientes de todas as receitas planeadas na semana
    (week_start .. +6 dias) para a lista de compras. Um item por ingrediente
    de nome distinto na semana — a quantidade fica a da primeira ocorrência
    encontrada, as seguintes são descartadas (ex. bacalhau ao almoço e ao
    jantar não soma 800g, fica só a quantidade de uma das duas); somar a
    sério entre receitas exigiria conversão de unidades, fora de âmbito.
    Cabeçalhos de secção (`is_header`) são ignorados, não são ingredientes
    reais. Para gerar não duplicar ao carregar duas vezes, salta ingredientes
    cujo nome já existe como item por marcar na lista — itens já comprados
    (marcados) não bloqueiam, para poder voltar a gerar depois de esvaziar o
    carrinho."""
    week_end = week_start + timedelta(days=6)
    entries = list_meal_plan_entries(db, workspace_id, week_start, week_end)

    existing_query = select(models.ShoppingListItem.name).where(
        models.ShoppingListItem.workspace_id == workspace_id, models.ShoppingListItem.is_checked.is_(False)
    )
    existing_names = set(db.scalars(existing_query))

    new_items: list[models.ShoppingListItem] = []
    seen_this_run: set[str] = set()
    for entry in entries:
        for ingredient in entry.recipe.ingredients:
            if ingredient.is_header:
                continue
            if ingredient.name in existing_names or ingredient.name in seen_this_run:
                continue
            seen_this_run.add(ingredient.name)
            item = models.ShoppingListItem(
                workspace_id=workspace_id,
                name=ingredient.name,
                quantity=_format_quantity(ingredient.quantity, ingredient.unit),
            )
            db.add(item)
            new_items.append(item)

    db.commit()
    return list_shopping_list_items(db, workspace_id)


def add_recipe_to_shopping_list(
    db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID
) -> list[models.ShoppingListItem] | None:
    """Mesma lógica de dedup de `generate_shopping_list`, mas a partir dos
    ingredientes de uma única receita em vez de todo o plano semanal.
    Devolve só os itens novos (não a lista toda), para o frontend poder
    mostrar "N ingredientes adicionados" sem ter de comparar antes/depois."""
    recipe = get_recipe(db, workspace_id, recipe_id)
    if recipe is None:
        return None

    existing_query = select(models.ShoppingListItem.name).where(
        models.ShoppingListItem.workspace_id == workspace_id, models.ShoppingListItem.is_checked.is_(False)
    )
    existing_names = set(db.scalars(existing_query))

    new_items: list[models.ShoppingListItem] = []
    seen_this_run: set[str] = set()
    for ingredient in recipe.ingredients:
        if ingredient.is_header:
            continue
        if ingredient.name in existing_names or ingredient.name in seen_this_run:
            continue
        seen_this_run.add(ingredient.name)
        item = models.ShoppingListItem(
            workspace_id=workspace_id,
            name=ingredient.name,
            quantity=_format_quantity(ingredient.quantity, ingredient.unit),
        )
        db.add(item)
        new_items.append(item)

    db.commit()
    for item in new_items:
        db.refresh(item)
    return new_items
