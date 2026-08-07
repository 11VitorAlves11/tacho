from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import recipes, taxonomy

app = FastAPI(title="Tacho API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recipes.router)
app.include_router(taxonomy.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}
