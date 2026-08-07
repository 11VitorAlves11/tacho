import uuid

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app import crud, schemas
from app.celery_app import celery_app
from app.config import get_settings
from app.database import get_db
from app.deps import get_workspace_id
from app.images import copy_recipe_image, delete_recipe_image, save_recipe_image
from app.schema_org import recipe_to_schema_org
from app.tasks import import_recipe_from_url

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("", response_model=list[schemas.RecipeSummary])
def list_recipes(
    category_id: uuid.UUID | None = None,
    tag_id: uuid.UUID | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    return crud.list_recipes(db, workspace_id, category_id=category_id, tag_id=tag_id, q=q)


@router.post("", response_model=schemas.RecipeOut, status_code=201)
def create_recipe(
    payload: schemas.RecipeCreate,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    return crud.create_recipe(db, workspace_id, payload)


# Registered before "/{recipe_id}" on purpose — Starlette matches routes in
# declaration order, so "/import" would otherwise be swallowed as a
# (invalid) recipe_id.
@router.post("/import", response_model=schemas.ImportStatus, status_code=202)
def import_recipe(
    payload: schemas.ImportRequest,
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    task = import_recipe_from_url.delay(str(payload.url), str(workspace_id))
    return schemas.ImportStatus(task_id=task.id, status="pending")


@router.get("/import/{task_id}", response_model=schemas.ImportStatus)
def get_import_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    if result.failed():
        raise HTTPException(status_code=422, detail=f"Falha ao importar: {result.result}")
    if result.ready():
        return schemas.ImportStatus(task_id=task_id, status="done", recipe_id=result.result)
    return schemas.ImportStatus(task_id=task_id, status="pending")


@router.get("/{recipe_id}", response_model=schemas.RecipeOut)
def get_recipe(
    recipe_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    recipe = crud.get_recipe(db, workspace_id, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Receita não encontrada")
    return recipe


@router.put("/{recipe_id}", response_model=schemas.RecipeOut)
def update_recipe(
    recipe_id: uuid.UUID,
    payload: schemas.RecipeUpdate,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    recipe = crud.update_recipe(db, workspace_id, recipe_id, payload)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Receita não encontrada")
    return recipe


@router.get("/{recipe_id}/export")
def export_recipe_schema_org(
    recipe_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    recipe = crud.get_recipe(db, workspace_id, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Receita não encontrada")
    settings = get_settings()
    base_url = settings.public_base_url or str(request.base_url).rstrip("/")
    image_url = f"{base_url}/images/{recipe.image_path}" if recipe.image_path else None
    return JSONResponse(content=recipe_to_schema_org(recipe, image_url), media_type="application/ld+json")


@router.post("/{recipe_id}/duplicate", response_model=schemas.RecipeOut, status_code=201)
def duplicate_recipe(
    recipe_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    original = crud.get_recipe(db, workspace_id, recipe_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Receita não encontrada")

    image_path = copy_recipe_image(original.image_path, get_settings()) if original.image_path else None
    return crud.duplicate_recipe(db, workspace_id, recipe_id, image_path)


@router.post("/{recipe_id}/mark-made", response_model=schemas.RecipeOut)
def mark_recipe_made(
    recipe_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    recipe = crud.mark_recipe_made(db, workspace_id, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Receita não encontrada")
    return recipe


@router.delete("/{recipe_id}", status_code=204)
def delete_recipe(
    recipe_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    recipe = crud.get_recipe(db, workspace_id, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Receita não encontrada")
    image_path = recipe.image_path
    crud.delete_recipe(db, workspace_id, recipe_id)
    if image_path:
        delete_recipe_image(image_path, get_settings())


@router.post("/{recipe_id}/image", response_model=schemas.RecipeOut)
async def upload_recipe_image(
    recipe_id: uuid.UUID,
    file: UploadFile,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    recipe = crud.get_recipe(db, workspace_id, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Receita não encontrada")

    settings = get_settings()
    old_image_path = recipe.image_path
    filename = await save_recipe_image(file, settings)
    recipe = crud.set_recipe_image(db, workspace_id, recipe_id, filename)
    if old_image_path:
        delete_recipe_image(old_image_path, settings)
    return recipe
