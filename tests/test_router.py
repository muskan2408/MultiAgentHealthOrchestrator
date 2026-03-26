"""
Tests for RouterAgent — intent classification and JSON parsing.
Run with: pytest tests/test_router.py -v
"""
from unittest.mock import MagicMock, patch

from src.agents.router_agent import RouterAgent
from src.models.schemas import AgentType, ConversationContext


class TestRouterAgent:
    @patch("src.agents.router_agent.litellm.completion")
    def test_routes_symptom(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"target_agent": "symptom", "reasoning": "physical complaint", "confidence": 0.95}'))]
        )
        router = RouterAgent()
        ctx = ConversationContext(session_id="t")
        decision = router.decide("I have a headache", ctx)
        assert decision.target_agent == AgentType.SYMPTOM
        assert decision.confidence == 0.95

    @patch("src.agents.router_agent.litellm.completion")
    def test_routes_medication(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"target_agent": "medication", "reasoning": "drug question", "confidence": 0.90}'))]
        )
        router = RouterAgent()
        ctx = ConversationContext(session_id="t")
        decision = router.decide("What are the side effects of ibuprofen?", ctx)
        assert decision.target_agent == AgentType.MEDICATION

    @patch("src.agents.router_agent.litellm.completion")
    def test_routes_lifestyle(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"target_agent": "lifestyle", "reasoning": "diet question", "confidence": 0.88}'))]
        )
        router = RouterAgent()
        ctx = ConversationContext(session_id="t")
        decision = router.decide("What foods help lower blood pressure?", ctx)
        assert decision.target_agent == AgentType.LIFESTYLE

    @patch("src.agents.router_agent.litellm.completion")
    def test_routes_fallback_for_offtopic(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"target_agent": "fallback", "reasoning": "off topic", "confidence": 0.99}'))]
        )
        router = RouterAgent()
        ctx = ConversationContext(session_id="t")
        decision = router.decide("What is the capital of France?", ctx)
        assert decision.target_agent == AgentType.FALLBACK

    @patch("src.agents.router_agent.litellm.completion")
    def test_fallback_on_garbage_response(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="not json at all !!!"))]
        )
        router = RouterAgent()
        ctx = ConversationContext(session_id="t")
        decision = router.decide("something weird", ctx)
        assert decision.target_agent == AgentType.FALLBACK
        assert decision.confidence == 0.0

    @patch("src.agents.router_agent.litellm.completion")
    def test_strips_markdown_fences(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='```json\n{"target_agent": "symptom", "reasoning": "test", "confidence": 0.8}\n```'))]
        )
        router = RouterAgent()
        ctx = ConversationContext(session_id="t")
        decision = router.decide("I feel dizzy", ctx)
        assert decision.target_agent == AgentType.SYMPTOM

    @patch("src.agents.router_agent.litellm.completion")
    def test_reasoning_preserved(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"target_agent": "symptom", "reasoning": "user describes pain", "confidence": 0.9}'))]
        )
        router = RouterAgent()
        ctx = ConversationContext(session_id="t")
        decision = router.decide("my back hurts", ctx)
        assert decision.reasoning == "user describes pain"

    @patch("src.agents.router_agent.litellm.completion")
    def test_confidence_clamped_in_model(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"target_agent": "lifestyle", "reasoning": "wellness", "confidence": 0.5}'))]
        )
        router = RouterAgent()
        ctx = ConversationContext(session_id="t")
        decision = router.decide("I want to eat better", ctx)
        assert 0.0 <= decision.confidence <= 1.0
