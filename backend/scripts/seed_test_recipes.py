"""Cria dez receitas visuais de demonstração no primeiro workspace.

Seguro para voltar a executar: os UUIDs são estáveis e receitas já existentes
com esses UUIDs não são alteradas.
"""

from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path

from sqlalchemy import select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings
from app.database import SessionLocal
from app.models import Category, Ingredient, Recipe, Step, Tag, Workspace


NAMESPACE = uuid.UUID("8b0b3772-077f-4e33-b5b7-aef6e1201cb6")
ASSET_DIR = BACKEND_ROOT / "test-data" / "recipe-images"

RECIPES = [
    {
        "slug": "esparguete-bolonhesa", "title": "Esparguete à Bolonhesa",
        "description": "Um clássico reconfortante com molho de tomate e carne lentamente apurado.",
        "servings": 4, "prep": 15, "cook": 35, "category": "Jantar", "tags": ["Massa", "Família"],
        "ingredients": [(400, "g", "esparguete"), (500, "g", "carne de vaca picada"), (400, "g", "tomate triturado"), (1, None, "cebola"), (2, None, "dentes de alho")],
        "steps": [("Refogar a cebola e o alho num fio de azeite.", 5), ("Juntar a carne e deixar alourar.", 8), ("Adicionar o tomate e cozinhar em lume brando.", 20), ("Cozer o esparguete e servir com o molho.", 12)],
    },
    {
        "slug": "strogonoff-frango", "title": "Strogonoff de Frango com Arroz",
        "description": "Frango tenro num molho cremoso, servido com arroz branco soltinho.",
        "servings": 4, "prep": 10, "cook": 25, "category": "Jantar", "tags": ["Frango", "Rápida"],
        "ingredients": [(600, "g", "peito de frango"), (200, "ml", "natas"), (150, "g", "cogumelos"), (1, "c. sopa", "mostarda"), (250, "g", "arroz")],
        "steps": [("Cozer o arroz em água temperada.", 12), ("Saltear o frango cortado em tiras.", 8), ("Juntar os cogumelos, a mostarda e as natas.", 8)],
    },
    {
        "slug": "bolo-chocolate", "title": "Bolo de Chocolate Fofo",
        "description": "Bolo húmido e intenso, coberto com ganache de chocolate negro.",
        "servings": 10, "prep": 20, "cook": 40, "category": "Sobremesa", "tags": ["Chocolate", "Forno"],
        "ingredients": [(200, "g", "chocolate negro"), (200, "g", "farinha"), (180, "g", "açúcar"), (4, None, "ovos"), (150, "g", "manteiga")],
        "steps": [("Derreter o chocolate com a manteiga.", 5), ("Bater os ovos com o açúcar e envolver a farinha.", 8), ("Adicionar o chocolate e levar ao forno a 180 ºC.", 35)],
    },
    {
        "slug": "salada-frango", "title": "Salada com Frango Grelhado",
        "description": "Uma salada fresca e completa com frango dourado e legumes crocantes.",
        "servings": 2, "prep": 15, "cook": 10, "category": "Almoço", "tags": ["Frango", "Rápida", "Leve"],
        "ingredients": [(300, "g", "peito de frango"), (150, "g", "mistura de alfaces"), (150, "g", "tomate-cereja"), (1, None, "pepino"), (1, "c. sopa", "azeite")],
        "steps": [("Temperar e grelhar o frango.", 10), ("Lavar e cortar os legumes.", 5), ("Fatiar o frango e montar a salada.", 3)],
    },
    {
        "slug": "sopa-abobora", "title": "Sopa de Abóbora com Gengibre",
        "description": "Creme aveludado de abóbora com um toque quente de gengibre.",
        "servings": 4, "prep": 10, "cook": 30, "category": "Sopa", "tags": ["Vegetariana", "Conforto"],
        "ingredients": [(800, "g", "abóbora"), (1, None, "cebola"), (1, None, "batata"), (15, "g", "gengibre fresco"), (750, "ml", "caldo de legumes")],
        "steps": [("Cortar os legumes em cubos.", 8), ("Cozer tudo no caldo até ficar macio.", 25), ("Triturar até obter um creme liso.", 3)],
    },
    {
        "slug": "bacalhau-bras", "title": "Bacalhau à Brás",
        "description": "Bacalhau desfiado com batata palha, ovos cremosos, salsa e azeitonas.",
        "servings": 4, "prep": 20, "cook": 25, "category": "Jantar", "tags": ["Peixe", "Português"],
        "ingredients": [(500, "g", "bacalhau demolhado"), (400, "g", "batata palha"), (6, None, "ovos"), (2, None, "cebolas"), (80, "g", "azeitonas pretas")],
        "steps": [("Alourar a cebola em azeite.", 10), ("Juntar o bacalhau e cozinhar.", 8), ("Envolver a batata e os ovos sem os deixar secar.", 5)],
    },
    {
        "slug": "caril-grao", "title": "Caril de Grão-de-Bico",
        "description": "Caril cremoso e aromático com grão, tomate e espinafres.",
        "servings": 4, "prep": 10, "cook": 25, "category": "Jantar", "tags": ["Vegetariana", "Rápida"],
        "ingredients": [(500, "g", "grão-de-bico cozido"), (400, "ml", "leite de coco"), (200, "g", "tomate"), (100, "g", "espinafres"), (2, "c. sopa", "caril em pó")],
        "steps": [("Refogar as especiarias.", 3), ("Juntar o tomate, o grão e o leite de coco.", 18), ("Envolver os espinafres e servir.", 3)],
    },
    {
        "slug": "panquecas-aveia", "title": "Panquecas de Aveia e Banana",
        "description": "Panquecas macias e naturalmente doces, ideais para um pequeno-almoço rápido.",
        "servings": 2, "prep": 5, "cook": 10, "category": "Pequeno-almoço", "tags": ["Rápida", "Sem açúcar"],
        "ingredients": [(1, None, "banana madura"), (100, "g", "flocos de aveia"), (2, None, "ovos"), (1, "c. chá", "canela"), (1, "c. chá", "fermento")],
        "steps": [("Triturar todos os ingredientes.", 2), ("Cozinhar pequenas porções numa frigideira antiaderente.", 8), ("Servir com fruta fresca.", 2)],
    },
    {
        "slug": "arroz-pato", "title": "Arroz de Pato",
        "description": "Arroz de forno rico e dourado, com pato desfiado e rodelas de chouriço.",
        "servings": 6, "prep": 25, "cook": 60, "category": "Jantar", "tags": ["Português", "Forno"],
        "ingredients": [(1.2, "kg", "pato"), (400, "g", "arroz agulha"), (150, "g", "chouriço"), (1, None, "cebola"), (1, "l", "caldo da cozedura")],
        "steps": [("Cozer o pato e reservar o caldo.", 40), ("Desfiar o pato e preparar o refogado.", 12), ("Cozer o arroz no caldo e montar o tabuleiro.", 15), ("Levar ao forno até dourar.", 20)],
    },
    {
        "slug": "tarte-maca", "title": "Tarte de Maçã e Canela",
        "description": "Tarte rústica com maçã caramelizada, massa estaladiça e aroma de canela.",
        "servings": 8, "prep": 20, "cook": 40, "category": "Sobremesa", "tags": ["Fruta", "Forno"],
        "ingredients": [(1, None, "base de massa quebrada"), (5, None, "maçãs"), (80, "g", "açúcar mascavado"), (1, "c. chá", "canela"), (20, "g", "manteiga")],
        "steps": [("Forrar a tarteira com a massa.", 5), ("Fatiar e temperar as maçãs.", 10), ("Dispor a maçã e levar ao forno a 180 ºC.", 40)],
    },
]


def stable_id(kind: str, slug: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"{kind}:{slug}")


def get_or_create_taxonomy(db, model, workspace_id, name):
    item = db.scalar(select(model).where(model.workspace_id == workspace_id, model.name == name))
    if item is None:
        item = model(id=stable_id(model.__tablename__, name), workspace_id=workspace_id, name=name)
        db.add(item)
        db.flush()
    return item


def main() -> None:
    settings = get_settings()
    image_root = Path(settings.images_dir)
    created = 0
    skipped = 0

    with SessionLocal() as db:
        workspace = db.scalars(select(Workspace).order_by(Workspace.created_at)).first()
        if workspace is None:
            raise RuntimeError("Não existe nenhum workspace. Cria primeiro uma conta na aplicação.")

        for data in RECIPES:
            recipe_id = stable_id("recipe", data["slug"])
            if db.get(Recipe, recipe_id) is not None:
                skipped += 1
                continue

            relative_image = Path("receitas") / str(recipe_id) / f"{data['slug']}.png"
            destination = image_root / relative_image
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ASSET_DIR / f"{data['slug']}.png", destination)

            recipe = Recipe(
                id=recipe_id, workspace_id=workspace.id, title=data["title"],
                description=data["description"], servings=data["servings"],
                prep_minutes=data["prep"], cook_minutes=data["cook"],
                source_url=None, notes="Receita de demonstração", image_path=str(relative_image),
                calories_kcal=None, protein_g=None, carbs_g=None, fat_g=None,
                estimated_cost=None, last_made_at=None, rating=None,
                share_token=None, share_expires_at=None,
            )
            db.add(recipe)
            recipe.categories.append(get_or_create_taxonomy(db, Category, workspace.id, data["category"]))
            recipe.tags.extend(get_or_create_taxonomy(db, Tag, workspace.id, name) for name in data["tags"])
            recipe.ingredients.extend(
                Ingredient(position=position, quantity=quantity, unit=unit, name=name, is_header=False)
                for position, (quantity, unit, name) in enumerate(data["ingredients"])
            )
            recipe.steps.extend(
                Step(position=position, instruction=instruction, duration_minutes=duration)
                for position, (instruction, duration) in enumerate(data["steps"])
            )
            created += 1

        db.commit()

    print(f"Receitas criadas: {created}; já existentes: {skipped}")


if __name__ == "__main__":
    main()
