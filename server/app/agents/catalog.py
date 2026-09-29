from app.agents.base.enums import AgentState
from app.agents.base.base_agent import BaseAgent
from app.agents.base.response import AgentResponse
from app.agents.base.task import AgentTask
from app.agents.market_discovery import MarketDiscoveryAgent
from app.agents.discovery.intelligence_agents import FundingIntelligenceAgent, HiringIntelligenceAgent
from app.agents.business_dna.business_dna_agent import BusinessDNAAgent as _RealBusinessDNAAgent
from app.agents.recommendation.recommendation_agent import RecommendationAgent as _RealRecommendationAgent
from app.core.constants import DEFAULT_AGENT_PRIORITY, DEFAULT_AGENT_VERSION


class MockAgent(BaseAgent):
    description = "Placeholder agent for future implementation."
    version = DEFAULT_AGENT_VERSION
    priority = DEFAULT_AGENT_PRIORITY
    supported_inputs: tuple[str, ...] = ("mission",)
    supported_outputs: tuple[str, ...] = ("agent_response",)

    async def initialize(self) -> None:
        return None

    async def run(self, task: AgentTask) -> AgentResponse:
        return AgentResponse(
            success=True,
            mission_id=task.mission_id,
            task_id=task.task_id,
            agent_name=self.name,
            status=AgentState.COMPLETED,
            confidence=0.0,
            reasoning="Mock response from backend skeleton. No agent logic executed.",
            evidence=[],
            execution_time=0.0,
            metadata={"category": self.category, "version": self.version},
            output={},
        )

    async def validate(self, task: AgentTask) -> bool:
        return task.agent_name == self.name

    async def summarize(self, response: AgentResponse) -> str:
        return response.reasoning

    async def calculate_confidence(self, response: AgentResponse) -> float:
        return response.confidence

    async def cleanup(self) -> None:
        return None


class PlannerAgent(MockAgent):
    name = "planner"
    category = "planner"


class NewsAgent(MockAgent):
    name = "news"
    category = "discovery"


class PatentAgent(MockAgent):
    name = "patent"
    category = "discovery"


class ConferenceAgent(MockAgent):
    name = "conference"
    category = "discovery"


class TechnologyAgent(MockAgent):
    name = "technology"
    category = "discovery"


class ExpansionAgent(MockAgent):
    name = "expansion"
    category = "discovery"


class LeadershipAgent(MockAgent):
    name = "leadership"
    category = "discovery"


class AcquisitionAgent(MockAgent):
    name = "acquisition"
    category = "discovery"


class CompanyDiscoveryAgent(MockAgent):
    name = "company_discovery"
    category = "enrichment"


class CompanyValidationAgent(MockAgent):
    name = "company_validation"
    category = "enrichment"


class LinkedInAgent(MockAgent):
    name = "linkedin"
    category = "enrichment"


class WebsiteAgent(MockAgent):
    name = "website"
    category = "enrichment"


class EmailAgent(MockAgent):
    name = "email"
    category = "enrichment"


class PhoneAgent(MockAgent):
    name = "phone"
    category = "enrichment"


class DecisionMakerAgent(MockAgent):
    name = "decision_maker"
    category = "intelligence"


class TechStackAgent(MockAgent):
    name = "tech_stack"
    category = "intelligence"


BusinessDNAAgent = _RealBusinessDNAAgent


class RelationshipGraphAgent(MockAgent):
    name = "relationship_graph"
    category = "intelligence"


class SignalAggregationAgent(MockAgent):
    name = "signal_aggregation"
    category = "reasoning"


class EvidenceAgent(MockAgent):
    name = "evidence"
    category = "reasoning"


class ConfidenceAgent(MockAgent):
    name = "confidence"
    category = "reasoning"


class OpportunityAgent(MockAgent):
    name = "opportunity"
    category = "recommendation"


class RiskAgent(MockAgent):
    name = "risk"
    category = "recommendation"


class CompetitionAgent(MockAgent):
    name = "competition"
    category = "recommendation"


class SalesAgent(MockAgent):
    name = "sales"
    category = "recommendation"


class FinanceAgent(MockAgent):
    name = "finance"
    category = "recommendation"


RecommendationAgent = _RealRecommendationAgent


class SimulationAgent(MockAgent):
    name = "simulation"
    category = "utility"


class SummaryAgent(MockAgent):
    name = "summary"
    category = "utility"


class ExportAgent(MockAgent):
    name = "export"
    category = "utility"


class NotificationAgent(MockAgent):
    name = "notification"
    category = "utility"


class LoggerAgent(MockAgent):
    name = "logger"
    category = "utility"


INITIAL_AGENT_CLASSES = (
    PlannerAgent,
    MarketDiscoveryAgent,
    NewsAgent,
    HiringIntelligenceAgent,
    FundingIntelligenceAgent,
    PatentAgent,
    ConferenceAgent,
    TechnologyAgent,
    ExpansionAgent,
    LeadershipAgent,
    AcquisitionAgent,
    CompanyDiscoveryAgent,
    CompanyValidationAgent,
    LinkedInAgent,
    WebsiteAgent,
    EmailAgent,
    PhoneAgent,
    DecisionMakerAgent,
    TechStackAgent,
    BusinessDNAAgent,
    RelationshipGraphAgent,
    SignalAggregationAgent,
    EvidenceAgent,
    ConfidenceAgent,
    OpportunityAgent,
    RiskAgent,
    CompetitionAgent,
    SalesAgent,
    FinanceAgent,
    RecommendationAgent,
    SimulationAgent,
    SummaryAgent,
    ExportAgent,
    NotificationAgent,
    LoggerAgent,
)

# The planner may only schedule agents with a complete, production-backed
# execution path. The broader catalog remains available to its dedicated APIs.
ACTIVE_INTELLIGENCE_AGENT_CLASSES = (
    HiringIntelligenceAgent,
    FundingIntelligenceAgent,
)
