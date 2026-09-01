import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_workspace_id

router = APIRouter(prefix="/dietary-profiles", tags=["dietary-profiles"])


def _clean(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def _validate_member(db: Session, workspace_id: uuid.UUID, user_id: uuid.UUID | None) -> None:
    if (
        user_id is not None
        and db.scalar(
            select(models.WorkspaceMember.id).where(
                models.WorkspaceMember.workspace_id == workspace_id,
                models.WorkspaceMember.user_id == user_id,
            )
        )
        is None
    ):
        raise HTTPException(status_code=422, detail="O membro escolhido não pertence a este agregado")


@router.get("", response_model=list[schemas.DietaryProfileOut])
def list_profiles(db: Session = Depends(get_db), workspace_id: uuid.UUID = Depends(get_workspace_id)):
    return list(
        db.scalars(
            select(models.DietaryProfile)
            .where(models.DietaryProfile.workspace_id == workspace_id)
            .order_by(models.DietaryProfile.name)
        )
    )


@router.post("", response_model=schemas.DietaryProfileOut, status_code=201)
def create_profile(
    payload: schemas.DietaryProfileWrite,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    _validate_member(db, workspace_id, payload.user_id)
    profile = models.DietaryProfile(
        workspace_id=workspace_id,
        **payload.model_dump(exclude={"allergies", "intolerances", "preferences"}),
        allergies=_clean(payload.allergies),
        intolerances=_clean(payload.intolerances),
        preferences=_clean(payload.preferences),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.put("/{profile_id}", response_model=schemas.DietaryProfileOut)
def update_profile(
    profile_id: uuid.UUID,
    payload: schemas.DietaryProfileWrite,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    profile = db.scalar(
        select(models.DietaryProfile).where(
            models.DietaryProfile.id == profile_id,
            models.DietaryProfile.workspace_id == workspace_id,
        )
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    _validate_member(db, workspace_id, payload.user_id)
    for field, value in payload.model_dump().items():
        setattr(profile, field, _clean(value) if isinstance(value, list) else value)
    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/{profile_id}", status_code=204)
def delete_profile(
    profile_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    profile = db.scalar(
        select(models.DietaryProfile).where(
            models.DietaryProfile.id == profile_id,
            models.DietaryProfile.workspace_id == workspace_id,
        )
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    db.delete(profile)
    db.commit()
