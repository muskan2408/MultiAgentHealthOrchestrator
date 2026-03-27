"""
Response Synthesizer

Takes the specialist agent's raw reply and the recent conversation
context, then asks the LLM to produce a final response that:
  - Is coherent with what was said earlier in the conversation
  - Does not lose important context from prior turns
  - Maintains the agent's tone and safety boundaries
  - Feels like a continuous conversation, not isolated answers
"""
from pathlib import Path

import litellm
from src.config import MAX_TOKENS, MODEL_NAME, TEMPERATURE
from src.models.schemas import AgentResponse, AgentType, ConversationContext

SYNTHESIS_WINDOW = 6  # last N messages to include as context


class ResponseSynthesizer:
    """
    Refines a specialist agent's raw reply using recent conversation
    context so the final response feels coherent across turns.
    """

    def __init__(self) -> None:
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "synthesizer.md"
        self.system_prompt = prompt_path.read_text(encoding="utf-8").strip()

    def synthesize(
        self,
        raw_response: AgentResponse,
        context: ConversationContext,
    ) -> AgentResponse:
        """Single-agent convenience wrapper."""
        return self.merge([raw_response], context)

    def merge(
        self,
        responses: list[AgentResponse],
        context: ConversationContext,
    ) -> AgentResponse:
        """Merge one or more agent responses into a coherent final answer.

        Passes through untouched when only one agent responded and
        there is minimal conversation history (first turn).
        """
        if not responses:
            return AgentResponse(
                agent=AgentType.FALLBACK,
                text="I'm not sure how to help with that.",
                routed_by=AgentType.ROUTER,
            )

        recent = context.history[-SYNTHESIS_WINDOW:]
        is_multi_agent = len(responses) > 1
        has_prior_context = len(recent) > 1

        # Pass through directly — no synthesis needed
        if not is_multi_agent and not has_prior_context:
            return responses[0]

        history_text = "\n".join(
            f"{m.role.upper()}: {m.content}" for m in recent
        )
        draft_text = "\n\n".join(
            f"{r.agent.value.upper()} AGENT DRAFT:\n{r.text}" for r in responses
        )

        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": (
                    f"RECENT CONVERSATION:\n{history_text}\n\n"
                    f"DRAFT RESPONSES:\n{draft_text}\n\n"
                    f"Produce the final response now."
                ),
            },
        ]

        try:
            llm_response = litellm.completion(
                model=MODEL_NAME,
                messages=messages,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
            )
            refined_text = llm_response.choices[0].message.content.strip()
        except Exception:
            refined_text = "\n\n".join(r.text for r in responses)

        should_escalate = any(r.should_escalate for r in responses)
        valid_confidences = [r.confidence for r in responses if r.confidence is not None]
        confidence = min(valid_confidences) if valid_confidences else None
        primary_agent = responses[0].agent if len(responses) == 1 else AgentType.SYNTHESIZER

        return AgentResponse(
            agent=primary_agent,
            text=refined_text,
            routed_by=AgentType.ROUTER,
            confidence=confidence,
            should_escalate=should_escalate,
        )
