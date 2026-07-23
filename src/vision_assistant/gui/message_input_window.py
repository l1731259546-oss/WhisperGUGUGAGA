"""Popup message input window for user-initiated messages."""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QPushButton, QHBoxLayout,
    QApplication
)
from PyQt6.QtCore import (
    Qt, QPoint, QSize,
)
from PyQt6.QtGui import (
    QKeyEvent, QPalette, QColor,
)


class MessageInputWindow(QDialog):
    """Popup dialog for user to input a message when double-clicking character.

    Positioned above the character's head, supports Enter to submit and
    Escape to cancel.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._user_message: str = ""
        self._setup_window()
        self._create_layout()

    def _setup_window(self):
        """Setup window properties."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(280)
        self.setFixedHeight(60)

    def _create_layout(self):
        """Create the input layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Input field
        self._input = QLineEdit()
        self._input.setPlaceholderText("输入消息，按回车发送...")
        self._input.returnPressed.connect(self._on_submit)
        # Style the input
        palette = self._input.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor(240, 240, 240, 230))
        self._input.setPalette(palette)
        self._input.setMinimumHeight(36)
        layout.addWidget(self._input)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self._cancel_btn)
        self._submit_btn = QPushButton("发送")
        self._submit_btn.clicked.connect(self._on_submit)
        button_layout.addWidget(self._submit_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def position_near_character(self, character_pos: QPoint, character_size: QSize):
        """Position the input window above the character's head.

        Args:
            character_pos: Position of character window (top-left)
            character_size: Size of character window
        """
        # Place input above the character, horizontally centered
        x = character_pos.x() + (character_size.width() - self.width()) // 2
        y = character_pos.y() - self.height() - 10  # 10px gap above

        # Ensure it stays within screen bounds
        screen = QApplication.primaryScreen()
        if screen:
            screen_rect = screen.availableGeometry()
            # Check left/right bounds
            x = max(screen_rect.left(), min(x, screen_rect.right() - self.width()))
            # If it doesn't fit above the character, place below instead
            if y < screen_rect.top():
                y = character_pos.y() + character_size.height() + 10
            y = max(screen_rect.top(), min(y, screen_rect.bottom() - self.height()))

        self.move(QPoint(x, y))

    def show_input(self, character_pos: QPoint, character_size: QSize):
        """Show the input dialog and focus it.

        Args:
            character_pos: Position of character window
            character_size: Size of character window
        """
        self.position_near_character(character_pos, character_size)
        self._input.clear()
        self.show()
        self._input.setFocus()

    def get_message(self) -> str:
        """Get the submitted message."""
        return self._user_message.strip()

    def _on_submit(self):
        """Handle submit button or Enter key."""
        self._user_message = self._input.text()
        if self._user_message.strip():
            self.accept()

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key presses - Escape to cancel."""
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        super().keyPressEvent(event)
