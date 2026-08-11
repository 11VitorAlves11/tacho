import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.deps import get_workspace_id

router = APIRouter(prefix="/pantry", tags=["pantry"])


@router.get("", response_model=list[schemas.PantryItemOut])
def list_pantry_items(db: Session = Depends(get_db), workspace_id: uuid.UUID = Depends(get_workspace_id)):
    return crud.list_pantry_items(db, workspace_id)


@router.post("", response_model=schemas.PantryItemOut, status_code=201)
def create_pantry_item(
    payload: schemas.PantryItemIn,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    return crud.create_pantry_item(db, workspace_id, payload)


@router.patch("/{item_id}", response_model=schemas.PantryItemOut)
def update_pantry_item(
    item_id: uuid.UUID,
    payload: schemas.PantryItemUpdate,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    item = crud.update_pantry_item(db, workspace_id, item_id, payload)
    if item is None:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    return item


@router.delete("/{item_id}", status_code=204)
def delete_pantry_item(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    if not crud.delete_pantry_item(db, workspace_id, item_id):
        raise HTTPException(status_code=404, detail="Item não encontrado")
