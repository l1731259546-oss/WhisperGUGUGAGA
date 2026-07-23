import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtCore import QTimer

from vision_assistant.types import (
    AppConfig,
    VisionAgent,
    ScreenMonitor,
    ConfigLoader,
    CharacterWindow,
    ScreenImage,
    AnalysisResult,
    BackgroundTaskRunner,
)
from vision_assistant.agent.conversation_memory import ConversationMemory
from vision_assistant.config.yaml_config import YamlConfigLoader
from vision_assistant.agent.doubao_vision_agent import DoubaoVisionAgent
from vision_assistant.monitor.mss_screen_monitor import MSSScreenMonitor
from vision_assistant.background.qt_threadpool_runner import QThreadPoolBackgroundTaskRunner
from vision_assistant.gui.mosaic_character_window import MosaicCharacterWindow
from vision_assistant.gui.message_input_window import MessageInputWindow


class VisionMonitoringApp:
    """Main application that wires all modules together.

    Supports dependency injection for all components to enable testing
    with mock adapters. If not provided, defaults to creating concrete
    implementations.
    """

    def __init__(
        self,
        config_path: str,
        api_key: str | None = None,
        base_url: str | None = None,
        model_name: str | None = None,
        *,
        config_loader: ConfigLoader | None = None,
        vision_agent: VisionAgent | None = None,
        screen_monitor: ScreenMonitor | None = None,
        character_window: CharacterWindow | None = None,
        background_task_runner: BackgroundTaskRunner | None = None,
    ):
        self._config_path = config_path
        self._api_key = api_key
        self._base_url = base_url
        self._model_name = model_name

        # Injected components (optional)
        self._provided_config_loader = config_loader
        self._provided_vision_agent = vision_agent
        self._provided_screen_monitor = screen_monitor
        self._provided_character_window = character_window
        self._provided_background_task_runner = background_task_runner

        # Components - will be initialized in setup
        self._config_loader: ConfigLoader | None = None
        self._vision_agent: VisionAgent | None = None
        self._screen_monitor: ScreenMonitor | None = None
        self._character_window: CharacterWindow | None = None
        self._background_task_runner: BackgroundTaskRunner | None = None
        self._memory: ConversationMemory | None = None

        # State
        self._current_config: AppConfig | None = None
        self._last_screenshot: ScreenImage | None = None
        self._timer: QTimer | None = None
        self._app: QApplication | None = None
        # User-initiated message state
        self._pending_user_message: str | None = None

    def setup(self) -> None:
        """Setup all components."""
        # Load environment variables if not provided
        if self._api_key is None:
            load_dotenv()
            self._api_key = os.getenv('API_KEY')
        if self._base_url is None:
            self._base_url = os.getenv('BASE_URL')
        if self._model_name is None:
            self._model_name = os.getenv('MODEL_NAME', 'doubao-seed-2.0-pro')

        if not self._api_key or not self._base_url:
            raise ValueError(
                "API_KEY and BASE_URL must be provided via environment variables "
                "or constructor arguments."
            )

        # Load configuration - use injected config loader if provided
        if self._provided_config_loader is not None:
            self._config_loader = self._provided_config_loader
        else:
            self._config_loader = YamlConfigLoader(self._config_path)
        self._current_config = self._config_loader.load()

        # Initialize memory
        self._memory = ConversationMemory(self._current_config.max_history_turns)

        # Initialize components - use injected if provided
        if self._provided_vision_agent is not None:
            self._vision_agent = self._provided_vision_agent
        else:
            self._vision_agent = DoubaoVisionAgent(
                api_key=self._api_key,
                base_url=self._base_url,
                model_name=self._model_name,
            )
        self._vision_agent.update_config(self._current_config)

        if self._provided_screen_monitor is not None:
            self._screen_monitor = self._provided_screen_monitor
        else:
            self._screen_monitor = MSSScreenMonitor()

        # Initialize background task runner - use injected if provided
        if self._provided_background_task_runner is not None:
            self._background_task_runner = self._provided_background_task_runner
        else:
            self._background_task_runner = QThreadPoolBackgroundTaskRunner()

        # Create GUI - this must happen after QApplication is created
        if QApplication.instance() is None:
            self._app = QApplication(sys.argv)
        else:
            self._app = QApplication.instance()

        if self._provided_character_window is not None:
            self._character_window = self._provided_character_window
        else:
            self._character_window = MosaicCharacterWindow(
                auto_hide_seconds=self._current_config.speech_bubble_duration_seconds,
                welcome_message=self._current_config.welcome_message,
                speech_bubble_font_family=self._current_config.speech_bubble_font_family,
                speech_bubble_font_size=self._current_config.speech_bubble_font_size
            )
        self._character_window.show()

        # Create message input window for user-initiated messages
        self._message_input_window = MessageInputWindow()
        # Connect double-click signal from character window
        if isinstance(self._character_window, MosaicCharacterWindow):
            self._character_window.character_double_clicked.connect(
                self._on_character_double_clicked
            )
        
        # Show welcome message if configured
        if isinstance(self._character_window, MosaicCharacterWindow) and self._current_config.welcome_message:
            self._character_window.show_message(self._current_config.welcome_message)

        # Setup config hot-reload
        if self._current_config.hot_reload:
            self._config_loader.start_watching(self._on_config_change)

        # Setup timer for periodic checking
        self._timer = QTimer()
        self._timer.timeout.connect(self._check_screen)
        interval_ms = int(self._current_config.interval_seconds * 1000)
        self._timer.start(interval_ms)

        print(f"Application started. Monitoring every {self._current_config.interval_seconds} seconds.")
        print(f"Monitoring target: {self._current_config.monitoring_target}")

    def _on_config_change(self, new_config: AppConfig) -> None:
        """Handle configuration change."""
        print("Configuration reloaded.")
        old_config = self._current_config
        self._current_config = new_config

        # Update components
        if self._memory:
            self._memory.update_max_turns(new_config.max_history_turns)

        if self._vision_agent:
            self._vision_agent.update_config(new_config)

        # Restart timer with new interval
        if self._timer:
            self._timer.stop()
            interval_ms = int(new_config.interval_seconds * 1000)
            self._timer.start(interval_ms)

        # Update speech bubble auto-hide duration
        if self._character_window and isinstance(self._character_window, MosaicCharacterWindow):
            self._character_window.update_auto_hide_duration(new_config.speech_bubble_duration_seconds)
            self._character_window.update_font(
                new_config.speech_bubble_font_family,
                new_config.speech_bubble_font_size
            )

    def _check_screen(self) -> None:
        """Check screen: capture, compare, analyze if needed."""
        if self._current_config is None or self._vision_agent is None:
            return

        # Capture current screen
        current = self._screen_monitor.capture()

        # Check for significant change
        has_change = self._screen_monitor.has_significant_change(
            current,
            self._last_screenshot,
            self._current_config.pixel_change_threshold
        )

        # Store current as last for next check
        self._last_screenshot = current

        if not has_change:
            # Skip analysis - too little change
            return

        print(f"Significant change detected. Analyzing...")

        # Get pending user message if any
        pending_user_message = self.get_pending_user_message()

        # Run analysis on background thread to avoid blocking GUI
        def background_task():
            try:
                self._analysis_result = self._vision_agent.analyze_screenshot(
                    current.image,
                    self._current_config,
                    self._memory.get_history(),
                    pending_user_message,
                )
            except Exception as e:
                print(f"Error during analysis: {e}")
                self._analysis_result = None
                self._analysis_error = e

        def on_complete():
            # Called on main thread after analysis completes
            if self._analysis_result is not None:
                self._process_analysis_result(
                    self._analysis_result,
                    current.timestamp,
                    pending_user_message
                )
            else:
                # Clear pending message on error
                self.clear_pending_user_message()
            # Clean up
            delattr(self, '_analysis_result')
            if hasattr(self, '_analysis_error'):
                delattr(self, '_analysis_error')

        # Store result for callback to pick up
        self._analysis_result: AnalysisResult | None = None
        self._background_task_runner.run(background_task, on_complete)

    def _process_analysis_result(
        self,
        result: AnalysisResult,
        timestamp: datetime,
        pending_user_message: str | None,
    ) -> None:
        """Process analysis result.

        Args:
            result: The analysis result from LLM
            timestamp: Current timestamp
            pending_user_message: Optional user-initiated message that was
                sent to LLM in this analysis cycle.
        """
        # If this is a user-initiated message, add it to memory first
        # The LLM response will be added as the assistant response
        if pending_user_message and self._memory:
            # User message is not a detection result, so detected_behavior=False
            self._memory.add_round(
                timestamp=timestamp,
                detected_behavior=False,
                message=pending_user_message,
            )

        # Add the analysis result to memory
        if self._memory:
            self._memory.add_round(
                timestamp=timestamp,
                detected_behavior=result.detected,
                message=result.message,
            )

        # Show message: for automatic detection only show if detected
        # For user-initiated, always show the response regardless of detected
        should_show = (result.detected and result.message) or pending_user_message
        if should_show and self._character_window:
            if pending_user_message:
                print(f"Showing response to user message: {result.message}")
            else:
                print(f"Target detected: {result.message}")
            self._character_window.show_message(result.message)

        # Clear the pending user message after processing whether it succeeded or not
        self.clear_pending_user_message()

    def set_pending_user_message(self, message: str) -> None:
        """Set a user-initiated message that will be processed in the next analysis cycle."""
        self._pending_user_message = message

    def clear_pending_user_message(self) -> None:
        """Clear the pending user message after processing."""
        self._pending_user_message = None

    def has_pending_user_message(self) -> bool:
        """Check if there is a pending user-initiated message."""
        return self._pending_user_message is not None

    def get_pending_user_message(self) -> str | None:
        """Get the pending user message."""
        return self._pending_user_message

    def _on_character_double_clicked(self):
        """Handle double-click on character - show message input dialog.

        Immediately show the preset message to provide instant feedback,
        then show input dialog for user to enter their message.
        """
        if not isinstance(self._character_window, MosaicCharacterWindow):
            return

        # Immediately show the preset message when double-click occurs
        if self._current_config and self._character_window:
            preset_message = self._current_config.click_preset_message
            self._character_window.show_message(preset_message)

        # Get character window position and size
        char_pos = self._character_window.pos()
        char_size = self._character_window.size()

        # Show input dialog
        self._message_input_window.show_input(char_pos, char_size)

        # If user accepted, process the message
        result = self._message_input_window.exec()
        if result == QDialog.DialogCode.Accepted:
            user_message = self._message_input_window.get_message()
            if user_message:
                self._on_user_message_submitted(user_message)

    def _on_user_message_submitted(self, user_message: str):
        """Handle submitted user message from input dialog.

        Store the message and immediately trigger LLM analysis, so the user
        doesn't have to wait for the next periodic check.
        """
        # Store the message to be processed
        self.set_pending_user_message(user_message)

        # Immediately trigger LLM analysis - don't wait for next timer tick
        self._trigger_immediate_analysis()

    def _trigger_immediate_analysis(self):
        """Trigger an immediate analysis when user submits a message.

        This bypasses the timer and processes the pending user message immediately
        instead of waiting for the next periodic check. No screenshot is captured
        since this is a text-only conversation.
        """
        if self._current_config is None or self._vision_agent is None:
            return

        print(f"Processing user-initiated message...")

        pending_user_message = self.get_pending_user_message()

        # Run analysis on background thread to avoid blocking GUI
        def background_task():
            try:
                self._analysis_result = self._vision_agent.analyze_screenshot(
                    None,  # No screenshot for text-only user messages
                    self._current_config,
                    self._memory.get_history(),
                    pending_user_message,
                )
            except Exception as e:
                print(f"Error during immediate analysis: {e}")
                self._analysis_result = None
                self._analysis_error = e

        def on_complete():
            # Called on main thread after analysis completes
            if self._analysis_result is not None:
                self._process_analysis_result(
                    self._analysis_result,
                    datetime.now(),
                    pending_user_message
                )
            else:
                # Clear pending message on error
                self.clear_pending_user_message()
            # Clean up
            delattr(self, '_analysis_result')
            if hasattr(self, '_analysis_error'):
                delattr(self, '_analysis_error')

        # Store result for callback to pick up
        self._analysis_result: AnalysisResult | None = None
        self._background_task_runner.run(background_task, on_complete)

    def run(self) -> int:
        """Run the application main loop."""
        if self._app is None:
            raise RuntimeError("Application not setup. Call setup() first.")

        return self._app.exec()

    def shutdown(self) -> None:
        """Clean shutdown."""
        if self._config_loader:
            self._config_loader.stop_watching()
        if self._timer:
            self._timer.stop()
        if self._character_window:
            self._character_window.hide()
        # Clear any pending analysis result
        if hasattr(self, '_analysis_result'):
            delattr(self, '_analysis_result')
        if hasattr(self, '_analysis_error'):
            delattr(self, '_analysis_error')
