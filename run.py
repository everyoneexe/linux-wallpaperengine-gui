#!/usr/bin/env python3
"""
Wallpaper Engine Launcher Script

This script is used to launch the wallpaper engine application.
"""

import sys
from pathlib import Path

# Add project directory to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import and run the main application
if __name__ == "__main__":
    from main import main
    main()