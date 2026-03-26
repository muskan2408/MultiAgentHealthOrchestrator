"""
Unit tests for routing logic and agent behaviour.
Run with: pytest tests/ -v
"""
import pytest
from unittest.mock import MagicMock, patch
from src.models.schemas import (
    AgentType,
    AgentResponse,
    ConversationContext,
    RouterDecision,
    UserMessage,
    Message,
)
from src.agents.router_agent import RouterAgent
from src.agents.symptom_agent import SymptomAgent, ESCALATION_KEYWORDS
from src.orchestrator.orchestrator import Orchestrator, FALLBACK_RESPONSE


# ---------------------------------------------------------------------------
# ConversationContext tests
# ---------------------------------------------------------------------------

class TestConversationContext:
    def test_add_user_message(self):
        ctx = ConversationContext(session_id="test")
        ctx.add_user_message("hello")
        assert len(ctx.history) == 1
        assert ctx.history[0].role == "user"
        assert ctx.history[0].content == "hello"

    def test_add_agent_response(self):
        ctx = ConversationContext(session_id="test")
        response = AgentResponse(agent=AgentType.SYMPTOM, text="How long?")
        ctx.add_agent_response(response)
        assert len(ctx.history) == 1
        assert ctx.history[0].role == "assistant"
        assert ctx.history[0].agent == AgentType.SYMPTOM

    def test_history_trimmed_to_max(self):
        ctx = ConversationContext(session_id="test", max_history=4)
        for i in range(6):
            ctx.add_user_message(f"message {i}")
        assert len(ctx.history) == 4
        assert ctx.history[-1].content == "message 5"

    def test_get_history_for_prompt_format(self):
        ctx = ConversationContext(session_id="test")
        ctx.add_user_message("hi")
        history = ctx.get_history_for_prompt()
        assert history == [{"role": "user", "content": "hi"}]

    def test_empty_history(self):
        ctx = ConversationContext(session_id="test")
        assert ctx.get_history_for_prompt() == []


# ---------------------------------------------------------------------------
# RouterAgent tests (LLM call is mocked)
# ---------------------------------------------------------------------------

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
    def test_routes_fallback_for_offtopic(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"target_agent": "fallback", "reasoning": "off topic", "confidence": 0.99}'))]
        )
        router = RouterAgent()
        ctx = ConversationContext(session_id="t")
        decision = router.decide("What is the capital of France?", ctx)
        assert decision.target_agent == AgentType.FALLBACK


# ---------------------------------------------------------------------------
# SymptomAgent tests (LLM call is mocked)
# ---------------------------------------------------------------------------

class TestSymptomAgent:
    @patch("src.agents.base_agent.litellm.completion")
    def test_respond_returns_agent_response(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="How long have you had the headache?"))]
        )
        agent = SymptomAgent()
        ctx = ConversationContext(session_id="t")
        result = agent.respond("I have a headache", ctx)
        assert result.agent == AgentType.SYMPTOM
        assert len(result.text) > 0

    @patch("src.agents.base_agent.litellm.completion")
    def test_escalation_flag_on_chest_pain(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Please call emergency services immediately."))]
        )
        agent = SymptomAgent()
        ctx = ConversationContext(session_id="t")
        result = agent.respond("I have chest pain and can't breathe", ctx)
        assert result.should_escalate is True

    @patch("src.agents.base_agent.litellm.completion")
    def test_no_escalation_for_mild_symptom(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="How long have you had this?"))]
        )
        agent = SymptomAgent()
        ctx = ConversationContext(session_id="t")
        result = agent.respond("I have a mild headache", ctx)
        assert result.should_escalate is False

    def test_escalation_keywords_list_not_empty(self):
        assert len(ESCALATION_KEYWORDS) > 0
        assert "chest pain" in ESCALATION_KEYWORDS

    @patch("src.agents.base_agent.litellm.completion")
    def test_context_history_included_in_messages(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="I see, tell me more."))]
        )
        agent = SymptomAgent()
        ctx = ConversationContext(session_id="t")
        ctx.add_user_message("I had a headache yesterday")
        ctx.add_agent_response(AgentResponse(agent=AgentType.SYMPTOM, text="How bad was it?"))
        agent.respond("It is worse today", ctx)
        call_messages = mock_llm.call_args[1]["messages"]
        roles = [m["role"] for m in call_messages]
        assert "system" in roles
        assert roles.count("user") >= 1


# ---------------------------------------------------------------------------
# Orchestrator tests
# NOTE: @patch decorators apply bottom-up, so the argument order in the
# function signature must be reversed relative to the decorator order.
# Bottom decorator → first argument, top decorator → second argument.
# ---------------------------------------------------------------------------

class TestOrchestrator:
    @patch("src.agents.router_agent.litellm.completion")   # applied second → mock_agent_llm
    @patch("src.agents.base_agent.litellm.completion")     # applied first  → mock_router_llm
    def test_full_flow_symptom(self, mock_router_llm, mock_agent_llm):
        mock_agent_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"target_agent": "symptom", "reasoning": "pain", "confidence": 0.9}'))]
        )
        mock_router_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Tell me more about your headache."))]
        )
        orch = Orchestrator()
        msg = UserMessage(text="I have a headache", session_id="s1")
        response = orch.process(msg)
        assert response.agent == AgentType.SYMPTOM
        assert len(response.text) > 0

    @patch("src.agents.router_agent.litellm.completion")
    def test_fallback_response(self, mock_router_llm):
        mock_router_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"target_agent": "fallback", "reasoning": "off topic", "confidence": 0.99}'))]
        )
        orch = Orchestrator()
        msg = UserMessage(text="Who won the World Cup?", session_id="s2")
        response = orch.process(msg)
        assert response.agent == AgentType.FALLBACK
        assert response.text == FALLBACK_RESPONSE

    @patch("src.agents.router_agent.litellm.completion")   # applied second → mock_agent_llm
    @patch("src.agents.base_agent.litellm.completion")     # applied first  → mock_router_llm
    def test_context_persists_across_turns(self, mock_router_llm, mock_agent_llm):
        mock_agent_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"target_agent": "symptom", "reasoning": "pain", "confidence": 0.9}'))]
        )
        mock_router_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Noted."))]
        )
        orch = Orchestrator()
        orch.process(UserMessage(text="Turn 1", session_id="persist"))
        orch.process(UserMessage(text="Turn 2", session_id="persist"))
        ctx = orch._contexts["persist"]
        assert len(ctx.history) == 4  # 2 user + 2 assistant

    @patch("src.agents.router_agent.litellm.completion")   # applied second → mock_agent_llm
    @patch("src.agents.base_agent.litellm.completion")     # applied first  → mock_router_llm
    def test_different_sessions_are_isolated(self, mock_router_llm, mock_agent_llm):
        mock_agent_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"target_agent": "lifestyle", "reasoning": "diet", "confidence": 0.85}'))]
        )
        mock_router_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Eat well."))]
        )
        orch = Orchestrator()
        orch.process(UserMessage(text="Hello", session_id="userA"))
        orch.process(UserMessage(text="Hello", session_id="userB"))
        assert "userA" in orch._contexts
        assert "userB" in orch._contexts
        assert orch._contexts["userA"] is not orch._contexts["userB"]


# ---------------------------------------------------------------------------
# ResponseSynthesizer tests
# ---------------------------------------------------------------------------

class TestResponseSynthesizer:
    @patch("src.orchestrator.synthesizer.litellm.completion")
    def test_synthesize_refines_text(self, mock_llm):
        from src.orchestrator.synthesizer import ResponseSynthesizer
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Refined: drink water and rest."))]
        )
        synth = ResponseSynthesizer()
        ctx = ConversationContext(session_id="t")
        ctx.add_user_message("I have a headache")
        ctx.add_agent_response(AgentResponse(agent=AgentType.SYMPTOM, text="Raw reply."))
        ctx.add_user_message("It is getting worse")
        raw = AgentResponse(agent=AgentType.SYMPTOM, text="Raw reply.")
        result = synth.synthesize(raw, ctx)
        assert result.text == "Refined: drink water and rest."
        assert result.agent == AgentType.SYMPTOM

    @patch("src.orchestrator.synthesizer.litellm.completion")
    def test_synthesize_skips_on_first_turn(self, mock_llm):
        from src.orchestrator.synthesizer import ResponseSynthesizer
        synth = ResponseSynthesizer()
        ctx = ConversationContext(session_id="t")
        ctx.add_user_message("Hello")
        raw = AgentResponse(agent=AgentType.LIFESTYLE, text="Original text.")
        result = synth.synthesize(raw, ctx)
        assert result.text == "Original text."
        mock_llm.assert_not_called()

    @patch("src.orchestrator.synthesizer.litellm.completion")
    def test_synthesize_preserves_escalation_flag(self, mock_llm):
        from src.orchestrator.synthesizer import ResponseSynthesizer
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Call emergency services."))]
        )
        synth = ResponseSynthesizer()
        ctx = ConversationContext(session_id="t")
        ctx.add_user_message("chest pain")
        ctx.add_agent_response(AgentResponse(agent=AgentType.SYMPTOM, text="Emergency."))
        ctx.add_user_message("it is severe")
        raw = AgentResponse(agent=AgentType.SYMPTOM, text="Emergency.", should_escalate=True)
        result = synth.synthesize(raw, ctx)
        assert result.should_escalate is True

    @patch("src.orchestrator.synthesizer.litellm.completion")
    def test_synthesize_falls_back_on_llm_error(self, mock_llm):
        from src.orchestrator.synthesizer import ResponseSynthesizer
        mock_llm.side_effect = Exception("LLM unavailable")
        synth = ResponseSynthesizer()
        ctx = ConversationContext(session_id="t")
        ctx.add_user_message("question")
        ctx.add_agent_response(AgentResponse(agent=AgentType.MEDICATION, text="Original."))
        ctx.add_user_message("follow up")
        raw = AgentResponse(agent=AgentType.MEDICATION, text="Original.")
        result = synth.synthesize(raw, ctx)
        assert result.text == "Original."
