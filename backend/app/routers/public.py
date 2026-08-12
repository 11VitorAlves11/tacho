from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/recipes/{token}", response_model=schemas.PublicRecipeOut)
def get_public_recipe(token: str, db: Session = Depends(get_db)):
    """Sem autenticação de propósito — token gerado por
    `POST /recipes/{id}/share`, válido 5h. 404 tanto para token
    inexistente como expirado (nunca revelar qual dos dois é o caso)."""
    recipe = crud.get_recipe_by_share_token(db, token)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Link de partilha inválido ou expirado")
    return recipe
