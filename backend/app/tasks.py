import re
import uuid
from collections.abc import Callable

from recipe_scrapers import AbstractScraper, WebsiteNotImplementedError, scrape_html, scrape_me

from app import gemini, models
from app.celery_app import celery_app
from app.config import get_settings
from app.database import SessionLocal
from app.images import save_recipe_image_from_url


def _safe_field(getter: Callable[[], object]) -> object | None:
    """recipe-scrapers raises when a site doesn't expose a given field —
    treat that the same as the field being missing rather than failing the
    whole import (see backend/README.md, "Limitações conhecidas")."""
    try:
        return getter()
    except Exception:
        return None


def _parse_servings(yields: str | None) -> int | None:
    if not yields:
        return None
    match = re.search(r"\d+", yields)
    return int(match.group()) if match else None


# Unidades PT reconhecidas para separar a linha scraped em quantidade/unidade/
# nome (ver backend/README.md, "Limitações conhecidas"). Ordem importa: as
# variantes compostas ("colher de sopa") têm de vir antes de "colher" sozinho,
# senão o regex para cedo demais e deixa "de sopa" preso ao nome.
_INGREDIENT_UNIT_ALTERNATIVES = (
    r"colher(?:es)?\s+de\s+sopa",
    r"colher(?:es)?\s+de\s+ch[áa]",
    r"colher(?:es)?\s+de\s+caf[ée]",
    r"colher(?:es)?",
    r"c\.\s+de\s+sopa",
    r"c\.\s+de\s+ch[áa]",
    r"c\.\s+de\s+caf[ée]",
    r"ch[áa]venas?",
    r"copos?",
    r"dentes?",
    r"fatias?",
    r"ramos?",
    r"raminhos?",
    r"folhas?",
    r"pitadas?",
    r"punhados?",
    r"latas?",
    r"pacotes?",
    r"embalage(?:m|ns)",
    r"unidades?",
    r"unid\.",
    r"quilos?",
    r"gramas?",
    r"mililitros?",
    r"litros?",
    r"kg",
    r"gr",
    r"g",
    r"ml",
    r"dl",
    r"l",
)
# (?!\w) em vez de \b: unidades abreviadas terminam em "." (ex. "unid.",
# "c."), e \b não conta como fronteira entre dois caracteres não-palavra
# (o "." e o espaço a seguir seriam ambos "não-palavra") — ficava por
# combinar mesmo com a unidade certa.
_UNIT_RE = re.compile(r"^\s*(" + "|".join(_INGREDIENT_UNIT_ALTERNATIVES) + r")(?!\w)", re.IGNORECASE)
_LEADING_DE_RE = re.compile(r"^\s*(?:de|d['’])\s+", re.IGNORECASE)

_FRACTIONS = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3, "⅛": 0.125}
_QUANTITY_RE = re.compile(r"^\s*(\d+/\d+|\d+(?:[.,]\d+)?|[" + "".join(_FRACTIONS) + r"])")
# "2-3 dentes" / "2 a 3 dentes" — intervalo, não um número só; guardar como
# número único seria adivinhar qual dos dois lados fica, por isso a linha
# inteira fica por parsear nestes casos (mesma disciplina do _extract_steps:
# nunca arriscar destruir informação real por uma heurística).
_RANGE_AFTER_RE = re.compile(r"^\s*(-|a\s)\s*\d")
# Alguns sites (ex. pingodoce.pt) escrevem "1 q.b. salsa fresca" — o "1" não
# é uma quantidade real, é só o formato deles para "quanto baste"/"a gosto".
# Tratar como quantidade dava um número enganador; fica tudo por parsear.
_QB_AFTER_RE = re.compile(r"^\s*q\.?\s*b\.?\b", re.IGNORECASE)


def _parse_quantity(raw: str) -> float | None:
    if "/" in raw:
        num, _, den = raw.partition("/")
        return round(int(num) / int(den), 2)
    if raw in _FRACTIONS:
        return round(_FRACTIONS[raw], 2)
    return float(raw.replace(",", "."))


def _parse_ingredient_line(line: str) -> tuple[str, float | None, str | None]:
    """Separa "500 g de bacalhau desfiado" em (name="bacalhau desfiado",
    quantity=500, unit="g"). Só separa quando tem a certeza — quantidades em
    intervalo, frações mistas ("1 ½"), ou linhas sem quantidade no início
    (ex. "Sal q.b.", "Azeite (opcional)") ficam com a linha original intacta
    em `name` e quantity/unit a None, em vez de arriscar um split errado."""
    quantity_match = _QUANTITY_RE.match(line)
    if not quantity_match:
        return line, None, None
    rest = line[quantity_match.end() :]
    if _RANGE_AFTER_RE.match(rest) or _QB_AFTER_RE.match(rest):
        return line, None, None
    try:
        quantity = _parse_quantity(quantity_match.group(1))
    except (ValueError, ZeroDivisionError):
        return line, None, None

    unit_match = _UNIT_RE.match(rest)
    if not unit_match:
        name = rest.strip()
        return (name or line), (quantity if name else None), None

    unit = unit_match.group(1)
    name = _LEADING_DE_RE.sub("", rest[unit_match.end() :].strip(" ,;")).strip()
    if not name:
        # "500 g" sem nenhum ingrediente a seguir — não deve acontecer numa
        # receita real, mas se acontecer é mais seguro devolver a linha
        # completa do que um Ingredient sem nome.
        return line, None, None
    return name, quantity, unit


# Alguns sites publicam JSON-LD malformado onde uma HowToSection tem
# `itemListElement` como um dict solto em vez de uma lista (visto em
# mundodereceitasbimby.com.pt). O recipe-scrapers, ao fazer `for item in
# schema_item.get("itemListElement")` sobre esse dict, itera as suas
# chaves como se fossem passos — devolve "@type", "position", "name",
# "text" soltos no meio de passos reais. Filtramos só correspondências
# exatas (não por comprimento) para nunca arriscar apagar um passo real
# só porque é curto (ex. "Sirva.").
_SCHEMA_ORG_KEY_LEAKS = frozenset(
    {"@type", "@context", "name", "text", "position", "url", "image", "itemlistelement", "howtostep", "howtosection"}
)


def _extract_steps(scraper: AbstractScraper) -> list[str]:
    steps = _safe_field(scraper.instructions_list) or []
    if not steps:
        raw = _safe_field(scraper.instructions) or ""
        steps = [line.strip() for line in raw.split("\n") if line.strip()]
    return [step for step in steps if step.strip().lower() not in _SCHEMA_ORG_KEY_LEAKS]


def _scrape(url: str) -> AbstractScraper:
    try:
        return scrape_me(url)
    except WebsiteNotImplementedError:
        # No site-specific scraper — fall back to generic schema.org parsing.
        return scrape_html(None, url, online=True, wild_mode=True)


@celery_app.task(name="tacho.import_recipe_from_url", bind=True)
def import_recipe_from_url(self, url: str, workspace_id: str) -> str:
    scraper = _scrape(url)

    # Gerado já aqui (em vez de deixar o INSERT atribuir um) para a foto
    # poder ser descarregada logo para a pasta certa (`receitas/<recipe_id>/`)
    # antes da receita existir na BD.
    recipe_id = uuid.uuid4()

    prep_minutes = _safe_field(scraper.prep_time)
    cook_minutes = _safe_field(scraper.cook_time) or _safe_field(scraper.total_time)
    image_url = _safe_field(scraper.image)
    image_path = save_recipe_image_from_url(image_url, get_settings(), recipe_id) if image_url else None

    ingredients = [
        models.Ingredient(position=i, name=name, quantity=quantity, unit=unit)
        for i, (name, quantity, unit) in enumerate(
            _parse_ingredient_line(line) for line in _safe_field(scraper.ingredients) or []
        )
    ]
    steps = [models.Step(position=i, instruction=line) for i, line in enumerate(_extract_steps(scraper))]

    # Fallback via Gemini só quando o recipe-scrapers não trouxe NADA de
    # nenhum dos dois — nunca para "melhorar" um resultado que já veio
    # preenchido. Usa os campos já estruturados da extração diretamente,
    # sem os achatar de volta a texto e reparsear (⚠️ não testado contra a
    # API real, ver app/gemini.py).
    if not ingredients and not steps and gemini.is_available(get_settings()):
        extraction = gemini.extract_from_html(get_settings(), scraper.page_data)
        if extraction is not None:
            ingredients = [
                models.Ingredient(
                    position=i, name=ing.name, quantity=ing.quantity, unit=ing.unit, is_header=ing.is_header
                )
                for i, ing in enumerate(extraction.ingredients)
            ]
            steps = [
                models.Step(position=i, instruction=step.instruction, duration_minutes=step.duration_minutes)
                for i, step in enumerate(extraction.steps)
            ]

    db = SessionLocal()
    try:
        recipe = models.Recipe(
            id=recipe_id,
            workspace_id=uuid.UUID(workspace_id),
            title=scraper.title(),
            servings=_parse_servings(_safe_field(scraper.yields)),
            prep_minutes=prep_minutes,
            cook_minutes=cook_minutes,
            source_url=url,
            image_path=image_path,
            ingredients=ingredients,
            steps=steps,
        )
        db.add(recipe)
        db.commit()
        db.refresh(recipe)
        return str(recipe.id)
    finally:
        db.close()
