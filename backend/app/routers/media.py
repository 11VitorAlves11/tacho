from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select, union_all
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_workspace_id
from app.images import ImageSize, image_file_to_serve
from app.models import Recipe, RecipeImage

router = APIRouter(prefix="/media", tags=["media"])

# Nomes de ficheiro são uuid4 únicos e nunca reescritos — o conteúdo de um
# URL nunca muda. `private`: a resposta depende do cookie de sessão, por
# isso nenhuma cache partilhada (proxy) a pode guardar.
MEDIA_CACHE_CONTROL = "private, max-age=31536000, immutable"


@router.get("/{image_path:path}", include_in_schema=False)
def get_private_image(
    image_path: str,
    size: ImageSize | None = None,
    db: Session = Depends(get_db),
    workspace_id=Depends(get_workspace_id),
):
    """Serve recipe media only to a member of the owning workspace.

    A autorização é sempre feita sobre o caminho do original (o que está na
    BD); `size` só escolhe qual dos ficheiros derivados dele é servido."""
    cover = select(Recipe.id).where(Recipe.workspace_id == workspace_id, Recipe.image_path == image_path)
    gallery = (
        select(RecipeImage.id)
        .join(Recipe, Recipe.id == RecipeImage.recipe_id)
        .where(Recipe.workspace_id == workspace_id, RecipeImage.filename == image_path)
    )
    if db.scalar(union_all(cover, gallery).limit(1)) is None:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")

    path = image_file_to_serve(image_path, size, get_settings())
    return FileResponse(path, headers={"Cache-Control": MEDIA_CACHE_CONTROL})
