from fastapi import APIRouter, Depends

from app.schemas.market_discovery import MarketDiscoveryRunRequest, MarketDiscoveryRunResponse
from app.services.market_discovery_service import MarketDiscoveryService

router = APIRouter(prefix="/market-discovery", tags=["market-discovery"])


def get_market_discovery_service() -> MarketDiscoveryService:
    return MarketDiscoveryService()


@router.post(
    "/run",
    response_model=MarketDiscoveryRunResponse,
    summary="Run the Market Discovery Agent",
)
async def run_market_discovery(
    request: MarketDiscoveryRunRequest,
    service: MarketDiscoveryService = Depends(get_market_discovery_service),
) -> MarketDiscoveryRunResponse:
    return await service.run(str(request.mission_id))
