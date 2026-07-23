"""Bubble position and layout calculator.

Pure calculation logic for SpeechBubbleWindow:
- 360-degree polar search for best angle
- Multi-criteria scoring (visibility > reading preference > edge distance > naturalness)
- Optimal scaling based on available screen space
- Text layout calculation with word wrapping
"""

import math
from PyQt6.QtGui import QFontMetrics


class BubblePositionCalculator:
    """Calculate optimal bubble position, scale and text layout.

    This class holds configuration parameters and provides pure calculation
    methods for positioning the speech bubble around the character.
    """

    def __init__(
        self,
        max_width: int = 300,
        min_scale: float = 0.55,
        collapse_threshold: float = 0.6,
        base_font_size: int = 10,
        padding: int = 12,
        distance_from_char: int = 18,
    ):
        self._max_width = max_width
        self._min_scale = min_scale
        self._collapse_threshold = collapse_threshold
        self._base_font_size = base_font_size
        self._padding = padding
        self._distance_from_char = distance_from_char

    def calculate(
        self,
        message: str,
        char_center_x: int,
        char_center_y: int,
        char_size: int,
        fm: QFontMetrics,
        screen_available,
        current_scale: float = 1.0,
    ) -> tuple[float, float, bool, int, int, list[str]]:
        """Calculate complete bubble layout.

        Args:
            message: Text message to display
            char_center_x: Character center X (global coordinates)
            char_center_y: Character center Y (global coordinates)
            char_size: Character size in pixels
            fm: Font metrics for the current font
            screen_available: Screen available geometry
            current_scale: Current scale (unused but kept for future)

        Returns:
            Tuple of (angle, scale, is_collapsed, bubble_width, bubble_height, lines)
        """
        # Calculate base text layout at 100% scale
        base_max_width = int(self._max_width * current_scale)
        base_padding = int(self._padding * current_scale)
        lines, base_width, base_height = self.calculate_text_layout(
            message, fm, base_max_width, base_padding
        )

        # Find best angle through 360-degree search
        angle = self.find_best_angle(
            base_width, base_height, char_center_x, char_center_y, char_size, screen_available
        )

        # Calculate optimal scale based on available space
        scale = self.calculate_optimal_scale(
            angle, base_width, base_height, char_center_x, char_center_y, char_size, screen_available
        )

        # Check if collapsed mode should be triggered
        is_collapsed = scale < self._collapse_threshold

        # Calculate final dimensions with current scale
        actual_font_size = int(self._base_font_size * scale)
        if actual_font_size < 6:
            actual_font_size = 6
        actual_padding = int(self._padding * scale)
        actual_max_width = int(self._max_width * scale)

        if not is_collapsed:
            lines, bubble_width, bubble_height = self.calculate_text_layout(
                message, fm, actual_max_width, actual_padding
            )
        else:
            # Collapsed mode - show only icon
            bubble_width = int(100 * scale + 40)
            bubble_height = int(40 * scale + 10)
            lines = []

        return angle, scale, is_collapsed, bubble_width, bubble_height, lines

    def find_best_angle(
        self,
        bubble_width: int,
        bubble_height: int,
        char_center_x: int,
        char_center_y: int,
        char_size: int,
        screen_available,
    ) -> float:
        """Find the best angle to position the bubble using 360-degree search.

        Tests 72 candidate positions (5-degree steps) and selects based on
        multi-criteria scoring: visibility > reading preference > edge distance > angle naturalness.
        """
        best_score = -10000
        best_angle = 0.0

        # Search 360 degrees with 5-degree steps = 72 candidates
        search_steps = 72

        for i in range(search_steps):
            angle = (i / search_steps) * 2 * math.pi
            score = self.score_angle(
                angle, bubble_width, bubble_height,
                char_center_x, char_center_y, char_size,
                screen_available
            )

            if score > best_score:
                best_score = score
                best_angle = angle

        return best_angle

    def score_angle(
        self,
        angle: float,
        bubble_width: int,
        bubble_height: int,
        char_center_x: int,
        char_center_y: int,
        char_size: int,
        screen_available,
    ) -> float:
        """Score a candidate angle with multi-criteria.

        Total score ~ 100 (visibility) + 30 (reading preference) + 20 (edge distance) + 10 (naturalness) = 160

        1. Visibility ratio: 0-100 points - higher is better
        2. Reading preference: prefers 45 degrees upper right - 0-30 points
        3. Edge distance: prefers being away from screen edges - 0-20 points
        4. Angle naturalness: prefers cardinal directions (up/down/left/right) - 0-10 points
        """
        # Calculate bubble position from polar coordinates
        radius = char_size / 2 + self._distance_from_char + max(bubble_width, bubble_height) / 2
        bx = char_center_x + radius * math.cos(angle) - bubble_width / 2
        by = char_center_y - radius * math.sin(angle) - bubble_height / 2

        # Calculate visible area
        x1 = max(bx, screen_available.left())
        x2 = min(bx + bubble_width, screen_available.right())
        y1 = max(by, screen_available.top())
        y2 = min(by + bubble_height, screen_available.bottom())

        if x1 >= x2 or y1 >= y2:
            return -10000  # Completely off-screen

        visible_area = (x2 - x1) * (y2 - y1)
        visible_ratio = visible_area / (bubble_width * bubble_height)

        # Base score: visibility ratio
        score = visible_ratio * 100

        # Bonus 1: Prefer upper right (45 degrees) - matches reading habit
        ideal_angle = math.pi / 4  # 45 degrees
        angle_diff = abs(((angle - ideal_angle + math.pi) % (2 * math.pi)) - math.pi)
        angle_penalty = angle_diff / math.pi  # 0-1 range
        score += 30 * (1 - angle_penalty)

        # Bonus 2: Prefer being away from screen edges
        margin = 60
        bubble_cx = bx + bubble_width / 2
        bubble_cy = by + bubble_height / 2
        dist_to_edge = min(
            bubble_cx - screen_available.left(),
            bubble_cy - screen_available.top(),
            screen_available.right() - bubble_cx,
            screen_available.bottom() - bubble_cy
        )
        edge_score = min(1.0, dist_to_edge / margin)
        score += 20 * edge_score

        # Bonus 3: Prefer cardinal directions (more natural looking)
        normalized_angle = angle % (math.pi / 2)
        if normalized_angle > math.pi / 4:
            normalized_angle = math.pi / 2 - normalized_angle
        cardinal_score = 1 - (normalized_angle / (math.pi / 4))
        score += 10 * cardinal_score

        return score

    def calculate_optimal_scale(
        self,
        angle: float,
        base_width: int,
        base_height: int,
        char_center_x: int,
        char_center_y: int,
        char_size: int,
        screen_available,
    ) -> float:
        """Calculate optimal scaling factor based on available space.

        If bubble would overflow screen edges, scale it down proportionally.
        """
        radius = char_size / 2 + self._distance_from_char + max(base_width, base_height) / 2

        # Calculate position with base size
        bx = char_center_x + radius * math.cos(angle) - base_width / 2
        by = char_center_y - radius * math.sin(angle) - base_height / 2

        # Calculate overflow on each side (with safety margin)
        safety_margin = 30
        overflow_left = max(0, (screen_available.left() + safety_margin) - bx)
        overflow_right = max(0, (bx + base_width) - (screen_available.right() - safety_margin))
        overflow_top = max(0, (screen_available.top() + safety_margin) - by)
        overflow_bottom = max(0, (by + base_height) - (screen_available.bottom() - safety_margin))

        max_overflow = max(overflow_left, overflow_right, overflow_top, overflow_bottom)

        if max_overflow > 0:
            # Need to shrink - proportional reduction
            shrink_factor = base_width / (base_width + max_overflow * 2)
            return max(self._min_scale, shrink_factor)
        else:
            # Plenty of space - full size
            return 1.0

    def calculate_text_layout(
        self,
        message: str,
        fm: QFontMetrics,
        max_width: int,
        padding: int = 12,
    ) -> tuple[list[str], int, int]:
        """Calculate text layout with proper word wrapping.

        Handles long words by character-level wrapping when needed.

        Args:
            message: The text message to layout
            fm: Font metrics for the current font
            max_width: Maximum available text width (including padding)
            padding: Horizontal and vertical padding

        Returns:
            Tuple of (wrapped_lines, bubble_width, bubble_height)
        """
        max_text_width = max_width - padding * 2
        lines = []
        current_line = ""
        current_width = 0
        max_line_width = 0

        for word in message.split():
            word_with_space = word + " "
            word_width = fm.horizontalAdvance(word_with_space)

            single_word_width = fm.horizontalAdvance(word)
            if single_word_width > max_text_width:
                # Long word - need character-level wrapping
                if current_line:
                    lines.append(current_line)
                    max_line_width = max(max_line_width, current_width)
                    current_line = ""
                    current_width = 0

                current_char_line = ""
                for char in word:
                    test_line = current_char_line + char
                    test_width = fm.horizontalAdvance(test_line)
                    if test_width <= max_text_width:
                        current_char_line = test_line
                    else:
                        lines.append(current_char_line)
                        max_line_width = max(max_line_width, fm.horizontalAdvance(current_char_line))
                        current_char_line = char
                if current_char_line:
                    current_line = current_char_line + " "
                    current_width = fm.horizontalAdvance(current_line)
            elif current_width + word_width <= max_text_width:
                current_line += word_with_space
                current_width += word_width
            else:
                if current_line.endswith(" "):
                    current_line = current_line[:-1]
                    current_width -= fm.horizontalAdvance(" ")
                lines.append(current_line)
                max_line_width = max(max_line_width, current_width)
                current_line = word_with_space
                current_width = word_width

        if current_line:
            if current_line.endswith(" "):
                current_line = current_line[:-1]
                current_width -= fm.horizontalAdvance(" ")
            lines.append(current_line)
            max_line_width = max(max_line_width, current_width)

        line_height = fm.height()
        text_height = len(lines) * line_height
        bubble_width = min(self._max_width, max_line_width + padding * 2)
        bubble_height = text_height + padding * 2

        return lines, bubble_width, bubble_height

    def calculate_final_position(
        self,
        angle: float,
        bubble_width: int,
        bubble_height: int,
        char_center_x: int,
        char_center_y: int,
        char_size: int,
    ) -> tuple[int, int]:
        """Calculate final window position in global coordinates.

        Returns:
            Tuple of (bx, by) - top-left position for the window
        """
        radius = char_size / 2 + self._distance_from_char + max(bubble_width, bubble_height) / 2
        bx = char_center_x + radius * math.cos(angle) - bubble_width / 2
        by = char_center_y - radius * math.sin(angle) - bubble_height / 2
        return int(bx), int(by)
