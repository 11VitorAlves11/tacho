import os
import uuid

from fastapi import HTTPException, UploadFile

from app.config import Settings

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


async def save_recipe_image(file: UploadFile, settings: Settings) -> str:
    """Valida e grava a foto em disco, devolvendo só o nome do ficheiro."""
    ext = ALLOWED_CONTENT_TYPES.get(file.content_type or "")
    if ext is None:
        raise HTTPException(
            status_code=422, detail="Formato de imagem não suportado (usa JPEG, PNG ou WEBP)."
        )

    contents = await file.read()
    if len(contents) > settings.max_image_bytes:
        max_mb = settings.max_image_bytes // (1024 * 1024)
        raise HTTPException(status_code=422, detail=f"Imagem demasiado grande (máx. {max_mb}MB).")

    os.makedirs(settings.images_dir, exist_ok=True)
    filename = f"{uuid.uuid4()}{ext}"
    with open(os.path.join(settings.images_dir, filename), "wb") as f:
        f.write(contents)
    return filename


def delete_recipe_image(image_path: str, settings: Settings) -> None:
    try:
        os.remove(os.path.join(settings.images_dir, image_path))
    except OSError:
        pass
