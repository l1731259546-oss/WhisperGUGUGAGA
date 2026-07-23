"""Mosaic character window with separate speech bubble window."""
from PyQt6.QtWidgets import (
    QWidget, QMainWindow, QApplication,
)
from PyQt6.QtCore import (
    Qt, QPoint, QTimer, pyqtSignal,
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QMouseEvent,
)

from vision_assistant.gui.characterPlan import IKUN_PIXEL_DATA
from vision_assistant.gui.speech_bubble_window import SpeechBubbleWindow


class MosaicCharacterWindow(QMainWindow):
    """Draggable mosaic character window with separate speech bubble window."""

    # Signal emitted when character is double-clicked
    character_double_clicked = pyqtSignal()

    def __init__(
        self,
        character_size: int = 120,
        auto_hide_seconds: int = 15,
        welcome_message: str | None = None,
        speech_bubble_font_family: str = "Segoe UI",
        speech_bubble_font_size: int = 10,
        parent=None,
    ):
        super().__init__(parent)

        self._character_size = character_size
        self._auto_hide_seconds = auto_hide_seconds
        self._welcome_message = welcome_message
        self._speech_bubble_font_family = speech_bubble_font_family
        self._speech_bubble_font_size = speech_bubble_font_size

        # For dragging
        self._dragging = False
        self._drag_start = QPoint()
        self._message_max_width = 300

        self._setup_window()
        self._create_widgets()
        
        # Create separate speech bubble window
        self._speech_bubble_window = SpeechBubbleWindow(
            self,
            max_width=self._message_max_width,
            font_family=self._speech_bubble_font_family,
            base_font_size=self._speech_bubble_font_size
        )
        self._speech_bubble_window.update_auto_hide_duration(auto_hide_seconds)

    def _setup_window(self):
        """Setup window properties."""
        # Frameless window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Get screen geometry
        screen = QApplication.primaryScreen()
        if screen:
            rect = screen.availableGeometry()
            # Position at bottom-left
            x = 20
            y = rect.height() - self._character_size - 60
            self.move(x, y)

        # Size fits character
        self.resize(self._character_size, self._character_size)

    def _create_widgets(self):
        """Create central widget."""
        self._central_widget = MosaicCharacterWidget(
            character_size=self._character_size,
            parent=self
        )
        self.setCentralWidget(self._central_widget)

    def show_message(self, message: str) -> None:
        """Show a message in speech bubble."""
        self._speech_bubble_window.show_message(message)

    def hide_message(self) -> None:
        """Hide the speech bubble."""
        self._speech_bubble_window.hide_message()

    def update_auto_hide_duration(self, seconds: int) -> None:
        """Update the auto-hide duration (called on config reload)."""
        self._auto_hide_seconds = seconds
        self._speech_bubble_window.update_auto_hide_duration(seconds)

    def update_font(self, font_family: str, base_font_size: int) -> None:
        """Update the font configuration (called on config reload)."""
        self._speech_bubble_font_family = font_family
        self._speech_bubble_font_size = base_font_size
        self._speech_bubble_window.update_font(font_family, base_font_size)
    
    def get_character_size(self) -> int:
        """Get the character size in pixels."""
        return self._character_size

    def show(self) -> None:
        """Show the window."""
        super().show()
        # Ensure it stays on top
        self.raise_()
        self.activateWindow()

    def hide(self) -> None:
        """Hide the window."""
        self._speech_bubble_window.hide()
        super().hide()

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for dragging."""
        if self._dragging:
            delta = event.position().toPoint() - self._drag_start
            self.move(self.pos() + delta)
            # Update bubble position while dragging
            self._speech_bubble_window.update_position()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release to stop dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            # After dragging, update bubble position
            self._speech_bubble_window.update_position()
        super().mouseReleaseEvent(event)

    def moveEvent(self, event):
        """Handle window move - update bubble position."""
        self._speech_bubble_window.update_position()
        super().moveEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle double-click event - emit signal for input dialog.

        This is handled at the top-level window to ensure it's not blocked
        by child widgets and can be reliably detected.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            # Emit signal to notify that user wants to input a message
            self.character_double_clicked.emit()
        super().mouseDoubleClickEvent(event)


class MosaicCharacterWidget(QWidget):
    """Widget that draws the mosaic character with colored squares.
    Pixel-art Kun based on reference image from i坤.png.
    """

    def __init__(
        self,
        character_size: int = 120,
        parent=None,
    ):
        super().__init__(parent)
        self._character_size = character_size
        self._pixel_data = IKUN_PIXEL_DATA
        # Calculate grid dimensions from data
        self._grid_height = len(self._pixel_data)
        self._grid_width = max(len(row) for row in self._pixel_data) if self._pixel_data else 0
        # Square size based on character size and grid
        self._square_size = int(character_size / max(self._grid_width, self._grid_height))

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Add padding around the pixel art
        total_width = self._grid_width * self._square_size + 10
        total_height = self._grid_height * self._square_size + 10
        self.setFixedSize(total_width, total_height)

    def paintEvent(self, event):
        """Draw the pixel-art character from characterPlan.py."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Center the pixel art in the widget
        total_grid_width = self._grid_width * self._square_size
        total_grid_height = self._grid_height * self._square_size
        offset_x = (self.width() - total_grid_width) // 2
        offset_y = (self.height() - total_grid_height) // 2

        # Draw each pixel square from the imported pixel data
        for row_idx, row in enumerate(self._pixel_data):
            for col_idx, color_info in enumerate(row):
                if color_info is None:
                    continue  # Transparent
                r, g, b = color_info
                color = QColor(r, g, b)
                x = offset_x + col_idx * self._square_size
                y = offset_y + row_idx * self._square_size
                painter.fillRect(x, y, self._square_size, self._square_size, color)

                # Add slight border between pixels
                painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
                painter.drawRect(x, y, self._square_size, self._square_size)
