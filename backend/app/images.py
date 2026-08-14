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


def _recipe_dir(recipe_id: uuid.UUID | str, settings: Settings) -> str:
    """`images_dir/receitas/<recipe_id>/` — uma pasta por receita, capa e
    galeria juntas, em vez de um único diretório plano com todos os
    ficheiros de todas as receitas misturados. `image_path`/`filename`
    guardados na BD passam a ser o caminho relativo completo (ex.
    "receitas/<uuid-da-receita>/<uuid-do-ficheiro>.jpg"), não só o nome do
    ficheiro — StaticFiles (app/main.py) serve subcaminhos sem alteração
    nenhuma, por isso caminhos antigos (planos, de antes desta mudança)
    continuam a funcionar tal como estão, sem migração de dados."""
    return os.path.join(settings.images_dir, "receitas", str(recipe_id))


async def save_recipe_image(file: UploadFile, settings: Settings, recipe_id: uuid.UUID | str) -> str:
    """Valida e grava a foto em disco, devolvendo o caminho relativo (a
    partir de `images_dir`) a guardar em `Recipe.image_path`/
    `RecipeImage.filename`."""
    ext = ALLOWED_CONTENT_TYPES.get(file.content_type or "")
    if ext is None:
        raise HTTPException(
            status_code=422, detail="Formato de imagem não suportado (usa JPEG, PNG ou WEBP)."
        )

    contents = await file.read()
    if len(contents) > settings.max_image_bytes:
        max_mb = settings.max_image_bytes // (1024 * 1024)
        raise HTTPException(status_code=422, detail=f"Imagem demasiado grande (máx. {max_mb}MB).")

    dir_path = _recipe_dir(recipe_id, settings)
    os.makedirs(dir_path, exist_ok=True)
    filename = f"{uuid.uuid4()}{ext}"
    with open(os.path.join(dir_path, filename), "wb") as f:
        f.write(contents)
    return os.path.join("receitas", str(recipe_id), filename)


def save_recipe_image_from_url(url: str, settings: Settings, recipe_id: uuid.UUID | str) -> str | None:
    """Descarrega a foto de uma receita importada por URL.

    Best-effort: devolve None em qualquer falha (site sem imagem, formato não
    suportado, imagem grande demais, erro de rede a meio do download, `url`
    que nem é uma string — schema.org permite `image` como lista/objeto) em
    vez de levantar — a foto nunca deve chumbar a importação em si (ver
    tasks.py). `recipe_id` já vem atribuído pelo chamador antes da receita
    ser gravada (`tasks.py` gera o uuid primeiro) para a foto cair logo na
    pasta certa."""
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

    dir_path = _recipe_dir(recipe_id, settings)
    os.makedirs(dir_path, exist_ok=True)
    filename = f"{uuid.uuid4()}{ext}"
    with open(os.path.join(dir_path, filename), "wb") as f:
        for chunk in chunks:
            f.write(chunk)
    return os.path.join("receitas", str(recipe_id), filename)


def copy_recipe_image(image_path: str, settings: Settings, new_recipe_id: uuid.UUID | str) -> str | None:
    """Copia a foto de uma receita para a pasta da receita nova (nome
    uuid4 novo dentro dela), para que duplicar uma receita não deixe duas
    receitas a apontar para o mesmo ficheiro — apagar uma apagaria a foto
    da outra. Funciona tanto a partir de um caminho novo (`receitas/<id>/
    <ficheiro>`) como de um caminho antigo, plano, anterior a esta
    organização por pastas."""
    ext = os.path.splitext(image_path)[1]
    src = os.path.join(settings.images_dir, image_path)
    if not os.path.isfile(src):
        return None
    dir_path = _recipe_dir(new_recipe_id, settings)
    os.makedirs(dir_path, exist_ok=True)
    filename = f"{uuid.uuid4()}{ext}"
    shutil.copyfile(src, os.path.join(dir_path, filename))
    return os.path.join("receitas", str(new_recipe_id), filename)


def delete_recipe_image(image_path: str, settings: Settings) -> None:
    try:
        os.remove(os.path.join(settings.images_dir, image_path))
    except OSError:
        pass


def delete_recipe_images_dir(recipe_id: uuid.UUID | str, settings: Settings) -> None:
    """Apaga a pasta inteira da receita (capa + galeria) de uma vez, ao
    apagar a receita — antes disto só a capa (`Recipe.image_path`) era
    apagada do disco; as fotos da galeria (`RecipeImage`) perdiam só a
    linha na BD e ficavam órfãs em disco para sempre. `ignore_errors`:
    receitas sem fotos não têm pasta nenhuma a apagar."""
    shutil.rmtree(_recipe_dir(recipe_id, settings), ignore_errors=True)
