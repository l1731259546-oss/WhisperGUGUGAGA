"""Speech bubble window - separate floating window for speech bubble.

Implements Ultimate Scheme: 360° infinite rotation + smart scale & collapse.
- 360-degree polar search with 5-degree steps (72 candidates)
- Multi-criteria scoring for best position selection
- Automatic scaling when space is limited
- Collapse mode for extremely crowded conditions
- Smooth pointer with large sharp point and rounded base for clean connection
"""
import math
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, QRectF, QPoint, QPointF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QPainterPath, QFont, QFontMetrics

from vision_assistant.bubble.bubble_position_calculator import BubblePositionCalculator


class SpeechBubbleWindow(QWidget):
    """Separate floating window for speech bubble.

    This window floats around the character window, positioned using polar coordinates
    to allow smooth rotation around the character while keeping text upright.

    Ultimate Scheme features:
    - 360-degree infinite search (72 candidates at 5-degree steps)
    - Multi-criteria intelligent scoring
    - Automatic scaling when space is limited
    - Collapse mode for extreme edge cases
    """

    def __init__(
        self,
        character_window,
        max_width: int = 300,
        min_scale: float = 0.55,
        collapse_threshold: float = 0.6,
        font_family: str = "Segoe UI",
        base_font_size: int = 10,
        parent=None,
    ):
        super().__init__(parent)
        self._character_window = character_window
        self._max_width = max_width
        self._corner_radius = 12
        self._padding = 12
        self._distance_from_char = 18  # Distance from character edge
        self._pointer_size = 20  # Larger pointer size for better connection
        self._pointer_half_base = 10  # Wider base at connection point
        self._font_family = font_family
        self._base_font_size = base_font_size

        self._current_message: str = ""
        self._showing_message = False
        self._hide_timer: QTimer | None = None
        self._auto_hide_seconds = 15
        self._lines: list[str] = []

        # 360-degree polar coordinates around character
        self._angle = 0.0  # radians, 0 = right, π/2 = up, π = left, 3π/2 = down
        self._current_scale = 1.0
        self._min_scale = min_scale
        self._collapse_threshold = collapse_threshold
        self._is_collapsed = False

        # Create position calculator (pure calculation logic)
        self._calculator = BubblePositionCalculator(
            max_width=max_width,
            min_scale=min_scale,
            collapse_threshold=collapse_threshold,
            base_font_size=base_font_size,
            padding=self._padding,
            distance_from_char=self._distance_from_char,
        )

        self._setup_window()

    def _setup_window(self):
        """Setup window properties."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def update_position(self):
        """Update bubble position based on character position and best angle.

        Performs full 360-degree search for best angle and calculates optimal scale.
        """
        if not self._showing_message:
            return

        char_geom = self._character_window.geometry()
        char_center_x = char_geom.center().x()
        char_center_y = char_geom.center().y()
        char_size = self._character_window.get_character_size()

        screen = QApplication.primaryScreen()
        screen_available = screen.availableGeometry() if screen else None

        if not screen_available:
            return

        # Calculate base font for initial calculation
        base_font = QFont(self._font_family, self._base_font_size)
        base_fm = QFontMetrics(base_font)

        # Full calculation delegated to calculator
        (self._angle, self._current_scale, self._is_collapsed,
         bubble_width, bubble_height, lines) = self._calculator.calculate(
            self._current_message,
            char_center_x,
            char_center_y,
            char_size,
            base_fm,
            screen_available,
            self._current_scale
        )

        # Calculate final position from polar coordinates
        bx, by = self._calculator.calculate_final_position(
            self._angle, bubble_width, bubble_height,
            char_center_x, char_center_y, char_size
        )

        # Store lines for painting
        self._lines = lines

        # Resize and move window (add room for pointer)
        self.resize(bubble_width + self._pointer_size, bubble_height + self._pointer_size)
        self.move(bx, by)

    def _build_pointer_path(
        self,
        bubble_rect: QRectF,
        char_center_global: QPoint,
        bubble_color: QColor,
    ) -> QPainterPath:
        """Build pointer path with large sharp tip and smooth rounded connection.

        The pointer connects from bubble edge to character center with:
        - Wider base at bubble edge for clean connection
        - Sharp pointed tip at character side
        - Smooth curved transition for professional look
        """
        # Bubble center in local coordinates
        bubble_cx = bubble_rect.center().x()
        bubble_cy = bubble_rect.center().y()

        # Get character center in global coordinates, convert to local
        char_geom = self._character_window.geometry()
        char_global_center = char_geom.center()
        bubble_global_top_left = self.geometry().topLeft()
        char_local_x = char_global_center.x() - bubble_global_top_left.x()
        char_local_y = char_global_center.y() - bubble_global_top_left.y()

        # Direction vector from bubble center to character
        dx = char_local_x - bubble_cx
        dy = char_local_y - bubble_cy
        length = math.sqrt(dx * dx + dy * dy)
        if length > 0:
            dx /= length
            dy /= length

        # Find intersection with bubble rectangle boundary
        half_w = bubble_rect.width() / 2
        half_h = bubble_rect.height() / 2
        t_x = abs(half_w / dx) if abs(dx) > 0.001 else float('inf')
        t_y = abs(half_h / dy) if abs(dy) > 0.001 else float('inf')
        t = min(t_x, t_y)

        # Base point is on bubble edge (this is where pointer connects to bubble)
        base_x = bubble_cx + dx * t
        base_y = bubble_cy + dy * t

        # Tip point extends beyond bubble towards character
        tip_x = base_x + dx * self._pointer_size
        tip_y = base_y + dy * self._pointer_size

        # Create smooth triangle with wider base and sharp tip
        # Perpendicular vector for base width
        perp_dx = -dy
        perp_dy = dx

        # Base corners - wider base at connection point
        half_base = self._pointer_half_base
        p1x = base_x + perp_dx * half_base
        p1y = base_y + perp_dy * half_base
        p2x = base_x - perp_dx * half_base
        p2y = base_y - perp_dy * half_base

        # Use cubic Bezier curves for smooth connection to bubble border
        path = QPainterPath()

        # Start at one base corner
        path.moveTo(p1x, p1y)

        # Curve to tip for smooth transition - gives rounded shoulder
        control1_x = p1x + dx * (self._pointer_size * 0.3)
        control1_y = p1y + dy * (self._pointer_size * 0.3)
        path.quadTo(control1_x, control1_y, tip_x, tip_y)

        # Curve from tip to other base corner
        control2_x = p2x + dx * (self._pointer_size * 0.3)
        control2_y = p2y + dy * (self._pointer_size * 0.3)
        path.quadTo(control2_x, control2_y, p2x, p2y)

        # Close the path - the curve creates smooth rounded shoulders
        # that connect cleanly to the bubble border
        path.closeSubpath()

        return path

    def _get_bubble_colors(self) -> tuple[QColor, QColor]:
        """Get bubble colors based on current state.

        - Normal: white background, gray border
        - Scaled down: light yellow background, yellow border
        - Collapsed: light red background, red border
        """
        if self._is_collapsed:
            return QColor(255, 220, 220), QColor(255, 100, 100)
        elif self._current_scale < 0.9:
            return QColor(255, 255, 220), QColor(255, 200, 50)
        else:
            return QColor(255, 255, 255, 245), QColor(120, 120, 120)

    def paintEvent(self, event):
        """Paint the speech bubble with current state."""
        if not self._showing_message:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate actual dimensions with current scale
        actual_font_size = int(self._base_font_size * self._current_scale)
        if actual_font_size < 6:
            actual_font_size = 6
        actual_padding = int(self._padding * self._current_scale)

        font = QFont(self._font_family, actual_font_size)
        painter.setFont(font)
        fm = QFontMetrics(font)

        # Position bubble rectangle (leave room for pointer)
        bubble_x = self._pointer_size // 2
        bubble_y = self._pointer_size // 2

        if self._is_collapsed:
            # Collapsed mode - small rectangle with "..."
            bubble_width = int(100 * self._current_scale + 40)
            bubble_height = int(40 * self._current_scale + 10)
        else:
            # Already calculated in update_position by BubblePositionCalculator
            bubble_width = self.size().width() - self._pointer_size
            bubble_height = self.size().height() - self._pointer_size

        bubble_rect = QRectF(
            float(bubble_x),
            float(bubble_y),
            float(bubble_width),
            float(bubble_height)
        )

        # Get colors based on state
        bg_color, border_color = self._get_bubble_colors()

        # Build main bubble path
        path = QPainterPath()
        path.addRoundedRect(bubble_rect, float(self._corner_radius), float(self._corner_radius))

        # Add smooth pointer path (large sharp tip with smooth connection)
        char_geom = self._character_window.geometry()
        pointer_path = self._build_pointer_path(
            bubble_rect,
            char_geom.center(),
            bg_color
        )
        path.addPath(pointer_path)

        # Draw bubble
        painter.fillPath(path, QBrush(bg_color))
        painter.setPen(QPen(border_color, 2))
        painter.drawPath(path)

        # Draw text
        if not self._is_collapsed:
            painter.setPen(QPen(QColor(40, 40, 40)))
            y_offset = bubble_y + actual_padding
            line_height = fm.height()
            for line in self._lines:
                painter.drawText(
                    int(bubble_x + actual_padding),
                    int(y_offset + fm.ascent()),
                    line
                )
                y_offset += line_height
        else:
            # Collapsed mode - show hint
            painter.setPen(QPen(QColor(150, 50, 50)))
            hint_y = int(bubble_y + bubble_height / 2 + 5 * self._current_scale)
            painter.drawText(
                int(bubble_x + actual_padding),
                hint_y,
                "💬 消息折叠中..."
            )

    def show_message(self, message: str) -> None:
        """Show a message in speech bubble."""
        self._current_message = message
        self._showing_message = True
        self._current_scale = 1.0
        self._is_collapsed = False

        # Update position first to get correct size
        self.update_position()
        self.show()
        self.update()

        # Start auto-hide timer
        if self._hide_timer is None:
            self._hide_timer = QTimer(self)
            self._hide_timer.timeout.connect(self.hide_message)
            self._hide_timer.setSingleShot(True)

        self._hide_timer.start(int(self._auto_hide_seconds * 1000))

    def hide_message(self) -> None:
        """Hide the speech bubble."""
        self._showing_message = False
        self._current_message = ""
        self._current_scale = 1.0
        self._is_collapsed = False
        if self._hide_timer:
            self._hide_timer.stop()
        self.hide()

    def update_auto_hide_duration(self, seconds: int) -> None:
        """Update the auto-hide duration."""
        self._auto_hide_seconds = seconds
        if self._hide_timer and self._hide_timer.isActive():
            self._hide_timer.start(int(seconds * 1000))

    def update_font(self, font_family: str, base_font_size: int) -> None:
        """Update the font configuration (called on config reload)."""
        self._font_family = font_family
        self._base_font_size = base_font_size
