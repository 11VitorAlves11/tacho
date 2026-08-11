import uuid

from fastapi import APIRouter, Depends

from app import schemas
from app.deps import get_workspace_id
from app.nutrition import estimate_nutrition

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


@router.post("/estimate", response_model=schemas.NutritionEstimate)
def estimate(
    payload: schemas.NutritionEstimateRequest,
    workspace_id: uuid.UUID = Depends(get_workspace_id),  # só para exigir sessão válida, sem usar o valor
):
    return estimate_nutrition(payload.ingredients, payload.servings)
