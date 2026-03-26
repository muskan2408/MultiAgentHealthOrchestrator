import logging
from src.agents.base_agent import BaseAgent
from src.agents.lifestyle_agent import LifestyleAgent
from src.agents.medication_agent import MedicationAgent
from src.agents.router_agent import RouterAgent
from src.agents.symptom_agent import SymptomAgent
from src.models.schemas import (
    AgentResponse,
    AgentType,
    ConversationContext,
    RouterDecision,
    UserMessage,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


FALLBACK_RESPONSE = (
    "I'm here to help with health-related questions about symptoms, "
    "medications, and lifestyle. Could you tell me more about what you're "
    "looking for? If this is a medical emergency, please call your local "
    "emergency services immediately."
)


class Orchestrator:
    """
    Central coordinator. Receives a user message, asks the router which
    specialist should handle it, delegates to that agent, and returns
    the final response while keeping conversation context up to date.
    """

    def __init__(self) -> None:
        self.router = RouterAgent()
        self._agents: dict[AgentType, BaseAgent] = {
            AgentType.SYMPTOM: SymptomAgent(),
            AgentType.MEDICATION: MedicationAgent(),
            AgentType.LIFESTYLE: LifestyleAgent(),
        }
        self._contexts: dict[str, ConversationContext] = {}

    def _get_context(self, session_id: str) -> ConversationContext:
        if session_id not in self._contexts:
            self._contexts[session_id] = ConversationContext(session_id=session_id)
        return self._contexts[session_id]

    def _handle_fallback(self, session_id: str) -> AgentResponse:
        return AgentResponse(
            agent=AgentType.FALLBACK,
            text=FALLBACK_RESPONSE,
            routed_by=AgentType.ROUTER,
        )

    def process(self, user_message: UserMessage) -> AgentResponse:
        context = self._get_context(user_message.session_id)

        context.add_user_message(user_message.text)

        decision: RouterDecision = self.router.decide(user_message.text, context)

        logger.info(
            "Router decision: agent=%s confidence=%.2f reasoning=%s",
            decision.target_agent,
            decision.confidence,
            decision.reasoning,
        )

        if decision.target_agent == AgentType.FALLBACK:
            response = self._handle_fallback(user_message.session_id)
        else:
            agent = self._agents[decision.target_agent]
            response = agent.respond(user_message.text, context)

        if response.should_escalate:
            logger.warning(
                "ESCALATION flagged for session=%s text=%s",
                user_message.session_id,
                user_message.text[:80],
            )

        context.add_agent_response(response)

        return response
