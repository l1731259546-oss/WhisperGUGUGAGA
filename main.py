#!/usr/bin/env python3
"""Vision Desktop Assistant - Main entry point."""

import sys
import os
from pathlib import Path

# Add src to path for development
src_path = Path(__file__).parent / 'src'
if src_path.exists():
    sys.path.insert(0, str(src_path))

from vision_assistant.application import VisionMonitoringApp


def main():
    # Use config.yaml from project root
    config_path = Path(__file__).parent / 'config.yaml'

    if not config_path.exists():
        print(f"Configuration file not found at {config_path}")
        print("Please copy config.example.yaml to config.yaml and edit it.")
        sys.exit(1)

    try:
        app = VisionMonitoringApp(config_path=str(config_path))
        app.setup()
        exit_code = app.run()
        app.shutdown()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
