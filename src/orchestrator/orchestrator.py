import logging
from typing import Dict

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

# Configurable thresholds
MIN_CONFIDENCE_THRESHOLD = 0.6
MAX_CONTEXT_MESSAGES = 12


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

        self._agents: Dict[AgentType, BaseAgent] = {
            AgentType.SYMPTOM: SymptomAgent(),
            AgentType.MEDICATION: MedicationAgent(),
            AgentType.LIFESTYLE: LifestyleAgent(),
        }

        self._contexts: Dict[str, ConversationContext] = {}

    # -------------------------
    # Context Management
    # -------------------------
    def _get_context(self, session_id: str) -> ConversationContext:
        """Returns existing context for session or creates a new one."""
        if session_id not in self._contexts:
            self._contexts[session_id] = ConversationContext(session_id=session_id)
            logger.info("New session created: %s", session_id)
        return self._contexts[session_id]

    def _trim_context(self, context: ConversationContext) -> None:
        """Prevent unbounded growth — trims to MAX_CONTEXT_MESSAGES."""
        if len(context.history) > MAX_CONTEXT_MESSAGES:
            context.history = context.history[-MAX_CONTEXT_MESSAGES:]

    def get_all_sessions(self) -> list[str]:
        """Returns all active session IDs."""
        return list(self._contexts.keys())

    def clear_session(self, session_id: str) -> None:
        """Clears history for a given session."""
        if session_id in self._contexts:
            del self._contexts[session_id]
            logger.info("Session cleared: %s", session_id)

    # -------------------------
    # Fallback Handling
    # -------------------------
    def _handle_fallback(self) -> AgentResponse:
        return AgentResponse(
            agent=AgentType.FALLBACK,
            text=FALLBACK_RESPONSE,
            routed_by=AgentType.ROUTER,
        )

    # -------------------------
    # Main Processing Pipeline
    # -------------------------
    def process(self, user_message: UserMessage) -> AgentResponse:
        context = self._get_context(user_message.session_id)

        # Add user message
        context.add_user_message(user_message.text)

        # Trim context to avoid token explosion
        self._trim_context(context)

        # Step 1: Routing
        try:
            decision: RouterDecision = self.router.decide(user_message.text, context)
        except Exception:
            logger.exception("Router failed")
            return self._handle_fallback()

        logger.info(
            "Router decision: session=%s agents=%s confidence=%.2f reasoning=%s",
            user_message.session_id,
            [a.value for a in decision.target_agents],
            decision.confidence,
            decision.reasoning,
        )

        # Step 2: Confidence gating
        if decision.confidence < MIN_CONFIDENCE_THRESHOLD:
            logger.warning(
                "Low confidence routing: session=%s confidence=%.2f",
                user_message.session_id,
                decision.confidence,
            )
            return self._handle_fallback()

        # Step 3: Agent execution — fan out to all target agents
        try:
            # Filter out fallback early
            agents_to_run = [
                a for a in decision.target_agents
                if a != AgentType.FALLBACK and a in self._agents
            ]

            if not agents_to_run:
                response = self._handle_fallback()
            else:
                raw_responses = []
                for agent_type in agents_to_run:
                    agent = self._agents[agent_type]
                    raw = agent.respond(user_message.text, context)
                    raw_responses.append(raw)
                    logger.info(
                        "Agent responded: session=%s agent=%s",
                        user_message.session_id,
                        agent_type.value,
                    )

                # Step 4: Merge all responses via synthesizer
                response = self.synthesizer.merge(raw_responses, context)

        except Exception:
            logger.exception(
                "Agent execution failed: session=%s agents=%s",
                user_message.session_id,
                [a.value for a in decision.target_agents],
            )
            return self._handle_fallback()

        # Step 5: Escalation logging
        if getattr(response, "should_escalate", False):
            logger.warning(
                "ESCALATION flagged: session=%s text=%s",
                user_message.session_id,
                user_message.text[:80],
            )

        # Step 6: Persist response in context
        try:
            context.add_agent_response(response)
        except Exception:
            logger.warning("Failed to store agent response", exc_info=True)

        return response