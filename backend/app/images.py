import os
import shutil
import uuid

import requests
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


def save_recipe_image_from_url(url: str, settings: Settings) -> str | None:
    """Descarrega a foto de uma receita importada por URL.

    Best-effort: devolve None em qualquer falha (site sem imagem, formato não
    suportado, imagem grande demais, erro de rede a meio do download, `url`
    que nem é uma string — schema.org permite `image` como lista/objeto) em
    vez de levantar — a foto nunca deve chumbar a importação em si (ver
    tasks.py)."""
    try:
        with requests.get(url, timeout=10, stream=True) as response:
            response.raise_for_status()

            content_type = response.headers.get("content-type", "").split(";")[0].strip()
            ext = ALLOWED_CONTENT_TYPES.get(content_type)
            if ext is None:
                return None

            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_content(chunk_size=65536):
                total += len(chunk)
                if total > settings.max_image_bytes:
                    return None
                chunks.append(chunk)
    except Exception:
        return None

    os.makedirs(settings.images_dir, exist_ok=True)
    filename = f"{uuid.uuid4()}{ext}"
    with open(os.path.join(settings.images_dir, filename), "wb") as f:
        for chunk in chunks:
            f.write(chunk)
    return filename


def copy_recipe_image(image_path: str, settings: Settings) -> str | None:
    """Copia a foto de uma receita para um ficheiro novo (nome uuid4 novo),
    para que duplicar uma receita não deixe duas receitas a apontar para o
    mesmo ficheiro — apagar uma apagaria a foto da outra."""
    ext = os.path.splitext(image_path)[1]
    src = os.path.join(settings.images_dir, image_path)
    if not os.path.isfile(src):
        return None
    filename = f"{uuid.uuid4()}{ext}"
    shutil.copyfile(src, os.path.join(settings.images_dir, filename))
    return filename


def delete_recipe_image(image_path: str, settings: Settings) -> None:
    try:
        os.remove(os.path.join(settings.images_dir, image_path))
    except OSError:
        pass
