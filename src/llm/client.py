import time
import logging
import litellm
from src.config.config import MODEL_NAME, MAX_TOKENS, TEMPERATURE

logger = logging.getLogger(__name__)

def call_llm(
    messages: list[dict],
    max_tokens: int = MAX_TOKENS,
    temperature: float = TEMPERATURE,
) -> str:
    for attempt in range(3):
        try:
            response = litellm.completion(
                model=MODEL_NAME,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if ("429" in str(e) or "rate" in str(e).lower()) and attempt < 2:
                wait = 15 * (attempt + 1)
                logger.warning("Rate limited, retrying in %ds (attempt %d)", wait, attempt + 1)
                time.sleep(wait)
            else:
                raise