"""
Tests for RouterAgent — intent classification and JSON parsing.
Run with: pytest tests/test_router.py -v
"""
from unittest.mock import patch

from src.agents.router_agent import RouterAgent
from src.models.schemas import AgentType
from tests.conftest import make_llm_response


class TestRouterAgent:
    @patch("src.llm.client.litellm.completion")
    def test_routes_symptom(self, mock_llm, ctx):
        mock_llm.return_value = make_llm_response('{"target_agent": "symptom", "reasoning": "physical complaint", "confidence": 0.95}')
        router = RouterAgent()
        decision = router.decide("I have a headache", ctx)
        assert decision.target_agent == AgentType.SYMPTOM
        assert decision.confidence == 0.95

    @patch("src.llm.client.litellm.completion")
    def test_routes_medication(self, mock_llm, ctx):
        mock_llm.return_value = make_llm_response('{"target_agent": "medication", "reasoning": "drug question", "confidence": 0.90}')
        router = RouterAgent()
        decision = router.decide("What are the side effects of ibuprofen?", ctx)
        assert decision.target_agent == AgentType.MEDICATION

    @patch("src.llm.client.litellm.completion")
    def test_routes_lifestyle(self, mock_llm, ctx):
        mock_llm.return_value = make_llm_response('{"target_agent": "lifestyle", "reasoning": "diet question", "confidence": 0.88}')
        router = RouterAgent()
        decision = router.decide("What foods help lower blood pressure?", ctx)
        assert decision.target_agent == AgentType.LIFESTYLE

    @patch("src.llm.client.litellm.completion")
    def test_routes_fallback_for_offtopic(self, mock_llm, ctx):
        mock_llm.return_value = make_llm_response('{"target_agent": "fallback", "reasoning": "off topic", "confidence": 0.99}')
        router = RouterAgent()
        decision = router.decide("What is the capital of France?", ctx)
        assert decision.target_agent == AgentType.FALLBACK

    @patch("src.llm.client.litellm.completion")
    def test_fallback_on_garbage_response(self, mock_llm, ctx):
        mock_llm.return_value = make_llm_response("not json at all !!!")
        router = RouterAgent()
        decision = router.decide("something weird", ctx)
        assert decision.target_agent == AgentType.FALLBACK
        assert decision.confidence == 0.0

    @patch("src.llm.client.litellm.completion")
    def test_strips_markdown_fences(self, mock_llm, ctx):
        mock_llm.return_value = make_llm_response('```json\n{"target_agent": "symptom", "reasoning": "test", "confidence": 0.8}\n```')
        router = RouterAgent()
        decision = router.decide("I feel dizzy", ctx)
        assert decision.target_agent == AgentType.SYMPTOM

    @patch("src.llm.client.litellm.completion")
    def test_reasoning_preserved(self, mock_llm, ctx):
        mock_llm.return_value = make_llm_response('{"target_agent": "symptom", "reasoning": "user describes pain", "confidence": 0.9}')
        router = RouterAgent()
        decision = router.decide("my back hurts", ctx)
        assert decision.reasoning == "user describes pain"

    @patch("src.llm.client.litellm.completion")
    def test_confidence_clamped_in_model(self, mock_llm, ctx):
        mock_llm.return_value = make_llm_response('{"target_agent": "lifestyle", "reasoning": "wellness", "confidence": 0.5}')
        router = RouterAgent()
        decision = router.decide("I want to eat better", ctx)
        assert 0.0 <= decision.confidence <= 1.0
