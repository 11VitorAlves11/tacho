import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.auth import current_active_user
from app.database import get_db
from app.deps import get_workspace_id
from app.models import User

router = APIRouter(tags=["planning"])

MealType = Literal["pequeno_almoco", "almoco", "lanche", "jantar"]


@router.get("/meal-plan", response_model=list[schemas.MealPlanEntryOut])
def list_meal_plan(
    start: date,
    end: date,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    user: User = Depends(current_active_user),
):
    return crud.list_meal_plan_entries(db, workspace_id, user.id, start, end)


@router.put("/meal-plan/{day}/{meal_type}", response_model=schemas.MealPlanEntryOut)
def upsert_meal_plan_entry(
    day: date,
    meal_type: MealType,
    payload: schemas.MealPlanEntryIn,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    user: User = Depends(current_active_user),
):
    entry = crud.upsert_meal_plan_entry(db, workspace_id, user.id, day, meal_type, payload.recipe_id)
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


@router.post("/meal-plan/copy-week", response_model=list[schemas.MealPlanEntryOut])
def copy_meal_plan_week(
    payload: schemas.CopyMealPlanWeekRequest,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    user: User = Depends(current_active_user),
):
    return crud.copy_meal_plan_week(
        db,
        workspace_id,
        user.id,
        payload.source_week_start,
        payload.target_week_start,
        payload.overwrite,
    )


@router.get("/meal-plan-templates", response_model=list[schemas.MealPlanTemplateOut])
def list_meal_plan_templates(db: Session = Depends(get_db), workspace_id: uuid.UUID = Depends(get_workspace_id)):
    return crud.list_meal_plan_templates(db, workspace_id)


@router.post("/meal-plan-templates", response_model=schemas.MealPlanTemplateOut, status_code=201)
def save_meal_plan_template(
    payload: schemas.MealPlanTemplateCreate,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    return crud.save_meal_plan_template(db, workspace_id, payload)


@router.post("/meal-plan-templates/{template_id}/apply", response_model=list[schemas.MealPlanEntryOut])
def apply_meal_plan_template(
    template_id: uuid.UUID,
    payload: schemas.MealPlanTemplateApply,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    user: User = Depends(current_active_user),
):
    entries = crud.apply_meal_plan_template(db, workspace_id, user.id, template_id, payload)
    if entries is None:
        raise HTTPException(status_code=404, detail="Modelo não encontrado")
    return entries


@router.delete("/meal-plan-templates/{template_id}", status_code=204)
def delete_meal_plan_template(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    if not crud.delete_meal_plan_template(db, workspace_id, template_id):
        raise HTTPException(status_code=404, detail="Modelo não encontrado")


@router.get("/meal-plan-recurrences", response_model=list[schemas.MealPlanRecurrenceOut])
def list_meal_plan_recurrences(db: Session = Depends(get_db), workspace_id: uuid.UUID = Depends(get_workspace_id)):
    return crud.list_meal_plan_recurrences(db, workspace_id)


@router.post("/meal-plan-recurrences", response_model=schemas.MealPlanRecurrenceOut, status_code=201)
def create_meal_plan_recurrence(
    payload: schemas.MealPlanRecurrenceCreate,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    recurrence = crud.create_meal_plan_recurrence(db, workspace_id, payload)
    if recurrence is None:
        raise HTTPException(status_code=404, detail="Receita não encontrada")
    return recurrence


@router.delete("/meal-plan-recurrences/{recurrence_id}", status_code=204)
def delete_meal_plan_recurrence(
    recurrence_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    if not crud.delete_meal_plan_recurrence(db, workspace_id, recurrence_id):
        raise HTTPException(status_code=404, detail="Recorrência não encontrada")


@router.get("/meal-plan-suggestion", response_model=list[schemas.MealPlanSuggestionItem])
def suggest_meal_plan(
    week_start: date,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    user: User = Depends(current_active_user),
):
    return crud.suggest_meal_plan(db, workspace_id, user.id, week_start)


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
