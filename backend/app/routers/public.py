from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import crud, schemas
from app.config import get_settings
from app.database import get_db
from app.images import resolve_image_path

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


@router.get("/recipes/{token}/image", include_in_schema=False)
def get_public_recipe_image(token: str, db: Session = Depends(get_db)):
    """Serve only the cover belonging to a currently valid share token."""
    recipe = crud.get_recipe_by_share_token(db, token)
    if recipe is None or not recipe.image_path:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    path = resolve_image_path(recipe.image_path, get_settings())
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    return FileResponse(path)
