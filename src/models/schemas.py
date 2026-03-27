from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class AgentType(str, Enum):
    ROUTER = "router"
    SYMPTOM = "symptom"
    MEDICATION = "medication"
    LIFESTYLE = "lifestyle"
    FALLBACK = "fallback"
    SYNTHESIZER = "synthesizer"


class Message(BaseModel):
    role: str
    content: str
    agent: Optional[AgentType] = None


class UserMessage(BaseModel):
    text: str
    session_id: str = Field(default="default")


class AgentResponse(BaseModel):
    agent: AgentType
    text: str
    routed_by: AgentType = AgentType.ROUTER
    confidence: Optional[float] = None
    should_escalate: bool = False


class ConversationContext(BaseModel):
    session_id: str
    history: List[Message] = Field(default_factory=list)
    max_history: int = 10

    def add_user_message(self, text: str) -> None:
        self.history.append(Message(role="user", content=text))
        self._trim()

    def add_agent_response(self, response: AgentResponse) -> None:
        self.history.append(
            Message(role="assistant", content=response.text, agent=response.agent)
        )
        self._trim()

    def get_history_for_prompt(self) -> List[dict]:
        return [{"role": m.role, "content": m.content} for m in self.history]

    def _trim(self) -> None:
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]


class RouterDecision(BaseModel):
    target_agents: List[AgentType]
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)

    @property
    def target_agent(self) -> AgentType:
        """Primary agent — always the first in the list."""
        return self.target_agents[0] if self.target_agents else AgentType.FALLBACK
