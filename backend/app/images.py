import io
import ipaddress
import logging
import os
import shutil
import socket
import uuid
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import requests
from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps
from starlette.concurrency import run_in_threadpool

from app.config import Settings

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
# Formato Pillow esperado para cada tipo declarado — o `content-type` vem do
# cliente (ou do site importado) e não prova nada sobre os bytes.
PIL_FORMATS = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}
INVALID_IMAGE_DETAIL = "Formato de imagem não suportado (usa JPEG, PNG ou WEBP)."

ImageSize = Literal["thumb", "medium"]
# Variantes derivadas, gravadas ao lado do original como
# `<uuid>.<tamanho>.webp`. O original fica intacto e continua a ser o
# ficheiro canónico (`image_path`/`filename` na BD não mudam); as variantes
# podem ser apagadas e voltam a ser geradas a pedido (`ensure_variant`).
VARIANT_MAX_WIDTH: dict[ImageSize, int] = {"thumb": 480, "medium": 1200}
VARIANT_QUALITY = 80


class InvalidImageError(ValueError):
    """Os bytes não descodificam como imagem do formato esperado."""


def resolve_image_path(image_path: str, settings: Settings) -> Path:
    """Resolve a stored relative image path without allowing traversal."""
    root = Path(settings.images_dir).resolve()
    candidate = (root / image_path).resolve()
    if candidate == root or root not in candidate.parents:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    return candidate


def variant_path(image_path: str, size: ImageSize) -> str:
    """Caminho relativo da variante `size` de uma imagem guardada
    ("receitas/<r>/<f>.jpg" -> "receitas/<r>/<f>.thumb.webp"). Funciona
    também com caminhos antigos, planos. Passar sempre o resultado por
    `resolve_image_path` antes de tocar no disco."""
    return f"{os.path.splitext(image_path)[0]}.{size}.webp"


def _load_image(source: bytes | Path, expected_format: str | None = None) -> Image.Image:
    """Descodifica e valida a imagem por inteiro e aplica a orientação EXIF.

    `formats` restringe os descodificadores tentados: um ficheiro declarado
    como PNG que na verdade é outra coisa falha aqui. `draft` deixa o
    descodificador JPEG reduzir já na leitura (DCT escalado) para o menor
    tamanho que ainda cobre a maior variante — uma foto de 24 MP ocupa ~4x
    menos memória. `Image.MAX_IMAGE_PIXELS` (omissão do Pillow) trava
    bombas de descompressão com `DecompressionBombError`."""
    formats = [expected_format] if expected_format else list(PIL_FORMATS.values())
    largest = max(VARIANT_MAX_WIDTH.values())

    def open_image() -> Image.Image:
        return Image.open(io.BytesIO(source) if isinstance(source, bytes) else source, formats=formats)

    try:
        with open_image() as probe:
            probe.verify()
        with open_image() as image:
            image.draft(None, (largest, largest))
            image.load()
            oriented = ImageOps.exif_transpose(image)
    except Exception as exc:
        # O Pillow levanta tipos variados para ficheiros corrompidos
        # (OSError, SyntaxError, struct.error, DecompressionBombError...).
        raise InvalidImageError(str(exc)) from exc
    # Perfis ICC de CMYK/cinzento não servem para a saída RGB.
    icc_profile = image.info.get("icc_profile") if image.mode in {"RGB", "RGBA"} else None
    converted = oriented.convert("RGBA" if oriented.has_transparency_data else "RGB")
    converted.info = {"icc_profile": icc_profile} if icc_profile else {}
    return converted


def _resize_to_width(image: Image.Image, max_width: int) -> Image.Image:
    if image.width <= max_width:
        return image
    height = max(1, round(image.height * max_width / image.width))
    resized = image.resize((max_width, height), Image.Resampling.LANCZOS)
    resized.info = image.info
    return resized


def _write_variant(image: Image.Image, target: Path) -> None:
    """Grava em ficheiro temporário + `os.replace` — dois pedidos a gerar
    a mesma variante ao mesmo tempo nunca deixam um ficheiro meio escrito.
    Só o perfil ICC passa para a variante; EXIF/XMP (ex.: GPS) não."""
    tmp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        image.save(
            tmp,
            "WEBP",
            quality=VARIANT_QUALITY,
            exif=b"",
            xmp=b"",
            icc_profile=image.info.get("icc_profile", b""),
        )
        os.replace(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)


def _write_variants(image: Image.Image, original: Path) -> None:
    """Gera todas as variantes de uma imagem já descodificada. Best-effort:
    o original já está gravado e `ensure_variant` volta a tentar a pedido,
    por isso uma falha aqui (ex.: disco cheio) não chumba o upload."""
    try:
        # Da maior para a menor: cada redução parte da anterior.
        for size in sorted(VARIANT_MAX_WIDTH, key=VARIANT_MAX_WIDTH.__getitem__, reverse=True):
            image = _resize_to_width(image, VARIANT_MAX_WIDTH[size])
            _write_variant(image, Path(variant_path(str(original), size)))
    except Exception:
        logger.warning("Falha a gerar variantes de %s", original, exc_info=True)


def ensure_variant(image_path: str, size: ImageSize, settings: Settings) -> Path:
    """Devolve o caminho absoluto da variante, gerando-a se faltar (ex.:
    imagens anteriores às variantes). Levanta `InvalidImageError` se o
    original não descodificar e `FileNotFoundError` se não existir."""
    target = resolve_image_path(variant_path(image_path, size), settings)
    if target.is_file():
        return target
    original = resolve_image_path(image_path, settings)
    if not original.is_file():
        raise FileNotFoundError(image_path)
    _write_variant(_resize_to_width(_load_image(original), VARIANT_MAX_WIDTH[size]), target)
    return target


def _store_recipe_image(data: bytes, content_type: str, settings: Settings, recipe_id: uuid.UUID | str) -> str:
    """Valida os bytes, grava o original tal como veio e gera as variantes."""
    image = _load_image(data, PIL_FORMATS[content_type])
    dir_path = _recipe_dir(recipe_id, settings)
    os.makedirs(dir_path, exist_ok=True)
    filename = f"{uuid.uuid4()}{ALLOWED_CONTENT_TYPES[content_type]}"
    original = Path(dir_path) / filename
    original.write_bytes(data)
    _write_variants(image, original)
    return os.path.join("receitas", str(recipe_id), filename)


def validate_remote_url(url: str) -> None:
    """Reject URLs that resolve to local or otherwise non-public addresses."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("only public HTTP(S) URLs are accepted")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or 443)}
    except socket.gaierror as exc:
        raise ValueError("URL hostname could not be resolved") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError("URLs resolving to private or local networks are not accepted")


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
    content_type = file.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=422, detail=INVALID_IMAGE_DETAIL)

    contents = await file.read()
    if len(contents) > settings.max_image_bytes:
        max_mb = settings.max_image_bytes // (1024 * 1024)
        raise HTTPException(status_code=422, detail=f"Imagem demasiado grande (máx. {max_mb}MB).")

    try:
        # Descodificar/redimensionar é CPU puro — fora do event loop.
        return await run_in_threadpool(_store_recipe_image, contents, content_type, settings, recipe_id)
    except InvalidImageError:
        raise HTTPException(status_code=422, detail=INVALID_IMAGE_DETAIL)


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
        validate_remote_url(url)
        with requests.get(url, timeout=10, stream=True, allow_redirects=False) as response:
            response.raise_for_status()

            content_type = response.headers.get("content-type", "").split(";")[0].strip()
            if content_type not in ALLOWED_CONTENT_TYPES:
                return None

            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_content(chunk_size=65536):
                total += len(chunk)
                if total > settings.max_image_bytes:
                    return None
                chunks.append(chunk)
        # Bytes que não descodificam como o tipo anunciado também caem no
        # `except` — receita importada sem foto, como antes.
        return _store_recipe_image(b"".join(chunks), content_type, settings, recipe_id)
    except Exception:
        return None


def copy_recipe_image(image_path: str, settings: Settings, new_recipe_id: uuid.UUID | str) -> str | None:
    """Copia a foto de uma receita para a pasta da receita nova (nome
    uuid4 novo dentro dela), para que duplicar uma receita não deixe duas
    receitas a apontar para o mesmo ficheiro — apagar uma apagaria a foto
    da outra. Funciona tanto a partir de um caminho novo (`receitas/<id>/
    <ficheiro>`) como de um caminho antigo, plano, anterior a esta
    organização por pastas.

    A origem já está no disco (foi validada ao entrar), por isso é copiada
    byte a byte; as variantes da cópia são geradas a partir dela, em
    best-effort, tal como num upload."""
    ext = os.path.splitext(image_path)[1]
    src = resolve_image_path(image_path, settings)
    if not src.is_file():
        return None
    dir_path = _recipe_dir(new_recipe_id, settings)
    os.makedirs(dir_path, exist_ok=True)
    filename = f"{uuid.uuid4()}{ext}"
    destination = Path(dir_path) / filename
    shutil.copyfile(src, destination)
    try:
        _write_variants(_load_image(destination), destination)
    except InvalidImageError:
        logger.warning("Imagem copiada não descodifica: %s", destination)
    return os.path.join("receitas", str(new_recipe_id), filename)


def delete_recipe_image(image_path: str, settings: Settings) -> None:
    """Apaga o original e as variantes derivadas dele."""
    for path in (image_path, *(variant_path(image_path, size) for size in VARIANT_MAX_WIDTH)):
        try:
            os.remove(resolve_image_path(path, settings))
        except OSError:
            pass


def delete_recipe_images_dir(recipe_id: uuid.UUID | str, settings: Settings) -> None:
    """Apaga a pasta inteira da receita (capa + galeria) de uma vez, ao
    apagar a receita — antes disto só a capa (`Recipe.image_path`) era
    apagada do disco; as fotos da galeria (`RecipeImage`) perdiam só a
    linha na BD e ficavam órfãs em disco para sempre. `ignore_errors`:
    receitas sem fotos não têm pasta nenhuma a apagar."""
    shutil.rmtree(_recipe_dir(recipe_id, settings), ignore_errors=True)
