from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from app.agents.base.task import AgentTask
from app.agents.business_dna.business_dna_agent import BusinessDNAAgent
from app.core.logger import app_logger
from app.schemas.business_dna import BusinessDNADatabaseStatus, BusinessDNAOutput, BusinessDNARunResponse
from app.supabase.repositories.business_dna_repository import BusinessDNARepository
from app.supabase.repositories.market_discovery_repository import MarketDiscoveryRepository
from app.supabase.repositories.mission_repository import MissionRepository


class BusinessDNAService:
    """Application service for running the Business DNA intelligence pipeline."""

    def __init__(
        self,
        *,
        agent: BusinessDNAAgent | None = None,
        mission_repository: MissionRepository | None = None,
        market_repository: MarketDiscoveryRepository | None = None,
        business_dna_repository: BusinessDNARepository | None = None,
    ) -> None:
        self.agent = agent or BusinessDNAAgent()
        self.mission_repository = mission_repository or MissionRepository()
        self.market_repository = market_repository or MarketDiscoveryRepository()
        self.business_dna_repository = business_dna_repository or BusinessDNARepository()

    async def run(self, mission_id: str) -> BusinessDNARunResponse:
        started = time.perf_counter()

        # Load mission
        mission = await self.mission_repository.get_mission(mission_id)

        # Load market discovery results to feed into Business DNA
        market_rows = await self.market_repository.list_by_mission(mission_id)
        app_logger.info(
            "Business DNA service loaded market rows",
            mission_id=mission_id,
            market_rows=len(market_rows),
        )

        # Build shared memory from stored market discovery
        market_discovery_memory = self._build_market_memory(market_rows)

        shared_memory: dict[str, Any] = dict(mission.get("shared_memory") or {})
        shared_memory.update({
            "market_discovery": market_discovery_memory,
        })

        task = AgentTask(
            mission_id=mission_id,
            task_id=f"business_dna_{uuid4().hex}",
            agent_name=self.agent.name,
            objective=str(mission.get("objective") or ""),
            context={
                "mission": mission,
                "strategy": mission.get("strategy") or {},
                "icp": mission.get("icp") or {},
                "market_discovery": market_discovery_memory,
                "shared_memory": shared_memory,
            },
        )

        response = await self.agent.run(task)
        output = BusinessDNAOutput.model_validate(response.output)

        # Persist
        saved_rows = await self.business_dna_repository.save_results(mission_id, output.profiles)
        database_status = BusinessDNADatabaseStatus(
            saved=bool(saved_rows),
            verified=(len(saved_rows) == len(output.profiles)),
            table_name=self.business_dna_repository.table_name,
            rows=len(saved_rows),
        )
        if len(saved_rows) < len(output.profiles):
            database_status.verified = False
            app_logger.warning(
                "Business DNA persistence mismatch",
                expected=len(output.profiles),
                saved=len(saved_rows),
                mission_id=mission_id,
            )

        # Update shared memory
        shared_memory["business_dna"] = self._shared_memory_payload(output)
        if hasattr(self.mission_repository, "update_shared_memory"):
            await self.mission_repository.update_shared_memory(mission_id, shared_memory)

        # Update mission metadata
        await self._update_mission_metadata(mission_id, mission, output, database_status)

        runtime = time.perf_counter() - started
        app_logger.info("Business DNA service completed", mission_id=mission_id, runtime=runtime)

        return BusinessDNARunResponse(
            mission_id=mission_id,
            status="COMPLETED",
            business_dna=output,
            shared_memory=shared_memory,
            database_status=database_status,
            runtime=runtime,
        )

    def _build_market_memory(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        """Reconstruct market discovery memory from database rows."""
        companies = []
        scraped_pages = []
        for row in rows:
            metadata = row.get("firecrawl_metadata") or {}
            company_payload = metadata.get("company") if isinstance(metadata, dict) else None
            if isinstance(company_payload, dict):
                company = company_payload
            else:
                company = {
                    "company_name": row.get("title"),
                    "website": row.get("url"),
                    "summary": row.get("snippet"),
                    "evidence": [],
                    "metadata": metadata if isinstance(metadata, dict) else {},
                }
            company.setdefault("company_name", row.get("title"))
            company.setdefault("website", row.get("url"))
            company.setdefault("summary", row.get("snippet"))
            company.setdefault("evidence", metadata.get("evidence", []) if isinstance(metadata, dict) else [])
            company.setdefault("metadata", metadata if isinstance(metadata, dict) else {})
            company.setdefault("products", [])
            company.setdefault("services", [])
            company.setdefault("technologies", [])
            company.setdefault("use_cases", [])
            company: dict[str, Any] = {
                "company_name": company.get("company_name"),
                "website": company.get("website"),
                "summary": company.get("summary"),
                "industry": company.get("industry"),
                "country": company.get("country"),
                "headquarters": company.get("headquarters"),
                "products": company.get("products") or [],
                "services": company.get("services") or [],
                "technologies": company.get("technologies") or [],
                "use_cases": company.get("use_cases") or [],
                "evidence": company.get("evidence") or [],
                "metadata": company.get("metadata") or {},
            }
            companies.append(company)
            # Reconstruct a scraped page payload from stored company data for LLM context
            page: dict[str, Any] = {
                "url": row.get("url"),
                "title": row.get("title"),
                "content": row.get("firecrawl_markdown") or company.get("summary") or "",
            }
            scraped_pages.append(page)
        return {
            "companies": companies,
            "scraped_pages": scraped_pages,
            "company_count": len(companies),
        }

    def _shared_memory_payload(self, output: BusinessDNAOutput) -> dict[str, Any]:
        return {
            "profiles": [p.model_dump(mode="json") for p in output.profiles],
            "profile_count": output.profile_count,
            "execution_time": output.execution_time,
        }

    async def _update_mission_metadata(
        self,
        mission_id: str,
        mission: dict[str, Any],
        output: BusinessDNAOutput,
        database_status: BusinessDNADatabaseStatus,
    ) -> None:
        metadata = dict(mission.get("metadata") or {})
        metadata["business_dna"] = {
            "completed": True,
            "profile_count": output.profile_count,
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "table": "business_dna_results",
        }
        await self.mission_repository.update_metadata(mission_id, metadata)
