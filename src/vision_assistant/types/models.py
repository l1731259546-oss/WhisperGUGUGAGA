from __future__ import annotations
from typing import Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod
from datetime import datetime
from PIL import Image


@dataclass
class AppConfig:
    """Application configuration loaded from YAML."""
    hot_reload: bool
    llm_system_prompt: str
    monitoring_target: str
    interval_seconds: float
    max_history_turns: int
    pixel_change_threshold: float  # Percentage (0-100)
    target_width: int
    target_height: int
    jpeg_quality: int
    speech_bubble_duration_seconds: int  # How long speech bubble stays visible
    welcome_message: str  # Welcome message shown on startup
    speech_bubble_font_family: str  # Font family for speech bubble text
    speech_bubble_font_size: int  # Base font size for speech bubble text
    click_preset_message: str  # Preset message shown immediately after user clicks


@dataclass
class ConversationRound:
    """A single round of conversation in memory."""
    timestamp: datetime
    detected_behavior: bool
    message: str


@dataclass
class AnalysisResult:
    """Result of vision analysis from the agent."""
    detected: bool
    message: str
    raw_analysis: str


@dataclass
class ScreenImage:
    """Captured screen image with metadata."""
    image: Image.Image
    timestamp: datetime
    width: int
    height: int


class VisionAgent(ABC):
    """Abstract interface for the vision analysis agent."""

    @abstractmethod
    def analyze_screenshot(
        self,
        image: Image.Image | None,
        config: AppConfig,
        history: list[ConversationRound],
        user_message: str | None = None,
    ) -> AnalysisResult:
        """Analyze a screenshot and return the result.

        Args:
            image: Current screenshot image (None for text-only user messages)
            config: Application configuration
            history: Previous conversation history
            user_message: Optional user-initiated message from manual input
                when user double-clicks the character. If provided, this message
                is added to the prompt and we skip automatic detection.

        Returns:
            Analysis result with detected flag and message
        """
        pass

    @abstractmethod
    def update_config(self, config: AppConfig) -> None:
        """Update agent with new configuration."""
        pass


class ScreenMonitor(ABC):
    """Abstract interface for screen monitoring."""

    @abstractmethod
    def capture(self) -> ScreenImage:
        """Capture current screen."""
        pass

    @abstractmethod
    def has_significant_change(
        self,
        current: ScreenImage,
        previous: ScreenImage | None,
        threshold: float,
    ) -> bool:
        """Check if current screen has significant change compared to previous."""
        pass


class ConfigLoader(ABC):
    """Abstract interface for configuration loading."""

    @abstractmethod
    def load(self) -> AppConfig:
        """Load current configuration."""
        pass

    @abstractmethod
    def start_watching(self, on_change: callable[[AppConfig], None]) -> None:
        """Start watching for config file changes."""
        pass

    @abstractmethod
    def stop_watching(self) -> None:
        """Stop watching for config file changes."""
        pass


class CharacterWindow(ABC):
    """Abstract interface for the GUI character window."""

    @abstractmethod
    def show_message(self, message: str) -> None:
        """Show a message in speech bubble."""
        pass

    @abstractmethod
    def hide_message(self) -> None:
        """Hide the speech bubble."""
        pass

    @abstractmethod
    def show(self) -> None:
        """Show the window."""
        pass

    @abstractmethod
    def hide(self) -> None:
        """Hide the window."""
        pass


class BackgroundTaskRunner(ABC):
    """Abstract interface for running background tasks.

    Used to execute blocking operations (like LLM network calls) on a background
    thread without blocking the GUI main thread.
    """

    @abstractmethod
    def run(
        self,
        task: Callable[[], None],
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        """Run a task on a background thread.

        Args:
            task: The task to execute (called on background thread).
            on_complete: Optional callback called on the main thread after
                the task completes successfully.
        """
        pass
