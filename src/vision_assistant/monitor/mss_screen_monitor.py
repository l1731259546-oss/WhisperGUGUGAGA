from datetime import datetime
import numpy as np
from PIL import Image
import mss

from vision_assistant.types import ScreenImage, ScreenMonitor


class MSSScreenMonitor(ScreenMonitor):
    """Screen monitor using mss for fast screenshot capture with pixel difference detection."""

    def __init__(self):
        self._sct = mss.MSS()

    def capture(self) -> ScreenImage:
        """Capture current screen."""
        # Capture primary monitor
        monitor = self._sct.monitors[1]  # monitor 0 is all, 1 is primary
        screenshot = self._sct.grab(monitor)

        # Convert to PIL Image
        img = Image.frombytes('RGB', (screenshot.width, screenshot.height), screenshot.rgb)

        return ScreenImage(
            image=img,
            timestamp=datetime.now(),
            width=screenshot.width,
            height=screenshot.height,
        )

    def has_significant_change(
        self,
        current: ScreenImage,
        previous: ScreenImage | None,
        threshold: float,
    ) -> bool:
        """Check if current screen has significant change compared to previous."""
        if previous is None:
            return True  # Always process first frame

        # Resize both images to smaller size for faster comparison
        current_small = current.image.resize((320, 180), Image.Resampling.BILINEAR)
        prev_small = previous.image.resize((320, 180), Image.Resampling.BILINEAR)

        # Convert to numpy arrays
        current_np = np.array(current_small.convert('L'), dtype=np.float32)
        prev_np = np.array(prev_small.convert('L'), dtype=np.float32)

        # Calculate absolute difference
        diff = np.abs(current_np - prev_np)

        # Calculate percentage of pixels that changed more than 10 intensity units
        changed_pixels = np.sum(diff > 10)
        total_pixels = diff.size
        change_percent = (changed_pixels / total_pixels) * 100

        # Return True if change exceeds threshold
        return bool(change_percent > threshold)
