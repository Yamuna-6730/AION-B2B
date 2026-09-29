class CompanyService:
    async def list_companies(self, mission_id: str | None = None) -> None:
        raise NotImplementedError

    async def get_company(self, company_id: str) -> None:
        raise NotImplementedError

