"""
Response Synthesizer

Takes the specialist agent's raw reply and the recent conversation
context, then asks the LLM to produce a final response that:
  - Is coherent with what was said earlier in the conversation
  - Does not lose important context from prior turns
  - Maintains the agent's tone and safety boundaries
  - Feels like a continuous conversation, not isolated answers
"""
import litellm
from src.config import MODEL_NAME, TEMPERATURE
from src.models.schemas import AgentResponse, AgentType, ConversationContext

SYNTHESIS_WINDOW = 6  # last N messages to include as context

SYNTHESIZER_PROMPT = """You are a response quality specialist for mama health, a patient health platform.

You will receive:
1. A draft response from a specialist agent (symptom, medication, or lifestyle)
2. The recent conversation history

Your job is to refine the draft into a final response that:
- Flows naturally from the conversation — never repeat what was already said
- Acknowledges relevant details from prior turns if needed
- Preserves ALL safety information, medical caveats, and factual details EXACTLY as written
- Does NOT introduce new medical advice, assumptions, or information
- Keeps the same agent personality, tone, and scope — do not expand beyond it
- Improves clarity and removes redundancy only when necessary

Important rules:
- If the draft is already clear and coherent, return it with minimal or no changes
- Do NOT hallucinate or add new content
- Do NOT change the meaning of the response in any way

Return ONLY the final response text. No preamble, no labels, no explanation."""


class ResponseSynthesizer:
    """
    Refines a specialist agent's raw reply using recent conversation
    context so the final response feels coherent across turns.
    """

    def __init__(self) -> None:
        self.system_prompt = SYNTHESIZER_PROMPT

    def synthesize(
        self,
        raw_response: AgentResponse,
        context: ConversationContext,
    ) -> AgentResponse:
        recent = context.history[-(SYNTHESIS_WINDOW):]

        if len(recent) <= 1:
            return raw_response

        history_text = "\n".join(
            f"{m.role.upper()}: {m.content}" for m in recent
        )

        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": (
                    f"RECENT CONVERSATION:\n{history_text}\n\n"
                    f"DRAFT RESPONSE FROM {raw_response.agent.value.upper()} AGENT:\n"
                    f"{raw_response.text}\n\n"
                    f"Please produce the final refined response."
                ),
            },
        ]

        try:
            llm_response = litellm.completion(
                model=MODEL_NAME,
                messages=messages,
                max_tokens=1024,
                temperature=TEMPERATURE,
            )
            refined_text = llm_response.choices[0].message.content.strip()
        except Exception:
            return raw_response

        return AgentResponse(
            agent=raw_response.agent,
            text=refined_text,
            routed_by=raw_response.routed_by,
            confidence=raw_response.confidence,
            should_escalate=raw_response.should_escalate,
        )
