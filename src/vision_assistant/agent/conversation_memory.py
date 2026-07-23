from datetime import datetime
from typing import List
from vision_assistant.types import ConversationRound


class ConversationMemory:
    """Fixed-size conversation memory that keeps only the last N rounds."""

    def __init__(self, max_turns: int = 10):
        self._max_turns = max_turns
        self._history: List[ConversationRound] = []

    def add_round(
        self,
        timestamp: datetime,
        detected_behavior: bool,
        message: str,
    ) -> None:
        """Add a new conversation round, dropping the oldest if exceeding max size."""
        round_obj = ConversationRound(
            timestamp=timestamp,
            detected_behavior=detected_behavior,
            message=message,
        )
        self._history.append(round_obj)

        # Trim history if exceeds max
        if len(self._history) > self._max_turns:
            self._history = self._history[-self._max_turns:]

    def get_history(self) -> List[ConversationRound]:
        """Get the current history (copy)."""
        return list(self._history)

    def clear(self) -> None:
        """Clear all history."""
        self._history.clear()

    def update_max_turns(self, new_max: int) -> None:
        """Update maximum turns and trim if needed."""
        self._max_turns = new_max
        if len(self._history) > self._max_turns:
            self._history = self._history[-self._max_turns:]

    def format_for_prompt(self) -> str:
        """Format history for inclusion in LLM prompt."""
        if not self._history:
            return ""

        lines = ["Previous analysis history:"]
        for i, round_obj in enumerate(self._history, 1):
            status = "TARGET DETECTED" if round_obj.detected_behavior else "No target detected"
            lines.append(f"{i}. [{round_obj.timestamp.strftime('%H:%M:%S')}] {status}: {round_obj.message}")

        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._history)
