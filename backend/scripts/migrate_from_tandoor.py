"""Migra receitas de um export "Default" do Tandoor para o tacho_app.

Uso:
    python -m scripts.migrate_from_tandoor caminho/para/tandoor-export.zip [--dry-run]

No Tandoor: Definições > Dados e Ferramentas > Exportar Dados > formato
"Default" (é o único que preserva todos os campos, incluindo fotos — os
outros formatos de export do Tandoor perdem dados ou não têm fotos; ver
backend/README.md, secção "Migração do Tandoor").

O esquema JSON abaixo foi confirmado a partir do código-fonte real do
Tandoor (github.com/TandoorRecipes/recipes, cookbook/integration/default.py
+ cookbook/serializer.py, `RecipeExportSerializer`), não adivinhado — mas
**nunca foi testado contra um export real desta instância** (não há acesso
a partir desta máquina às credenciais Authentik do Tandoor em
192.168.1.202 para gerar um). Correr sempre primeiro com --dry-run e
confirmar visualmente que os números fazem sentido antes de importar a
sério. Se a versão do Tandoor em uso for muito diferente da atual (o
próprio Tandoor documenta que import/export só é garantido entre a mesma
versão), alguns campos podem não bater certo — o script falha alto (não
silenciosamente) se `recipe.json` não tiver a forma esperada.

Estrutura do export "Default": um .zip externo contém um `<pk>.zip` por
receita; cada um desses contém `recipe.json` e, opcionalmente,
`image.<ext>`.

Limitações conhecidas desta migração (documentadas também no README):
- Fotos são extraídas para `--images-dir` mas NÃO ligadas a nenhuma receita
  — o tacho_app ainda não tem armazenamento de imagens implementado (não é
  scope desta migração, é uma funcionalidade própria por construir).
- "Categorias" do tacho_app ficam vazias — o export do Tandoor só tem
  "keywords", que mapeamos para Tags.
- Cabeçalhos de secção nos ingredientes (`is_header`, ex. "Para o molho:")
  são descartados — o nosso modelo de Ingredient não suporta agrupamento.
- Deduplicação é só por título igual dentro do workspace — recorrer duas
  vezes ao mesmo export não duplica receitas, mas duas receitas
  genuinamente diferentes com o mesmo título ficam por resolver à mão.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from zipfile import ZipFile

from sqlalchemy import select

from app import models
from app.constants import DEFAULT_WORKSPACE_ID
from app.database import SessionLocal


def _parse_amount(raw: object) -> float | None:
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value or None


def _zero_to_none(raw: object) -> int | None:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value or None


def _flatten_ingredients(steps: list[dict]) -> tuple[list[dict], int]:
    """Achata os ingredientes por passo do Tandoor numa única lista, na
    ordem dos passos. Devolve (ingredientes, nº de cabeçalhos descartados)."""
    flat: list[dict] = []
    skipped_headers = 0
    for step in steps:
        for ing in step.get("ingredients", []):
            if ing.get("is_header"):
                skipped_headers += 1
                continue
            food = ing.get("food") or {}
            unit = ing.get("unit") or {}
            name = food.get("name") or ing.get("note") or "(ingrediente sem nome)"
            if ing.get("note") and food.get("name"):
                name = f"{name} — {ing['note']}"
            flat.append(
                {
                    "name": name,
                    "quantity": _parse_amount(ing.get("amount")),
                    "unit": unit.get("name"),
                }
            )
    return flat, skipped_headers


def _build_steps(steps: list[dict]) -> list[str]:
    ordered = sorted(steps, key=lambda s: s.get("order", 0))
    instructions = []
    for step in ordered:
        text = step.get("instruction", "").strip()
        if step.get("name"):
            text = f"{step['name']}: {text}" if text else step["name"]
        if text:
            instructions.append(text)
    return instructions


def _get_or_create_tag(db, workspace_id, name: str, cache: dict[str, models.Tag]) -> models.Tag:
    if name in cache:
        return cache[name]
    tag = db.scalars(
        select(models.Tag).where(models.Tag.workspace_id == workspace_id, models.Tag.name == name)
    ).first()
    if tag is None:
        tag = models.Tag(workspace_id=workspace_id, name=name)
        db.add(tag)
        db.flush()
    cache[name] = tag
    return tag


def _recipe_exists(db, workspace_id, title: str) -> bool:
    return (
        db.scalars(
            select(models.Recipe.id).where(
                models.Recipe.workspace_id == workspace_id, models.Recipe.title == title
            )
        ).first()
        is not None
    )


def migrate(export_path: Path, *, dry_run: bool, images_dir: Path) -> None:
    db = None if dry_run else SessionLocal()
    tag_cache: dict[str, models.Tag] = {}

    imported = skipped_duplicates = 0
    total_ingredients = total_steps = total_headers_skipped = 0
    images_extracted = 0

    with ZipFile(export_path) as outer:
        inner_names = [n for n in outer.namelist() if n.endswith(".zip")]
        if not inner_names:
            sys.exit(
                f"Nenhum '<id>.zip' encontrado dentro de {export_path} — não parece um "
                "export 'Default' do Tandoor. Confirma o formato escolhido na exportação."
            )

        for inner_name in inner_names:
            with ZipFile(outer.open(inner_name)) as inner:
                try:
                    raw = inner.read("recipe.json").decode("utf-8")
                except KeyError:
                    sys.exit(f"{inner_name} não tem recipe.json — export inesperado, a abortar.")
                data = json.loads(raw)

                image_names = [n for n in inner.namelist() if n.startswith("image")]
                if image_names:
                    images_extracted += 1
                    if not dry_run:
                        images_dir.mkdir(parents=True, exist_ok=True)
                        suffix = Path(image_names[0]).suffix or ".jpg"
                        stem = Path(inner_name).stem
                        (images_dir / f"{stem}{suffix}").write_bytes(inner.read(image_names[0]))

            title = data.get("name")
            if not title:
                sys.exit(f"{inner_name}: recipe.json sem campo 'name' — export inesperado, a abortar.")

            if not dry_run and _recipe_exists(db, DEFAULT_WORKSPACE_ID, title):
                skipped_duplicates += 1
                print(f"  [salta] já existe uma receita com o título '{title}'")
                continue

            steps_raw = data.get("steps", [])
            ingredients, headers_skipped = _flatten_ingredients(steps_raw)
            step_texts = _build_steps(steps_raw)
            tag_names = [k["name"] for k in data.get("keywords", []) if k.get("name")]

            total_ingredients += len(ingredients)
            total_steps += len(step_texts)
            total_headers_skipped += headers_skipped

            print(
                f"  {title} — {len(ingredients)} ingrediente(s), {len(step_texts)} passo(s), "
                f"{len(tag_names)} tag(s)"
            )

            if dry_run:
                imported += 1
                continue

            recipe = models.Recipe(
                workspace_id=DEFAULT_WORKSPACE_ID,
                title=title,
                description=data.get("description") or None,
                servings=_zero_to_none(data.get("servings")),
                prep_minutes=_zero_to_none(data.get("working_time")),
                cook_minutes=_zero_to_none(data.get("waiting_time")),
                source_url=data.get("source_url") or None,
                ingredients=[
                    models.Ingredient(position=i, name=ing["name"], quantity=ing["quantity"], unit=ing["unit"])
                    for i, ing in enumerate(ingredients)
                ],
                steps=[models.Step(position=i, instruction=text) for i, text in enumerate(step_texts)],
                tags=[_get_or_create_tag(db, DEFAULT_WORKSPACE_ID, name, tag_cache) for name in tag_names],
            )
            db.add(recipe)
            imported += 1

    if not dry_run:
        db.commit()
        db.close()

    print()
    print(f"{'[dry-run] ' if dry_run else ''}Receitas importadas: {imported}")
    print(f"Receitas saltadas (título já existia): {skipped_duplicates}")
    print(f"Ingredientes: {total_ingredients} (cabeçalhos de secção descartados: {total_headers_skipped})")
    print(f"Passos: {total_steps}")
    print(f"Tags criadas/reutilizadas: {len(tag_cache)}")
    print(f"Receitas com foto no export (NÃO importada — só extraída): {images_extracted}")
    if images_extracted and not dry_run:
        print(f"  fotos guardadas em: {images_dir}/")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("export_zip", type=Path, help="Export 'Default' do Tandoor (.zip)")
    parser.add_argument(
        "--dry-run", action="store_true", help="Só analisa e imprime um resumo, não escreve na base de dados"
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=Path("imports/tandoor_images"),
        help="Onde guardar as fotos extraídas (default: imports/tandoor_images/)",
    )
    args = parser.parse_args()

    if not args.export_zip.exists():
        sys.exit(f"Ficheiro não encontrado: {args.export_zip}")

    migrate(args.export_zip, dry_run=args.dry_run, images_dir=args.images_dir)


if __name__ == "__main__":
    main()
