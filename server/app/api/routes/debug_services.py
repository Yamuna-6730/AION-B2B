from fastapi import APIRouter, Query

from app.services.tavily_service import TavilyService
from app.services.firecrawl_service import FirecrawlService

router = APIRouter(
    prefix="/api/debug/services",
    tags=["Debug Services"],
)

tavily = TavilyService()
firecrawl = FirecrawlService()


@router.get("/tavily")
async def test_tavily(
    query: str = Query(
        default="Enterprise AI cybersecurity companies in Germany"
    )
):
    """
    Test live Tavily API.
    """
    return await tavily.search(query)


@router.get("/firecrawl")
async def test_firecrawl(
    url: str = Query(
        default="https://www.darktrace.com"
    )
):
    """
    Test live Firecrawl API.
    """
    return await firecrawl.scrape(url)