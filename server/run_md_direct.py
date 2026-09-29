import asyncio
from app.supabase.repositories.mission_repository import MissionRepository
from app.services.market_discovery_service import MarketDiscoveryService

async def main():
    repo = MissionRepository()
    mission = await repo.create_mission(title='MD Test', objective='Discover companies')
    mission_id = mission.get('id') if isinstance(mission, dict) else str(mission)
    print('Created mission', mission_id)

    svc = MarketDiscoveryService()
    resp = await svc.run(mission_id)
    print('Saved company count:', resp.saved_company_count)
    print('Shared memory companies:', resp.shared_memory.get('market_discovery', {}).get('company_count'))

if __name__ == '__main__':
    asyncio.run(main())
