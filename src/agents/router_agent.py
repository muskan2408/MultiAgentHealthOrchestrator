import json
import logging
import re
from pathlib import Path

from src.llm.client import call_llm 
from src.models.schemas import AgentType, ConversationContext, RouterDecision

logger = logging.getLogger(__name__)

class RouterAgent:
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

        try:
            raw = call_llm(messages, max_tokens=256)
            logger.info("Router raw LLM response: %s", raw)
        except Exception as e:
            return RouterDecision(
                target_agents=[AgentType.FALLBACK],
                reasoning=f"LLM call failed: {e}",
                confidence=0.0,
            )

        return self._parse_decision(raw)

    def _parse_decision(self, raw: str) -> RouterDecision:
        try:
            cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if not match:
                raise ValueError("No JSON object found")

            data = json.loads(match.group())
            raw_agents = data.get("target_agents") or data.get("target_agent")

            if isinstance(raw_agents, str):
                raw_agents = [raw_agents]
            elif not isinstance(raw_agents, list):
                raw_agents = ["fallback"]

            target_agents = []
            for a in raw_agents:
                try:
                    target_agents.append(AgentType(str(a).strip().lower()))
                except ValueError:
                    target_agents.append(AgentType.FALLBACK)

            if not target_agents:
                target_agents = [AgentType.FALLBACK]

            return RouterDecision(
                target_agents=target_agents,
                reasoning=str(data.get("reasoning", "")),
                confidence=float(data.get("confidence", 0.8)),
            )

        except Exception as e:
            return RouterDecision(
                target_agents=[AgentType.FALLBACK],
                reasoning=f"Parse failed: {e}",
                confidence=0.0,
            )
