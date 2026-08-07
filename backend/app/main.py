import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import recipes, taxonomy

settings = get_settings()

app = FastAPI(title="Tacho API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recipes.router)
app.include_router(taxonomy.router)

os.makedirs(settings.images_dir, exist_ok=True)
app.mount("/images", StaticFiles(directory=settings.images_dir), name="images")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


# Em produção (ver Dockerfile, raiz do repo), o frontend já compilado é
# copiado para este caminho e o FastAPI serve-o diretamente — sem container
# nginx separado. Em dev local este diretório não existe, por isso nada
# abaixo é registado e o comportamento atual não muda.
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend_dist"

if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="frontend-assets")

    @app.get("/favicon.svg", include_in_schema=False)
    def favicon() -> FileResponse:
        return FileResponse(FRONTEND_DIST / "favicon.svg")

    # Catch-all registado por último, propositadamente: só apanha caminhos
    # que nenhum router acima serviu — as rotas client-side do React Router
    # (/adicionar, /receitas/{id}, etc.) devolvem sempre o mesmo index.html,
    # a SPA é que decide o que mostrar.
    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str) -> FileResponse:
        return FileResponse(FRONTEND_DIST / "index.html")
