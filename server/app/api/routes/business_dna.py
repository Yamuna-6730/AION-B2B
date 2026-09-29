from fastapi import APIRouter, Depends

from app.schemas.business_dna import BusinessDNARunRequest, BusinessDNARunResponse
from app.services.business_dna import BusinessDNAService

router = APIRouter(prefix="/business-dna", tags=["business-dna"])


def get_business_dna_service() -> BusinessDNAService:
    return BusinessDNAService()


@router.post(
    "/run",
    response_model=BusinessDNARunResponse,
    summary="Run the Business DNA Agent",
    description=(
        "Loads market discovery data for the given mission, runs the Business DNA intelligence "
        "agent to generate deep company profiles, persists results to Supabase, and returns "
        "the structured output."
    ),
)
async def run_business_dna(
    request: BusinessDNARunRequest,
    service: BusinessDNAService = Depends(get_business_dna_service),
) -> BusinessDNARunResponse:
    return await service.run(str(request.mission_id))
