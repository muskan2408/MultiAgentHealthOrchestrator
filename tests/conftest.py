import pytest
from unittest.mock import MagicMock

from src.models.schemas import ConversationContext


@pytest.fixture
def ctx():
    return ConversationContext(session_id="t")


def make_llm_response(content: str) -> MagicMock:
    return MagicMock(
        choices=[MagicMock(message=MagicMock(content=content))]
    )
