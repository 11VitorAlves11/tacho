import requests

from app import schemas

OFF_SEARCH_URL = "https://world.openfoodfacts.org/api/v2/search"

# Fator de conversão para gramas-equivalente. ml/dl/l assumem densidade ~1
# (água) — aproximação grosseira mas aceitável para uma estimativa, não
# para dados de saúde precisos (o próprio TODO.md já assinala esse risco
# para a importação por foto via Gemini; aqui aplica-se o mesmo cuidado).
_GRAMS_PER_UNIT = {"g": 1, "kg": 1000, "ml": 1, "l": 1000, "dl": 100}

_NUTRIMENT_FIELDS = {
    "calories_kcal": "energy-kcal_100g",
    "protein_g": "proteins_100g",
    "carbs_g": "carbohydrates_100g",
    "fat_g": "fat_100g",
}


def _search_off(name: str) -> dict | None:
    """Pesquisa a Open Food Facts pelo nome do ingrediente, devolve o
    primeiro produto com pelo menos um valor nutricional, ou None em
    qualquer falha — rede em baixo, timeout, resposta inesperada, sem
    resultados. Nunca levanta: uma estimativa nunca deve chumbar por causa
    de um único ingrediente sem correspondência."""
    try:
        response = requests.get(
            OFF_SEARCH_URL,
            params={"search_terms": name, "fields": "nutriments", "page_size": 5},
            timeout=8,
            headers={"User-Agent": "TachoApp/1.0 (https://receitas.alveslab.dev)"},
        )
        response.raise_for_status()
        products = response.json().get("products", [])
    except (requests.RequestException, ValueError):
        return None

    for product in products:
        nutriments = product.get("nutriments") or {}
        if any(field in nutriments for field in _NUTRIMENT_FIELDS.values()):
            return nutriments
    return None


def estimate_nutrition(ingredients: list[schemas.IngredientIn], servings: int | None) -> schemas.NutritionEstimate:
    """Soma os nutrientes de todos os ingredientes (receita inteira) e só no
    fim divide pelas porções — `Recipe.calories_kcal`/etc. são "por porção"
    (RecipeForm.tsx), não pela receita toda. Sem porções definidas, assume
    1 (mostra o total da receita) em vez de recusar a estimativa."""
    totals = {key: 0.0 for key in _NUTRIMENT_FIELDS}
    matched = 0
    skipped = 0
    portions = servings if servings and servings > 0 else 1

    for ingredient in ingredients:
        if ingredient.is_header:
            continue
        unit = (ingredient.unit or "").strip().lower()
        grams_per_unit = _GRAMS_PER_UNIT.get(unit)
        if ingredient.quantity is None or grams_per_unit is None:
            skipped += 1
            continue

        nutriments = _search_off(ingredient.name)
        if nutriments is None:
            skipped += 1
            continue

        grams = float(ingredient.quantity) * grams_per_unit
        for key, off_field in _NUTRIMENT_FIELDS.items():
            value = nutriments.get(off_field)
            if value is not None:
                totals[key] += float(value) * grams / 100
        matched += 1

    if matched == 0:
        return schemas.NutritionEstimate(
            calories_kcal=None, protein_g=None, carbs_g=None, fat_g=None, matched_count=0, skipped_count=skipped
        )

    return schemas.NutritionEstimate(
        calories_kcal=round(totals["calories_kcal"] / portions),
        protein_g=round(totals["protein_g"] / portions, 1),
        carbs_g=round(totals["carbs_g"] / portions, 1),
        fat_g=round(totals["fat_g"] / portions, 1),
        matched_count=matched,
        skipped_count=skipped,
    )
