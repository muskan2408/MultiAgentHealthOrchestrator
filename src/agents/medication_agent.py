from src.agents.base_agent import BaseAgent
from src.models.schemas import AgentResponse, AgentType, ConversationContext


class MedicationAgent(BaseAgent):
    agent_type = AgentType.MEDICATION
    prompt_file = "medication.md"

    def respond(
        self, user_text: str, context: ConversationContext
    ) -> AgentResponse:
        messages = self._build_messages(user_text, context)
        reply = self._call_llm(messages)
        return AgentResponse(
            agent=self.agent_type,
            text=reply,
        )
