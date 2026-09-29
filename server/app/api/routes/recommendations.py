from fastapi import APIRouter, Depends

from app.schemas.recommendations import RecommendationRunRequest, RecommendationRunResponse
from app.services.recommendation import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def get_recommendation_service() -> RecommendationService:
    return RecommendationService()


@router.post(
    "/run",
    response_model=RecommendationRunResponse,
    summary="Run the Recommendation Agent",
    description=(
        "Loads Business DNA profiles and market discovery data for the given mission, "
        "runs the Recommendation agent to score and rank companies by ICP fit, "
        "persists results to Supabase, and returns the structured output."
    ),
)
async def run_recommendations(
    request: RecommendationRunRequest,
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationRunResponse:
    return await service.run(str(request.mission_id))


@router.get(
    "",
    summary="List recommendations (legacy placeholder)",
)
async def list_recommendations() -> dict[str, object]:
    return {
        "items": [],
        "total": 0,
        "message": "Use POST /recommendations/run with a mission_id to generate recommendations.",
    }
