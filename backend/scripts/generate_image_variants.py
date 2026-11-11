"""Gera as variantes (`thumb`, `medium`) em falta de todas as fotos guardadas.

Opcional: sem isto, cada variante é gerada no primeiro pedido que a usa.
Seguro para voltar a executar — variantes já existentes não são tocadas.
Percorre só o disco (`images_dir`), sem consultar a base de dados.
"""

from __future__ import annotations

from pathlib import Path

from app.config import Settings, get_settings
from app.images import VARIANT_MAX_WIDTH, InvalidImageError, ensure_variant, variant_path

ORIGINAL_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
VARIANT_SUFFIXES = tuple(f".{size}.webp" for size in VARIANT_MAX_WIDTH)


def originals(root: Path) -> list[str]:
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in ORIGINAL_SUFFIXES
        and not path.name.endswith(VARIANT_SUFFIXES)
        and not path.name.startswith(".")
    )


def generate(settings: Settings) -> dict[str, int]:
    root = Path(settings.images_dir)
    summary = {"imagens": 0, "criadas": 0, "existentes": 0, "falhadas": 0}
    for image_path in originals(root):
        summary["imagens"] += 1
        for size in VARIANT_MAX_WIDTH:
            if (root / variant_path(image_path, size)).is_file():
                summary["existentes"] += 1
                continue
            try:
                ensure_variant(image_path, size, settings)
            except (InvalidImageError, OSError) as exc:
                summary["falhadas"] += 1
                print(f"Falhou {image_path} ({size}): {exc}")
                break
            summary["criadas"] += 1
    return summary


def main() -> None:
    summary = generate(get_settings())
    print(
        f"Imagens: {summary['imagens']}; variantes criadas: {summary['criadas']}; "
        f"já existentes: {summary['existentes']}; imagens com falha: {summary['falhadas']}"
    )


if __name__ == "__main__":
    main()
