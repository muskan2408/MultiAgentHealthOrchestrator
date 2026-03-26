"""
Tests for specialist agents — SymptomAgent, MedicationAgent, LifestyleAgent.
Run with: pytest tests/test_agents.py -v
"""
from unittest.mock import MagicMock, patch

from src.agents.symptom_agent import SymptomAgent, ESCALATION_KEYWORDS
from src.agents.medication_agent import MedicationAgent
from src.agents.lifestyle_agent import LifestyleAgent
from src.models.schemas import AgentResponse, AgentType, ConversationContext


class TestSymptomAgent:
    @patch("src.agents.base_agent.litellm.completion")
    def test_respond_returns_correct_agent_type(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="How long have you had the headache?"))]
        )
        agent = SymptomAgent()
        ctx = ConversationContext(session_id="t")
        result = agent.respond("I have a headache", ctx)
        assert result.agent == AgentType.SYMPTOM

    @patch("src.agents.base_agent.litellm.completion")
    def test_respond_returns_non_empty_text(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Tell me more."))]
        )
        agent = SymptomAgent()
        ctx = ConversationContext(session_id="t")
        result = agent.respond("I feel unwell", ctx)
        assert len(result.text) > 0

    @patch("src.agents.base_agent.litellm.completion")
    def test_escalation_flag_on_chest_pain(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Please call emergency services."))]
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

    def test_escalation_keywords_not_empty(self):
        assert len(ESCALATION_KEYWORDS) > 0

    def test_chest_pain_in_escalation_keywords(self):
        assert "chest pain" in ESCALATION_KEYWORDS

    def test_stroke_in_escalation_keywords(self):
        assert "stroke" in ESCALATION_KEYWORDS

    @patch("src.agents.base_agent.litellm.completion")
    def test_context_history_passed_to_llm(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="I see, tell me more."))]
        )
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
    @patch("src.agents.base_agent.litellm.completion")
    def test_respond_returns_correct_agent_type(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Ibuprofen can cause stomach upset."))]
        )
        agent = MedicationAgent()
        ctx = ConversationContext(session_id="t")
        result = agent.respond("What are the side effects of ibuprofen?", ctx)
        assert result.agent == AgentType.MEDICATION

    @patch("src.agents.base_agent.litellm.completion")
    def test_no_escalation_by_default(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Some info."))]
        )
        agent = MedicationAgent()
        ctx = ConversationContext(session_id="t")
        result = agent.respond("What is aspirin used for?", ctx)
        assert result.should_escalate is False


class TestLifestyleAgent:
    @patch("src.agents.base_agent.litellm.completion")
    def test_respond_returns_correct_agent_type(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Reduce sodium intake."))]
        )
        agent = LifestyleAgent()
        ctx = ConversationContext(session_id="t")
        result = agent.respond("Foods to avoid with high blood pressure?", ctx)
        assert result.agent == AgentType.LIFESTYLE

    @patch("src.agents.base_agent.litellm.completion")
    def test_respond_returns_non_empty_text(self, mock_llm):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Exercise regularly."))]
        )
        agent = LifestyleAgent()
        ctx = ConversationContext(session_id="t")
        result = agent.respond("How do I stay healthy?", ctx)
        assert len(result.text) > 0
