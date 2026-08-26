from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_workspace_id
from app.images import resolve_image_path
from app.models import Recipe, RecipeImage

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/{image_path:path}", include_in_schema=False)
def get_private_image(
    image_path: str,
    db: Session = Depends(get_db),
    workspace_id=Depends(get_workspace_id),
):
    """Serve recipe media only to a member of the owning workspace."""
    cover_exists = db.scalar(
        select(Recipe.id).where(
            Recipe.workspace_id == workspace_id,
            Recipe.image_path == image_path,
        )
    )
    gallery_exists = db.scalar(
        select(RecipeImage.id)
        .join(Recipe, Recipe.id == RecipeImage.recipe_id)
        .where(Recipe.workspace_id == workspace_id, RecipeImage.filename == image_path)
    )
    if cover_exists is None and gallery_exists is None:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")

    path = resolve_image_path(image_path, get_settings())
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    return FileResponse(path)
