import json
import re

import litellm

from src.config import MODEL_NAME, TEMPERATURE
from src.models.schemas import AgentType, ConversationContext, RouterDecision
from pathlib import Path


class RouterAgent:
    """Classifies user intent and returns a routing decision."""

    def __init__(self) -> None:
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "router.md"
        self.system_prompt = prompt_path.read_text(encoding="utf-8").strip()

    def decide(
        self, user_text: str, context: ConversationContext
    ) -> RouterDecision:
        messages = [
            {"role": "system", "content": self.system_prompt},
            *context.get_history_for_prompt()[-4:],
            {"role": "user", "content": user_text},
        ]
        response = litellm.completion(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=256,
            temperature=TEMPERATURE,
        )
        raw = response.choices[0].message.content.strip()
        return self._parse_decision(raw)

    def _parse_decision(self, raw: str) -> RouterDecision:
        try:
            cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
            data = json.loads(cleaned)
            return RouterDecision(
                target_agent=AgentType(data["target_agent"]),
                reasoning=data.get("reasoning", ""),
                confidence=float(data.get("confidence", 0.8)),
            )
        except Exception:
            return RouterDecision(
                target_agent=AgentType.FALLBACK,
                reasoning="Could not parse router response",
                confidence=0.0,
            )
