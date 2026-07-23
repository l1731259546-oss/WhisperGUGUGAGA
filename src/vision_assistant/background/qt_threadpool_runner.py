from typing import Callable
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal, QThreadPool
from vision_assistant.types import BackgroundTaskRunner


class TaskSignals(QObject):
    """Signals for task completion."""
    completed = pyqtSignal()


class TaskWrapper(QRunnable):
    """Wrapper for a background task with completion signal."""

    def __init__(
        self,
        task: Callable[[], None],
        on_complete: Callable[[], None] | None = None,
    ):
        super().__init__()
        self._task = task
        self._on_complete = on_complete
        self._signals = TaskSignals()

        if on_complete is not None:
            self._signals.completed.connect(on_complete)

    def run(self) -> None:
        """Execute the task and emit completion signal."""
        self._task()
        if self._on_complete is not None:
            self._signals.completed.emit()


class QThreadPoolBackgroundTaskRunner(BackgroundTaskRunner):
    """Background task runner using Qt QThreadPool.

    Executes tasks on a background thread pool from Qt, keeping the GUI
    main thread responsive.
    """

    def __init__(self):
        super().__init__()
        self._pool = QThreadPool.globalInstance()

    def run(
        self,
        task: Callable[[], None],
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        """Submit a task to the thread pool.

        Args:
            task: The task to execute on the background thread.
            on_complete: Optional callback invoked on the main thread
                after the task completes.
        """
        wrapper = TaskWrapper(task, on_complete)
        self._pool.start(wrapper)
