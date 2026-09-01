import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.deps import get_workspace_id

router = APIRouter(tags=["taxonomy"])


@router.get("/categories", response_model=list[schemas.CategoryOut])
def list_categories(db: Session = Depends(get_db), workspace_id: uuid.UUID = Depends(get_workspace_id)):
    return crud.list_categories(db, workspace_id)


@router.post("/categories", response_model=schemas.CategoryOut, status_code=201)
def create_category(
    payload: schemas.CategoryCreate,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    return crud.create_category(db, workspace_id, payload)


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(
    category_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    if not crud.delete_category(db, workspace_id, category_id):
        raise HTTPException(status_code=404, detail="Categoria não encontrada")


@router.patch("/categories/{category_id}", response_model=schemas.CategoryOut)
def update_category(
    category_id: uuid.UUID,
    payload: schemas.CategoryUpdate,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    category = crud.update_category(db, workspace_id, category_id, payload)
    if category is None:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    return category


@router.get("/tags", response_model=list[schemas.TagOut])
def list_tags(db: Session = Depends(get_db), workspace_id: uuid.UUID = Depends(get_workspace_id)):
    return crud.list_tags(db, workspace_id)


@router.post("/tags", response_model=schemas.TagOut, status_code=201)
def create_tag(
    payload: schemas.TagCreate,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    return crud.create_tag(db, workspace_id, payload)


@router.delete("/tags/{tag_id}", status_code=204)
def delete_tag(
    tag_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    if not crud.delete_tag(db, workspace_id, tag_id):
        raise HTTPException(status_code=404, detail="Tag não encontrada")
