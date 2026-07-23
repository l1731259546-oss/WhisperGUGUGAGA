"""Tests for MSSScreenMonitor."""
from datetime import datetime
from PIL import Image
import numpy as np
from vision_assistant.monitor.mss_screen_monitor import MSSScreenMonitor
from vision_assistant.types import ScreenImage


def create_test_image(width: int, height: int, color: tuple[int, int, int]) -> Image.Image:
    """Create a test PIL image with solid color."""
    return Image.new('RGB', (width, height), color)


def create_test_screen_image(width: int, height: int, color: tuple[int, int, int]) -> ScreenImage:
    """Create a test ScreenImage."""
    img = create_test_image(width, height, color)
    return ScreenImage(
        image=img,
        timestamp=datetime.now(),
        width=width,
        height=height
    )


def test_has_significant_change_first_frame():
    """Test that first frame always returns True (no previous)."""
    monitor = MSSScreenMonitor()
    current = create_test_screen_image(100, 100, (0, 0, 0))

    result = monitor.has_significant_change(current, None, 5.0)
    assert result is True


def test_has_significant_change_no_change():
    """Test that identical images have no significant change."""
    monitor = MSSScreenMonitor()
    current = create_test_screen_image(100, 100, (100, 100, 100))
    previous = create_test_screen_image(100, 100, (100, 100, 100))

    result = monitor.has_significant_change(current, previous, 5.0)
    assert result is False


def test_has_significant_change_full_change():
    """Test that completely different images have significant change."""
    monitor = MSSScreenMonitor()
    current = create_test_screen_image(100, 100, (0, 0, 0))
    previous = create_test_screen_image(100, 100, (255, 255, 255))

    result = monitor.has_significant_change(current, previous, 5.0)
    assert result is True
