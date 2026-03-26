from abc import ABC, abstractmethod
from pathlib import Path

import litellm

from src.config import MAX_TOKENS, MODEL_NAME, TEMPERATURE
from src.models.schemas import AgentResponse, AgentType, ConversationContext


class BaseAgent(ABC):
    """Abstract base class all specialist agents must implement."""

    agent_type: AgentType
    prompt_file: str

    def __init__(self) -> None:
        self.system_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / self.prompt_file
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8").strip()

    def _build_messages(
        self, user_text: str, context: ConversationContext
    ) -> list[dict]:
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(context.get_history_for_prompt())
        messages.append({"role": "user", "content": user_text})
        return messages

    @abstractmethod
    def respond(
        self, user_text: str, context: ConversationContext
    ) -> AgentResponse:
        pass

    def _call_llm(self, messages: list[dict]) -> str:
        response = litellm.completion(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
        return response.choices[0].message.content.strip()
