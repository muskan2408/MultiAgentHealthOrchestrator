from src.agents.base_agent import BaseAgent
from src.llm.client import call_llm 
from src.models.schemas import AgentResponse, AgentType, ConversationContext

ESCALATION_KEYWORDS = [
    "chest pain", "can't breathe", "cannot breathe", "difficulty breathing",
    "stroke", "unconscious", "severe bleeding", "heart attack", "overdose",
]


class SymptomAgent(BaseAgent):
    agent_type = AgentType.SYMPTOM
    prompt_file = "symptom.md"

    def respond(
        self, user_text: str, context: ConversationContext
    ) -> AgentResponse:
        messages = self._build_messages(user_text, context)
        reply = call_llm(messages)
        should_escalate = any(
            kw in user_text.lower() for kw in ESCALATION_KEYWORDS
        )
        return AgentResponse(
            agent=self.agent_type,
            text=reply,
            should_escalate=should_escalate,
        )
