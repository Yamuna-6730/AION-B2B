import asyncio
from app.supabase.repositories.mission_repository import MissionRepository
from app.services.strategy_service import StrategyService
from app.services.planner import PlannerService
from app.services.market_discovery_service import MarketDiscoveryService
from app.services.business_dna import BusinessDNAService
from app.services.recommendation import RecommendationService

async def main():
    repo = MissionRepository()
    mission = await repo.create_mission(title='E2E Test', objective='Find AI companies', strategy={}, icp={})
    mission_id = mission.get('id') if isinstance(mission, dict) else str(mission)
    print('Created mission', mission_id)

    try:
        strat_svc = StrategyService()
        strat_resp = await strat_svc.run(mission_id)
        print('Strategy done')
    except Exception as e:
        print('Strategy skipped or failed:', e)

    try:
        planner = PlannerService()
        planner_resp = await planner.run(mission_id)
        print('Planner done')
    except Exception as e:
        print('Planner skipped or failed:', e)

    md = MarketDiscoveryService()
    md_resp = await md.run(mission_id)
    print('Market discovery done: saved', md_resp.saved_company_count)

    bdna = BusinessDNAService()
    bdna_resp = await bdna.run(mission_id)
    print('Business DNA done: profiles', len(bdna_resp.business_dna.profiles))

    rec = RecommendationService()
    rec_resp = await rec.run(mission_id)
    print('Recommendation done: companies', len(rec_resp.recommendations.companies) if hasattr(rec_resp, 'recommendations') else rec_resp)

if __name__ == '__main__':
    asyncio.run(main())
