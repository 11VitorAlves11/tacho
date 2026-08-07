import re
import uuid
from collections.abc import Callable

from recipe_scrapers import AbstractScraper, WebsiteNotImplementedError, scrape_html, scrape_me

from app import models
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

    prep_minutes = _safe_field(scraper.prep_time)
    cook_minutes = _safe_field(scraper.cook_time) or _safe_field(scraper.total_time)
    image_url = _safe_field(scraper.image)
    image_path = save_recipe_image_from_url(image_url, get_settings()) if image_url else None

    db = SessionLocal()
    try:
        recipe = models.Recipe(
            workspace_id=uuid.UUID(workspace_id),
            title=scraper.title(),
            servings=_parse_servings(_safe_field(scraper.yields)),
            prep_minutes=prep_minutes,
            cook_minutes=cook_minutes,
            source_url=url,
            image_path=image_path,
            # Scraped ingredient lines aren't split into quantity/unit/name —
            # see backend/README.md, "Limitações conhecidas".
            ingredients=[
                models.Ingredient(position=i, name=line) for i, line in enumerate(scraper.ingredients())
            ],
            steps=[
                models.Step(position=i, instruction=line) for i, line in enumerate(_extract_steps(scraper))
            ],
        )
        db.add(recipe)
        db.commit()
        db.refresh(recipe)
        return str(recipe.id)
    finally:
        db.close()
