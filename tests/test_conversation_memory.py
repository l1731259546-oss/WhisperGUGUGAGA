"""Tests for ConversationMemory."""
from datetime import datetime
from vision_assistant.agent.conversation_memory import ConversationMemory


def test_add_round_trims_old():
    """Test that adding rounds beyond max trims old ones."""
    memory = ConversationMemory(max_turns=3)

    for i in range(5):
        memory.add_round(datetime.now(), False, f"message {i}")

    assert len(memory) == 3

    history = memory.get_history()
    assert [m.message for m in history] == ["message 2", "message 3", "message 4"]


def test_clear():
    """Test clear works."""
    memory = ConversationMemory(max_turns=3)
    memory.add_round(datetime.now(), False, "test")
    memory.clear()
    assert len(memory) == 0


def test_update_max_turns_trims():
    """Test updating max_turns trims if needed."""
    memory = ConversationMemory(max_turns=5)
    for i in range(5):
        memory.add_round(datetime.now(), False, f"message {i}")

    assert len(memory) == 5

    memory.update_max_turns(2)
    assert len(memory) == 2

    history = memory.get_history()
    assert [m.message for m in history] == ["message 3", "message 4"]


def test_format_for_prompt_empty():
    """Test formatting when empty."""
    memory = ConversationMemory(max_turns=3)
    assert memory.format_for_prompt() == ""
