from fastapi import APIRouter, Depends

from app.schemas.strategy import MissionIntelligence, StrategyAnalyzeRequest
from app.services.strategy_service import StrategyService

router = APIRouter(prefix="/strategy", tags=["strategy"])


def get_strategy_service() -> StrategyService:
    return StrategyService()


@router.post(
    "/analyze",
    response_model=MissionIntelligence,
    summary="Analyze a mission with the Strategy Agent",
)
async def analyze_strategy(
    request: StrategyAnalyzeRequest,
    strategy_service: StrategyService = Depends(get_strategy_service),
) -> MissionIntelligence:
    return await strategy_service.analyze(request)
