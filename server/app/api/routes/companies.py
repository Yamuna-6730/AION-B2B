from fastapi import APIRouter

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("")
async def list_companies() -> dict[str, object]:
    return {
        "items": [
            {
                "id": "company_mock_001",
                "mission_id": "mission_mock_001",
                "name": "Example Corp",
                "domain": "example.com",
            }
        ],
        "total": 1,
    }


@router.get("/{company_id}")
async def get_company(company_id: str) -> dict[str, object]:
    return {
        "id": company_id,
        "mission_id": "mission_mock_001",
        "name": "Example Corp",
        "domain": "example.com",
        "signals": [],
        "decision_makers": [],
        "business_dna": {},
    }

