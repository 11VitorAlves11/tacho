import re
import secrets
import unicodedata
import uuid
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal

from pydantic import ValidationError
from sqlalchemy import ColumnElement, delete, func, select
from sqlalchemy.orm import Session, selectinload

from app import models, schemas


def _normalize(text: str) -> str:
    """Minúsculas e sem acentos, para comparar nomes de ingredientes com
    nomes de itens da despensa sem depender de escrita exata (ex. "Farinha"
    == "farinha", "açúcar" == "acucar")."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return without_accents.lower().strip()


# Correspondência despensa ↔ ingrediente (lista de compras, "dá para fazer",
# ingredientes em falta, sugestões). Regra: ambos os nomes passam por
# `_normalize` e são partidos em palavras (tudo o que não é letra separa);
# um item da despensa cobre o ingrediente se CADA palavra do item existir,
# como palavra inteira, no nome do ingrediente. Assim "sal" não cobre
# "salmão" nem "salsa", "ovo" não cobre "novo", "azeite" cobre "azeite
# virgem" mas "azeite virgem" não cobre "azeite". Itens da despensa sem
# letras (vazios, só espaços/números) são ignorados.
#
# Plurais (tolerância conservadora, ver `_word_forms`): duas palavras
# correspondem se partilharem uma forma — a própria palavra, sem "s" final,
# sem "es" final, e "-ões"/"-ães" -> "-ão" (pães ≈ pão, limões ≈ limão).
# Cada forma reduzida tem de manter pelo menos 3 letras.
#
# Limitação aceite: um item de uma palavra cobre qualquer ingrediente que
# contenha essa palavra — "alho" na despensa cobre "alho francês".
_WORD_RE = re.compile(r"[^\W\d_]+")
_MIN_STEM = 3

PantryTokens = list[tuple[frozenset[str], ...]]


def _word_forms(word: str) -> frozenset[str]:
    forms = {word}
    for suffix, replacement in (("oes", "ao"), ("aes", "ao"), ("es", ""), ("s", "")):
        if word.endswith(suffix) and len(word) - len(suffix) + len(replacement) >= _MIN_STEM:
            forms.add(word[: -len(suffix)] + replacement)
    return frozenset(forms)


def _name_forms(name: str) -> tuple[frozenset[str], ...]:
    return tuple(_word_forms(word) for word in _WORD_RE.findall(_normalize(name)))


def _pantry_tokens(pantry_names: Iterable[str]) -> PantryTokens:
    """Pré-calcula as formas de cada item da despensa uma vez por pedido."""
    return [tokens for tokens in map(_name_forms, pantry_names) if tokens]


def _in_pantry(ingredient_name: str, pantry: PantryTokens) -> bool:
    ingredient_forms = frozenset[str]().union(*_name_forms(ingredient_name))
    return any(all(forms & ingredient_forms for forms in tokens) for tokens in pantry)


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


RecipeSort = Literal["title", "newest", "updated", "rating", "least_recently_made"]


def _recipe_order_by(sort: RecipeSort) -> list[ColumnElement]:
    """Cláusulas ORDER BY de cada ordenação da lista de receitas. O título
    entra sempre como desempate para a ordem ser estável entre pedidos.
    Em "há mais tempo sem cozinhar", as nunca cozinhadas (NULL) vêm
    primeiro; em "melhor classificadas", as sem classificação vão para o fim."""
    title = models.Recipe.title.asc()
    if sort == "newest":
        return [models.Recipe.created_at.desc(), title]
    if sort == "updated":
        return [models.Recipe.updated_at.desc(), title]
    if sort == "rating":
        return [models.Recipe.rating.desc().nulls_last(), title]
    if sort == "least_recently_made":
        return [models.Recipe.last_made_at.asc().nulls_first(), title]
    return [title]


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
            selectinload(models.Recipe.cook_notes),
            selectinload(models.Recipe.cook_history),
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


def _is_makeable(recipe: models.Recipe, pantry: PantryTokens) -> bool:
    ingredients = [i for i in recipe.ingredients if not i.is_header]
    if not ingredients:
        return False
    return all(_in_pantry(ingredient.name, pantry) for ingredient in ingredients)


def _missing_ingredients(recipe: models.Recipe, pantry: PantryTokens) -> list[str]:
    return [
        ingredient.name
        for ingredient in recipe.ingredients
        if not ingredient.is_header and not _in_pantry(ingredient.name, pantry)
    ]


def _annotate_availability(recipes: list[models.Recipe], pantry: PantryTokens) -> list[models.Recipe]:
    for recipe in recipes:
        missing = _missing_ingredients(recipe, pantry)
        recipe.missing_ingredients = missing
        recipe.missing_ingredient_count = len(missing)
        recipe.is_makeable = bool(recipe.ingredients) and len(missing) == 0
    return recipes


def _annotate_dietary_warnings(
    db: Session,
    workspace_id: uuid.UUID,
    recipes: list[models.Recipe],
    profile_ids: list[uuid.UUID] | None = None,
) -> list[models.Recipe]:
    profile_query = select(models.DietaryProfile).where(models.DietaryProfile.workspace_id == workspace_id)
    if profile_ids:
        profile_query = profile_query.where(models.DietaryProfile.id.in_(profile_ids))
    profiles = list(db.scalars(profile_query))
    for recipe in recipes:
        ingredient_text = " | ".join(_normalize(item.name) for item in recipe.ingredients if not item.is_header)
        warnings: list[str] = []
        for profile in profiles:
            for kind, terms in (("alergia", profile.allergies), ("intolerância", profile.intolerances)):
                for term in terms:
                    if _normalize(term) in ingredient_text:
                        warnings.append(f"{profile.name}: {term} ({kind})")
        recipe.dietary_warnings = warnings
    return recipes


def _annotate_substitution_suggestions(
    db: Session, workspace_id: uuid.UUID, recipes: list[models.Recipe], pantry: PantryTokens
) -> list[models.Recipe]:
    substitutions = list(
        db.scalars(
            select(models.IngredientSubstitution).where(models.IngredientSubstitution.workspace_id == workspace_id)
        )
    )
    for recipe in recipes:
        suggestions = []
        for ingredient in recipe.ingredients:
            if ingredient.is_header or _in_pantry(ingredient.name, pantry):
                continue
            for substitution in substitutions:
                if _normalize(substitution.ingredient_name) in _normalize(ingredient.name):
                    suggestions.append({"ingredient_name": ingredient.name, "substitution": substitution})
        recipe.substitution_suggestions = suggestions
    return recipes


def list_recipes(
    db: Session,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    category_id: uuid.UUID | None = None,
    tag_ids: list[uuid.UUID] | None = None,
    q: str | None = None,
    ingredient: str | None = None,
    rating_min: int | None = None,
    max_total_minutes: int | None = None,
    favorite_only: bool = False,
    makeable_only: bool = False,
    pantry_suggestions: bool = False,
    safe_for_all: bool = False,
    dietary_profile_ids: list[uuid.UUID] | None = None,
    sort: RecipeSort = "title",
) -> list[models.Recipe]:
    query = _recipe_query(workspace_id)
    if category_id is not None:
        query = query.where(models.Recipe.categories.any(models.Category.id == category_id))
    for tag_id in tag_ids or []:
        query = query.where(models.Recipe.tags.any(models.Tag.id == tag_id))
    if ingredient:
        query = query.where(models.Recipe.ingredients.any(models.Ingredient.name.ilike(f"%{ingredient.strip()}%")))
    if rating_min is not None:
        query = query.where(models.Recipe.rating >= rating_min)
    if max_total_minutes is not None:
        query = query.where(
            func.coalesce(models.Recipe.prep_minutes, 0) + func.coalesce(models.Recipe.cook_minutes, 0)
            <= max_total_minutes
        )
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
    recipes = list(db.scalars(query.order_by(*_recipe_order_by(sort))))
    pantry_query = select(models.PantryItem.name).where(
        models.PantryItem.workspace_id == workspace_id, models.PantryItem.has_it.is_(True)
    )
    pantry = _pantry_tokens(db.scalars(pantry_query))
    _annotate_availability(recipes, pantry)
    _annotate_dietary_warnings(db, workspace_id, recipes, dietary_profile_ids)
    if makeable_only:
        recipes = [r for r in recipes if _is_makeable(r, pantry)]
    if pantry_suggestions:
        # Ingredientes em falta mandam sempre; o sort é estável, por isso a
        # ordenação escolhida (vinda do SQL) fica como desempate.
        if sort == "title":
            recipes.sort(key=lambda recipe: (recipe.missing_ingredient_count, recipe.title.lower()))
        else:
            recipes.sort(key=lambda recipe: recipe.missing_ingredient_count)
    if safe_for_all:
        recipes = [recipe for recipe in recipes if not recipe.dietary_warnings]
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
        recipe = _annotate_dietary_warnings(db, workspace_id, [recipe])[0]
        pantry = _pantry_tokens(
            db.scalars(
                select(models.PantryItem.name).where(
                    models.PantryItem.workspace_id == workspace_id,
                    models.PantryItem.has_it.is_(True),
                )
            )
        )
        recipe = _annotate_substitution_suggestions(db, workspace_id, [recipe], pantry)[0]
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
    db.add(models.CookHistoryEntry(recipe_id=recipe.id, made_at=recipe.last_made_at))
    db.commit()
    db.refresh(recipe)
    return recipe


def add_cook_note(
    db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID, user_id: uuid.UUID, text: str
) -> models.Recipe | None:
    recipe = get_recipe(db, workspace_id, recipe_id, user_id)
    if recipe is None:
        return None
    history_id = recipe.cook_history[0].id if recipe.cook_history else None
    db.add(models.CookNote(recipe_id=recipe.id, cook_history_id=history_id, text=text))
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
        source_recipe_id=original.source_recipe_id or original.id,
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


def _import_key(text: str) -> str:
    return " ".join(_normalize(text).split())


def _duplicate_keys(title: str, source_url: str | None, ingredient_names: list[str]) -> set[tuple]:
    """Chaves de duplicado de uma receita: mesmo título normalizado E (mesma
    `source_url` OU mesmo conjunto de nomes de ingredientes normalizados).
    Duas receitas são duplicadas quando partilham pelo menos uma chave."""
    title_key = _import_key(title)
    names = frozenset(key for key in (_import_key(name) for name in ingredient_names) if key)
    keys: set[tuple] = {(title_key, "ingredients", names)}
    url = (source_url or "").strip().rstrip("/").lower()
    if url:
        keys.add((title_key, "url", url))
    return keys


def _workspace_duplicate_keys(db: Session, workspace_id: uuid.UUID) -> set[tuple]:
    recipes = db.execute(
        select(models.Recipe.id, models.Recipe.title, models.Recipe.source_url).where(
            models.Recipe.workspace_id == workspace_id
        )
    ).all()
    names: dict[uuid.UUID, list[str]] = {recipe.id: [] for recipe in recipes}
    ingredient_rows = db.execute(
        select(models.Ingredient.recipe_id, models.Ingredient.name)
        .join(models.Recipe)
        .where(models.Recipe.workspace_id == workspace_id, models.Ingredient.is_header.is_(False))
    ).all()
    for row in ingredient_rows:
        names[row.recipe_id].append(row.name)
    keys: set[tuple] = set()
    for recipe in recipes:
        keys |= _duplicate_keys(recipe.title, recipe.source_url, names[recipe.id])
    return keys


def _validation_detail(exc: ValidationError) -> str:
    fields = sorted({".".join(str(part) for part in error["loc"]) or "receita" for error in exc.errors()})
    return f"Campos inválidos: {', '.join(fields)}"


def import_recipes(
    db: Session, workspace_id: uuid.UUID, entries: list[Any], allow_duplicates: bool
) -> schemas.RecipeImportResult:
    """Importa as receitas de um `tacho.recipe-export` numa única transação
    (um só commit no fim — um erro inesperado não deixa metade do ficheiro
    gravado). Entradas malformadas e duplicadas são saltadas e reportadas
    em `items`, sem abortar as restantes. Categorias e tags são associadas
    por nome normalizado dentro da workspace e criadas quando faltam."""
    existing_keys = set() if allow_duplicates else _workspace_duplicate_keys(db, workspace_id)
    file_keys: set[tuple] = set()
    categories = {
        _import_key(c.name): c
        for c in db.scalars(select(models.Category).where(models.Category.workspace_id == workspace_id))
    }
    tags = {
        _import_key(t.name): t for t in db.scalars(select(models.Tag).where(models.Tag.workspace_id == workspace_id))
    }
    created_categories: list[str] = []
    created_tags: list[str] = []
    images_not_imported = 0
    items: list[schemas.RecipeImportItem] = []

    for index, raw in enumerate(entries):
        raw_title = raw.get("title") if isinstance(raw, dict) else None
        title = (raw_title.strip() if isinstance(raw_title, str) else "") or f"#{index + 1}"
        try:
            entry = schemas.RecipeImportEntry.model_validate(raw)
        except ValidationError as exc:
            items.append(
                schemas.RecipeImportItem(
                    title=title, status="skipped", reason="invalid", detail=_validation_detail(exc)
                )
            )
            continue

        keys = _duplicate_keys(entry.title, entry.source_url, [i.name for i in entry.ingredients if not i.is_header])
        if keys & existing_keys:
            items.append(schemas.RecipeImportItem(title=entry.title, status="skipped", reason="duplicate"))
            continue
        if keys & file_keys:
            items.append(schemas.RecipeImportItem(title=entry.title, status="skipped", reason="duplicate_in_file"))
            continue
        file_keys |= keys

        recipe_categories: list[models.Category] = []
        for exported_category in entry.categories:
            name = exported_category.name.strip()
            key = _import_key(name)
            if not key:
                continue
            category = categories.get(key)
            if category is None:
                category = models.Category(
                    workspace_id=workspace_id, name=name, color=exported_category.color, icon=exported_category.icon
                )
                db.add(category)
                categories[key] = category
                created_categories.append(name)
            if category not in recipe_categories:
                recipe_categories.append(category)
        recipe_tags: list[models.Tag] = []
        for exported_tag in entry.tags:
            key = _import_key(exported_tag.name)
            tag = tags.get(key)
            if tag is None:
                tag = models.Tag(workspace_id=workspace_id, name=exported_tag.name)
                db.add(tag)
                tags[key] = tag
                created_tags.append(exported_tag.name)
            if tag not in recipe_tags:
                recipe_tags.append(tag)

        recipe = models.Recipe(
            workspace_id=workspace_id,
            title=entry.title,
            description=entry.description,
            servings=entry.servings,
            prep_minutes=entry.prep_minutes,
            cook_minutes=entry.cook_minutes,
            source_url=entry.source_url,
            notes=entry.notes,
            rating=entry.rating,
            calories_kcal=entry.calories_kcal,
            protein_g=entry.protein_g,
            carbs_g=entry.carbs_g,
            fat_g=entry.fat_g,
            estimated_cost=entry.estimated_cost,
            ingredients=[
                models.Ingredient(
                    position=i, name=ing.name, quantity=ing.quantity, unit=ing.unit, is_header=ing.is_header
                )
                for i, ing in enumerate(entry.ingredients)
            ],
            steps=[
                models.Step(position=i, instruction=step.instruction, duration_minutes=step.duration_minutes)
                for i, step in enumerate(entry.steps)
            ],
            categories=recipe_categories,
            tags=recipe_tags,
        )
        db.add(recipe)
        db.flush()
        if entry.image_path or entry.images:
            images_not_imported += 1
        items.append(schemas.RecipeImportItem(title=entry.title, status="imported", recipe_id=recipe.id))

    db.commit()
    imported = sum(1 for item in items if item.status == "imported")
    return schemas.RecipeImportResult(
        imported=imported,
        skipped=len(items) - imported,
        created_categories=created_categories,
        created_tags=created_tags,
        images_not_imported=images_not_imported,
        items=items,
    )


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
    category = models.Category(workspace_id=workspace_id, **payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(
    db: Session, workspace_id: uuid.UUID, category_id: uuid.UUID, payload: schemas.CategoryUpdate
) -> models.Category | None:
    category = db.scalar(
        select(models.Category).where(
            models.Category.workspace_id == workspace_id,
            models.Category.id == category_id,
        )
    )
    if category is None:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, key, value)
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
        cookbook.cover_image_paths = _cookbook_cover_paths(cookbook.recipes)
    return cookbooks


_COOKBOOK_COVER_LIMIT = 4


def _cookbook_cover_paths(recipes: list[models.Recipe]) -> list[str]:
    """Até 4 fotos para a colagem da capa, por ordem de título — as receitas
    já vêm do selectinload de list_cookbooks, sem consultas extra."""
    ordered = sorted(recipes, key=lambda recipe: (recipe.title.casefold(), str(recipe.id)))
    return [recipe.image_path for recipe in ordered if recipe.image_path][:_COOKBOOK_COVER_LIMIT]


def create_cookbook(db: Session, workspace_id: uuid.UUID, payload: schemas.CookbookCreate) -> models.Cookbook:
    cookbook = models.Cookbook(workspace_id=workspace_id, name=payload.name)
    db.add(cookbook)
    db.commit()
    db.refresh(cookbook)
    cookbook.recipe_count = 0
    cookbook.cover_image_paths = []
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
    materialize_meal_plan_recurrences(db, workspace_id, start, end)
    query = _meal_plan_query(workspace_id).where(models.MealPlanEntry.day >= start, models.MealPlanEntry.day <= end)
    entries = list(db.scalars(query).unique())
    # MealPlanEntryOut.recipe é um RecipeSummary — exige is_favorite, que só
    # existe depois de anotado (ver models.py/_annotate_favorites).
    _annotate_favorites(db, user_id, [e.recipe for e in entries])
    return entries


def materialize_meal_plan_recurrences(db: Session, workspace_id: uuid.UUID, start: date, end: date) -> None:
    recurrences = list(
        db.scalars(
            select(models.MealPlanRecurrence).where(
                models.MealPlanRecurrence.workspace_id == workspace_id,
                models.MealPlanRecurrence.active.is_(True),
                models.MealPlanRecurrence.starts_on <= end,
                (models.MealPlanRecurrence.ends_on.is_(None) | (models.MealPlanRecurrence.ends_on >= start)),
            )
        )
    )
    if not recurrences:
        return
    existing = list(
        db.scalars(
            select(models.MealPlanEntry).where(
                models.MealPlanEntry.workspace_id == workspace_id,
                models.MealPlanEntry.day >= start,
                models.MealPlanEntry.day <= end,
            )
        )
    )
    occupied = {(entry.day, entry.meal_type) for entry in existing}
    changed = False
    for recurrence in recurrences:
        candidate = max(start, recurrence.starts_on)
        while candidate <= end:
            weeks_since_start = (candidate - recurrence.starts_on).days // 7
            if (
                candidate.weekday() == recurrence.weekday
                and weeks_since_start % recurrence.interval_weeks == 0
                and (recurrence.ends_on is None or candidate <= recurrence.ends_on)
                and (candidate, recurrence.meal_type) not in occupied
            ):
                db.add(
                    models.MealPlanEntry(
                        workspace_id=workspace_id,
                        day=candidate,
                        meal_type=recurrence.meal_type,
                        recipe_id=recurrence.recipe_id,
                    )
                )
                occupied.add((candidate, recurrence.meal_type))
                changed = True
            candidate += timedelta(days=1)
    if changed:
        db.commit()


def list_meal_plan_recurrences(db: Session, workspace_id: uuid.UUID) -> list[models.MealPlanRecurrence]:
    return list(
        db.scalars(
            select(models.MealPlanRecurrence)
            .where(models.MealPlanRecurrence.workspace_id == workspace_id)
            .order_by(models.MealPlanRecurrence.weekday, models.MealPlanRecurrence.meal_type)
        )
    )


def create_meal_plan_recurrence(
    db: Session, workspace_id: uuid.UUID, payload: schemas.MealPlanRecurrenceCreate
) -> models.MealPlanRecurrence | None:
    if get_recipe(db, workspace_id, payload.recipe_id) is None:
        return None
    recurrence = models.MealPlanRecurrence(workspace_id=workspace_id, **payload.model_dump())
    db.add(recurrence)
    db.commit()
    db.refresh(recurrence)
    return recurrence


def delete_meal_plan_recurrence(db: Session, workspace_id: uuid.UUID, recurrence_id: uuid.UUID) -> bool:
    recurrence = db.scalar(
        select(models.MealPlanRecurrence).where(
            models.MealPlanRecurrence.workspace_id == workspace_id,
            models.MealPlanRecurrence.id == recurrence_id,
        )
    )
    if recurrence is None:
        return False
    db.delete(recurrence)
    db.commit()
    return True


def suggest_meal_plan(db: Session, workspace_id: uuid.UUID, user_id: uuid.UUID, week_start: date) -> list[dict]:
    recipes = list_recipes(db, workspace_id, user_id, pantry_suggestions=True, safe_for_all=True)
    if not recipes:
        return []
    expiring = _pantry_tokens(
        db.scalars(
            select(models.PantryItem.name).where(
                models.PantryItem.workspace_id == workspace_id,
                models.PantryItem.has_it.is_(True),
                models.PantryItem.expires_on.is_not(None),
                models.PantryItem.expires_on <= week_start + timedelta(days=7),
            )
        )
    )

    def uses_expiring_product(recipe: models.Recipe) -> bool:
        return any(_in_pantry(ingredient.name, expiring) for ingredient in recipe.ingredients)

    recipes.sort(
        key=lambda recipe: (
            not uses_expiring_product(recipe),
            not recipe.is_favorite,
            -(recipe.rating or 0),
            recipe.missing_ingredient_count,
            recipe.last_made_at is not None,
            recipe.last_made_at or datetime.min.replace(tzinfo=UTC),
            (recipe.prep_minutes or 0) + (recipe.cook_minutes or 0),
            recipe.title.lower(),
        )
    )
    existing = list(
        db.scalars(
            select(models.MealPlanEntry).where(
                models.MealPlanEntry.workspace_id == workspace_id,
                models.MealPlanEntry.day >= week_start,
                models.MealPlanEntry.day <= week_start + timedelta(days=6),
            )
        )
    )
    occupied = {(entry.day, entry.meal_type) for entry in existing}
    suggestions: list[dict] = []
    recipe_index = 0
    for day_offset in range(7):
        day = week_start + timedelta(days=day_offset)
        for meal_type in ("almoco", "jantar"):
            if (day, meal_type) in occupied:
                continue
            recipe = recipes[recipe_index % len(recipes)]
            recipe_index += 1
            suggestions.append({"day": day, "meal_type": meal_type, "recipe": recipe})
    return suggestions


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


def _apply_meal_plan_slots(
    db: Session,
    workspace_id: uuid.UUID,
    week_start: date,
    slots: list[dict],
    overwrite: bool,
) -> None:
    week_end = week_start + timedelta(days=6)
    existing = list(
        db.scalars(
            select(models.MealPlanEntry).where(
                models.MealPlanEntry.workspace_id == workspace_id,
                models.MealPlanEntry.day >= week_start,
                models.MealPlanEntry.day <= week_end,
            )
        )
    )
    by_slot = {(entry.day, entry.meal_type): entry for entry in existing}
    valid_recipe_ids = set(db.scalars(select(models.Recipe.id).where(models.Recipe.workspace_id == workspace_id)))
    for slot in slots:
        recipe_id = uuid.UUID(str(slot["recipe_id"]))
        if recipe_id not in valid_recipe_ids:
            continue
        target = week_start + timedelta(days=int(slot["day_offset"]))
        key = (target, str(slot["meal_type"]))
        current = by_slot.get(key)
        if current is not None and not overwrite:
            continue
        if current is None:
            current = models.MealPlanEntry(
                workspace_id=workspace_id,
                day=target,
                meal_type=str(slot["meal_type"]),
                recipe_id=recipe_id,
            )
            db.add(current)
            by_slot[key] = current
        else:
            current.recipe_id = recipe_id
    db.commit()


def copy_meal_plan_week(
    db: Session,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    source_week_start: date,
    target_week_start: date,
    overwrite: bool,
) -> list[models.MealPlanEntry]:
    source_entries = list(
        db.scalars(
            select(models.MealPlanEntry).where(
                models.MealPlanEntry.workspace_id == workspace_id,
                models.MealPlanEntry.day >= source_week_start,
                models.MealPlanEntry.day <= source_week_start + timedelta(days=6),
            )
        )
    )
    slots = [
        {
            "day_offset": (entry.day - source_week_start).days,
            "meal_type": entry.meal_type,
            "recipe_id": str(entry.recipe_id),
        }
        for entry in source_entries
    ]
    _apply_meal_plan_slots(db, workspace_id, target_week_start, slots, overwrite)
    return list_meal_plan_entries(db, workspace_id, user_id, target_week_start, target_week_start + timedelta(days=6))


def list_meal_plan_templates(db: Session, workspace_id: uuid.UUID) -> list[models.MealPlanTemplate]:
    return list(
        db.scalars(
            select(models.MealPlanTemplate)
            .where(models.MealPlanTemplate.workspace_id == workspace_id)
            .order_by(models.MealPlanTemplate.name)
        )
    )


def save_meal_plan_template(
    db: Session, workspace_id: uuid.UUID, payload: schemas.MealPlanTemplateCreate
) -> models.MealPlanTemplate:
    entries = list(
        db.scalars(
            select(models.MealPlanEntry).where(
                models.MealPlanEntry.workspace_id == workspace_id,
                models.MealPlanEntry.day >= payload.week_start,
                models.MealPlanEntry.day <= payload.week_start + timedelta(days=6),
            )
        )
    )
    slots = [
        {
            "day_offset": (entry.day - payload.week_start).days,
            "meal_type": entry.meal_type,
            "recipe_id": str(entry.recipe_id),
        }
        for entry in entries
    ]
    template = db.scalar(
        select(models.MealPlanTemplate).where(
            models.MealPlanTemplate.workspace_id == workspace_id,
            func.lower(models.MealPlanTemplate.name) == payload.name.strip().lower(),
        )
    )
    if template is None:
        template = models.MealPlanTemplate(workspace_id=workspace_id, name=payload.name.strip(), slots=slots)
        db.add(template)
    else:
        template.slots = slots
    db.commit()
    db.refresh(template)
    return template


def apply_meal_plan_template(
    db: Session,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    template_id: uuid.UUID,
    payload: schemas.MealPlanTemplateApply,
) -> list[models.MealPlanEntry] | None:
    template = db.scalar(
        select(models.MealPlanTemplate).where(
            models.MealPlanTemplate.workspace_id == workspace_id,
            models.MealPlanTemplate.id == template_id,
        )
    )
    if template is None:
        return None
    _apply_meal_plan_slots(db, workspace_id, payload.week_start, template.slots, payload.overwrite)
    return list_meal_plan_entries(db, workspace_id, user_id, payload.week_start, payload.week_start + timedelta(days=6))


def delete_meal_plan_template(db: Session, workspace_id: uuid.UUID, template_id: uuid.UUID) -> bool:
    template = db.scalar(
        select(models.MealPlanTemplate).where(
            models.MealPlanTemplate.workspace_id == workspace_id,
            models.MealPlanTemplate.id == template_id,
        )
    )
    if template is None:
        return False
    db.delete(template)
    db.commit()
    return True


def list_shopping_list_items(db: Session, workspace_id: uuid.UUID) -> list[models.ShoppingListItem]:
    query = (
        select(models.ShoppingListItem)
        .where(models.ShoppingListItem.workspace_id == workspace_id)
        .options(selectinload(models.ShoppingListItem.source_recipes))
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


def delete_checked_shopping_list_items(db: Session, workspace_id: uuid.UUID) -> int:
    """Remove os itens já comprados (marcados); as ligações às receitas de
    origem saem por CASCADE na BD. Devolve quantos foram removidos."""
    result = db.execute(
        delete(models.ShoppingListItem).where(
            models.ShoppingListItem.workspace_id == workspace_id, models.ShoppingListItem.is_checked.is_(True)
        )
    )
    db.commit()
    return result.rowcount


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


def _attach_last_prices(
    db: Session, workspace_id: uuid.UUID, items: list[models.PantryItem]
) -> list[models.PantryItem]:
    """Preenche `item.last_price` (schemas.PantryItemOut) com a compra mais
    recente de cada item numa só query (`DISTINCT ON`), sem N+1."""
    ids = [item.id for item in items]
    latest: dict[uuid.UUID, models.PantryPriceEntry] = {}
    if ids:
        query = (
            select(models.PantryPriceEntry)
            .where(
                models.PantryPriceEntry.workspace_id == workspace_id,
                models.PantryPriceEntry.pantry_item_id.in_(ids),
            )
            .distinct(models.PantryPriceEntry.pantry_item_id)
            .order_by(
                models.PantryPriceEntry.pantry_item_id,
                models.PantryPriceEntry.purchased_on.desc(),
                models.PantryPriceEntry.created_at.desc(),
            )
        )
        latest = {entry.pantry_item_id: entry for entry in db.scalars(query)}
    for item in items:
        item.last_price = latest.get(item.id)
    return items


def list_pantry_items(db: Session, workspace_id: uuid.UUID) -> list[models.PantryItem]:
    query = (
        select(models.PantryItem).where(models.PantryItem.workspace_id == workspace_id).order_by(models.PantryItem.name)
    )
    return _attach_last_prices(db, workspace_id, list(db.scalars(query)))


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

    result = list(_upsert_pantry_items_by_name(db, workspace_id, cleaned).values())
    db.commit()
    for item in result:
        db.refresh(item)
    return _attach_last_prices(db, workspace_id, result)


def _upsert_pantry_items_by_name(
    db: Session, workspace_id: uuid.UUID, names: list[str]
) -> dict[str, models.PantryItem]:
    """Núcleo partilhado por `bulk_upsert_pantry_items` e `confirm_receipt`:
    um item por nome normalizado (pela ordem de `names`), criando os que
    faltam e marcando `has_it=True` nos existentes. Não faz commit."""
    existing = list(db.scalars(select(models.PantryItem).where(models.PantryItem.workspace_id == workspace_id)))
    existing_by_key = {_normalize(item.name): item for item in existing}

    result: dict[str, models.PantryItem] = {}
    for name in names:
        key = _normalize(name)
        if key in result:
            continue
        item = existing_by_key.get(key)
        if item is not None:
            item.has_it = True
        else:
            item = models.PantryItem(workspace_id=workspace_id, name=name)
            db.add(item)
        result[key] = item
    return result


def create_pantry_item(db: Session, workspace_id: uuid.UUID, payload: schemas.PantryItemIn) -> models.PantryItem:
    item = models.PantryItem(workspace_id=workspace_id, **payload.model_dump())
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
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return _attach_last_prices(db, workspace_id, [item])[0]


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


def _get_pantry_item(db: Session, workspace_id: uuid.UUID, item_id: uuid.UUID) -> models.PantryItem | None:
    query = select(models.PantryItem).where(
        models.PantryItem.workspace_id == workspace_id, models.PantryItem.id == item_id
    )
    return db.scalars(query).first()


def _clean_text(value: str | None) -> str | None:
    return (value.strip() or None) if value else None


def list_price_entries(
    db: Session, workspace_id: uuid.UUID, item_id: uuid.UUID
) -> list[models.PantryPriceEntry] | None:
    if _get_pantry_item(db, workspace_id, item_id) is None:
        return None
    entry = models.PantryPriceEntry
    query = (
        select(entry)
        .where(entry.workspace_id == workspace_id, entry.pantry_item_id == item_id)
        .order_by(entry.purchased_on.desc(), entry.created_at.desc())
    )
    return list(db.scalars(query))


def create_price_entry(
    db: Session, workspace_id: uuid.UUID, item_id: uuid.UUID, payload: schemas.PantryPriceEntryIn
) -> models.PantryPriceEntry | None:
    if _get_pantry_item(db, workspace_id, item_id) is None:
        return None
    entry = models.PantryPriceEntry(
        workspace_id=workspace_id,
        pantry_item_id=item_id,
        price=payload.price,
        quantity=payload.quantity,
        unit=_clean_text(payload.unit),
        store=_clean_text(payload.store),
        purchased_on=payload.purchased_on or date.today(),
        source="manual",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def delete_price_entry(db: Session, workspace_id: uuid.UUID, item_id: uuid.UUID, entry_id: uuid.UUID) -> bool:
    query = select(models.PantryPriceEntry).where(
        models.PantryPriceEntry.workspace_id == workspace_id,
        models.PantryPriceEntry.pantry_item_id == item_id,
        models.PantryPriceEntry.id == entry_id,
    )
    entry = db.scalars(query).first()
    if entry is None:
        return False
    db.delete(entry)
    db.commit()
    return True


def first_day_of_window(today: date, months: int) -> date:
    """Primeiro dia do mês que abre uma janela de `months` meses a terminar
    no mês de `today` (inclusive) — `months=1` é só o mês corrente."""
    month_index = today.year * 12 + today.month - 1 - (months - 1)
    return date(month_index // 12, month_index % 12 + 1, 1)


def get_price_history(
    db: Session, workspace_id: uuid.UUID, months: int, today: date | None = None
) -> schemas.PantryPriceHistory:
    """Séries por item (pontos por data, ascendente) e totais mensais do
    workspace nos últimos `months` meses. Só devolve meses com compras —
    o frontend preenche os meses vazios ao desenhar o gráfico."""
    start = first_day_of_window(today or date.today(), months)
    entry = models.PantryPriceEntry
    rows = db.execute(
        select(entry, models.PantryItem.name)
        .join(models.PantryItem, models.PantryItem.id == entry.pantry_item_id)
        .where(entry.workspace_id == workspace_id, entry.purchased_on >= start)
        .order_by(models.PantryItem.name, entry.purchased_on, entry.created_at)
    ).all()

    series: dict[uuid.UUID, schemas.PriceHistorySeries] = {}
    for price_entry, name in rows:
        current = series.setdefault(
            price_entry.pantry_item_id,
            schemas.PriceHistorySeries(item_id=price_entry.pantry_item_id, name=name, points=[]),
        )
        price = float(price_entry.price)
        quantity = float(price_entry.quantity) if price_entry.quantity is not None else None
        current.points.append(
            schemas.PriceHistoryPoint(
                purchased_on=price_entry.purchased_on,
                price=price,
                quantity=quantity,
                unit=price_entry.unit,
                unit_price=schemas.compute_unit_price(price, quantity),
            )
        )

    month = func.to_char(entry.purchased_on, "YYYY-MM")
    totals = db.execute(
        select(month, func.sum(entry.price))
        .where(entry.workspace_id == workspace_id, entry.purchased_on >= start)
        .group_by(month)
        .order_by(month)
    ).all()
    return schemas.PantryPriceHistory(
        items=list(series.values()),
        monthly_totals=[schemas.MonthlySpend(month=label, total=float(total)) for label, total in totals],
    )


def confirm_receipt(
    db: Session, workspace_id: uuid.UUID, payload: schemas.ReceiptConfirmIn
) -> tuple[list[models.PantryItem], int]:
    """Grava uma fatura revista pelo utilizador, numa só transação: upsert
    dos itens por nome (mesma regra de `bulk_upsert_pantry_items`),
    quantidade/unidade atualizadas quando a linha as traz, e uma entrada de
    preço `source="receipt"` por cada linha com preço. Devolve os itens e o
    número de entradas de preço criadas."""
    lines = [(line.name.strip(), line) for line in payload.items if line.name.strip()]
    items_by_key = _upsert_pantry_items_by_name(db, workspace_id, [name for name, _ in lines])
    db.flush()

    purchased_on = payload.purchased_on or date.today()
    store = _clean_text(payload.store)
    created = 0
    for name, line in lines:
        item = items_by_key[_normalize(name)]
        unit = _clean_text(line.unit)
        if line.quantity is not None:
            item.quantity = line.quantity
        if unit is not None:
            item.unit = unit
        if line.price is None:
            continue
        db.add(
            models.PantryPriceEntry(
                workspace_id=workspace_id,
                pantry_item_id=item.id,
                price=line.price,
                quantity=line.quantity,
                unit=unit,
                store=store,
                purchased_on=purchased_on,
                source="receipt",
            )
        )
        created += 1
    db.commit()
    items = list(items_by_key.values())
    for item in items:
        db.refresh(item)
    return _attach_last_prices(db, workspace_id, items), created


def _format_quantity(quantity, unit: str | None) -> str | None:
    parts = []
    if quantity is not None:
        parts.append(f"{float(quantity):g}")
    if unit:
        parts.append(unit)
    return " ".join(parts) if parts else None


def _link_listed_items_to_recipe(
    db: Session,
    workspace_id: uuid.UUID,
    recipe: models.Recipe,
    skip: list[models.ShoppingListItem],
    key: Callable[[str], str] = _normalize,
) -> None:
    """Junta `recipe` às origens dos itens por marcar que já estavam na lista
    com o nome de um dos seus ingredientes — esses ingredientes foram
    saltados pela dedup, mas a lista continua a dizer de onde vêm."""
    names = {key(ingredient.name) for ingredient in recipe.ingredients if not ingredient.is_header}
    query = (
        select(models.ShoppingListItem)
        .where(models.ShoppingListItem.workspace_id == workspace_id, models.ShoppingListItem.is_checked.is_(False))
        .options(selectinload(models.ShoppingListItem.source_recipes))
    )
    for item in db.scalars(query):
        if item in skip or key(item.name) not in names or recipe in item.source_recipes:
            continue
        item.source_recipes.append(recipe)


def generate_shopping_list(db: Session, workspace_id: uuid.UUID, week_start: date) -> list[models.ShoppingListItem]:
    """Agrega os ingredientes de todas as receitas planeadas na semana
    (week_start .. +6 dias) para a lista de compras. Quantidades com o mesmo
    nome e unidade são somadas; unidades diferentes permanecem separadas,
    pois não devem ser convertidas sem uma regra explícita.
    Cabeçalhos de secção (`is_header`) são ignorados, não são ingredientes
    reais. Ingredientes já disponíveis na despensa são excluídos. Para gerar
    não duplicar ao carregar duas vezes, salta ingredientes
    cujo nome já existe como item por marcar na lista — itens já comprados
    (marcados) não bloqueiam, para poder voltar a gerar depois de esvaziar o
    carrinho."""
    week_end = week_start + timedelta(days=6)
    entries = list(
        db.scalars(
            _meal_plan_query(workspace_id).where(
                models.MealPlanEntry.day >= week_start,
                models.MealPlanEntry.day <= week_end,
            )
        ).unique()
    )

    existing_query = select(models.ShoppingListItem.name).where(
        models.ShoppingListItem.workspace_id == workspace_id, models.ShoppingListItem.is_checked.is_(False)
    )
    existing_names = {_normalize(name) for name in db.scalars(existing_query)}

    pantry_query = select(models.PantryItem.name).where(
        models.PantryItem.workspace_id == workspace_id,
        models.PantryItem.has_it.is_(True),
    )
    pantry = _pantry_tokens(db.scalars(pantry_query))

    aggregated: dict[tuple[str, str], tuple[str, float, bool, str | None]] = {}
    sources: dict[tuple[str, str], list[models.Recipe]] = {}
    for entry in entries:
        for ingredient in entry.recipe.ingredients:
            if ingredient.is_header:
                continue
            normalized_name = _normalize(ingredient.name)
            if normalized_name in existing_names or _in_pantry(ingredient.name, pantry):
                continue
            normalized_unit = _normalize(ingredient.unit or "")
            key = (normalized_name, normalized_unit)
            previous = aggregated.get(key)
            amount = float(ingredient.quantity) if ingredient.quantity is not None else 0.0
            if previous is None:
                aggregated[key] = (ingredient.name, amount, ingredient.quantity is not None, ingredient.unit)
            else:
                aggregated[key] = (
                    previous[0],
                    previous[1] + amount,
                    previous[2] or ingredient.quantity is not None,
                    previous[3],
                )
            if entry.recipe not in sources.setdefault(key, []):
                sources[key].append(entry.recipe)

    new_items: list[models.ShoppingListItem] = []
    for key, (name, amount, has_quantity, unit) in aggregated.items():
        item = models.ShoppingListItem(
            workspace_id=workspace_id,
            name=name,
            quantity=_format_quantity(amount if has_quantity else None, unit),
            source_recipes=sources[key],
        )
        db.add(item)
        new_items.append(item)
    for recipe in {entry.recipe for entry in entries}:
        _link_listed_items_to_recipe(db, workspace_id, recipe, skip=new_items)

    db.commit()
    return list_shopping_list_items(db, workspace_id)


def add_recipe_to_shopping_list(
    db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID
) -> list[models.ShoppingListItem] | None:
    """Mesma lógica de dedup de `generate_shopping_list` (nomes normalizados),
    mas a partir dos ingredientes de uma única receita em vez de todo o plano
    semanal. Não exclui o que já está na despensa — isso é o
    `add_missing_recipe_ingredients_to_shopping_list`.
    Devolve só os itens novos (não a lista toda), para o frontend poder
    mostrar "N ingredientes adicionados" sem ter de comparar antes/depois."""
    recipe = get_recipe(db, workspace_id, recipe_id)
    if recipe is None:
        return None

    existing_query = select(models.ShoppingListItem.name).where(
        models.ShoppingListItem.workspace_id == workspace_id, models.ShoppingListItem.is_checked.is_(False)
    )
    existing_names = {_normalize(name) for name in db.scalars(existing_query)}

    new_items: list[models.ShoppingListItem] = []
    seen_this_run: set[str] = set()
    for ingredient in recipe.ingredients:
        if ingredient.is_header:
            continue
        normalized_name = _normalize(ingredient.name)
        if normalized_name in existing_names or normalized_name in seen_this_run:
            continue
        seen_this_run.add(normalized_name)
        item = models.ShoppingListItem(
            workspace_id=workspace_id,
            name=ingredient.name,
            quantity=_format_quantity(ingredient.quantity, ingredient.unit),
            source_recipes=[recipe],
        )
        db.add(item)
        new_items.append(item)
    _link_listed_items_to_recipe(db, workspace_id, recipe, skip=new_items, key=str)

    db.commit()
    for item in new_items:
        db.refresh(item)
    return new_items


def add_missing_recipe_ingredients_to_shopping_list(
    db: Session, workspace_id: uuid.UUID, recipe_id: uuid.UUID
) -> list[models.ShoppingListItem] | None:
    recipe = get_recipe(db, workspace_id, recipe_id)
    if recipe is None:
        return None
    pantry_query = select(models.PantryItem.name).where(
        models.PantryItem.workspace_id == workspace_id,
        models.PantryItem.has_it.is_(True),
    )
    pantry = _pantry_tokens(db.scalars(pantry_query))
    existing_query = select(models.ShoppingListItem.name).where(
        models.ShoppingListItem.workspace_id == workspace_id,
        models.ShoppingListItem.is_checked.is_(False),
    )
    existing_names = {_normalize(name) for name in db.scalars(existing_query)}

    new_items: list[models.ShoppingListItem] = []
    seen: set[str] = set()
    for ingredient in recipe.ingredients:
        normalized_name = _normalize(ingredient.name)
        if (
            ingredient.is_header
            or normalized_name in existing_names
            or normalized_name in seen
            or _in_pantry(ingredient.name, pantry)
        ):
            continue
        seen.add(normalized_name)
        item = models.ShoppingListItem(
            workspace_id=workspace_id,
            name=ingredient.name,
            quantity=_format_quantity(ingredient.quantity, ingredient.unit),
            source_recipes=[recipe],
        )
        db.add(item)
        new_items.append(item)
    _link_listed_items_to_recipe(db, workspace_id, recipe, skip=new_items)
    db.commit()
    for item in new_items:
        db.refresh(item)
    return new_items
