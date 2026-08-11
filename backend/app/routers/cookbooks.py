import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.auth import current_active_user
from app.database import get_db
from app.deps import get_workspace_id
from app.models import User

router = APIRouter(prefix="/cookbooks", tags=["cookbooks"])


@router.get("", response_model=list[schemas.CookbookSummary])
def list_cookbooks(db: Session = Depends(get_db), workspace_id: uuid.UUID = Depends(get_workspace_id)):
    return crud.list_cookbooks(db, workspace_id)


@router.post("", response_model=schemas.CookbookSummary, status_code=201)
def create_cookbook(
    payload: schemas.CookbookCreate,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    return crud.create_cookbook(db, workspace_id, payload)


@router.get("/{cookbook_id}", response_model=schemas.CookbookDetail)
def get_cookbook(
    cookbook_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    user: User = Depends(current_active_user),
):
    cookbook = crud.get_cookbook(db, workspace_id, cookbook_id, user.id)
    if cookbook is None:
        raise HTTPException(status_code=404, detail="Coleção não encontrada")
    return cookbook


@router.delete("/{cookbook_id}", status_code=204)
def delete_cookbook(
    cookbook_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    if not crud.delete_cookbook(db, workspace_id, cookbook_id):
        raise HTTPException(status_code=404, detail="Coleção não encontrada")


@router.post("/{cookbook_id}/recipes/{recipe_id}", response_model=schemas.CookbookDetail)
def add_recipe_to_cookbook(
    cookbook_id: uuid.UUID,
    recipe_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    user: User = Depends(current_active_user),
):
    cookbook = crud.add_recipe_to_cookbook(db, workspace_id, cookbook_id, recipe_id, user.id)
    if cookbook is None:
        raise HTTPException(status_code=404, detail="Coleção ou receita não encontrada")
    return cookbook


@router.delete("/{cookbook_id}/recipes/{recipe_id}", response_model=schemas.CookbookDetail)
def remove_recipe_from_cookbook(
    cookbook_id: uuid.UUID,
    recipe_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    user: User = Depends(current_active_user),
):
    cookbook = crud.remove_recipe_from_cookbook(db, workspace_id, cookbook_id, recipe_id, user.id)
    if cookbook is None:
        raise HTTPException(status_code=404, detail="Coleção não encontrada")
    return cookbook
