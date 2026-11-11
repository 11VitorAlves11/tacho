import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app import crud, gemini, schemas
from app.config import get_settings
from app.database import get_db
from app.deps import get_workspace_id
from app.images import ALLOWED_CONTENT_TYPES

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


# Registado antes de "/{item_id}" pelo mesmo motivo de "/import" em
# recipes.py: Starlette casaria "import" como um (inválido) item_id.
# Síncrono e devolve só um rascunho para confirmação — nunca grava sozinho
# (ver schemas.PantryExtraction). ⚠️ Não testado contra a API Gemini real
# nesta sessão — ver app/gemini.py.
@router.post("/import/receipt", response_model=schemas.PantryExtraction)
async def import_pantry_from_receipt(
    file: UploadFile,
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    settings = get_settings()
    if not gemini.is_available(settings):
        raise HTTPException(status_code=422, detail="Leitura de fatura não está configurada (sem GEMINI_API_KEY).")

    content_type = file.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=422, detail="Formato de imagem não suportado (usa JPEG, PNG ou WEBP).")
    contents = await file.read()
    if len(contents) > settings.max_image_bytes:
        max_mb = settings.max_image_bytes // (1024 * 1024)
        raise HTTPException(status_code=422, detail=f"Imagem demasiado grande (máx. {max_mb}MB).")

    extraction = gemini.extract_pantry_items_from_image(settings, (contents, content_type))
    if extraction is None:
        raise HTTPException(status_code=422, detail="Não foi possível reconhecer artigos nesta fatura.")
    return extraction


# Grava uma fatura já revista pelo utilizador (ver crud.confirm_receipt).
@router.post("/receipt/confirm", response_model=schemas.ReceiptConfirmOut, status_code=201)
def confirm_receipt(
    payload: schemas.ReceiptConfirmIn,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    items, created = crud.confirm_receipt(db, workspace_id, payload)
    return {"items": items, "price_entries_created": created}


# Registado antes de "/{item_id}/prices" — "prices" não é um item_id.
@router.get("/prices/history", response_model=schemas.PantryPriceHistory)
def price_history(
    months: int = Query(default=12, ge=1, le=60),
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    return crud.get_price_history(db, workspace_id, months)


@router.post("/bulk", response_model=list[schemas.PantryItemOut], status_code=201)
def bulk_create_pantry_items(
    payload: schemas.PantryBulkIn,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    return crud.bulk_upsert_pantry_items(db, workspace_id, payload.names)


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


@router.get("/{item_id}/prices", response_model=list[schemas.PantryPriceEntryOut])
def list_price_entries(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    entries = crud.list_price_entries(db, workspace_id, item_id)
    if entries is None:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    return entries


@router.post("/{item_id}/prices", response_model=schemas.PantryPriceEntryOut, status_code=201)
def create_price_entry(
    item_id: uuid.UUID,
    payload: schemas.PantryPriceEntryIn,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    entry = crud.create_price_entry(db, workspace_id, item_id, payload)
    if entry is None:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    return entry


@router.delete("/{item_id}/prices/{entry_id}", status_code=204)
def delete_price_entry(
    item_id: uuid.UUID,
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    if not crud.delete_price_entry(db, workspace_id, item_id, entry_id):
        raise HTTPException(status_code=404, detail="Preço não encontrado")
