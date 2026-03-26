"""
Tests for ConversationContext — memory and history management.
Run with: pytest tests/test_context.py -v
"""
from src.models.schemas import AgentResponse, AgentType, ConversationContext


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

    def test_alternating_roles_preserved(self):
        ctx = ConversationContext(session_id="test")
        ctx.add_user_message("question")
        ctx.add_agent_response(AgentResponse(agent=AgentType.SYMPTOM, text="answer"))
        ctx.add_user_message("follow up")
        roles = [m.role for m in ctx.history]
        assert roles == ["user", "assistant", "user"]

    def test_agent_type_stored_on_assistant_message(self):
        ctx = ConversationContext(session_id="test")
        ctx.add_agent_response(AgentResponse(agent=AgentType.MEDICATION, text="Take with food."))
        assert ctx.history[0].agent == AgentType.MEDICATION

    def test_trim_keeps_most_recent_messages(self):
        ctx = ConversationContext(session_id="test", max_history=3)
        for i in range(5):
            ctx.add_user_message(f"msg {i}")
        contents = [m.content for m in ctx.history]
        assert contents == ["msg 2", "msg 3", "msg 4"]
