"""
Constants for Wallpaper Engine application
"""
import os
import shutil
from pathlib import Path

def find_wallpaper_engine_binary():
    """
    Finds linux-wallpaperengine binary in various locations.
    
    Returns:
        Path: Path to the binary or None if not found
    """
    # Common installation paths
    search_paths = [
        # User's Downloads (common build location)
        Path.home() / "Downloads/linux-wallpaperengine/build/output/linux-wallpaperengine",
        Path.home() / "Downloads/linux-wallpaperengine/build/linux-wallpaperengine",
        
        # System-wide installations
        Path("/usr/local/bin/linux-wallpaperengine"),
        Path("/usr/bin/linux-wallpaperengine"),
        Path("/opt/linux-wallpaperengine/linux-wallpaperengine"),
        
        # Current directory relative paths
        Path("./linux-wallpaperengine"),
        Path("../linux-wallpaperengine/build/output/linux-wallpaperengine"),
        
        # Home directory builds
        Path.home() / "linux-wallpaperengine/build/output/linux-wallpaperengine",
        Path.home() / "src/linux-wallpaperengine/build/output/linux-wallpaperengine",
        Path.home() / "git/linux-wallpaperengine/build/output/linux-wallpaperengine",
    ]
    
    # First check if it's in PATH
    if shutil.which("linux-wallpaperengine"):
        return Path(shutil.which("linux-wallpaperengine"))
    
    # Then check common paths
    for path in search_paths:
        if path.exists() and path.is_file():
            # Verify it's executable
            if os.access(path, os.X_OK):
                return path
    
    return None

# File paths
STEAM_WORKSHOP_PATH = Path.home() / ".steam/steam/steamapps/workshop/content/431960"
SETTINGS_FILE = Path.home() / ".config" / "wallpaper_engine" / "settings.json"

# Dynamic binary detection
WALLPAPER_ENGINE_BINARY = find_wallpaper_engine_binary()

# UI Dimensions
WALLPAPER_BUTTON_SIZE = 140
MIN_WINDOW_WIDTH = 1400
MIN_WINDOW_HEIGHT = 900
WALLPAPER_GRID_COLUMNS = 6

# Timer intervals (seconds)
TIMER_INTERVALS = {
    "30 seconds": 30,
    "1 minute": 60,
    "5 minutes": 300,
    "10 minutes": 600,
    "30 minutes": 1800,
    "1 hour": 3600,
    "2 hours": 7200,
    "6 hours": 21600,
    "12 hours": 43200,
    "24 hours (daily)": 86400,
    "Custom...": "custom"
}

# Default settings
DEFAULT_VOLUME = 50
DEFAULT_FPS = 60
DEFAULT_TIMER_INTERVAL = 60

# Supported file formats
SUPPORTED_IMAGE_FORMATS = ["jpg", "jpeg", "png", "gif"]

# Default hotkeys
DEFAULT_HOTKEYS = {
    "play": "Space",
    "next": "Right",
    "prev": "Left"
}

# Application information
APP_NAME = "Linux Wallpaper Engine Enhanced"
APP_VERSION = "2.0"
ORGANIZATION_NAME = "WallpaperEngine"