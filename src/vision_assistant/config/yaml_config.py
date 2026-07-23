import yaml
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from typing import Callable
import threading

from vision_assistant.types import AppConfig, ConfigLoader


class YamlConfigLoader(ConfigLoader):
    """YAML configuration loader with hot-reload support."""

    def __init__(self, config_path: str | Path):
        self._config_path = Path(config_path).resolve()
        self._observer: Observer | None = None
        self._handler: ConfigChangeHandler | None = None
        self._lock = threading.Lock()

    def load(self) -> AppConfig:
        """Load configuration from YAML file."""
        with open(self._config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # Handle empty file
        if data is None:
            data = {}

        # Set defaults for optional values
        return AppConfig(
            hot_reload=data.get('hot_reload', True),
            llm_system_prompt=data.get('llm_system_prompt', ''),
            monitoring_target=data.get('monitoring_target', ''),
            interval_seconds=data.get('interval_seconds', 10.0),
            max_history_turns=data.get('max_history_turns', 10),
            pixel_change_threshold=data.get('pixel_change_threshold', 5.0),
            target_width=data.get('target_width', 1280),
            target_height=data.get('target_height', 720),
            jpeg_quality=data.get('jpeg_quality', 80),
            speech_bubble_duration_seconds=data.get('speech_bubble_duration_seconds', 15),
            welcome_message=data.get('welcome_message', 'Niiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii好'),
            speech_bubble_font_family=data.get('speech_bubble_font_family', 'Segoe UI'),
            speech_bubble_font_size=data.get('speech_bubble_font_size', 10),
            click_preset_message=data.get('click_preset_message', '有事快说'),
        )

    def start_watching(self, on_change: Callable[[AppConfig], None]) -> None:
        """Start watching for configuration file changes."""
        if self._observer is not None:
            self.stop_watching()

        with self._lock:
            self._handler = ConfigChangeHandler(
                config_path=self._config_path,
                loader=self,
                on_change=on_change
            )
            self._observer = Observer()
            self._observer.schedule(
                self._handler,
                str(self._config_path.parent),
                recursive=False
            )
            self._observer.start()

    def stop_watching(self) -> None:
        """Stop watching for configuration file changes."""
        with self._lock:
            if self._observer is not None:
                self._observer.stop()
                self._observer.join()
                self._observer = None
                self._handler = None


class ConfigChangeHandler(FileSystemEventHandler):
    """Handle configuration file changes."""

    def __init__(
        self,
        config_path: Path,
        loader: YamlConfigLoader,
        on_change: Callable[[AppConfig], None],
    ):
        self._config_path = config_path
        self._loader = loader
        self._on_change = on_change
        self._debounce_timer: threading.Timer | None = None
        self._debounce_delay = 1.0  # 1 second debounce

    def on_modified(self, event: FileSystemEventHandler | FileModifiedEvent):
        """Called when a file is modified."""
        if not isinstance(event, FileModifiedEvent):
            return

        if Path(event.src_path).resolve() != self._config_path.resolve():
            return

        # Debounce: multiple writes may happen in quick succession
        if self._debounce_timer is not None:
            self._debounce_timer.cancel()

        self._debounce_timer = threading.Timer(
            self._debounce_delay,
            self._do_reload
        )
        self._debounce_timer.start()

    def _do_reload(self):
        """Actually reload the configuration."""
        try:
            config = self._loader.load()
            self._on_change(config)
        except Exception as e:
            print(f"Error reloading configuration: {e}")
