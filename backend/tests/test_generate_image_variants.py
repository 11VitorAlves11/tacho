from pathlib import Path

from PIL import Image

from app.config import Settings
from scripts.generate_image_variants import generate


def test_generates_missing_variants_once_and_reports_failures(tmp_path: Path) -> None:
    settings = Settings(
        database_url="postgresql+psycopg2://tacho:tacho@localhost/tacho",
        redis_url="redis://localhost:6379/0",
        images_dir=str(tmp_path),
    )
    (tmp_path / "receitas" / "r1").mkdir(parents=True)
    Image.new("RGB", (1600, 900)).save(tmp_path / "receitas" / "r1" / "nova.jpg")
    Image.new("RGB", (300, 300)).save(tmp_path / "antiga.png")
    (tmp_path / "estragada.webp").write_bytes(b"nope")

    assert generate(settings) == {"imagens": 3, "criadas": 4, "existentes": 0, "falhadas": 1}
    assert (tmp_path / "receitas" / "r1" / "nova.thumb.webp").is_file()
    assert (tmp_path / "antiga.medium.webp").is_file()

    # Segunda passagem: as variantes não contam como originais.
    assert generate(settings) == {"imagens": 3, "criadas": 0, "existentes": 4, "falhadas": 1}
