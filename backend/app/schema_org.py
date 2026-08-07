from app import models


def _duration(minutes: int | None) -> str | None:
    return f"PT{minutes}M" if minutes else None


def _format_quantity(quantity) -> str:
    value = float(quantity)
    if value == int(value):
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _ingredient_line(ing: models.Ingredient) -> str:
    parts = []
    if ing.quantity is not None:
        parts.append(_format_quantity(ing.quantity))
    if ing.unit:
        parts.append(ing.unit)
    parts.append(ing.name)
    return " ".join(parts)


def recipe_to_schema_org(recipe: models.Recipe, image_url: str | None) -> dict:
    """Serializa a receita no formato schema.org/Recipe (JSON-LD) — o mesmo
    standard que os sites de receitas publicam e que o recipe-scrapers lê,
    para qualquer app futura poder importar sem script dedicado (TODO.md)."""
    data: dict = {
        "@context": "https://schema.org/",
        "@type": "Recipe",
        "name": recipe.title,
    }
    if recipe.description:
        data["description"] = recipe.description
    if image_url:
        data["image"] = [image_url]
    if recipe.servings:
        data["recipeYield"] = str(recipe.servings)
    if recipe.prep_minutes:
        data["prepTime"] = _duration(recipe.prep_minutes)
    if recipe.cook_minutes:
        data["cookTime"] = _duration(recipe.cook_minutes)
    total_minutes = (recipe.prep_minutes or 0) + (recipe.cook_minutes or 0)
    if total_minutes:
        data["totalTime"] = _duration(total_minutes)

    # Cabeçalhos de secção (Ingredient.is_header) não têm equivalente
    # direto em recipeIngredient — schema.org espera uma lista plana de
    # ingredientes reais, por isso ficam de fora.
    ingredients = [_ingredient_line(ing) for ing in recipe.ingredients if not ing.is_header]
    if ingredients:
        data["recipeIngredient"] = ingredients

    if recipe.steps:
        data["recipeInstructions"] = [
            {"@type": "HowToStep", "text": step.instruction} for step in recipe.steps
        ]

    if recipe.categories:
        data["recipeCategory"] = [c.name for c in recipe.categories]
    if recipe.tags:
        data["keywords"] = ", ".join(t.name for t in recipe.tags)

    nutrition = {}
    if recipe.calories_kcal is not None:
        nutrition["calories"] = f"{recipe.calories_kcal} kcal"
    if recipe.protein_g is not None:
        nutrition["proteinContent"] = f"{_format_quantity(recipe.protein_g)} g"
    if recipe.carbs_g is not None:
        nutrition["carbohydrateContent"] = f"{_format_quantity(recipe.carbs_g)} g"
    if recipe.fat_g is not None:
        nutrition["fatContent"] = f"{_format_quantity(recipe.fat_g)} g"
    if nutrition:
        nutrition["@type"] = "NutritionInformation"
        data["nutrition"] = nutrition

    return data
