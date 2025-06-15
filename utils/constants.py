"""
Wallpaper Engine uygulaması için sabitler
"""
from pathlib import Path

# Dosya yolları
STEAM_WORKSHOP_PATH = Path.home() / ".steam/steam/steamapps/workshop/content/431960"
SETTINGS_FILE = Path.home() / ".config" / "wallpaper_engine" / "settings.json"
WALLPAPER_ENGINE_BINARY = Path.home() / "Downloads/linux-wallpaperengine/build/output/linux-wallpaperengine"

# UI Boyutları
WALLPAPER_BUTTON_SIZE = 140
MIN_WINDOW_WIDTH = 1400
MIN_WINDOW_HEIGHT = 900
WALLPAPER_GRID_COLUMNS = 6

# Timer aralıkları (saniye)
TIMER_INTERVALS = {
    "30 saniye": 30,
    "1 dakika": 60,
    "5 dakika": 300,
    "10 dakika": 600,
    "30 dakika": 1800,
    "1 saat": 3600,
    "2 saat": 7200,
    "6 saat": 21600,
    "12 saat": 43200,
    "24 saat (günlük)": 86400,
    "Özel...": "custom"
}

# Varsayılan ayarlar
DEFAULT_VOLUME = 50
DEFAULT_FPS = 60
DEFAULT_TIMER_INTERVAL = 60

# Desteklenen dosya formatları
SUPPORTED_IMAGE_FORMATS = ["jpg", "jpeg", "png", "gif"]

# Varsayılan kısayol tuşları
DEFAULT_HOTKEYS = {
    "play": "Space",
    "next": "Right",
    "prev": "Left"
}

# Uygulama bilgileri
APP_NAME = "Linux Wallpaper Engine Enhanced"
APP_VERSION = "2.0"
ORGANIZATION_NAME = "WallpaperEngine"