import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.deps import get_workspace_id

router = APIRouter(tags=["planning"])

MealType = Literal["almoco", "jantar"]


@router.get("/meal-plan", response_model=list[schemas.MealPlanEntryOut])
def list_meal_plan(
    start: date,
    end: date,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    return crud.list_meal_plan_entries(db, workspace_id, start, end)


@router.put("/meal-plan/{day}/{meal_type}", response_model=schemas.MealPlanEntryOut)
def upsert_meal_plan_entry(
    day: date,
    meal_type: MealType,
    payload: schemas.MealPlanEntryIn,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    entry = crud.upsert_meal_plan_entry(db, workspace_id, day, meal_type, payload.recipe_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Receita não encontrada")
    return entry


@router.delete("/meal-plan/{day}/{meal_type}", status_code=204)
def delete_meal_plan_entry(
    day: date,
    meal_type: MealType,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    if not crud.delete_meal_plan_entry(db, workspace_id, day, meal_type):
        raise HTTPException(status_code=404, detail="Não há receita atribuída a este dia/refeição")


@router.get("/shopping-list", response_model=list[schemas.ShoppingListItemOut])
def list_shopping_list(db: Session = Depends(get_db), workspace_id: uuid.UUID = Depends(get_workspace_id)):
    return crud.list_shopping_list_items(db, workspace_id)


# Registado antes de "/shopping-list/{item_id}" de propósito — mesmo motivo
# do "/import" em routers/recipes.py: o Starlette faz match por ordem de
# declaração, "/shopping-list/generate" seria interpretado como item_id.
@router.post("/shopping-list/generate", response_model=list[schemas.ShoppingListItemOut])
def generate_shopping_list(
    payload: schemas.GenerateShoppingListRequest,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    return crud.generate_shopping_list(db, workspace_id, payload.week_start)


@router.post("/shopping-list", response_model=schemas.ShoppingListItemOut, status_code=201)
def create_shopping_list_item(
    payload: schemas.ShoppingListItemIn,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    return crud.create_shopping_list_item(db, workspace_id, payload)


@router.patch("/shopping-list/{item_id}", response_model=schemas.ShoppingListItemOut)
def update_shopping_list_item(
    item_id: uuid.UUID,
    payload: schemas.ShoppingListItemUpdate,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    item = crud.update_shopping_list_item(db, workspace_id, item_id, payload)
    if item is None:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    return item


@router.delete("/shopping-list/{item_id}", status_code=204)
def delete_shopping_list_item(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    if not crud.delete_shopping_list_item(db, workspace_id, item_id):
        raise HTTPException(status_code=404, detail="Item não encontrado")
