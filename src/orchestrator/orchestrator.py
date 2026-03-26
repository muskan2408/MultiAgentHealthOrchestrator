import logging
from src.agents.base_agent import BaseAgent
from src.agents.lifestyle_agent import LifestyleAgent
from src.agents.medication_agent import MedicationAgent
from src.agents.router_agent import RouterAgent
from src.agents.symptom_agent import SymptomAgent
from src.orchestrator.synthesizer import ResponseSynthesizer
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
    specialist should handle it, delegates to that agent, synthesizes
    the response with conversation context, and returns the final reply.
    Supports multiple independent sessions simultaneously.
    """

    def __init__(self) -> None:
        self.router = RouterAgent()
        self.synthesizer = ResponseSynthesizer()
        self._agents: dict[AgentType, BaseAgent] = {
            AgentType.SYMPTOM: SymptomAgent(),
            AgentType.MEDICATION: MedicationAgent(),
            AgentType.LIFESTYLE: LifestyleAgent(),
        }
        self._contexts: dict[str, ConversationContext] = {}

    def _get_context(self, session_id: str) -> ConversationContext:
        """Returns existing context for session or creates a new one."""
        if session_id not in self._contexts:
            self._contexts[session_id] = ConversationContext(session_id=session_id)
            logger.info("New session created: %s", session_id)
        return self._contexts[session_id]

    def get_all_sessions(self) -> list[str]:
        """Returns all active session IDs."""
        return list(self._contexts.keys())

    def clear_session(self, session_id: str) -> None:
        """Clears history for a given session."""
        if session_id in self._contexts:
            del self._contexts[session_id]
            logger.info("Session cleared: %s", session_id)

    def _handle_fallback(self) -> AgentResponse:
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
            "Router decision: session=%s agent=%s confidence=%.2f reasoning=%s",
            user_message.session_id,
            decision.target_agent,
            decision.confidence,
            decision.reasoning,
        )

        if decision.target_agent == AgentType.FALLBACK:
            response = self._handle_fallback()
        else:
            agent = self._agents[decision.target_agent]
            raw_response = agent.respond(user_message.text, context)

            logger.info(
                "Synthesizing response for session=%s agent=%s",
                user_message.session_id,
                raw_response.agent,
            )
            response = self.synthesizer.synthesize(raw_response, context)

        if response.should_escalate:
            logger.warning(
                "ESCALATION flagged: session=%s text=%s",
                user_message.session_id,
                user_message.text[:80],
            )

        context.add_agent_response(response)

        return response
