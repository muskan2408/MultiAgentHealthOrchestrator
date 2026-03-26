from src.agents.base_agent import BaseAgent
from src.models.schemas import AgentResponse, AgentType, ConversationContext


class LifestyleAgent(BaseAgent):
    agent_type = AgentType.LIFESTYLE
    prompt_file = "lifestyle.md"

    def respond(
        self, user_text: str, context: ConversationContext
    ) -> AgentResponse:
        messages = self._build_messages(user_text, context)
        reply = self._call_llm(messages)
        return AgentResponse(
            agent=self.agent_type,
            text=reply,
        )
