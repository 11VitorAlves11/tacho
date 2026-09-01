import uuid

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app import crud, gemini, schemas
from app.auth import current_active_user
from app.celery_app import celery_app
from app.config import get_settings
from app.database import get_db
from app.deps import get_workspace_id
from app.images import (
    ALLOWED_CONTENT_TYPES,
    copy_recipe_image,
    delete_recipe_image,
    delete_recipe_images_dir,
    save_recipe_image,
    validate_remote_url,
)
from app.models import User
from app.schema_org import recipe_to_schema_org
from app.tasks import import_recipe_from_url

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("", response_model=list[schemas.RecipeSummary])
def list_recipes(
    category_id: uuid.UUID | None = None,
    tag_ids: str | None = None,
    q: str | None = None,
    ingredient: str | None = None,
    rating_min: int | None = Query(default=None, ge=1, le=5),
    max_total_minutes: int | None = Query(default=None, ge=1, le=1440),
    favorite: bool = False,
    makeable: bool = False,
    pantry_suggestions: bool = False,
    safe_for_all: bool = False,
    profile_ids: str | None = None,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    user: User = Depends(current_active_user),
):
    parsed_tag_ids: list[uuid.UUID] = []
    if tag_ids:
        try:
            parsed_tag_ids = [uuid.UUID(value) for value in tag_ids.split(",") if value]
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Uma das tags não é válida") from exc
    parsed_profile_ids: list[uuid.UUID] = []
    if profile_ids:
        try:
            parsed_profile_ids = [uuid.UUID(value) for value in profile_ids.split(",") if value]
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Um dos perfis alimentares não é válido") from exc
    return crud.list_recipes(
        db,
        workspace_id,
        user.id,
        category_id=category_id,
        tag_ids=parsed_tag_ids,
        q=q,
        ingredient=ingredient,
        rating_min=rating_min,
        max_total_minutes=max_total_minutes,
        favorite_only=favorite,
        makeable_only=makeable,
        pantry_suggestions=pantry_suggestions,
        safe_for_all=safe_for_all,
        dietary_profile_ids=parsed_profile_ids,
    )


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
    try:
        validate_remote_url(str(payload.url))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    task = import_recipe_from_url.delay(str(payload.url), str(workspace_id))
    return schemas.ImportStatus(task_id=task.id, status="pending")


# Registado antes de "/{recipe_id}" pelo mesmo motivo do "/import" acima.
# Síncrono (não Celery, ao contrário da importação por URL) — é uma ação
# pontual do utilizador (1-3 fotos), não um scrape que pode demorar; e
# devolve um rascunho para revisão manual, não uma receita já criada, por
# isso não faz sentido reaproveitar o schemas.ImportStatus/polling.
# ⚠️ Não testado contra a API Gemini real nesta sessão — ver app/gemini.py.
@router.post("/import/photo", response_model=schemas.RecipeExtraction)
async def import_recipe_from_photos(
    files: list[UploadFile],
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    if not files or len(files) > 3:
        raise HTTPException(status_code=422, detail="Envia entre 1 e 3 fotos.")

    settings = get_settings()
    if not gemini.is_available(settings):
        raise HTTPException(status_code=422, detail="Importação por foto não está configurada (sem GEMINI_API_KEY).")

    images: list[tuple[bytes, str]] = []
    for file in files:
        content_type = file.content_type or ""
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(status_code=422, detail="Formato de imagem não suportado (usa JPEG, PNG ou WEBP).")
        contents = await file.read()
        if len(contents) > settings.max_image_bytes:
            max_mb = settings.max_image_bytes // (1024 * 1024)
            raise HTTPException(status_code=422, detail=f"Imagem demasiado grande (máx. {max_mb}MB).")
        images.append((contents, content_type))

    extraction = gemini.extract_from_images(settings, images)
    if extraction is None:
        raise HTTPException(status_code=422, detail="Não foi possível reconhecer uma receita nestas fotos.")
    return extraction


@router.get("/import/{task_id}", response_model=schemas.ImportStatus)
def get_import_status(task_id: str, user: User = Depends(current_active_user)):
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
    user: User = Depends(current_active_user),
):
    recipe = crud.get_recipe(db, workspace_id, recipe_id, user.id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Receita não encontrada")
    return recipe


@router.put("/{recipe_id}", response_model=schemas.RecipeOut)
def update_recipe(
    recipe_id: uuid.UUID,
    payload: schemas.RecipeUpdate,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    user: User = Depends(current_active_user),
):
    recipe = crud.update_recipe(db, workspace_id, recipe_id, user.id, payload)
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
    image_url = f"{base_url}/media/{recipe.image_path}" if recipe.image_path else None
    return JSONResponse(content=recipe_to_schema_org(recipe, image_url), media_type="application/ld+json")


@router.post("/{recipe_id}/share", response_model=schemas.RecipeShareOut)
def share_recipe(
    recipe_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    """Gera/renova o link público temporário (5h) — ver `crud.create_recipe_share`
    e `routers/public.py::get_public_recipe`, o endpoint sem autenticação que
    o consome."""
    recipe = crud.create_recipe_share(db, workspace_id, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Receita não encontrada")
    settings = get_settings()
    base_url = settings.share_base_url or settings.public_base_url or str(request.base_url).rstrip("/")
    return schemas.RecipeShareOut(
        share_url=f"{base_url}/partilha/{recipe.share_token}",
        share_expires_at=recipe.share_expires_at,
    )


@router.post("/{recipe_id}/duplicate", response_model=schemas.RecipeOut, status_code=201)
def duplicate_recipe(
    recipe_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    original = crud.get_recipe(db, workspace_id, recipe_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Receita não encontrada")

    # Gerado aqui (em vez de deixar o INSERT atribuir um) para a foto poder
    # ser copiada já para a pasta certa (`receitas/<new_id>/…`) antes da
    # receita nova existir na BD.
    new_id = uuid.uuid4()
    image_path = copy_recipe_image(original.image_path, get_settings(), new_id) if original.image_path else None
    return crud.duplicate_recipe(db, workspace_id, recipe_id, image_path, new_id=new_id)


@router.post("/{recipe_id}/shopping-list", response_model=list[schemas.ShoppingListItemOut])
def add_recipe_to_shopping_list(
    recipe_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    items = crud.add_recipe_to_shopping_list(db, workspace_id, recipe_id)
    if items is None:
        raise HTTPException(status_code=404, detail="Receita não encontrada")
    return items


@router.post("/{recipe_id}/shopping-list/missing", response_model=list[schemas.ShoppingListItemOut])
def add_missing_recipe_ingredients_to_shopping_list(
    recipe_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    items = crud.add_missing_recipe_ingredients_to_shopping_list(db, workspace_id, recipe_id)
    if items is None:
        raise HTTPException(status_code=404, detail="Receita não encontrada")
    return items


@router.post("/{recipe_id}/favorite", response_model=schemas.RecipeOut)
def toggle_recipe_favorite(
    recipe_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    user: User = Depends(current_active_user),
):
    recipe = crud.toggle_recipe_favorite(db, workspace_id, recipe_id, user.id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Receita não encontrada")
    return recipe


@router.patch("/{recipe_id}/rating", response_model=schemas.RecipeOut)
def set_recipe_rating(
    recipe_id: uuid.UUID,
    payload: schemas.RecipeRatingIn,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    user: User = Depends(current_active_user),
):
    recipe = crud.set_recipe_rating(db, workspace_id, recipe_id, user.id, payload.rating)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Receita não encontrada")
    return recipe


@router.post("/{recipe_id}/mark-made", response_model=schemas.RecipeOut)
def mark_recipe_made(
    recipe_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    user: User = Depends(current_active_user),
):
    recipe = crud.mark_recipe_made(db, workspace_id, recipe_id, user.id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Receita não encontrada")
    return recipe


@router.post("/{recipe_id}/notes", response_model=schemas.RecipeOut)
def add_cook_note(
    recipe_id: uuid.UUID,
    payload: schemas.CookNoteIn,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    user: User = Depends(current_active_user),
):
    recipe = crud.add_cook_note(db, workspace_id, recipe_id, user.id, payload.text)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Receita não encontrada")
    return recipe


@router.post("/{recipe_id}/comments", response_model=schemas.RecipeOut, status_code=201)
def add_comment(
    recipe_id: uuid.UUID,
    payload: schemas.CommentIn,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    user: User = Depends(current_active_user),
):
    recipe = crud.add_comment(db, workspace_id, recipe_id, user.id, payload.text)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Receita não encontrada")
    return recipe


@router.delete("/{recipe_id}/comments/{comment_id}", status_code=204)
def delete_comment(
    recipe_id: uuid.UUID,
    comment_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    if not crud.delete_comment(db, workspace_id, recipe_id, comment_id):
        raise HTTPException(status_code=404, detail="Comentário não encontrado")


@router.delete("/{recipe_id}", status_code=204)
def delete_recipe(
    recipe_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    recipe = crud.get_recipe(db, workspace_id, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Receita não encontrada")
    settings = get_settings()
    # Caminho antigo, plano (de antes da organização por pastas) não vive
    # dentro de receitas/<id>/ — apagado à parte, já que o rmtree da pasta
    # não o alcança.
    legacy_image_path = recipe.image_path if recipe.image_path and "/" not in recipe.image_path else None
    crud.delete_recipe(db, workspace_id, recipe_id)
    # Apaga a pasta toda (capa + galeria) duma vez — antes só a capa era
    # apagada do disco, as fotos da galeria ficavam órfãs (ver images.py).
    delete_recipe_images_dir(recipe_id, settings)
    if legacy_image_path:
        delete_recipe_image(legacy_image_path, settings)


@router.post("/{recipe_id}/image", response_model=schemas.RecipeOut)
async def upload_recipe_image(
    recipe_id: uuid.UUID,
    file: UploadFile,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    user: User = Depends(current_active_user),
):
    recipe = crud.get_recipe(db, workspace_id, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Receita não encontrada")

    settings = get_settings()
    old_image_path = recipe.image_path
    filename = await save_recipe_image(file, settings, recipe_id)
    recipe = crud.set_recipe_image(db, workspace_id, recipe_id, user.id, filename)
    if old_image_path:
        delete_recipe_image(old_image_path, settings)
    return recipe


@router.post("/{recipe_id}/images", response_model=schemas.RecipeOut, status_code=201)
async def add_recipe_gallery_image(
    recipe_id: uuid.UUID,
    file: UploadFile,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    user: User = Depends(current_active_user),
):
    filename = await save_recipe_image(file, get_settings(), recipe_id)
    recipe = crud.add_recipe_image(db, workspace_id, recipe_id, user.id, filename)
    if recipe is None:
        delete_recipe_image(filename, get_settings())
        raise HTTPException(status_code=404, detail="Receita não encontrada")
    return recipe


@router.delete("/{recipe_id}/images/{image_id}", response_model=schemas.RecipeOut)
def delete_recipe_gallery_image(
    recipe_id: uuid.UUID,
    image_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    user: User = Depends(current_active_user),
):
    result = crud.delete_recipe_image_row(db, workspace_id, recipe_id, image_id, user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    recipe, filename = result
    delete_recipe_image(filename, get_settings())
    return recipe


@router.post("/{recipe_id}/images/{image_id}/cover", response_model=schemas.RecipeOut)
def set_recipe_gallery_cover(
    recipe_id: uuid.UUID,
    image_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    user: User = Depends(current_active_user),
):
    recipe = crud.set_recipe_image_cover(db, workspace_id, recipe_id, image_id, user.id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    return recipe
