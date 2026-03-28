"""
Tests for specialist agents — SymptomAgent, MedicationAgent, LifestyleAgent.
Run with: pytest tests/test_agents.py -v
"""
from unittest.mock import patch

from src.agents.symptom_agent import SymptomAgent, ESCALATION_KEYWORDS
from src.agents.medication_agent import MedicationAgent
from src.agents.lifestyle_agent import LifestyleAgent
from src.models.schemas import AgentResponse, AgentType, ConversationContext
from tests.conftest import make_llm_response


class TestSymptomAgent:
    @patch("src.llm.client.litellm.completion")
    def test_respond_returns_correct_agent_type(self, mock_llm, ctx):
        mock_llm.return_value = make_llm_response("How long have you had the headache?")
        agent = SymptomAgent()
        result = agent.respond("I have a headache", ctx)
        assert result.agent == AgentType.SYMPTOM

    @patch("src.llm.client.litellm.completion")
    def test_respond_returns_non_empty_text(self, mock_llm, ctx):
        mock_llm.return_value = make_llm_response("Tell me more.")
        agent = SymptomAgent()
        result = agent.respond("I feel unwell", ctx)
        assert len(result.text) > 0

    @patch("src.llm.client.litellm.completion")
    def test_escalation_flag_on_chest_pain(self, mock_llm, ctx):
        mock_llm.return_value = make_llm_response("Please call emergency services.")
        agent = SymptomAgent()
        result = agent.respond("I have chest pain and can't breathe", ctx)
        assert result.should_escalate is True

    @patch("src.llm.client.litellm.completion")
    def test_no_escalation_for_mild_symptom(self, mock_llm, ctx):
        mock_llm.return_value = make_llm_response("How long have you had this?")
        agent = SymptomAgent()
        result = agent.respond("I have a mild headache", ctx)
        assert result.should_escalate is False

    def test_escalation_keywords_not_empty(self):
        assert len(ESCALATION_KEYWORDS) > 0

    def test_chest_pain_in_escalation_keywords(self):
        assert "chest pain" in ESCALATION_KEYWORDS

    def test_stroke_in_escalation_keywords(self):
        assert "stroke" in ESCALATION_KEYWORDS

    @patch("src.llm.client.litellm.completion")
    def test_context_history_passed_to_llm(self, mock_llm):
        mock_llm.return_value = make_llm_response("I see, tell me more.")
        agent = SymptomAgent()
        ctx = ConversationContext(session_id="t")
        ctx.add_user_message("I had a headache yesterday")
        ctx.add_agent_response(AgentResponse(agent=AgentType.SYMPTOM, text="How bad?"))
        agent.respond("It is worse today", ctx)
        call_messages = mock_llm.call_args[1]["messages"]
        roles = [m["role"] for m in call_messages]
        assert "system" in roles
        assert roles.count("user") >= 2


class TestMedicationAgent:
    @patch("src.llm.client.litellm.completion")
    def test_respond_returns_correct_agent_type(self, mock_llm, ctx):
        mock_llm.return_value = make_llm_response("Ibuprofen can cause stomach upset.")
        agent = MedicationAgent()
        result = agent.respond("What are the side effects of ibuprofen?", ctx)
        assert result.agent == AgentType.MEDICATION

    @patch("src.llm.client.litellm.completion")
    def test_no_escalation_by_default(self, mock_llm, ctx):
        mock_llm.return_value = make_llm_response("Some info.")
        agent = MedicationAgent()
        result = agent.respond("What is aspirin used for?", ctx)
        assert result.should_escalate is False


class TestLifestyleAgent:
    @patch("src.llm.client.litellm.completion")
    def test_respond_returns_correct_agent_type(self, mock_llm, ctx):
        mock_llm.return_value = make_llm_response("Reduce sodium intake.")
        agent = LifestyleAgent()
        result = agent.respond("Foods to avoid with high blood pressure?", ctx)
        assert result.agent == AgentType.LIFESTYLE

    @patch("src.llm.client.litellm.completion")
    def test_respond_returns_non_empty_text(self, mock_llm, ctx):
        mock_llm.return_value = make_llm_response("Exercise regularly.")
        agent = LifestyleAgent()
        result = agent.respond("How do I stay healthy?", ctx)
        assert len(result.text) > 0
