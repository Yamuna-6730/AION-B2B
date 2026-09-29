from fastapi import APIRouter

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("")
async def list_signals() -> dict[str, object]:
    return {
        "items": [
            {
                "id": "signal_mock_001",
                "mission_id": "mission_mock_001",
                "company_id": "company_mock_001",
                "signal_type": "placeholder",
                "confidence": 0.0,
                "evidence": [],
            }
        ],
        "total": 1,
    }

