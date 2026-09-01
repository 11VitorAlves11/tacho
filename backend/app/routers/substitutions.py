import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_workspace_id

router = APIRouter(prefix="/ingredient-substitutions", tags=["ingredient-substitutions"])


@router.get("", response_model=list[schemas.IngredientSubstitutionOut])
def list_substitutions(db: Session = Depends(get_db), workspace_id: uuid.UUID = Depends(get_workspace_id)):
    return list(
        db.scalars(
            select(models.IngredientSubstitution)
            .where(models.IngredientSubstitution.workspace_id == workspace_id)
            .order_by(models.IngredientSubstitution.ingredient_name, models.IngredientSubstitution.substitute_name)
        )
    )


@router.post("", response_model=schemas.IngredientSubstitutionOut, status_code=201)
def create_substitution(
    payload: schemas.IngredientSubstitutionWrite,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    substitution = models.IngredientSubstitution(workspace_id=workspace_id, **payload.model_dump())
    db.add(substitution)
    db.commit()
    db.refresh(substitution)
    return substitution


@router.put("/{substitution_id}", response_model=schemas.IngredientSubstitutionOut)
def update_substitution(
    substitution_id: uuid.UUID,
    payload: schemas.IngredientSubstitutionWrite,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    substitution = db.scalar(
        select(models.IngredientSubstitution).where(
            models.IngredientSubstitution.id == substitution_id,
            models.IngredientSubstitution.workspace_id == workspace_id,
        )
    )
    if substitution is None:
        raise HTTPException(status_code=404, detail="Substituição não encontrada")
    for field, value in payload.model_dump().items():
        setattr(substitution, field, value)
    db.commit()
    db.refresh(substitution)
    return substitution


@router.delete("/{substitution_id}", status_code=204)
def delete_substitution(
    substitution_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    substitution = db.scalar(
        select(models.IngredientSubstitution).where(
            models.IngredientSubstitution.id == substitution_id,
            models.IngredientSubstitution.workspace_id == workspace_id,
        )
    )
    if substitution is None:
        raise HTTPException(status_code=404, detail="Substituição não encontrada")
    db.delete(substitution)
    db.commit()
