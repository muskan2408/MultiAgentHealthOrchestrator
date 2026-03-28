"""
Tests for ResponseSynthesizer — context-aware response refinement.
Run with: pytest tests/test_synthesizer.py -v
"""
from unittest.mock import MagicMock, patch

from src.models.schemas import AgentResponse, AgentType, ConversationContext
from src.orchestrator.synthesizer import ResponseSynthesizer


class TestResponseSynthesizer:
    @patch("src.llm.client.litellm.completion")
    def test_synthesize_refines_text(self, mock_llm):
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

    @patch("src.llm.client.litellm.completion")
    def test_synthesize_preserves_agent_type(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Refined reply."))]
        )
        synth = ResponseSynthesizer()
        ctx = ConversationContext(session_id="t")
        ctx.add_user_message("question")
        ctx.add_agent_response(AgentResponse(agent=AgentType.MEDICATION, text="Raw."))
        ctx.add_user_message("follow up")
        raw = AgentResponse(agent=AgentType.MEDICATION, text="Raw.")
        result = synth.synthesize(raw, ctx)
        assert result.agent == AgentType.MEDICATION

    @patch("src.llm.client.litellm.completion")
    def test_synthesize_skips_on_first_turn(self, mock_llm):
        synth = ResponseSynthesizer()
        ctx = ConversationContext(session_id="t")
        ctx.add_user_message("Hello")
        raw = AgentResponse(agent=AgentType.LIFESTYLE, text="Original text.")
        result = synth.synthesize(raw, ctx)
        assert result.text == "Original text."
        mock_llm.assert_not_called()

    @patch("src.llm.client.litellm.completion")
    def test_synthesize_preserves_escalation_flag(self, mock_llm):
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

    @patch("src.llm.client.litellm.completion")
    def test_synthesize_falls_back_on_llm_error(self, mock_llm):
        mock_llm.side_effect = Exception("LLM unavailable")
        synth = ResponseSynthesizer()
        ctx = ConversationContext(session_id="t")
        ctx.add_user_message("question")
        ctx.add_agent_response(AgentResponse(agent=AgentType.MEDICATION, text="Original."))
        ctx.add_user_message("follow up")
        raw = AgentResponse(agent=AgentType.MEDICATION, text="Original.")
        result = synth.synthesize(raw, ctx)
        assert result.text == "Original."

    @patch("src.llm.client.litellm.completion")
    def test_synthesize_preserves_routed_by(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Refined."))]
        )
        synth = ResponseSynthesizer()
        ctx = ConversationContext(session_id="t")
        ctx.add_user_message("q1")
        ctx.add_agent_response(AgentResponse(agent=AgentType.SYMPTOM, text="a1."))
        ctx.add_user_message("q2")
        raw = AgentResponse(agent=AgentType.SYMPTOM, text="Raw.", routed_by=AgentType.ROUTER)
        result = synth.synthesize(raw, ctx)
        assert result.routed_by == AgentType.ROUTER

    @patch("src.llm.client.litellm.completion")
    def test_merge_multiple_agents(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Merged answer."))]
        )
        synth = ResponseSynthesizer()
        ctx = ConversationContext(session_id="t")
        ctx.add_user_message("I feel sick after taking ibuprofen")
        responses = [
            AgentResponse(agent=AgentType.SYMPTOM, text="Symptom draft.", should_escalate=True),
            AgentResponse(agent=AgentType.MEDICATION, text="Medication draft.", confidence=0.8),
        ]
        result = synth.merge(responses, ctx)
        assert result.agent == AgentType.SYNTHESIZER
        assert result.text == "Merged answer."
        assert result.should_escalate is True
        assert result.confidence == 0.8

    def test_merge_empty_responses(self):
        synth = ResponseSynthesizer()
        ctx = ConversationContext(session_id="t")
        result = synth.merge([], ctx)
        assert result.agent == AgentType.FALLBACK
