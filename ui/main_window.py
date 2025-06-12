"""
Main window widget
"""
import logging
import psutil
import os
from typing import Optional, Dict
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QComboBox,
    QSlider, QCheckBox, QSplitter, QFrame,
    QScrollArea, QGridLayout, QSystemTrayIcon,
    QMenu, QApplication, QDialog, QButtonGroup, QRadioButton,
    QLineEdit, QPushButton, QTabWidget
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QAction, QMouseEvent

from core import PlaylistManager, WallpaperEngine
from core.wallpaper_controller import WallpaperController
from utils import (
    get_preview_paths, get_screens,
    MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT, WALLPAPER_GRID_COLUMNS,
    APP_NAME, DEFAULT_VOLUME, DEFAULT_FPS, SteamWorkshopWatcher
)
from utils.ffmpeg_utils import ffmpeg_processor, get_media_info, generate_thumbnail, is_ffmpeg_available
from ui.wallpaper_button import WallpaperButton
from ui.playlist_widget import PlaylistWidget
from ui.search_widget import SearchWidget

logger = logging.getLogger(__name__)

# Steam Browser widget is optional - won't work without QWebEngine
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtCore import QUrl
    STEAM_BROWSER_AVAILABLE = True
    logger.info("QWebEngine loaded successfully")
except ImportError as e:
    logger.warning(f"QWebEngine unavailable: {e}")
    STEAM_BROWSER_AVAILABLE = False

# Constants
PERFORMANCE_UPDATE_INTERVAL = 2000  # ms
DEFAULT_TOAST_DURATION = 3000  # ms

# Dynamic icon path - relative to project directory
def get_icon_path():
    """Get dynamic icon path relative to project directory."""
    try:
        # Get the directory where this file is located
        current_dir = Path(__file__).parent.parent
        icon_path = current_dir / "wallpaper-engine.png"
        
        if icon_path.exists():
            return str(icon_path)
        
        # Fallback paths
        fallback_paths = [
            Path.home() / "Downloads" / "linux-wallpaperengine" / "wallpaper-engine.png",
            Path.home() / "Downloads" / "wallpaper_engine" / "wallpaper-engine.png",
            Path("/usr/share/pixmaps/wallpaper-engine.png"),
            Path("/usr/local/share/pixmaps/wallpaper-engine.png")
        ]
        
        for fallback in fallback_paths:
            if fallback.exists():
                return str(fallback)
                
        return None
        
    except Exception as e:
        logger.error(f"Error getting icon path: {e}")
        return None

ICON_PATH = get_icon_path()


class ThemeSettingsManager:
    """Class that manages JSON operations for theme settings."""
    
    def __init__(self):
        self.settings_file = Path.home() / ".config" / "wallpaper_engine" / "settings.json"
    
    def load_theme(self) -> str:
        """Loads saved theme."""
        try:
            import json
            
            if not self.settings_file.exists():
                logger.debug("Settings file doesn't exist, using default theme")
                return "default"
            
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                logger.debug("Settings file is empty, using default theme")
                return "default"
            
            data = json.loads(content)
            saved_theme = data.get('current_theme', 'default')
            
            logger.info(f"Saved theme loaded: {saved_theme}")
            return saved_theme
            
        except Exception as e:
            logger.error(f"Error loading theme: {e}")
            return "default"
    
    def save_theme(self, theme_id: str) -> bool:
        """Saves theme."""
        try:
            import json
            
            # Create directory
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Read current settings
            data = {}
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
            
            # Add theme setting
            data['current_theme'] = theme_id
            
            # Write to file
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
            
            logger.info(f"Theme saved: {theme_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving theme: {e}")
            return False


class PerformanceMonitor:
    """Hidden performance monitor."""
    
    def __init__(self):
        import subprocess
        self.subprocess = subprocess
        self.process = psutil.Process(os.getpid())
        self.wallpaper_process = None
        self.last_cpu_percent = 0.0
        self.last_system_cpu = 0.0
        self._find_wallpaper_process()
        # Start first CPU measurement (non-blocking)
        if self.wallpaper_process:
            try:
                self.wallpaper_process.cpu_percent()  # First call, baseline for next
            except:
                pass
        # Baseline for system CPU too
        psutil.cpu_percent()
    
    def _find_wallpaper_process(self) -> None:
        """Finds linux-wallpaperengine process (for debugging purposes)."""
        try:
            found_processes = []
            all_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'exe']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info.get('name', '')
                    
                    # Save all processes (for debug)
                    if 'wallpaper' in proc_name.lower() or 'engine' in proc_name.lower():
                        all_processes.append((proc_info['pid'], proc_name, proc_info.get('exe', 'N/A')))
                    
                    # Check different conditions
                    if (proc_name == 'linux-wallpaperengine' or
                        proc_name == 'wallpaperengine' or
                        proc_name == 'wallpaper-engine' or
                        (proc_info['cmdline'] and any('wallpaperengine' in str(cmd).lower() for cmd in proc_info['cmdline'])) or
                        (proc_info['cmdline'] and any('wallpaper-engine' in str(cmd).lower() for cmd in proc_info['cmdline'])) or
                        (proc_info['exe'] and 'wallpaperengine' in str(proc_info['exe']).lower())):
                        
                        found_processes.append((proc_info['pid'], proc_name, proc_info.get('exe', 'N/A')))
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            # Debug: log all wallpaper/engine containing processes
            if all_processes:
                logger.info(f"Wallpaper related processes: {all_processes}")
            
            if found_processes:
                # Use the latest found process (after new restart)
                latest_pid = max(found_processes, key=lambda x: x[0])[0]
                self.wallpaper_process = psutil.Process(latest_pid)
                
                # Start baseline for CPU measurement
                try:
                    self.wallpaper_process.cpu_percent()
                except:
                    pass
                    
                logger.info(f"Wallpaper process found: PID {latest_pid} ({len(found_processes)} count) - {found_processes}")
                return
            
            logger.info("linux-wallpaperengine process not found")
            self.wallpaper_process = None
            
        except Exception as e:
            logger.error(f"Error searching wallpaper process: {e}")
            self.wallpaper_process = None
        
    def get_memory_usage(self) -> float:
        """Returns wallpaper engine RAM usage in MB."""
        try:
            # Continuous process check
            self._ensure_wallpaper_process()
            
            if self.wallpaper_process and self.wallpaper_process.is_running():
                return self.wallpaper_process.memory_info().rss / 1024 / 1024
            else:
                return 0.0
                
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            logger.debug("Wallpaper process RAM info unavailable, searching again...")
            self.wallpaper_process = None
            return 0.0
        
    def get_cpu_usage(self) -> float:
        """Returns wallpaper engine CPU usage as percentage."""
        try:
            # Continuous process check
            self._ensure_wallpaper_process()
            
            if self.wallpaper_process and self.wallpaper_process.is_running():
                # Non-blocking CPU measurement (since previous call)
                current_cpu = self.wallpaper_process.cpu_percent()
                self.last_cpu_percent = current_cpu
                return current_cpu
            else:
                return 0.0
                
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            logger.debug("Wallpaper process CPU info unavailable, searching again...")
            self.wallpaper_process = None
            return 0.0

    def get_system_cpu_usage(self) -> float:
        """Returns system-wide CPU usage as percentage."""
        try:
            # Non-blocking system CPU measurement
            current_system_cpu = psutil.cpu_percent()
            self.last_system_cpu = current_system_cpu
            return current_system_cpu
        except Exception:
            return 0.0
        
    def get_gpu_info(self) -> str:
        """Returns GPU information (more reliable)."""
        try:
            # Continuously check wallpaper process
            self._ensure_wallpaper_process()
            
            if self.wallpaper_process is None or not self.wallpaper_process.is_running():
                return "WE: Stopped"
            
            wallpaper_pid = str(self.wallpaper_process.pid)
            
            # First show general GPU usage (more reliable)
            general_gpu = self._get_general_gpu_usage()
            if general_gpu:
                return f"GPU: {general_gpu}"
            
            # If general fails, try process-specific
            nvidia_info = self._get_nvidia_gpu_info(wallpaper_pid)
            if nvidia_info:
                return nvidia_info
            
            amd_info = self._get_amd_gpu_info(wallpaper_pid)
            if amd_info:
                return amd_info
            
            intel_info = self._get_intel_gpu_info(wallpaper_pid)
            if intel_info:
                return intel_info
                
            return "GPU: N/A"
                
        except Exception as e:
            return "GPU: Error"
    
    def _ensure_wallpaper_process(self) -> None:
        """Ensures wallpaper process is active."""
        try:
            if self.wallpaper_process is None:
                self._find_wallpaper_process()
            elif not self.wallpaper_process.is_running():
                logger.debug("Wallpaper process stopped, searching again...")
                self.wallpaper_process = None
                self._find_wallpaper_process()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # Process no longer exists, search again
            logger.debug("Process exception, searching again...")
            self.wallpaper_process = None
            self._find_wallpaper_process()
    
    def _get_general_gpu_usage(self) -> str:
        """Returns general GPU usage (not process-specific)."""
        try:
            # NVIDIA general usage
            result = self.subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                gpu_usage = result.stdout.strip()
                if gpu_usage and gpu_usage.isdigit():
                    return f"{gpu_usage}%"
                    
        except:
            pass
        
        try:
            # AMD general usage
            result = self.subprocess.run(['rocm-smi', '--showuse'],
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and '%' in result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'GPU' in line and '%' in line:
                        parts = line.split()
                        for part in parts:
                            if '%' in part and part.replace('%', '').isdigit():
                                return part
        except:
            pass
            
        return None
    
    def _get_nvidia_gpu_info(self, wallpaper_pid: str) -> str:
        """Gets NVIDIA GPU information."""
        try:
            # Check all GPUs for multi-GPU situation
            gpu_count_result = self.subprocess.run(['nvidia-smi', '--query-gpu=count', '--format=csv,noheader'],
                                            capture_output=True, text=True, timeout=2)
            
            if gpu_count_result.returncode == 0:
                # Find which GPU the process is using
                pmon_result = self.subprocess.run(['nvidia-smi', 'pmon', '-c', '1'],
                                           capture_output=True, text=True, timeout=3)
                
                if pmon_result.returncode == 0:
                    lines = pmon_result.stdout.strip().split('\n')
                    for line in lines:
                        if wallpaper_pid in line:
                            parts = line.split()
                            if len(parts) >= 4:
                                gpu_id = parts[0]  # GPU ID
                                gpu_usage = parts[3]  # GPU usage percentage
                                return f"WE-GPU{gpu_id}: {gpu_usage}%"
                
                # Show general NVIDIA GPU usage (multi-GPU)
                general_result = self.subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
                                              capture_output=True, text=True, timeout=2)
                if general_result.returncode == 0:
                    gpu_usages = general_result.stdout.strip().split('\n')
                    if len(gpu_usages) == 1:
                        return f"GPU: {gpu_usages[0]}%"
                    else:
                        # Multi-GPU situation
                        gpu_info = []
                        for i, usage in enumerate(gpu_usages):
                            gpu_info.append(f"GPU{i}: {usage}%")
                        return " | ".join(gpu_info[:2])  # Show first 2 GPUs
                        
        except:
            pass
        return None
    
    def _get_amd_gpu_info(self, wallpaper_pid: str) -> str:
        """Gets AMD GPU information."""
        try:
            # radeontop or rocm-smi check
            amd_result = self.subprocess.run(['rocm-smi', '--showuse'],
                                      capture_output=True, text=True, timeout=2)
            
            if amd_result.returncode == 0:
                lines = amd_result.stdout.strip().split('\n')
                for line in lines:
                    if 'GPU' in line and '%' in line:
                        # Parse AMD GPU usage information
                        parts = line.split()
                        for part in parts:
                            if '%' in part:
                                return f"AMD-GPU: {part}"
                                
        except:
            pass
        return None
    
    def _get_intel_gpu_info(self, wallpaper_pid: str) -> str:
        """Gets Intel GPU information."""
        try:
            # intel_gpu_top check
            intel_result = self.subprocess.run(['intel_gpu_top', '-s', '1000'],
                                        capture_output=True, text=True, timeout=2)
            
            if intel_result.returncode == 0 and 'Render/3D' in intel_result.stdout:
                lines = intel_result.stdout.strip().split('\n')
                for line in lines:
                    if 'Render/3D' in line and '%' in line:
                        parts = line.split()
                        for part in parts:
                            if '%' in part:
                                return f"Intel-GPU: {part}"
                                
        except:
            pass
        return None


class ThemeDialog(QDialog):
    """Hidden theme selection dialog."""
    
    theme_changed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎨 Theme Options")
        self.setFixedSize(300, 350)
        self.setModal(True)
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("🎨 Select Theme")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #00d4ff; margin: 10px;")
        layout.addWidget(title)
        
        # Theme options
        self.theme_group = QButtonGroup(self)
        
        themes = [
            ("default", "🌙 Default (Modern Blue)"),
            ("gaming", "🔥 Gaming (Red-Black)"),
            ("matrix", "🌿 Matrix (Green Terminal)"),
            ("minimal", "🖤 Minimal (Black-White)")
        ]
        
        for theme_id, theme_name in themes:
            radio = QRadioButton(theme_name)
            radio.setObjectName(f"theme_{theme_id}")
            if theme_id == "default":
                radio.setChecked(True)
            self.theme_group.addButton(radio)
            layout.addWidget(radio)
            
        layout.addStretch()
        
        # Apply button
        apply_btn = QLabel("✅ Apply")
        apply_btn.setAlignment(Qt.AlignCenter)
        apply_btn.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 212, 255, 0.3), stop:1 rgba(0, 212, 255, 0.1));
                border: 2px solid #00d4ff;
                border-radius: 8px;
                padding: 10px;
                font-weight: bold;
                color: white;
                margin: 10px;
            }
            QLabel:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 212, 255, 0.5), stop:1 rgba(0, 212, 255, 0.3));
            }
        """)
        apply_btn.mousePressEvent = self.apply_theme
        layout.addWidget(apply_btn)
        
    def apply_theme(self, event):
        """Apply selected theme."""
        checked_button = self.theme_group.checkedButton()
        if checked_button:
            theme_id = checked_button.objectName().replace("theme_", "")
            self.theme_changed.emit(theme_id)
            self.accept()
    
    def set_current_theme(self, theme_id: str) -> None:
        """Sets current theme as selected."""
        for button in self.theme_group.buttons():
            if button.objectName() == f"theme_{theme_id}":
                button.setChecked(True)
                break


class MainWindow(QWidget):
    """
    Main application window.
    
    Signals:
        wallpaper_applied: Emitted when wallpaper is applied
        toast_requested: Emitted when toast notification is requested
    """
    
    wallpaper_applied = Signal(str)  # wallpaper_id
    toast_requested = Signal(str, int)  # message, duration
    
    def __init__(self):
        super().__init__()
        
        # Core components
        self.playlist_manager = PlaylistManager()
        self.wallpaper_engine = WallpaperEngine()
        
        # Dynamic control system
        self.wallpaper_controller = WallpaperController(self.wallpaper_engine)
        
        
        # UI components
        self.wallpaper_buttons: Dict[str, WallpaperButton] = {}
        self.selected_wallpaper_button: Optional[WallpaperButton] = None
        
        # Settings
        self.screens = get_screens()
        self.selected_screen = self.screens[0] if self.screens else "eDP-1"
        
        # Timer for playlist
        self.playlist_timer = QTimer()
        self.playlist_timer.timeout.connect(self._on_next_wallpaper)
        
        # Performance monitor (hidden)
        self.performance_monitor = PerformanceMonitor()
        self.perf_timer = QTimer()
        self.perf_timer.timeout.connect(self._update_performance)
        self.perf_timer.start(PERFORMANCE_UPDATE_INTERVAL)
        
        # Theme system
        self.theme_settings = ThemeSettingsManager()
        self.current_theme = "default"
        self.theme_colors = {
            "default": {
                "primary": "#00d4ff",
                "secondary": "#ff6b6b",
                "background": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f0f23, stop:1 #1a1a2e)",
                "panel": "rgba(255, 255, 255, 0.08)"
            },
            "gaming": {
                "primary": "#ff0040",
                "secondary": "#ff6600",
                "background": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a0000, stop:1 #330000)",
                "panel": "rgba(255, 0, 64, 0.15)"
            },
            "matrix": {
                "primary": "#00ff41",
                "secondary": "#00cc33",
                "background": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #000000, stop:1 #001100)",
                "panel": "rgba(0, 255, 65, 0.08)"
            },
            "minimal": {
                "primary": "#ffffff",
                "secondary": "#cccccc",
                "background": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #000000, stop:1 #111111)",
                "panel": "rgba(255, 255, 255, 0.05)"
            }
        }
        
        # Hidden performance label (initially invisible)
        self.perf_label = None
        self.perf_visible = False
        
        # Steam Workshop monitoring
        self.steam_watcher = None
        
        self._load_theme_setting()
        self.setup_ui()
        self.setup_system_tray()
        self.setup_connections()
        self.load_wallpapers()
        self._load_current_playlist()
        
        # Load saved custom timer settings
        self._load_custom_timer_settings()
        
        # Restore state (AT THE END - after all UI is ready)
        QTimer.singleShot(500, self._restore_app_state)
        
        # Steam Workshop monitoring disabled - manual refresh only
        # self._setup_steam_workshop_monitoring()
        
        # Update playlist widget after theme is loaded
        self._apply_loaded_theme()

    def setup_ui(self) -> None:
        """Sets up the UI."""
        self.setWindowTitle(f"🎨 {APP_NAME}")
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.resize(1600, 1000)
        self.setObjectName("MainWindow")

        # Load and apply styles
        self.load_styles()

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Main splitter
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left side - Tab widget with wallpapers and steam browser
        left_widget = self.create_tabbed_left_panel()
        
        # Right side - Playlist
        self.playlist_widget = PlaylistWidget(self)

        splitter.addWidget(left_widget)
        splitter.addWidget(self.playlist_widget)
        splitter.setSizes([1000, 400])


    def create_tabbed_left_panel(self) -> QWidget:
        """Creates left panel with tab widget."""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(10)

        # Header with compact controls (common for both tabs)
        header_section = self.create_header_section()
        container_layout.addWidget(header_section)

        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("MainTabWidget")
        
        # Wallpapers tab
        wallpapers_tab = self.create_wallpapers_tab()
        self.tab_widget.addTab(wallpapers_tab, "🖼️ Wallpaper Gallery")
        
        
        # Steam Browser tab - create from start for PRE-CREATE
        steam_tab = self.create_steam_browser_tab()
        self.tab_widget.addTab(steam_tab, "🌐 Steam Workshop")
        
        # Pre-initialize Steam browser in background to prevent first click issue
        QTimer.singleShot(100, self._pre_initialize_steam_browser)
        
        container_layout.addWidget(self.tab_widget)
        return container

    def create_wallpapers_tab(self) -> QWidget:
        """Creates wallpaper gallery tab."""
        tab_widget = QWidget()
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(10)

        # Wallpapers section with minimal search
        wallpapers_header = self.create_minimal_header()
        tab_layout.addWidget(wallpapers_header)

        # Wallpapers scroll area
        scroll_area = self.create_wallpapers_scroll_area()
        tab_layout.addWidget(scroll_area)

        return tab_widget


    def create_steam_browser_tab(self) -> QWidget:
        """Creates Steam Workshop browser tab - Minimal QWebEngine."""
        if STEAM_BROWSER_AVAILABLE:
            try:
                # Minimal Steam browser + Login Persistence
                from PySide6.QtWebEngineWidgets import QWebEngineView
                from PySide6.QtWebEngineCore import QWebEngineProfile
                from PySide6.QtCore import QUrl
                from pathlib import Path
                
                container = QWidget()
                layout = QVBoxLayout(container)
                layout.setContentsMargins(5, 5, 5, 5)
                
                # Path for persistent profile
                profile_path = Path.home() / ".config" / "wallpaper_engine" / "steam_minimal"
                profile_path.mkdir(parents=True, exist_ok=True)
                
                # Cookie persistence with custom profile
                profile = QWebEngineProfile("SteamMinimal", container)
                profile.setPersistentStoragePath(str(profile_path))
                profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
                
                # Steam-friendly user agent
                profile.setHttpUserAgent("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                
                # Create web view
                browser = QWebEngineView()
                
                # Connect profile with custom page
                from PySide6.QtWebEngineCore import QWebEnginePage
                page = QWebEnginePage(profile, browser)
                browser.setPage(page)
                
                # Load Steam Workshop directly
                workshop_url = "https://steamcommunity.com/workshop/browse/?appid=431960&browsesort=trend&section=readytouseitems"
                browser.load(QUrl(workshop_url))
                
                layout.addWidget(browser)
                
                logger.info(f"Minimal Steam browser + login persistence: {profile_path}")
                return container
                
            except Exception as e:
                logger.error(f"Could not create minimal Steam browser: {e}")
        
        # Fallback
        return self._create_fallback_widget()
            
    def _create_fallback_widget(self) -> QWidget:
        """Fallback widget for cases without QWebEngine"""
        fallback = QWidget()
        layout = QVBoxLayout(fallback)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(20)
        
        # Error message
        error_label = QLabel("🌐❌")
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setStyleSheet("font-size: 48px; margin: 20px;")
        layout.addWidget(error_label)
        
        title_label = QLabel("Steam Browser Unavailable")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ff6b6b; margin: 10px;")
        layout.addWidget(title_label)
        
        info_label = QLabel("QWebEngine required - install python-pyside6-webengine from AUR")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("color: #cccccc; font-size: 12px; line-height: 1.5;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        layout.addStretch()
        return fallback
        
    def _pre_initialize_steam_browser(self):
        """Pre-initialize Steam browser in background (prevents first click issue)"""
        try:
            if hasattr(self, 'steam_browser') and self.steam_browser:
                # Steam browser already exists, just secretly do a tab switch and back
                current_index = self.tab_widget.currentIndex()
                
                # Find Steam Workshop tab index
                for i in range(self.tab_widget.count()):
                    if "Steam Workshop" in self.tab_widget.tabText(i):
                        # Switch secretly and return immediately (user won't notice)
                        self.tab_widget.setCurrentIndex(i)
                        QTimer.singleShot(50, lambda: self.tab_widget.setCurrentIndex(current_index))
                        logger.info("Steam browser pre-initialized (background)")
                        break
                        
        except Exception as e:
            logger.error(f"Steam browser pre-initialization error: {e}")

    def create_left_panel(self) -> QWidget:
        """Creates left panel with search bar. (Old method - for backward compatibility)"""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Header with compact controls
        header_section = self.create_header_section()
        left_layout.addWidget(header_section)

        # Wallpapers section with minimal search
        wallpapers_header = self.create_minimal_header()
        left_layout.addWidget(wallpapers_header)

        # Wallpapers scroll area
        scroll_area = self.create_wallpapers_scroll_area()
        left_layout.addWidget(scroll_area)

        return left_widget

    def create_header_section(self) -> QWidget:
        """Creates compact header and controls."""
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        # Main title (double click for performance, right click for theme selection)
        self.title = QLabel("🎨 WALLPAPER ENGINE")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setObjectName("MainHeader")
        self.title.mouseDoubleClickEvent = self._on_title_double_click
        self.title.mousePressEvent = self._on_title_mouse_press
        header_layout.addWidget(self.title)

        # Hidden performance indicator (initially invisible)
        self.perf_label = QLabel("")
        self.perf_label.setAlignment(Qt.AlignCenter)
        self.perf_label.setObjectName("PerfLabel")
        self.perf_label.setVisible(False)
        header_layout.addWidget(self.perf_label)

        # Compact controls toolbar
        toolbar = self.create_compact_toolbar()
        header_layout.addWidget(toolbar)

        return header_widget

    def create_compact_toolbar(self) -> QFrame:
        """Creates compact control toolbar."""
        toolbar = QFrame()
        toolbar.setObjectName("CompactToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 10, 10, 10)
        toolbar_layout.setSpacing(15)

        # Screen selection (compact)
        screen_label = QLabel("SCREEN")
        screen_label.setObjectName("CompactLabel")
        self.screen_combo = QComboBox()
        self.screen_combo.addItems(self.screens)
        self.screen_combo.currentTextChanged.connect(self._on_screen_change)
        self.screen_combo.setMaximumWidth(120)

        # Volume control (compact)
        vol_label = QLabel("VOLUME")
        vol_label.setObjectName("CompactLabel")
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setMinimum(0)
        self.vol_slider.setMaximum(100)
        self.vol_slider.setValue(DEFAULT_VOLUME)
        self.vol_slider.setMaximumWidth(100)
        self.vol_value_label = QLabel(f"{DEFAULT_VOLUME}%")
        self.vol_value_label.setMinimumWidth(35)
        self.vol_value_label.setObjectName("ValueLabel")
        self.vol_slider.valueChanged.connect(self._on_volume_changed)

        # FPS control (compact)
        fps_label = QLabel("FPS")
        fps_label.setObjectName("CompactLabel")
        self.fps_slider = QSlider(Qt.Horizontal)
        self.fps_slider.setMinimum(10)
        self.fps_slider.setMaximum(144)
        self.fps_slider.setValue(DEFAULT_FPS)
        self.fps_slider.setMaximumWidth(100)
        self.fps_value_label = QLabel(str(DEFAULT_FPS))
        self.fps_value_label.setMinimumWidth(35)
        self.fps_value_label.setObjectName("ValueLabel")
        self.fps_slider.valueChanged.connect(self._on_fps_changed)

        # Advanced checkboxes (compact)
        self.noautomute_cb = QCheckBox("MUTE")
        self.noaudioproc_cb = QCheckBox("PROC")
        self.disable_mouse_cb = QCheckBox("MOUSE")
        
        # Style checkboxes
        for cb in [self.noautomute_cb, self.noaudioproc_cb, self.disable_mouse_cb]:
            cb.setObjectName("CompactCheckBox")
        
        # Tooltips for compact checkboxes
        self.noautomute_cb.setToolTip("Don't auto-mute audio")
        self.noaudioproc_cb.setToolTip("Audio processing disabled")
        self.disable_mouse_cb.setToolTip("Mouse interaction disabled")
        
        # Dynamic checkbox connections
        self.noautomute_cb.toggled.connect(self._on_auto_mute_toggle)
        self.noaudioproc_cb.toggled.connect(self._on_audio_processing_toggle)
        self.disable_mouse_cb.toggled.connect(self._on_mouse_toggle)

        # Add Media button (compact)
        self.gif_btn = QPushButton("🎬 MEDIA")
        self.gif_btn.setObjectName("GifButton")
        self.gif_btn.setToolTip("Add GIF/MP4/Video wallpaper")
        self.gif_btn.clicked.connect(self._on_add_gif_wallpaper)

        # Kill button (compact)
        self.kill_btn = QPushButton("🔴 KILL")
        self.kill_btn.setObjectName("KillButton")
        self.kill_btn.setToolTip("Kill Wallpaper Engine")
        self.kill_btn.clicked.connect(self._on_kill_wallpaper_engine)

        # Add to layout
        toolbar_layout.addWidget(screen_label)
        toolbar_layout.addWidget(self.screen_combo)
        toolbar_layout.addWidget(vol_label)
        toolbar_layout.addWidget(self.vol_slider)
        toolbar_layout.addWidget(self.vol_value_label)
        toolbar_layout.addWidget(fps_label)
        toolbar_layout.addWidget(self.fps_slider)
        toolbar_layout.addWidget(self.fps_value_label)
        toolbar_layout.addWidget(self.noautomute_cb)
        toolbar_layout.addWidget(self.noaudioproc_cb)
        toolbar_layout.addWidget(self.disable_mouse_cb)
        toolbar_layout.addWidget(self.gif_btn)
        toolbar_layout.addWidget(self.kill_btn)
        toolbar_layout.addStretch()

        return toolbar

    def create_minimal_header(self) -> QWidget:
        """Minimal wallpaper title and search."""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(15)
        
        # Wallpapers label
        wallpapers_label = QLabel("🖼️ Wallpaper Gallery")
        wallpapers_label.setObjectName("WallpapersLabel")
        header_layout.addWidget(wallpapers_label)
        
        # Refresh button removed
        # self.refresh_btn = QPushButton("🔄")
        # self.refresh_btn.setObjectName("RefreshButton")
        # self.refresh_btn.setMaximumWidth(35)
        # self.refresh_btn.setMaximumHeight(35)
        # self.refresh_btn.clicked.connect(self._on_manual_refresh)
        # header_layout.addWidget(self.refresh_btn)
        
        header_layout.addStretch()
        
        # Minimal search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search...")
        self.search_input.setObjectName("MinimalSearchInput")
        self.search_input.setMaximumWidth(200)
        self.search_input.setMinimumWidth(150)
        header_layout.addWidget(self.search_input)
        
        # Initialize metadata manager
        from utils.metadata_manager import metadata_manager
        self.metadata_manager = metadata_manager
        
        # Setup search connections
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_minimal_search)
        self.search_input.textChanged.connect(lambda: self.search_timer.start(500))
        
        # Load metadata in background
        QTimer.singleShot(1000, self.load_minimal_metadata)
        
        return header_widget

    def load_minimal_metadata(self):
        """Minimal metadata loading."""
        try:
            def load_in_background():
                self.metadata_manager.scan_wallpapers()
            QTimer.singleShot(100, load_in_background)
        except Exception as e:
            logger.error(f"Metadata loading error: {e}")

    def perform_minimal_search(self):
        """Minimal search."""
        try:
            query = self.search_input.text().strip()
            
            if query:
                results = self.metadata_manager.search(query, {})
                matching_ids = [r.workshop_id for r in results]
                self.filter_minimal_wallpapers(matching_ids)
            else:
                # Empty search - show all wallpapers
                self.filter_minimal_wallpapers(None)
                
        except Exception as e:
            logger.error(f"Search error: {e}")

    def filter_minimal_wallpapers(self, matching_ids=None):
        """Minimal wallpaper filtering and reorganization."""
        try:
            visible_buttons = []
            
            # First set visibility
            for folder_id, button in self.wallpaper_buttons.items():
                if matching_ids is None:
                    button.setVisible(True)
                    visible_buttons.append((folder_id, button))
                else:
                    is_visible = folder_id in matching_ids
                    button.setVisible(is_visible)
                    if is_visible:
                        visible_buttons.append((folder_id, button))
            
            # Reorganize visible buttons
            self.reorganize_grid_improved(visible_buttons)
            
        except Exception as e:
            logger.error(f"Filtering error: {e}")
    
    def reorganize_grid(self, visible_buttons):
        """Reorganizes visible buttons in proper grid."""
        try:
            # Remove all buttons from grid
            for i in reversed(range(self.wallpapers_grid.count())):
                item = self.wallpapers_grid.itemAt(i)
                if item and item.widget():
                    item.widget().setParent(None)
            
            # Add visible buttons back in order
            visible_buttons.sort(key=lambda x: x[0])  # Sort by folder_id
            
            for i, (folder_id, button) in enumerate(visible_buttons):
                row, col = divmod(i, WALLPAPER_GRID_COLUMNS)
                self.wallpapers_grid.addWidget(button, row, col)
                
        except Exception as e:
            logger.error(f"Grid reorganization error: {e}")
    
    def reorganize_grid_improved(self, visible_buttons):
        """Organization with FlowLayout - automatic wrapping."""
        try:
            # Clear all buttons from layout
            self.wallpapers_layout.clear()
            
            if not visible_buttons:
                # Show no results message
                self.show_no_results_message()
                return
            
            # Sort by folder ID (original order)
            sorted_buttons = sorted(visible_buttons, key=lambda x: x[0])
            
            # Add to FlowLayout - automatic left to right ordering
            for folder_id, button in sorted_buttons:
                self.wallpapers_layout.addWidget(button)
                
        except Exception as e:
            logger.error(f"FlowLayout organization error: {e}")
    
    def show_no_results_message(self):
        """Shows centered and theme-compatible message when no search results found."""
        try:
            # Container widget for centering
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(0)
            
            # Top spacing
            container_layout.addStretch(1)
            
            # Main message widget
            message_widget = QWidget()
            message_layout = QVBoxLayout(message_widget)
            message_layout.setContentsMargins(40, 40, 40, 40)
            message_layout.setSpacing(20)
            
            # Main title
            title_label = QLabel("🔍 No search results found")
            title_label.setAlignment(Qt.AlignCenter)
            title_label.setObjectName("NoResultsTitle")
            
            # Subtitle
            subtitle_label = QLabel("💡 Try different keywords or clear the search")
            subtitle_label.setAlignment(Qt.AlignCenter)
            subtitle_label.setObjectName("NoResultsSubtitle")
            
            message_layout.addWidget(title_label)
            message_layout.addWidget(subtitle_label)
            
            # Get current theme colors
            primary = self.theme_colors[self.current_theme]["primary"]
            secondary = self.theme_colors[self.current_theme]["secondary"]
            primary_rgba = self._hex_to_rgba(primary)
            secondary_rgba = self._hex_to_rgba(secondary)
            
            # Theme-compatible style
            message_widget.setStyleSheet(f"""
                QWidget {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba({primary_rgba}, 0.08),
                        stop:1 rgba({secondary_rgba}, 0.08));
                    border: 2px dashed rgba({primary_rgba}, 0.4);
                    border-radius: 20px;
                    max-width: 500px;
                    min-width: 400px;
                }}
                
                QLabel#NoResultsTitle {{
                    color: {primary};
                    font-size: 20px;
                    font-weight: bold;
                    background: transparent;
                    border: none;
                    padding: 10px;
                }}
                
                QLabel#NoResultsSubtitle {{
                    color: {secondary};
                    font-size: 14px;
                    font-weight: normal;
                    background: transparent;
                    border: none;
                    padding: 5px;
                }}
            """)
            
            # Horizontal layout for centering
            h_layout = QHBoxLayout()
            h_layout.addStretch(1)
            h_layout.addWidget(message_widget)
            h_layout.addStretch(1)
            
            container_layout.addLayout(h_layout)
            
            # Bottom spacing
            container_layout.addStretch(2)
            
            # Add to FlowLayout
            self.wallpapers_layout.addWidget(container)
            
        except Exception as e:
            logger.error(f"Error showing result message: {e}")
    
    
    

    def create_wallpapers_scroll_area(self) -> QScrollArea:
        """Creates wallpaper scroll area - with FlowLayout."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("WallpapersScrollArea")

        self.wallpapers_widget = QWidget()
        
        # Use FlowLayout - with automatic wrapping
        from .flow_layout import FlowLayout
        self.wallpapers_layout = FlowLayout(self.wallpapers_widget)
        self.wallpapers_layout.setSpacing(10)
        self.wallpapers_layout.setContentsMargins(15, 15, 15, 15)
        
        scroll_area.setWidget(self.wallpapers_widget)
        return scroll_area

    def setup_system_tray(self) -> None:
        """Sets up system tray - with dynamic controls."""
        try:
            # Create simple icon if icon file doesn't exist
            if ICON_PATH and Path(ICON_PATH).exists():
                icon = QIcon(ICON_PATH)
                logger.info(f"Using custom icon: {ICON_PATH}")
            else:
                # Default icon
                icon = self.style().standardIcon(self.style().SP_ComputerIcon)
                logger.warning("Using default system icon - wallpaper-engine.png not found")
            
            self.tray_icon = QSystemTrayIcon(icon, self)
            tray_menu = QMenu()

            # Main controls
            show_action = QAction("🎨 Show", self)
            show_action.triggered.connect(self.show)
            tray_menu.addAction(show_action)

            tray_menu.addSeparator()
            
            # Playlist controls
            play_action = QAction("▶️ Play/Pause", self)
            play_action.triggered.connect(self._on_toggle_playlist)
            tray_menu.addAction(play_action)

            next_action = QAction("⏭️ Next", self)
            next_action.triggered.connect(self._on_next_wallpaper)
            tray_menu.addAction(next_action)

            tray_menu.addSeparator()
            
            # Media Wallpaper adding
            gif_action = QAction("🎬 Add Media", self)
            gif_action.triggered.connect(self._on_add_gif_wallpaper)
            tray_menu.addAction(gif_action)
            
            tray_menu.addSeparator()
            
            # Quick controls
            silent_action = QAction("🔇 Silent Mode", self)
            silent_action.triggered.connect(self._on_tray_silent_toggle)
            tray_menu.addAction(silent_action)
            
            # Preset menu removed - unnecessary

            tray_menu.addSeparator()
            
            # Kill and exit
            kill_action = QAction("🔴 Wallpaper Kill", self)
            kill_action.triggered.connect(self._on_kill_wallpaper_engine)
            tray_menu.addAction(kill_action)
            
            quit_action = QAction("❌ Exit", self)
            quit_action.triggered.connect(QApplication.instance().quit)
            tray_menu.addAction(quit_action)

            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.show()
            
            logger.info("Advanced system tray set up")
            
        except Exception as e:
            logger.error(f"Error setting up system tray: {e}")

    def setup_connections(self) -> None:
        """Sets up signal connections."""
        # Playlist widget connections
        self.playlist_widget.play_pause_requested.connect(self._on_toggle_playlist)
        self.playlist_widget.next_requested.connect(self._on_next_wallpaper)
        self.playlist_widget.prev_requested.connect(self._on_prev_wallpaper)
        self.playlist_widget.add_current_requested.connect(self._on_add_current_to_playlist)
        self.playlist_widget.remove_selected_requested.connect(self._on_remove_from_playlist)
        self.playlist_widget.clear_playlist_requested.connect(self._on_clear_playlist)
        self.playlist_widget.timer_interval_changed.connect(self._on_timer_interval_changed)
        self.playlist_widget.play_mode_changed.connect(self._on_play_mode_changed)
        self.playlist_widget.wallpaper_selected.connect(self._on_playlist_wallpaper_selected)
        
        # Wallpaper button deletion connections
        # This connection will be made for each button in load_wallpapers()


    def load_styles(self) -> None:
        """Loads CSS styles."""
        try:
            # Get current theme colors
            colors = self.theme_colors.get(self.current_theme, self.theme_colors["default"])
            primary_color = colors["primary"]
            secondary_color = colors["secondary"]
            
            # Main theme
            theme_path = Path(__file__).parent.parent / "resources" / "styles" / "dark_theme.qss"
            if theme_path.exists():
                with open(theme_path, 'r', encoding='utf-8') as f:
                    theme_css = f.read()
            else:
                theme_css = ""

            # Button styles
            buttons_path = Path(__file__).parent.parent / "resources" / "styles" / "buttons.qss"
            if buttons_path.exists():
                with open(buttons_path, 'r', encoding='utf-8') as f:
                    buttons_css = f.read()
            else:
                buttons_css = ""

            # Apply theme colors to CSS
            theme_css = theme_css.replace("#00d4ff", primary_color)
            theme_css = theme_css.replace("#ff6b6b", secondary_color)
            buttons_css = buttons_css.replace("#00d4ff", primary_color)
            buttons_css = buttons_css.replace("#ff6b6b", secondary_color)

            # Additional styles (with theme colors)
            theme_background = colors.get("background", "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f0f23, stop:1 #1a1a2e)")
            theme_panel = colors.get("panel", "rgba(255, 255, 255, 0.08)")
            
            additional_css = f"""
                QWidget#MainWindow {{
                    background: {theme_background};
                    color: white;
                    font-family: 'Segoe UI', 'Arial', sans-serif;
                    font-size: 13px;
                }}
                
                QLabel#MainHeader {{
                    font-size: 24px;
                    font-weight: bold;
                    color: {primary_color};
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba({self._hex_to_rgba(primary_color)}, 0.15),
                        stop:1 rgba({self._hex_to_rgba(secondary_color)}, 0.15));
                    border: 2px solid rgba({self._hex_to_rgba(primary_color)}, 0.3);
                    border-radius: 10px;
                    padding: 15px;
                    margin: 5px;
                }}
                
                QLabel#PerfLabel {{
                    font-size: 11px;
                    font-weight: bold;
                    color: {primary_color};
                    background: rgba({self._hex_to_rgba(primary_color)}, 0.1);
                    border: 1px solid rgba({self._hex_to_rgba(primary_color)}, 0.3);
                    border-radius: 6px;
                    padding: 6px 10px;
                    margin: 2px;
                }}
                
                QFrame#CompactToolbar {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {theme_panel}, stop:1 rgba({self._hex_to_rgba(primary_color)}, 0.03));
                    border: 2px solid rgba({self._hex_to_rgba(primary_color)}, 0.3);
                    border-radius: 10px;
                    padding: 8px;
                    margin: 2px;
                }}
                
                QLabel#WallpapersLabel {{
                    font-size: 16px;
                    font-weight: bold;
                    color: {primary_color};
                    padding: 8px;
                    margin: 5px 0;
                }}
                
                QLabel#ValueLabel {{
                    color: {secondary_color};
                    font-weight: bold;
                    font-size: 12px;
                    min-width: 35px;
                    background: none;
                    border: 0px;
                    padding: 0px;
                    margin: 0px;
                }}
                
                QScrollArea#WallpapersScrollArea {{
                    border: 2px solid #444;
                    border-radius: 10px;
                    background: rgba(255, 255, 255, 0.02);
                }}
                
                QLabel#CompactLabel {{
                    color: {primary_color};
                    font-weight: bold;
                    font-size: 11px;
                    min-width: 40px;
                    background: rgba({self._hex_to_rgba(primary_color)}, 0.15);
                    border: 1px solid rgba({self._hex_to_rgba(primary_color)}, 0.4);
                    border-radius: 6px;
                    padding: 6px 10px;
                    margin: 2px;
                }}
                
                QCheckBox#CompactCheckBox {{
                    color: {primary_color};
                    font-weight: bold;
                    font-size: 10px;
                    spacing: 4px;
                    background: transparent;
                    padding: 4px 6px;
                    border-radius: 4px;
                }}
                
                QCheckBox#CompactCheckBox:hover {{
                    background: rgba({self._hex_to_rgba(primary_color)}, 0.1);
                }}
                
                QCheckBox#CompactCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    border-radius: 4px;
                    border: 2px solid {primary_color};
                    background: rgba({self._hex_to_rgba(primary_color)}, 0.1);
                }}
                
                QCheckBox#CompactCheckBox::indicator:checked {{
                    background: {primary_color};
                    border: 2px solid {primary_color};
                }}
                
                QPushButton#KillButton {{
                    background: rgba(255, 0, 0, 0.2);
                    color: #ff4444;
                    border: 1px solid rgba(255, 0, 0, 0.4);
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: bold;
                    font-size: 10px;
                    margin: 2px;
                }}
                
                QPushButton#KillButton:hover {{
                    background: rgba(255, 0, 0, 0.4);
                    border-color: #ff4444;
                    color: white;
                }}
                
                QPushButton#KillButton:pressed {{
                    background: rgba(255, 0, 0, 0.6);
                }}
                
                QPushButton#GifButton {{
                    background: rgba({self._hex_to_rgba(primary_color)}, 0.2);
                    color: {primary_color};
                    border: 1px solid rgba({self._hex_to_rgba(primary_color)}, 0.4);
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: bold;
                    font-size: 10px;
                    margin: 2px;
                }}
                
                QPushButton#GifButton:hover {{
                    background: rgba({self._hex_to_rgba(primary_color)}, 0.4);
                    border-color: {primary_color};
                    color: white;
                }}
                
                QPushButton#GifButton:pressed {{
                    background: rgba({self._hex_to_rgba(primary_color)}, 0.6);
                }}
                
                QPushButton#SilentButton {{
                    background: rgba({self._hex_to_rgba(primary_color)}, 0.2);
                    color: {primary_color};
                    border: 1px solid rgba({self._hex_to_rgba(primary_color)}, 0.4);
                    border-radius: 6px;
                    padding: 6px 8px;
                    font-weight: bold;
                    font-size: 12px;
                    margin: 2px;
                    min-width: 25px;
                }}
                
                QPushButton#SilentButton:hover {{
                    background: rgba({self._hex_to_rgba(primary_color)}, 0.3);
                    border-color: rgba({self._hex_to_rgba(primary_color)}, 0.6);
                }}
                
                QPushButton#SilentButton:checked {{
                    background: {primary_color};
                    color: white;
                    border-color: {primary_color};
                }}
                
                QComboBox#PresetCombo {{
                    background: rgba({self._hex_to_rgba(primary_color)}, 0.15);
                    color: {primary_color};
                    border: 1px solid rgba({self._hex_to_rgba(primary_color)}, 0.4);
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-weight: bold;
                    font-size: 10px;
                    margin: 2px;
                }}
                
                QComboBox#PresetCombo:hover {{
                    background: rgba({self._hex_to_rgba(primary_color)}, 0.25);
                    border-color: rgba({self._hex_to_rgba(primary_color)}, 0.6);
                }}
                
                QComboBox#PresetCombo::drop-down {{
                    border: none;
                    width: 20px;
                }}
                
                QComboBox#PresetCombo::down-arrow {{
                    image: none;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 6px solid {primary_color};
                    margin-right: 4px;
                }}
                
                QComboBox#PresetCombo QAbstractItemView {{
                    background: rgba(30, 30, 30, 0.95);
                    color: {primary_color};
                    border: 1px solid rgba({self._hex_to_rgba(primary_color)}, 0.6);
                    border-radius: 4px;
                    selection-background-color: rgba({self._hex_to_rgba(primary_color)}, 0.3);
                }}
                
                QCheckBox {{
                    font-size: 16px;
                    spacing: 5px;
                }}
                
                QSlider {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(255, 255, 255, 0.08), stop:1 rgba(255, 255, 255, 0.03));
                    border: 1px solid #444;
                    border-radius: 6px;
                    padding: 4px;
                }}
                
                QSlider::groove:horizontal {{
                    height: 4px;
                    background: #333;
                    border-radius: 2px;
                }}
                
                QSlider::handle:horizontal {{
                    width: 18px;
                    height: 18px;
                    margin: -7px 0;
                    background: {primary_color};
                    border-radius: 9px;
                }}
                
                QSlider::handle:horizontal:hover {{
                    background: {secondary_color};
                }}
                
                QSlider::sub-page:horizontal {{
                    background: {primary_color};
                    border-radius: 2px;
                }}
                
                QSlider::add-page:horizontal {{
                    background: #333;
                    border-radius: 2px;
                }}
                
                QLineEdit#MinimalSearchInput {{
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba({self._hex_to_rgba(primary_color)}, 0.2);
                    border-radius: 4px;
                    padding: 6px 10px;
                    color: white;
                    font-size: 12px;
                    selection-background-color: {primary_color};
                }}
                
                QLineEdit#MinimalSearchInput:focus {{
                    border-color: rgba({self._hex_to_rgba(primary_color)}, 0.5);
                    background: rgba(255, 255, 255, 0.08);
                }}
                
                QPushButton#SearchButton {{
                    background: {primary_color};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                    font-size: 13px;
                }}
                
                QPushButton#SearchButton:hover {{
                    background: {secondary_color};
                }}
                
                QPushButton#SearchButton:pressed {{
                    background: rgba({self._hex_to_rgba(primary_color)}, 0.8);
                }}
                
                QPushButton#ClearButton {{
                    background: rgba({self._hex_to_rgba(primary_color)}, 0.2);
                    color: {primary_color};
                    border: 1px solid rgba({self._hex_to_rgba(primary_color)}, 0.4);
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 12px;
                }}
                
                QPushButton#ClearButton:hover {{
                    background: rgba({self._hex_to_rgba(primary_color)}, 0.3);
                    border-color: {primary_color};
                }}
                
                QPushButton#CategoryButton {{
                    background: rgba({self._hex_to_rgba(primary_color)}, 0.1);
                    color: {primary_color};
                    border: 1px solid rgba({self._hex_to_rgba(primary_color)}, 0.3);
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: bold;
                    font-size: 11px;
                    margin: 1px;
                }}
                
                QPushButton#CategoryButton:hover {{
                    background: rgba({self._hex_to_rgba(primary_color)}, 0.2);
                    border-color: rgba({self._hex_to_rgba(primary_color)}, 0.5);
                }}
                
                QPushButton#CategoryButton:checked {{
                    background: {primary_color};
                    color: white;
                    border-color: {primary_color};
                }}
                
                QLabel#SearchInfo {{
                    color: {secondary_color};
                    font-size: 11px;
                    font-weight: bold;
                    background: transparent;
                    border: none;
                    padding: 0px;
                }}
                
            """

            # Tab widget styles
            tab_css = f"""
                QTabWidget#MainTabWidget {{
                    background: transparent;
                    border: none;
                }}
                
                QTabWidget#MainTabWidget::pane {{
                    border: 2px solid rgba({self._hex_to_rgba(primary_color)}, 0.3);
                    border-radius: 8px;
                    background: rgba(255, 255, 255, 0.02);
                    margin-top: 5px;
                }}
                
                QTabWidget#MainTabWidget::tab-bar {{
                    alignment: center;
                }}
                
                QTabBar::tab {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba({self._hex_to_rgba(primary_color)}, 0.15),
                        stop:1 rgba({self._hex_to_rgba(primary_color)}, 0.05));
                    border: 2px solid rgba({self._hex_to_rgba(primary_color)}, 0.3);
                    border-bottom: none;
                    border-radius: 8px 8px 0px 0px;
                    padding: 8px 20px;
                    margin: 2px;
                    color: {primary_color};
                    font-weight: bold;
                    font-size: 13px;
                }}
                
                QTabBar::tab:selected {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba({self._hex_to_rgba(primary_color)}, 0.3),
                        stop:1 rgba({self._hex_to_rgba(primary_color)}, 0.1));
                    border-color: {primary_color};
                    color: white;
                }}
                
                QTabBar::tab:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba({self._hex_to_rgba(primary_color)}, 0.25),
                        stop:1 rgba({self._hex_to_rgba(primary_color)}, 0.08));
                    border-color: rgba({self._hex_to_rgba(primary_color)}, 0.6);
                }}
            """

            # Combine all styles
            full_css = theme_css + "\n" + buttons_css + "\n" + additional_css + "\n" + tab_css
            self.setStyleSheet(full_css)
            
            logger.debug("Styles loaded")
            
        except Exception as e:
            logger.error(f"Error loading styles: {e}")

    def load_wallpapers(self) -> None:
        """Loads wallpapers - with FlowLayout (safe duplicate prevention)."""
        try:
            previews = get_preview_paths()
            
            # SAFE CLEANUP - Delete existing buttons safely
            for folder_id, button in list(self.wallpaper_buttons.items()):
                try:
                    # Safely disconnect connections
                    try:
                        button.wallpaper_selected.disconnect()
                        button.add_to_playlist_requested.disconnect()
                        button.delete_wallpaper_requested.disconnect()
                    except (RuntimeError, TypeError):
                        # For already deleted widgets
                        pass
                    
                    # Safely remove from layout
                    try:
                        if button.parent():
                            button.setParent(None)
                    except RuntimeError:
                        # Widget already deleted
                        pass
                    
                    # Safely delete widget
                    try:
                        button.deleteLater()
                    except RuntimeError:
                        # Widget already deleted
                        pass
                        
                except Exception as e:
                    logger.debug(f"Widget cleanup error (normal): {e}")
            
            # Clear dictionary
            self.wallpaper_buttons.clear()
            
            # SAFELY clear layout
            while self.wallpapers_layout.count() > 0:
                child = self.wallpapers_layout.takeAt(0)
                if child and child.widget():
                    widget = child.widget()
                    try:
                        widget.setParent(None)
                        widget.deleteLater()
                    except RuntimeError:
                        # Widget already deleted
                        pass

            # get_preview_paths() already does duplicate control, extra check unnecessary
            sorted_previews = sorted(previews, key=lambda x: x[0])

            # Add new buttons to FlowLayout
            for folder_id, preview_path in sorted_previews:
                try:
                    btn = WallpaperButton(folder_id, preview_path)
                    btn.wallpaper_selected.connect(self._on_wallpaper_selected)
                    btn.add_to_playlist_requested.connect(self._on_add_to_playlist_requested)
                    btn.delete_wallpaper_requested.connect(self._on_delete_wallpaper_requested)

                    self.wallpaper_buttons[folder_id] = btn
                    self.wallpapers_layout.addWidget(btn)
                except Exception as e:
                    logger.error(f"Wallpaper button creation error ({folder_id}): {e}")

            logger.info(f"{len(sorted_previews)} wallpapers loaded in FlowLayout (safe duplicate prevention)")
            
            # Update layout
            self.wallpapers_widget.update()
            
        except Exception as e:
            logger.error(f"Error loading wallpapers: {e}")

    def _on_screen_change(self, screen_name: str) -> None:
        """Called when screen changes."""
        self.selected_screen = screen_name
        logger.debug(f"Screen changed: {screen_name}")

    def _on_volume_changed(self, volume: int) -> None:
        """Called when volume level changes - dynamic control."""
        self.vol_value_label.setText(f"{volume}%")
        
        # Dynamic volume control - change instantly if wallpaper is running
        if self.wallpaper_controller.is_wallpaper_running():
            self.wallpaper_controller.set_volume(volume)
            
        logger.debug(f"Volume level changed: {volume}%")

    def _on_fps_changed(self, fps: int) -> None:
        """Called when FPS changes - dynamic control."""
        self.fps_value_label.setText(str(fps))
        
        # Dynamic FPS control - change instantly if wallpaper is running
        if self.wallpaper_controller.is_wallpaper_running():
            success = self.wallpaper_controller.set_fps(fps)
            if not success:
                logger.warning(f"FPS could not be changed: {fps}")
            
        logger.debug(f"FPS changed: {fps}")

    def _on_wallpaper_selected(self, wallpaper_id: str) -> None:
        """Called when wallpaper is selected."""
        self.apply_wallpaper(wallpaper_id)

    def _on_add_to_playlist_requested(self, wallpaper_id: str) -> None:
        """Called when adding to playlist is requested."""
        if self.playlist_widget.add_wallpaper_to_playlist(wallpaper_id):
            # Also add to PlaylistManager and save
            self.playlist_manager.add_to_current_playlist(wallpaper_id)
            self._save_current_playlist()
            self.show_toast(f"'{wallpaper_id}' added to playlist!", DEFAULT_TOAST_DURATION)

    def _on_toggle_playlist(self) -> None:
        """Playlist play/pause toggle - sıralı/rastgele ayarına göre."""
        if self.playlist_widget.get_playlist_count() == 0:
            self.show_toast("❌ Playlist is empty!", 2000)
            return

        if self.playlist_manager.is_playing:
            # Durdur
            self.playlist_timer.stop()
            self.playlist_manager.is_playing = False
            self.playlist_widget.set_playing_state(False)
            self.show_toast("⏸️ Playlist durduruldu", 2000)
        else:
            # Başlat - mod ayarını kontrol et
            is_random = self.playlist_widget.is_random_mode()
            self.playlist_manager.is_random = is_random
            
            # İlk wallpaper'ı seç ve uygula
            if is_random:
                wallpaper_id = self.playlist_manager.get_next_wallpaper(True)  # Rastgele
                mode_text = "rastgele"
            else:
                wallpaper_id = self.playlist_manager.get_next_wallpaper(False)  # Sıralı
                mode_text = "sıralı"
            
            if wallpaper_id:
                self.apply_wallpaper(wallpaper_id)
            
            # Timer'ı başlat
            self.playlist_timer.start(self.playlist_manager.timer_interval * 1000)
            self.playlist_manager.is_playing = True
            self.playlist_widget.set_playing_state(True)
            self.show_toast(f"▶️ Playlist started ({mode_text} mod)", 2000)

    def _on_next_wallpaper(self) -> None:
        """Sonraki wallpaper'a geç."""
        if self.playlist_widget.get_playlist_count() == 0:
            return

        wallpaper_id = self.playlist_manager.get_next_wallpaper(
            self.playlist_widget.is_random_mode()
        )
        if wallpaper_id:
            self.apply_wallpaper(wallpaper_id)

    def _on_prev_wallpaper(self) -> None:
        """Önceki wallpaper'a geç."""
        if self.playlist_widget.get_playlist_count() == 0:
            return

        if not self.playlist_widget.is_random_mode():
            wallpaper_id = self.playlist_manager.get_previous_wallpaper()
            if wallpaper_id:
                self.apply_wallpaper(wallpaper_id)

    def _on_add_current_to_playlist(self) -> None:
        """Mevcut wallpaper'ı playlist'e ekle."""
        current_wallpaper = self.wallpaper_engine.current_wallpaper
        if current_wallpaper:
            if self.playlist_widget.add_wallpaper_to_playlist(current_wallpaper):
                # PlaylistManager'a da ekle ve kaydet
                self.playlist_manager.add_to_current_playlist(current_wallpaper)
                self._save_current_playlist()
                self.show_toast(f"'{current_wallpaper}' playlist'e eklendi!", 2000)
        else:
            self.show_toast("❌ Please select a wallpaper first!", 2000)

    def _on_remove_from_playlist(self) -> None:
        """Seçili wallpaper'ı playlist'ten çıkar."""
        index = self.playlist_widget.get_selected_index()
        if index >= 0:
            wallpaper_id = self.playlist_widget.remove_wallpaper_from_playlist(index)
            if wallpaper_id:
                # PlaylistManager'dan da çıkar ve kaydet
                self.playlist_manager.remove_from_current_playlist(index)
                self._save_current_playlist()
                self.show_toast(f"🗑️ '{wallpaper_id}' removed from playlist", 2000)
        else:
            self.show_toast("❌ Select item to delete!", 2000)

    def _on_clear_playlist(self) -> None:
        """Playlist'i temizle."""
        self.playlist_widget.clear_playlist()
        self.playlist_timer.stop()
        self.playlist_manager.is_playing = False
        # PlaylistManager'ı da temizle ve kaydet
        self.playlist_manager.clear_current_playlist()
        self._save_current_playlist()
        self.show_toast("🗑️ Playlist temizlendi", 2000)

    def _on_timer_interval_changed(self, interval: int) -> None:
        """Timer aralığı değiştiğinde çağrılır."""
        self.playlist_manager.timer_interval = interval
        
        # Özel timer kontrolü - sadece gerçekten özel değilse temizle
        current_text = self.playlist_widget.timer_combo.currentText()
        if not current_text.startswith("Özel:"):
            self.playlist_manager.clear_custom_timer()
        
        self.playlist_manager.save_settings()
        
        # Timer çalışıyorsa yeni interval ile yeniden başlat
        if self.playlist_manager.is_playing:
            self.playlist_timer.stop()
            self.playlist_timer.start(interval * 1000)
            logger.info(f"Timer yeniden başlatıldı: {interval} saniye ({interval/60:.1f} dakika)")

    def _on_play_mode_changed(self, is_random: bool) -> None:
        """Çalma modu değiştiğinde çağrılır."""
        self.playlist_manager.is_random = is_random
        self.playlist_manager.save_settings()

    def _on_playlist_wallpaper_selected(self, wallpaper_id: str) -> None:
        """Playlist'ten wallpaper seçildiğinde çağrılır."""
        logger.debug(f"Playlist'ten wallpaper seçildi: {wallpaper_id}")
        self.apply_wallpaper(wallpaper_id)

    def _on_kill_wallpaper_engine(self) -> None:
        """Kills wallpaper processes - Does not touch SWWW, only kills video wallpapers and restores system wallpaper."""
        try:
            import subprocess
            killed_processes = []
            
            # 1. Linux-wallpaperengine process'lerini öldür
            try:
                result = subprocess.run(['killall', 'linux-wallpaperengine'],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    killed_processes.append("linux-wallpaperengine")
                    logger.info("linux-wallpaperengine durduruldu")
            except:
                pass
            
            # 2. Video wallpaper process'lerini öldür (mpvpaper, mpv)
            video_killed = self.wallpaper_controller.stop_video_wallpaper("all")
            if video_killed:
                killed_processes.append("video wallpaper")
            
            # 3. Ek güvenlik: mpvpaper ve mpv wallpaper process'lerini direkt öldür
            try:
                # mpvpaper process'leri
                result = subprocess.run(['pkill', '-f', 'mpvpaper'],
                                      capture_output=True, timeout=3)
                if result.returncode == 0:
                    killed_processes.append("mpvpaper")
                    logger.info("mpvpaper process'leri durduruldu")
            except:
                pass
            
            try:
                # mpv wallpaper process'leri
                result = subprocess.run(['pkill', '-f', 'mpv.*wallpaper'],
                                      capture_output=True, timeout=3)
                if result.returncode == 0:
                    killed_processes.append("mpv-wallpaper")
                    logger.info("mpv wallpaper process'leri durduruldu")
            except:
                pass
            
            # ⚠️ SWWW'Yİ KILL ETMİYORUZ - Kullanıcı isteği üzerine
            # SWWW sadece GIF/video uygulandığında otomatik kill edilecek
            
            # 4. Sistem wallpaper'ını restore et (swww ile)
            self._restore_system_wallpaper()
            
            # Performance monitor'ün process referansını sıfırla
            self.performance_monitor.wallpaper_process = None
            
            # Sonuç mesajı
            if killed_processes:
                processes_text = ", ".join(killed_processes)
                self.show_toast(f"🔴 Stopped: {processes_text} (system wallpaper restored)", 4000)
                logger.info(f"Wallpaper processes stopped: {processes_text} (system wallpaper restored)")
                
                # UI'ı güncelle - current wallpaper'ı temizle
                self.playlist_widget.set_current_wallpaper(None)
                
                # TÜM wallpaper butonlarını seçili olmayan duruma getir
                try:
                    for button_id, button in self.wallpaper_buttons.items():
                        try:
                            button.set_selected(False)
                        except RuntimeError:
                            # Widget zaten silinmiş
                            pass
                    
                    # Seçili wallpaper referansını temizle
                    self.selected_wallpaper_button = None
                    
                except Exception as e:
                    logger.warning(f"Widget güncelleme hatası (normal): {e}")
                    self.selected_wallpaper_button = None
                
            else:
                self.show_toast("❌ No wallpaper processes found", 2000)
                    
        except Exception as e:
            logger.error(f"Wallpaper kill edilirken hata: {e}")
            self.show_toast(f"❌ Kill hatası: {e}", 3000)
    
    def _restore_system_wallpaper(self) -> None:
        """Sistem wallpaper'ını restore eder - mevcut swww wallpaper'ını korur."""
        try:
            import subprocess
            from pathlib import Path
            
            # ÖNCELİKLE: swww zaten çalışıyor mu ve wallpaper var mı kontrol et
            try:
                result = subprocess.run(['swww', 'query'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    # swww çalışıyor ve wallpaper var - KORUYALIM!
                    logger.info("swww zaten çalışıyor ve wallpaper mevcut - korunuyor")
                    self.show_toast("✅ Current swww wallpaper preserved", 2000)
                    return
            except:
                # swww not running, continue with restore process
                pass

            # If swww is not running, restore system wallpaper
            logger.info("swww not running, restoring system wallpaper...")
            
            # Sistem wallpaper path'lerini kontrol et
            system_wallpaper_paths = [
                Path.home() / ".config" / "wallpaper",  # General system wallpaper
                Path.home() / ".config" / "hypr" / "wallpaper.jpg",  # Hyprland
                Path.home() / ".config" / "hypr" / "wallpaper.png",
                Path.home() / ".config" / "sway" / "wallpaper.jpg",  # Sway
                Path.home() / ".config" / "sway" / "wallpaper.png",
                Path("/usr/share/backgrounds/default.jpg"),  # Sistem varsayılan
                Path("/usr/share/backgrounds/default.png"),
                Path("/usr/share/pixmaps/backgrounds/gnome/default.jpg"),  # GNOME
                Path("/usr/share/pixmaps/backgrounds/gnome/default.png"),
            ]
            
            # Mevcut wallpaper'ı bul
            system_wallpaper = None
            for path in system_wallpaper_paths:
                if path.exists() and path.is_file():
                    system_wallpaper = path
                    logger.info(f"Sistem wallpaper bulundu: {path}")
                    break
            
            if not system_wallpaper:
                # Fallback: solid color
                logger.info("Sistem wallpaper bulunamadı, solid color uygulanacak")
                try:
                    # swww daemon başlat
                    subprocess.Popen(['swww', 'init'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    import time
                    time.sleep(2)
                    
                    # swww ile solid color
                    result = subprocess.run(['swww', 'img', '--color', '#1a1a2e'],
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        logger.info("Solid color wallpaper uygulandı")
                        return
                except:
                    pass
                
                logger.warning("Sistem wallpaper restore edilemedi")
                return
            
            # Apply system wallpaper with swww
            try:
                # swww daemon başlat
                logger.info("swww daemon başlatılıyor...")
                subprocess.Popen(['swww', 'init'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                import time
                time.sleep(3)
                
                # Wallpaper uygula
                cmd = ['swww', 'img', str(system_wallpaper)]
                cmd.extend(['--transition-type', 'fade', '--transition-duration', '2'])
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                
                if result.returncode == 0:
                    logger.info(f"Sistem wallpaper restore edildi: {system_wallpaper.name}")
                    self.show_toast(f"🖼️ Sistem wallpaper restore: {system_wallpaper.name}", 3000)
                else:
                    logger.error(f"Sistem wallpaper restore hatası: {result.stderr}")
                    self.show_toast("❌ Sistem wallpaper restore hatası", 2000)
                    
            except Exception as e:
                logger.error(f"swww wallpaper uygulama hatası: {e}")
                self.show_toast("❌ Wallpaper restore hatası", 2000)
            
        except Exception as e:
            logger.error(f"Sistem wallpaper restore hatası: {e}")
            self.show_toast("❌ Restore işlemi hatası", 2000)


    def _update_ui_from_controller(self) -> None:
        """WallpaperController'dan UI kontrollerini günceller."""
        try:
            if not self.wallpaper_controller.is_wallpaper_running():
                return
                
            current_settings = self.wallpaper_controller.get_current_settings()
            
            # Volume slider ve label
            volume = current_settings.get("volume", 50)
            self.vol_slider.setValue(volume)
            self.vol_value_label.setText(f"{volume}%")
            
            # FPS slider ve label
            fps = current_settings.get("fps", 60)
            self.fps_slider.setValue(fps)
            self.fps_value_label.setText(str(fps))
            
            # Checkbox'lar
            self.noautomute_cb.setChecked(current_settings.get("noautomute", False))
            self.noaudioproc_cb.setChecked(current_settings.get("no_audio_processing", False))
            self.disable_mouse_cb.setChecked(current_settings.get("disable_mouse", False))
            
        except Exception as e:
            logger.error(f"UI güncelleme hatası: {e}")

    def _on_auto_mute_toggle(self, checked: bool) -> None:
        """Auto mute checkbox toggle edildiğinde çağrılır."""
        try:
            if self.wallpaper_controller.is_wallpaper_running():
                success = self.wallpaper_controller.toggle_auto_mute()
                if not success:
                    # Başarısızsa checkbox'ı eski haline döndür
                    self.noautomute_cb.setChecked(not checked)
                    self.show_toast("❌ Otomatik ses kısma değiştirilemedi!", 2000)
            
        except Exception as e:
            logger.error(f"Auto mute toggle hatası: {e}")
            self.noautomute_cb.setChecked(not checked)

    def _on_audio_processing_toggle(self, checked: bool) -> None:
        """Audio processing checkbox toggle edildiğinde çağrılır."""
        try:
            if self.wallpaper_controller.is_wallpaper_running():
                success = self.wallpaper_controller.toggle_audio_processing()
                if not success:
                    # Başarısızsa checkbox'ı eski haline döndür
                    self.noaudioproc_cb.setChecked(not checked)
                    self.show_toast("❌ Ses işleme değiştirilemedi!", 2000)
            
        except Exception as e:
            logger.error(f"Audio processing toggle hatası: {e}")
            self.noaudioproc_cb.setChecked(not checked)

    def _on_mouse_toggle(self, checked: bool) -> None:
        """Mouse checkbox toggle edildiğinde çağrılır."""
        try:
            if self.wallpaper_controller.is_wallpaper_running():
                success = self.wallpaper_controller.toggle_mouse()
                if not success:
                    # Başarısızsa checkbox'ı eski haline döndür
                    self.disable_mouse_cb.setChecked(not checked)
                    self.show_toast("❌ Fare etkileşimi değiştirilemedi!", 2000)
            
        except Exception as e:
            logger.error(f"Mouse toggle hatası: {e}")
            self.disable_mouse_cb.setChecked(not checked)

    def _on_tray_silent_toggle(self) -> None:
        """Sistem tray'den sessiz mod toggle."""
        try:
            success = self.wallpaper_controller.toggle_silent()
            if success:
                is_silent = self.wallpaper_controller.is_silent()
                # Volume slider'ını güncelle
                current_volume = self.wallpaper_controller.get_volume()
                self.vol_slider.setValue(current_volume)
                self.vol_value_label.setText(f"{current_volume}%")
                
                status = "açıldı" if is_silent else "kapatıldı"
                self.show_toast(f"🔇 Sessiz mod {status} (tray)", 2000)
            else:
                self.show_toast("❌ Sessiz mod değiştirilemedi!", 2000)
                
        except Exception as e:
            logger.error(f"Tray silent toggle hatası: {e}")
            self.show_toast(f"❌ Tray silent toggle hatası: {e}", 3000)

    def _on_add_gif_wallpaper(self) -> None:
        """Medya dosyası (GIF/MP4) seçip wallpaper olarak ekler - NON-BLOCKING FFmpeg Enhanced."""
        try:
            from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox
            from PySide6.QtCore import QThread, QObject, Signal
            from pathlib import Path
            import shutil
            import os
            
            # FFmpeg durumu kontrol et
            ffmpeg_available = is_ffmpeg_available()
            if ffmpeg_available:
                logger.info("✅ FFmpeg mevcut - gelişmiş medya işleme aktif")
            else:
                logger.warning("⚠️ FFmpeg bulunamadı - temel işleme modu")
            
            # Medya dosyası seçme dialogu - FFmpeg varsa daha geniş format desteği
            file_dialog = QFileDialog(self)
            file_dialog.setWindowTitle("🎬 Medya Wallpaper Seç" + (" (FFmpeg Enhanced)" if ffmpeg_available else ""))
            file_dialog.setFileMode(QFileDialog.ExistingFile)
            
            if ffmpeg_available:
                # FFmpeg ile geniş format desteği
                file_dialog.setNameFilter(
                    "Medya Dosyaları (*.gif *.mp4 *.webm *.mov *.avi *.mkv *.flv *.wmv);;Video (*.mp4 *.webm *.mov *.avi *.mkv);;GIF (*.gif);;Tüm Dosyalar (*)"
                )
            else:
                # Temel format desteği
                file_dialog.setNameFilter("Medya Dosyaları (*.gif *.mp4 *.webm *.mov);;GIF (*.gif);;Video (*.mp4 *.webm *.mov);;Tüm Dosyalar (*)")
            
            file_dialog.setViewMode(QFileDialog.Detail)
            
            if file_dialog.exec():
                selected_files = file_dialog.selectedFiles()
                if selected_files:
                    media_path = Path(selected_files[0])
                    
                    if not media_path.exists():
                        self.show_toast("❌ Selected file not found!", 3000)
                        return
                    
                    # HIZLI TEMEL KONTROLLER (UI thread'de)
                    file_size_mb = media_path.stat().st_size / (1024 * 1024)
                    
                    # Temel format kontrolü
                    if ffmpeg_available:
                        supported_formats = ['.gif', '.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv', '.wmv']
                    else:
                        supported_formats = ['.gif', '.mp4', '.webm', '.mov']
                    
                    if media_path.suffix.lower() not in supported_formats:
                        format_list = ", ".join(supported_formats).upper()
                        self.show_toast(f"❌ Desteklenen formatlar: {format_list}", 3000)
                        return
                    
                    # Kullanıcıdan isim al (FFmpeg analizi öncesi)
                    default_name = media_path.stem
                    info_text = f"📁 Dosya: {media_path.name}\n📊 Boyut: {file_size_mb:.1f} MB"
                    
                    custom_name, ok = QInputDialog.getText(
                        self,
                        "🏷️ Wallpaper İsmi",
                        f"Bu wallpaper için bir isim girin:\n\n{info_text}",
                        text=default_name
                    )
                    
                    if not ok or not custom_name.strip():
                        self.show_toast("❌ No name entered, operation cancelled", 2000)
                        return
                    
                    custom_name = custom_name.strip()
                    
                    # UI'ı bloklamadan işleme başla
                    self.show_toast("🔄 Processing media, please wait...", 2000)
                    
                    # BACKGROUND THREAD'de FFmpeg işlemlerini yap
                    self._process_media_in_background(media_path, custom_name, ffmpeg_available)
                        
        except Exception as e:
            logger.error(f"Medya ekleme hatası: {e}")
            self.show_toast(f"❌ Medya ekleme hatası: {e}", 4000)

    def _process_media_in_background(self, media_path: Path, custom_name: str, ffmpeg_available: bool) -> None:
        """Medya işlemlerini background thread'de yapar - UI bloklamaz."""
        try:
            from PySide6.QtCore import QThread, QObject, Signal
            
            # MediaProcessor worker class tanımla
            class MediaProcessor(QObject):
                finished = Signal(str)  # media_id
                error = Signal(str)     # error_message
                progress = Signal(str)  # status_message
                
                def __init__(self, media_path, custom_name, ffmpeg_available, parent_window):
                    super().__init__()
                    self.media_path = media_path
                    self.custom_name = custom_name
                    self.ffmpeg_available = ffmpeg_available
                    self.parent_window = parent_window
                
                def process(self):
                    """Background thread'de medya işleme."""
                    try:
                        # İlerleme bildirimi
                        self.progress.emit("🔄 Medya analiz ediliyor...")
                        
                        # FFmpeg ile medya analizi (sync versiyon - worker thread'de güvenli)
                        if self.ffmpeg_available:
                            media_info = self._get_media_info_sync(self.media_path)
                            
                            if media_info:
                                duration = media_info.get('duration', 0)
                                width = media_info.get('width', 0)
                                height = media_info.get('height', 0)
                                
                                # Büyük dosya uyarısı
                                file_size_mb = self.media_path.stat().st_size / (1024 * 1024)
                                if file_size_mb > 100:
                                    self.progress.emit(f"⚠️ Büyük dosya ({file_size_mb:.1f}MB) - optimizasyon önerilir")
                                
                                # Yüksek çözünürlük kontrolü
                                if width > 1920 or height > 1080:
                                    self.progress.emit(f"🔄 Yüksek çözünürlük ({width}x{height}) - optimize ediliyor...")
                                    optimize = True
                                else:
                                    optimize = False
                            else:
                                optimize = False
                        else:
                            optimize = False
                        
                        # Medya kopyalama ve işleme
                        self.progress.emit("📁 Wallpaper klasörüne kopyalanıyor...")
                        
                        if self.ffmpeg_available:
                            media_id = self._copy_media_to_wallpaper_folder_enhanced_sync(
                                self.media_path, self.custom_name, optimize
                            )
                        else:
                            media_id = self._copy_media_to_wallpaper_folder_sync(
                                self.media_path, self.custom_name
                            )
                        
                        if media_id:
                            self.finished.emit(media_id)
                        else:
                            self.error.emit("Medya kopyalama başarısız")
                            
                    except Exception as e:
                        self.error.emit(f"İşleme hatası: {e}")
                
                def _get_media_info_sync(self, media_path):
                    """Sync versiyon - worker thread için güvenli."""
                    try:
                        from utils.ffmpeg_utils import get_media_info
                        return get_media_info(media_path)
                    except Exception as e:
                        logger.error(f"Media info sync hatası: {e}")
                        return None
                
                def _copy_media_to_wallpaper_folder_enhanced_sync(self, media_path, custom_name, optimize):
                    """Enhanced sync kopyalama - worker thread için."""
                    return self.parent_window._copy_media_to_wallpaper_folder_enhanced_sync(
                        media_path, custom_name, optimize
                    )
                
                def _copy_media_to_wallpaper_folder_sync(self, media_path, custom_name):
                    """Basic sync kopyalama - worker thread için."""
                    return self.parent_window._copy_media_to_wallpaper_folder_sync(
                        media_path, custom_name
                    )
            
            # Worker thread oluştur
            self.media_thread = QThread()
            self.media_processor = MediaProcessor(media_path, custom_name, ffmpeg_available, self)
            
            # Worker'ı thread'e taşı
            self.media_processor.moveToThread(self.media_thread)
            
            # Sinyal bağlantıları
            self.media_thread.started.connect(self.media_processor.process)
            self.media_processor.finished.connect(self._on_media_processing_finished)
            self.media_processor.error.connect(self._on_media_processing_error)
            self.media_processor.progress.connect(self._on_media_processing_progress)
            
            # Cleanup bağlantıları
            self.media_processor.finished.connect(self.media_thread.quit)
            self.media_processor.error.connect(self.media_thread.quit)
            self.media_thread.finished.connect(self.media_processor.deleteLater)
            self.media_thread.finished.connect(self.media_thread.deleteLater)
            
            # Thread'i başlat
            self.media_thread.start()
            
            logger.info(f"Background medya işleme başlatıldı: {media_path.name}")
            
        except Exception as e:
            logger.error(f"Background medya işleme başlatma hatası: {e}")
            self.show_toast(f"❌ İşleme başlatma hatası: {e}", 4000)
    
    def _on_media_processing_progress(self, message: str) -> None:
        """Medya işleme ilerlemesi."""
        self.show_toast(message, 2000)
    
    def _on_media_processing_finished(self, media_id: str) -> None:
        """Medya işleme tamamlandı."""
        try:
            # Sadece metadata'yı yenile ve tek seferlik wallpaper yükleme yap
            if hasattr(self, 'metadata_manager'):
                self.metadata_manager.scan_wallpapers()
            
            # Direkt güvenli wallpaper yükleme - duplicate önlemek için
            QTimer.singleShot(100, self._safe_load_wallpapers)
            
            # Başarı mesajı
            self.show_toast(f"✅ Media successfully added: {media_id}", 3000)
            logger.info(f"Background medya işleme tamamlandı: {media_id}")
            
        except Exception as e:
            logger.error(f"Medya işleme tamamlama hatası: {e}")
    
    def _on_media_processing_error(self, error_message: str) -> None:
        """Medya işleme hatası."""
        self.show_toast(f"❌ {error_message}", 4000)
        logger.error(f"Background medya işleme hatası: {error_message}")
    
    def _safe_refresh_gallery_after_media_add(self) -> None:
        """Medya ekleme sonrası güvenli galeri yenileme."""
        try:
            # Önce metadata'yı yenile
            if hasattr(self, 'metadata_manager'):
                self.metadata_manager.scan_wallpapers()
            
            # Güvenli wallpaper yenileme - sadece bir kez
            self._safe_load_wallpapers()
            
            logger.info("Galeri güvenli şekilde yenilendi")
            
        except Exception as e:
            logger.error(f"Güvenli galeri yenileme hatası: {e}")
    
    def _safe_load_wallpapers(self) -> None:
        """Güvenli wallpaper yükleme - Layout sorunlarını önler."""
        try:
            from utils import get_preview_paths
            
            previews = get_preview_paths()
            
            # Mevcut butonları GÜVENLİ şekilde temizle
            for folder_id, button in list(self.wallpaper_buttons.items()):
                try:
                    # Sinyal bağlantılarını güvenli şekilde kes
                    try:
                        button.wallpaper_selected.disconnect()
                        button.add_to_playlist_requested.disconnect()
                        button.delete_wallpaper_requested.disconnect()
                    except (RuntimeError, TypeError):
                        # Zaten kesilmiş veya widget silinmiş
                        pass
                    
                    # Layout'tan çıkar
                    try:
                        self.wallpapers_layout.removeWidget(button)
                    except:
                        pass
                    
                    # Parent'tan güvenli şekilde çıkar
                    try:
                        if button.parent():
                            button.setParent(None)
                    except RuntimeError:
                        # Widget zaten silinmiş
                        pass
                    
                    # Widget'ı sil
                    try:
                        button.deleteLater()
                    except RuntimeError:
                        # Widget zaten silinmiş
                        pass
                        
                except Exception as e:
                    logger.debug(f"Widget temizleme hatası (normal): {e}")
            
            # Dictionary'yi temizle
            self.wallpaper_buttons.clear()
            
            # Layout'ı TAMAMEN temizle - FlowLayout için özel yaklaşım
            try:
                # Tüm item'ları tek tek çıkar
                while self.wallpapers_layout.count() > 0:
                    child = self.wallpapers_layout.takeAt(0)
                    if child and child.widget():
                        widget = child.widget()
                        try:
                            widget.setParent(None)
                            widget.deleteLater()
                        except RuntimeError:
                            # Widget zaten silinmiş
                            pass
                
                # Layout'ı yeniden başlat
                self.wallpapers_widget.update()
                
            except Exception as e:
                logger.error(f"Layout temizleme hatası: {e}")
            
            # Kısa bir bekleme - layout'un tamamen temizlenmesi için
            QTimer.singleShot(50, lambda: self._add_wallpapers_to_layout(previews))
            
        except Exception as e:
            logger.error(f"Güvenli wallpaper yükleme hatası: {e}")
    
    def _add_wallpapers_to_layout(self, previews):
        """Wallpaper'ları layout'a ekler - gecikme ile."""
        try:
            # Yeni butonları oluştur
            sorted_previews = sorted(previews, key=lambda x: x[0])
            
            for folder_id, preview_path in sorted_previews:
                try:
                    btn = WallpaperButton(folder_id, preview_path)
                    btn.wallpaper_selected.connect(self._on_wallpaper_selected)
                    btn.add_to_playlist_requested.connect(self._on_add_to_playlist_requested)
                    btn.delete_wallpaper_requested.connect(self._on_delete_wallpaper_requested)
                    
                    self.wallpaper_buttons[folder_id] = btn
                    self.wallpapers_layout.addWidget(btn)
                except Exception as e:
                    logger.error(f"Wallpaper button oluşturma hatası ({folder_id}): {e}")
            
            # Layout'ı güncelle
            self.wallpapers_widget.update()
            self.wallpapers_widget.repaint()
            
            logger.info(f"{len(sorted_previews)} wallpaper layout'a eklendi")
            
        except Exception as e:
            logger.error(f"Layout'a ekleme hatası: {e}")

    def _copy_media_to_wallpaper_folder_enhanced_sync(self, media_path: Path, custom_name: str, optimize: bool = False) -> str:
        """FFmpeg Enhanced medya kopyalama - SYNC version for worker threads."""
        try:
            import shutil
            import json
            import hashlib
            from datetime import datetime
            
            # Steam Workshop klasörü path'i
            steam_workshop_path = Path.home() / ".steam" / "steam" / "steamapps" / "workshop" / "content" / "431960"
            
            if not steam_workshop_path.exists():
                steam_workshop_path = Path.home() / ".local" / "share" / "Steam" / "steamapps" / "workshop" / "content" / "431960"
                
            if not steam_workshop_path.exists():
                logger.error(f"Steam Workshop klasörü bulunamadı: {steam_workshop_path}")
                return None
            
            # Hash bazlı sabit ID oluştur
            try:
                hash_md5 = hashlib.md5()
                with open(media_path, "rb") as f:
                    chunk = f.read(1024 * 1024)  # İlk 1MB
                    hash_md5.update(chunk)
                    file_size = media_path.stat().st_size
                    hash_md5.update(str(file_size).encode())
                
                file_hash = hash_md5.hexdigest()[:10]
                media_id = f"custom_{file_hash}"
                logger.info(f"FFmpeg Enhanced Sync: Hash ID oluşturuldu: {media_path.name} -> {media_id}")
                
            except Exception as e:
                logger.warning(f"Hash hesaplama hatası, timestamp kullanılıyor: {e}")
                timestamp = int(datetime.now().timestamp())
                media_id = f"custom_{timestamp}"
            
            # Mevcut ID kontrolü
            existing_wallpaper_path = steam_workshop_path / media_id
            if existing_wallpaper_path.exists():
                logger.warning(f"Aynı medya zaten mevcut: {media_id}")
                return media_id
            
            # Yeni wallpaper klasörü oluştur
            new_wallpaper_path = steam_workshop_path / media_id
            new_wallpaper_path.mkdir(parents=True, exist_ok=True)
            
            # FFmpeg ile medya bilgisini al (sync)
            media_info = None
            if is_ffmpeg_available():
                try:
                    from utils.ffmpeg_utils import get_media_info
                    media_info = get_media_info(media_path)
                except Exception as e:
                    logger.error(f"Media info sync hatası: {e}")
            
            # Medya dosyasını işle
            if optimize and is_ffmpeg_available() and media_info:
                # FFmpeg ile optimize et (sync)
                logger.info(f"FFmpeg optimizasyonu başlatılıyor: {media_path.name}")
                
                optimized_filename = f"{media_id}_optimized{media_path.suffix}"
                optimized_path = new_wallpaper_path / optimized_filename
                
                try:
                    success = ffmpeg_processor.optimize_for_wallpaper(media_path, optimized_path)
                    if success:
                        media_filename = optimized_filename
                        logger.info(f"FFmpeg optimizasyonu başarılı: {optimized_path}")
                    else:
                        # Optimizasyon başarısızsa orijinali kopyala
                        logger.warning("FFmpeg optimizasyonu başarısız, orijinal kopyalanıyor")
                        media_filename = f"{media_id}{media_path.suffix}"
                        dest_media_path = new_wallpaper_path / media_filename
                        shutil.copy2(media_path, dest_media_path)
                except Exception as e:
                    logger.error(f"FFmpeg optimizasyon hatası: {e}")
                    # Fallback: orijinali kopyala
                    media_filename = f"{media_id}{media_path.suffix}"
                    dest_media_path = new_wallpaper_path / media_filename
                    shutil.copy2(media_path, dest_media_path)
            else:
                # Direkt kopyala
                media_filename = f"{media_id}{media_path.suffix}"
                dest_media_path = new_wallpaper_path / media_filename
                shutil.copy2(media_path, dest_media_path)
                logger.info(f"Medya direkt kopyalandı: {dest_media_path}")
            
            # FFmpeg ile thumbnail oluştur (sync)
            thumbnail_created = False
            if is_ffmpeg_available():
                try:
                    thumbnail_path = new_wallpaper_path / "preview.jpg"
                    source_file = new_wallpaper_path / media_filename
                    
                    # Video için 1. saniyeden, GIF için ilk frame'den thumbnail al
                    timestamp = 1.0 if media_path.suffix.lower() != '.gif' else 0.1
                    
                    from utils.ffmpeg_utils import generate_thumbnail
                    success = generate_thumbnail(source_file, thumbnail_path, size=(400, 300), timestamp=timestamp)
                    if success:
                        thumbnail_created = True
                        logger.info(f"FFmpeg thumbnail oluşturuldu: {thumbnail_path}")
                    else:
                        logger.warning("FFmpeg thumbnail oluşturulamadı")
                        
                except Exception as e:
                    logger.error(f"FFmpeg thumbnail hatası: {e}")
            
            # Fallback: Medya dosyasının kendisini preview olarak kullan
            if not thumbnail_created:
                preview_path = new_wallpaper_path / f"preview{media_path.suffix}"
                shutil.copy2(media_path, preview_path)
                logger.info(f"Fallback preview oluşturuldu: {preview_path}")
            
            # Enhanced project.json oluştur
            media_type = "gif" if media_path.suffix.lower() == '.gif' else "video"
            
            project_data = {
                "description": f"FFmpeg Enhanced {media_type.upper()} Wallpaper: {custom_name}",
                "file": media_filename,
                "general": {
                    "properties": {
                        "schemecolor": {
                            "order": 0,
                            "text": "ui_browse_properties_scheme_color",
                            "type": "color",
                            "value": "0.7647058823529411 0.3764705882352941 0.07450980392156863"
                        }
                    }
                },
                "preview": "preview.jpg" if thumbnail_created else f"preview{media_path.suffix}",
                "tags": [media_type, "custom", "animated", "ffmpeg_enhanced"],
                "title": custom_name,
                "type": "scene",
                "visibility": "private"
            }
            
            # FFmpeg metadata ekle
            if media_info:
                project_data["ffmpeg_metadata"] = {
                    "duration": media_info.get("duration", 0),
                    "width": media_info.get("width", 0),
                    "height": media_info.get("height", 0),
                    "fps": media_info.get("fps", 0),
                    "format": media_info.get("format", "unknown"),
                    "video_codec": media_info.get("video_codec", "unknown"),
                    "has_audio": media_info.get("has_audio", False),
                    "optimized": optimize
                }
            
            project_json_path = new_wallpaper_path / "project.json"
            with open(project_json_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"FFmpeg Enhanced Sync wallpaper oluşturuldu: {new_wallpaper_path} -> {custom_name}")
            return media_id
            
        except Exception as e:
            logger.error(f"FFmpeg Enhanced Sync medya kopyalama hatası: {e}")
            return None

    def _copy_media_to_wallpaper_folder_sync(self, media_path: Path, custom_name: str) -> str:
        """Basic medya kopyalama - SYNC version for worker threads."""
        try:
            import shutil
            import json
            import hashlib
            from datetime import datetime
            
            # Steam Workshop klasörü path'i
            steam_workshop_path = Path.home() / ".steam" / "steam" / "steamapps" / "workshop" / "content" / "431960"
            
            if not steam_workshop_path.exists():
                steam_workshop_path = Path.home() / ".local" / "share" / "Steam" / "steamapps" / "workshop" / "content" / "431960"
                
            if not steam_workshop_path.exists():
                logger.error(f"Steam Workshop klasörü bulunamadı: {steam_workshop_path}")
                return None
            
            # Hash bazlı sabit ID oluştur
            try:
                hash_md5 = hashlib.md5()
                with open(media_path, "rb") as f:
                    chunk = f.read(1024 * 1024)  # İlk 1MB
                    hash_md5.update(chunk)
                    file_size = media_path.stat().st_size
                    hash_md5.update(str(file_size).encode())
                
                file_hash = hash_md5.hexdigest()[:10]
                media_id = f"custom_{file_hash}"
                logger.info(f"Basic Sync: Hash ID oluşturuldu: {media_path.name} -> {media_id}")
                
            except Exception as e:
                logger.warning(f"Hash hesaplama hatası, timestamp kullanılıyor: {e}")
                timestamp = int(datetime.now().timestamp())
                media_id = f"custom_{timestamp}"
            
            # Mevcut ID kontrolü
            existing_wallpaper_path = steam_workshop_path / media_id
            if existing_wallpaper_path.exists():
                logger.warning(f"Aynı medya zaten mevcut: {media_id}")
                return media_id
            
            # Yeni wallpaper klasörü oluştur
            new_wallpaper_path = steam_workshop_path / media_id
            new_wallpaper_path.mkdir(parents=True, exist_ok=True)
            
            # Medya dosyasını kopyala
            media_filename = f"{media_id}{media_path.suffix}"
            dest_media_path = new_wallpaper_path / media_filename
            shutil.copy2(media_path, dest_media_path)
            
            # Preview dosyası oluştur
            preview_path = new_wallpaper_path / f"preview{media_path.suffix}"
            shutil.copy2(media_path, preview_path)
            
            # Medya türünü belirle
            media_type = "gif" if media_path.suffix.lower() == '.gif' else "video"
            
            # project.json oluştur
            project_data = {
                "description": f"Özel {media_type.upper()} Wallpaper: {custom_name}",
                "file": media_filename,
                "general": {
                    "properties": {
                        "schemecolor": {
                            "order": 0,
                            "text": "ui_browse_properties_scheme_color",
                            "type": "color",
                            "value": "0.7647058823529411 0.3764705882352941 0.07450980392156863"
                        }
                    }
                },
                "preview": f"preview{media_path.suffix}",
                "tags": [media_type, "custom", "animated"],
                "title": custom_name,
                "type": "scene",
                "visibility": "private"
            }
            
            project_json_path = new_wallpaper_path / "project.json"
            with open(project_json_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Basic Sync wallpaper oluşturuldu: {new_wallpaper_path} -> {custom_name}")
            return media_id
            
        except Exception as e:
            logger.error(f"Basic Sync medya kopyalama hatası: {e}")
            return None

    def _copy_media_to_wallpaper_folder_enhanced(self, media_path: Path, custom_name: str, optimize: bool = False) -> str:
        """FFmpeg Enhanced medya kopyalama - thumbnail generation ve optimizasyon ile."""
        try:
            import shutil
            import json
            import hashlib
            from datetime import datetime
            
            # Steam Workshop klasörü path'i
            steam_workshop_path = Path.home() / ".steam" / "steam" / "steamapps" / "workshop" / "content" / "431960"
            
            if not steam_workshop_path.exists():
                steam_workshop_path = Path.home() / ".local" / "share" / "Steam" / "steamapps" / "workshop" / "content" / "431960"
                
            if not steam_workshop_path.exists():
                self.show_toast("❌ Steam Workshop klasörü bulunamadı!", 4000)
                logger.error(f"Steam Workshop klasörü bulunamadı: {steam_workshop_path}")
                return None
            
            # Hash bazlı sabit ID oluştur
            try:
                hash_md5 = hashlib.md5()
                with open(media_path, "rb") as f:
                    chunk = f.read(1024 * 1024)  # İlk 1MB
                    hash_md5.update(chunk)
                    file_size = media_path.stat().st_size
                    hash_md5.update(str(file_size).encode())
                
                file_hash = hash_md5.hexdigest()[:10]
                media_id = f"custom_{file_hash}"
                logger.info(f"FFmpeg Enhanced: Hash ID oluşturuldu: {media_path.name} -> {media_id}")
                
            except Exception as e:
                logger.warning(f"Hash hesaplama hatası, timestamp kullanılıyor: {e}")
                timestamp = int(datetime.now().timestamp())
                media_id = f"custom_{timestamp}"
            
            # Mevcut ID kontrolü
            existing_wallpaper_path = steam_workshop_path / media_id
            if existing_wallpaper_path.exists():
                logger.warning(f"Aynı medya zaten mevcut: {media_id}")
                self.show_toast(f"⚠️ Bu medya zaten eklenmiş: {custom_name}", 3000)
                return media_id
            
            # Yeni wallpaper klasörü oluştur
            new_wallpaper_path = steam_workshop_path / media_id
            new_wallpaper_path.mkdir(parents=True, exist_ok=True)
            
            # FFmpeg ile medya bilgisini al
            media_info = get_media_info(media_path) if is_ffmpeg_available() else None
            
            # Medya dosyasını işle
            if optimize and is_ffmpeg_available() and media_info:
                # FFmpeg ile optimize et
                logger.info(f"FFmpeg optimizasyonu başlatılıyor: {media_path.name}")
                self.show_toast(f"🔄 Medya optimize ediliyor: {custom_name}", 3000)
                
                optimized_filename = f"{media_id}_optimized{media_path.suffix}"
                optimized_path = new_wallpaper_path / optimized_filename
                
                success = ffmpeg_processor.optimize_for_wallpaper(media_path, optimized_path)
                if success:
                    media_filename = optimized_filename
                    logger.info(f"FFmpeg optimizasyonu başarılı: {optimized_path}")
                else:
                    # Optimizasyon başarısızsa orijinali kopyala
                    logger.warning("FFmpeg optimizasyonu başarısız, orijinal kopyalanıyor")
                    media_filename = f"{media_id}{media_path.suffix}"
                    dest_media_path = new_wallpaper_path / media_filename
                    shutil.copy2(media_path, dest_media_path)
            else:
                # Direkt kopyala
                media_filename = f"{media_id}{media_path.suffix}"
                dest_media_path = new_wallpaper_path / media_filename
                shutil.copy2(media_path, dest_media_path)
                logger.info(f"Medya direkt kopyalandı: {dest_media_path}")
            
            # FFmpeg ile thumbnail oluştur
            thumbnail_created = False
            if is_ffmpeg_available():
                try:
                    thumbnail_path = new_wallpaper_path / "preview.jpg"
                    source_file = new_wallpaper_path / media_filename
                    
                    # Video için 1. saniyeden, GIF için ilk frame'den thumbnail al
                    timestamp = 1.0 if media_path.suffix.lower() != '.gif' else 0.1
                    
                    success = generate_thumbnail(source_file, thumbnail_path, size=(400, 300), timestamp=timestamp)
                    if success:
                        thumbnail_created = True
                        logger.info(f"FFmpeg thumbnail oluşturuldu: {thumbnail_path}")
                    else:
                        logger.warning("FFmpeg thumbnail oluşturulamadı")
                        
                except Exception as e:
                    logger.error(f"FFmpeg thumbnail hatası: {e}")
            
            # Fallback: Medya dosyasının kendisini preview olarak kullan
            if not thumbnail_created:
                preview_path = new_wallpaper_path / f"preview{media_path.suffix}"
                shutil.copy2(media_path, preview_path)
                logger.info(f"Fallback preview oluşturuldu: {preview_path}")
            
            # Enhanced project.json oluştur
            media_type = "gif" if media_path.suffix.lower() == '.gif' else "video"
            
            project_data = {
                "description": f"FFmpeg Enhanced {media_type.upper()} Wallpaper: {custom_name}",
                "file": media_filename,
                "general": {
                    "properties": {
                        "schemecolor": {
                            "order": 0,
                            "text": "ui_browse_properties_scheme_color",
                            "type": "color",
                            "value": "0.7647058823529411 0.3764705882352941 0.07450980392156863"
                        }
                    }
                },
                "preview": "preview.jpg" if thumbnail_created else f"preview{media_path.suffix}",
                "tags": [media_type, "custom", "animated", "ffmpeg_enhanced"],
                "title": custom_name,
                "type": "scene",
                "visibility": "private"
            }
            
            # FFmpeg metadata ekle
            if media_info:
                project_data["ffmpeg_metadata"] = {
                    "duration": media_info.get("duration", 0),
                    "width": media_info.get("width", 0),
                    "height": media_info.get("height", 0),
                    "fps": media_info.get("fps", 0),
                    "format": media_info.get("format", "unknown"),
                    "video_codec": media_info.get("video_codec", "unknown"),
                    "has_audio": media_info.get("has_audio", False),
                    "optimized": optimize
                }
            
            project_json_path = new_wallpaper_path / "project.json"
            with open(project_json_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"FFmpeg Enhanced wallpaper oluşturuldu: {new_wallpaper_path} -> {custom_name}")
            return media_id
            
        except Exception as e:
            logger.error(f"FFmpeg Enhanced medya kopyalama hatası: {e}")
            return None

    def _copy_media_to_wallpaper_folder(self, media_path: Path, custom_name: str) -> str:
        """Medya dosyasını wallpaper klasörüne kopyalar ve gerekli yapıyı oluşturur.
        
        Returns:
            str: Başarılı ise media_id, başarısız ise None
        """
        try:
            import shutil
            import json
            import hashlib
            from datetime import datetime
            
            # Steam Workshop klasörü path'i
            steam_workshop_path = Path.home() / ".steam" / "steam" / "steamapps" / "workshop" / "content" / "431960"
            
            if not steam_workshop_path.exists():
                # Alternatif path dene
                steam_workshop_path = Path.home() / ".local" / "share" / "Steam" / "steamapps" / "workshop" / "content" / "431960"
                
            if not steam_workshop_path.exists():
                self.show_toast("❌ Steam Workshop klasörü bulunamadı!", 4000)
                logger.error(f"Steam Workshop klasörü bulunamadı: {steam_workshop_path}")
                return None
            
            # DOSYA HASH'İNE GÖRE SABİT ID OLUŞTUR (duplicate önlemek için)
            try:
                # Dosya hash'ini hesapla (ilk 1MB'ı kullan - hızlı)
                hash_md5 = hashlib.md5()
                with open(media_path, "rb") as f:
                    # İlk 1MB'ı oku (büyük dosyalar için hızlı)
                    chunk = f.read(1024 * 1024)
                    hash_md5.update(chunk)
                    # Dosya boyutunu da hash'e ekle
                    file_size = media_path.stat().st_size
                    hash_md5.update(str(file_size).encode())
                
                # Hash'in ilk 10 karakterini kullan
                file_hash = hash_md5.hexdigest()[:10]
                media_id = f"custom_{file_hash}"
                
                logger.info(f"Dosya hash ID oluşturuldu: {media_path.name} -> {media_id}")
                
            except Exception as e:
                logger.warning(f"Hash hesaplama hatası, timestamp kullanılıyor: {e}")
                # Fallback: timestamp
                timestamp = int(datetime.now().timestamp())
                media_id = f"custom_{timestamp}"
            
            # MEVCUT ID KONTROLÜ - Aynı medya zaten varsa uyarı ver
            existing_wallpaper_path = steam_workshop_path / media_id
            if existing_wallpaper_path.exists():
                logger.warning(f"Aynı medya zaten mevcut: {media_id}")
                self.show_toast(f"⚠️ Bu medya zaten eklenmiş: {custom_name}", 3000)
                return media_id  # Mevcut ID'yi döndür
            
            # Yeni wallpaper klasörü oluştur
            new_wallpaper_path = steam_workshop_path / media_id
            new_wallpaper_path.mkdir(parents=True, exist_ok=True)
            
            # Medya dosyasını kopyala (orijinal uzantıyı koru)
            media_filename = f"{media_id}{media_path.suffix}"
            dest_media_path = new_wallpaper_path / media_filename
            shutil.copy2(media_path, dest_media_path)
            
            # Medya türünü belirle
            media_type = "gif" if media_path.suffix.lower() == '.gif' else "video"
            
            # project.json oluştur (Wallpaper Engine formatı)
            project_data = {
                "description": f"Özel {media_type.upper()} Wallpaper: {custom_name}",
                "file": media_filename,
                "general": {
                    "properties": {
                        "schemecolor": {
                            "order": 0,
                            "text": "ui_browse_properties_scheme_color",
                            "type": "color",
                            "value": "0.7647058823529411 0.3764705882352941 0.07450980392156863"
                        }
                    }
                },
                "preview": media_filename,  # Medya dosyasının kendisi preview
                "tags": [media_type, "custom", "animated"],
                "title": custom_name,  # Kullanıcının verdiği isim
                "type": "scene",
                "visibility": "private"
            }
            
            project_json_path = new_wallpaper_path / "project.json"
            with open(project_json_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
            
            # Preview dosyası oluştur (medya dosyasının kendisi)
            preview_path = new_wallpaper_path / f"preview{media_path.suffix}"
            shutil.copy2(media_path, preview_path)
            
            logger.info(f"Özel medya wallpaper oluşturuldu: {new_wallpaper_path} -> {custom_name}")
            return media_id
            
        except Exception as e:
            logger.error(f"Medya kopyalama hatası: {e}")
            return None

    def _refresh_wallpaper_gallery(self) -> None:
        """Wallpaper galerisini düzgün şekilde yeniler - hizalama sorununu çözer."""
        try:
            # Önce metadata'yı yenile
            if hasattr(self, 'metadata_manager'):
                self.metadata_manager.scan_wallpapers()
            
            # Wallpaper'ları yenile
            self.load_wallpapers()
            
            # UI'ı güncelle
            if hasattr(self, 'wallpapers_widget'):
                self.wallpapers_widget.update()
            
            # Scroll alanını yenile
            if hasattr(self, 'wallpapers_layout'):
                self.wallpapers_layout.update()
            
            logger.info("Wallpaper galerisi başarıyla yenilendi")
            
        except Exception as e:
            logger.error(f"Galeri yenileme hatası: {e}")

    def _on_delete_wallpaper_requested(self, wallpaper_id: str) -> None:
        """Wallpaper silme isteği."""
        try:
            from PySide6.QtWidgets import QMessageBox
            
            # Sadece özel wallpaper'ları sil
            if not (wallpaper_id.startswith('custom_') or wallpaper_id.startswith('gif_')):
                self.show_toast("❌ Sadece özel eklenen medyalar silinebilir!", 3000)
                return
            
            # Onay dialogu
            reply = QMessageBox.question(
                self,
                "🗑️ Wallpaper Sil",
                f"Bu özel medyayı silmek istediğinizden emin misiniz?\n\n"
                f"🆔 ID: {wallpaper_id}\n"
                f"📝 İsim: {self.playlist_widget.get_wallpaper_name(wallpaper_id)}\n\n"
                f"⚠️ Bu işlem geri alınamaz!",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Wallpaper'ı sil
                success = self.wallpaper_controller.delete_custom_wallpaper(wallpaper_id)
                if success:
                    # Galeriyi yenile
                    self._refresh_wallpaper_gallery()
                    self.show_toast(f"🗑️ Özel medya silindi: {wallpaper_id}", 3000)
                    logger.info(f"Özel wallpaper silindi: {wallpaper_id}")
                else:
                    self.show_toast("❌ Silme işlemi başarısız!", 3000)
            
        except Exception as e:
            logger.error(f"Wallpaper silme hatası: {e}")
            self.show_toast(f"❌ Silme hatası: {e}", 4000)

    # Preset fonksiyonları kaldırıldı - gereksiz

    def _save_current_playlist(self) -> None:
        """Mevcut playlist'i 'current' adıyla kaydeder."""
        if self.playlist_manager.current_playlist:
            self.playlist_manager.create_playlist("current", self.playlist_manager.current_playlist)
        else:
            # Boşsa sil
            if "current" in self.playlist_manager.playlists:
                self.playlist_manager.delete_playlist("current")

    def _load_current_playlist(self) -> None:
        """Kaydedilmiş 'current' playlist'ini yükler."""
        if "current" in self.playlist_manager.playlists:
            saved_playlist = self.playlist_manager.playlists["current"]
            # Sadece playlist boş değilse yükle
            if saved_playlist:
                # UI'ya yükle
                for wallpaper_id in saved_playlist:
                    self.playlist_widget.add_wallpaper_to_playlist(wallpaper_id)
                # PlaylistManager'a yükle
                self.playlist_manager.current_playlist = saved_playlist.copy()
                
                # ⚠️ DİKKAT: is_playing state'ini BOZMA!
                # PlaylistManager zaten settings'ten yükledi
                print(f"[DEBUG] Playlist yüklendi - is_playing state korundu: {self.playlist_manager.is_playing}")
                logger.info(f"Kaydedilmiş playlist yüklendi: {len(saved_playlist)} wallpaper (is_playing={self.playlist_manager.is_playing})")
            else:
                logger.debug("Kaydedilmiş playlist boş, yüklenmedi")

    def _load_custom_timer_settings(self) -> None:
        """Kaydedilmiş özel timer ayarını yükler."""
        try:
            if hasattr(self, 'playlist_widget') and self.playlist_widget:
                # Playlist widget'ın parent referansını ayarla
                self.playlist_widget._parent_window = self
                # Özel timer ayarını yükle
                self.playlist_widget.load_custom_timer_from_settings()
                logger.debug("Özel timer ayarları kontrol edildi")
        except Exception as e:
            logger.error(f"Özel timer ayarları yüklenirken hata: {e}")

    def _setup_steam_workshop_monitoring(self) -> None:
        """Steam Workshop klasörü monitoring'ini kurar."""
        try:
            self.steam_watcher = SteamWorkshopWatcher(self._on_steam_wallpaper_downloaded)
            self.steam_watcher.start()
            logger.info("Steam Workshop monitoring başlatıldı")
        except Exception as e:
            logger.error(f"Steam Workshop monitoring kurulurken hata: {e}")

    def _on_steam_wallpaper_downloaded(self, workshop_id: str) -> None:
        """Steam'den wallpaper indirildiğinde çağrılır."""
        try:
            # Wallpaper listesini yenile
            self.load_wallpapers()
            
            # Toast bildirimi göster
            self.show_toast(f"🎉 Steam wallpaper indirildi: {workshop_id}", 3000)
            
            # Wallpaper galerisi sekmesine geç
            if hasattr(self, 'tab_widget'):
                self.tab_widget.setCurrentIndex(0)  # Wallpaper galerisi sekmesi
                
            logger.info(f"Steam wallpaper indirildi ve galeri güncellendi: {workshop_id}")
            
        except Exception as e:
            logger.error(f"Steam wallpaper indirme sonrası hata: {e}")

    def _on_manual_refresh(self) -> None:
        """Manuel wallpaper galerisi yenileme."""
        try:
            # Wallpaper listesini yenile
            self.load_wallpapers()
            
            # Steam watcher devre dışı - sadece galeri yenileme
            # if hasattr(self, 'steam_watcher') and self.steam_watcher:
            #     self.steam_watcher.refresh()
            
            # Toast bildirimi
            self.show_toast("🔄 Wallpaper galerisi yenilendi", 2000)
            logger.info("Manuel wallpaper galerisi yenilemesi yapıldı")
            
        except Exception as e:
            logger.error(f"Manuel yenileme hatası: {e}")
            self.show_toast("❌ Yenileme hatası!", 3000)

    def apply_wallpaper(self, wallpaper_id: str) -> bool:
        """
        Wallpaper uygular - özel medyalar için swww kullanır.
        
        Args:
            wallpaper_id: Uygulanacak wallpaper ID'si
            
        Returns:
            bool: True if application successful
        """
        try:
            # Özel medya mı kontrol et
            if wallpaper_id.startswith('custom_') or wallpaper_id.startswith('gif_'):
                success = self._apply_custom_media_wallpaper(wallpaper_id)
            else:
                # Normal wallpaper engine ile uygula
                success = self.wallpaper_engine.apply_wallpaper(
                    wallpaper_id=wallpaper_id,
                    screen=self.selected_screen,
                    volume=self.vol_slider.value(),
                    fps=self.fps_slider.value(),
                    noautomute=self.noautomute_cb.isChecked(),
                    no_audio_processing=self.noaudioproc_cb.isChecked(),
                    disable_mouse=self.disable_mouse_cb.isChecked()
                )
            
            if success:
                # UI güncelle
                self.playlist_widget.set_current_wallpaper(wallpaper_id)
                self.playlist_manager.add_to_recent(wallpaper_id)
                
                # TÜM butonları seçili olmayan duruma getir (seçili kalma sorununu çözer)
                try:
                    for button_id, button in self.wallpaper_buttons.items():
                        try:
                            button.set_selected(False)
                        except RuntimeError:
                            # Widget zaten silinmiş
                            pass
                    
                    # Seçili wallpaper referansını temizle
                    self.selected_wallpaper_button = None
                    
                except Exception as e:
                    logger.warning(f"Widget güncelleme hatası (normal): {e}")
                    self.selected_wallpaper_button = None
                
                self.wallpaper_applied.emit(wallpaper_id)
                
                # Toast mesajında wallpaper ismini göster
                wallpaper_name = self.playlist_widget.get_wallpaper_name(wallpaper_id)
                media_type = "🎬 Medya" if (wallpaper_id.startswith('custom_') or wallpaper_id.startswith('gif_')) else "🖼️"
                self.show_toast(f"✅ {media_type} {wallpaper_name}", 3000)
                return True
            else:
                self.show_toast("❌ Wallpaper uygulanamadı!", 3000)
                return False
                
        except Exception as e:
            logger.error(f"Wallpaper uygulanırken hata: {e}")
            self.show_toast(f"❌ Hata: {e}", 5000)
            return False

    def _apply_custom_media_wallpaper(self, wallpaper_id: str) -> bool:
        """Özel medya wallpaper'ını swww ile uygular."""
        try:
            from pathlib import Path
            
            # Steam Workshop klasörü path'i
            steam_workshop_path = Path.home() / ".steam" / "steam" / "steamapps" / "workshop" / "content" / "431960"
            
            if not steam_workshop_path.exists():
                steam_workshop_path = Path.home() / ".local" / "share" / "Steam" / "steamapps" / "workshop" / "content" / "431960"
            
            wallpaper_path = steam_workshop_path / wallpaper_id
            
            if not wallpaper_path.exists():
                logger.error(f"Özel medya klasörü bulunamadı: {wallpaper_path}")
                return False
            
            # Medya dosyasını bul
            media_files = []
            for ext in ['.gif', '.mp4', '.webm', '.mov']:
                media_files.extend(wallpaper_path.glob(f"*{ext}"))
            
            if not media_files:
                logger.error(f"Medya dosyası bulunamadı: {wallpaper_path}")
                return False
            
            media_file = media_files[0]  # İlk bulunan medya dosyasını kullan
            
            # Platform uyumlu medya wallpaper uygula
            success = self.wallpaper_controller.apply_media_wallpaper(
                str(media_file),
                self.selected_screen
            )
            
            if success:
                logger.info(f"Özel medya platform uyumlu şekilde uygulandı: {media_file.name}")
                return True
            else:
                logger.error(f"Platform uyumlu medya uygulama başarısız: {media_file}")
                return False
                
        except Exception as e:
            logger.error(f"Özel medya uygulama hatası: {e}")
            return False


    def show_toast(self, message: str, duration: int = 3000) -> None:
        """
        Toast bildirimi gösterir.
        
        Args:
            message: Bildirim mesajı
            duration: Gösterim süresi (ms)
        """
        try:
            if hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon.showMessage(
                    APP_NAME,
                    message,
                    QSystemTrayIcon.Information,
                    duration
                )
            self.toast_requested.emit(message, duration)
            
        except Exception as e:
            logger.error(f"Toast gösterilirken hata: {e}")

    def closeEvent(self, event) -> None:
        """Pencere kapatılırken çağrılır."""
        # Steam Workshop monitoring devre dışı
        # if hasattr(self, 'steam_watcher') and self.steam_watcher:
        #     try:
        #         self.steam_watcher.stop()
        #         logger.info("Steam Workshop monitoring durduruldu")
        #     except Exception as e:
        #         logger.error(f"Steam Workshop monitoring durdurulamadı: {e}")
        
        event.ignore()
        self.hide()
        self.show_toast("Application minimized to system tray. Wallpaper continues running.", 3000)

    def keyPressEvent(self, event) -> None:
        """Klavye olaylarını işler."""
        try:
            # Basit kısayol tuşları (sabit)
            if event.key() == Qt.Key_Space:
                self._on_toggle_playlist()
            elif event.key() == Qt.Key_Right:
                self._on_next_wallpaper()
            elif event.key() == Qt.Key_Left:
                self._on_prev_wallpaper()
            else:
                super().keyPressEvent(event)
                
        except Exception as e:
            logger.error(f"Klavye olayı işlenirken hata: {e}")
            super().keyPressEvent(event)

    def _update_performance(self) -> None:
        """Updates Wallpaper Engine and system performance information (hidden)."""
        if self.perf_visible and self.perf_label:
            try:
                # Her güncellemede process'i kontrol et (restart durumu için)
                self.performance_monitor._ensure_wallpaper_process()
                
                we_ram_mb = self.performance_monitor.get_memory_usage()
                we_cpu_percent = self.performance_monitor.get_cpu_usage()
                sys_cpu_percent = self.performance_monitor.get_system_cpu_usage()
                gpu_info = self.performance_monitor.get_gpu_info()
                
                # Wallpaper engine çalışıyor mu kontrol et
                if we_ram_mb == 0.0 and we_cpu_percent == 0.0:
                    perf_text = f"📊 WE: Stopped | SYS-CPU: {sys_cpu_percent:.1f}% | {gpu_info}"
                    # Playlist'teki "Şu an" bilgisini temizle
                    self.playlist_widget.set_current_wallpaper(None)
                else:
                    perf_text = f"📊 WE-RAM: {we_ram_mb:.1f}MB | WE-CPU: {we_cpu_percent:.1f}% | SYS-CPU: {sys_cpu_percent:.1f}% | {gpu_info}"
                
                self.perf_label.setText(perf_text)
                
            except Exception as e:
                logger.debug(f"Performans bilgisi alınırken hata: {e}")

    def _on_title_double_click(self, event: QMouseEvent) -> None:
        """Başlığa çift tık ile gizli menü."""
        if event.button() == Qt.LeftButton:
            # Performans göstergesini aç/kapat
            self.perf_visible = not self.perf_visible
            self.perf_label.setVisible(self.perf_visible)
            
            if self.perf_visible:
                self.show_toast("📊 Performans göstergesi açıldı", 2000)
                self._update_performance()
            else:
                self.show_toast("📊 Performans göstergesi kapatıldı", 2000)

    def _on_title_mouse_press(self, event: QMouseEvent) -> None:
        """Başlığa mouse basma olayları."""
        if event.button() == Qt.RightButton:
            self._on_title_right_click(event)

    def _on_title_right_click(self, event: QMouseEvent) -> None:
        """Başlığa sağ tık ile tema seçimi."""
        if event.button() == Qt.RightButton:
            theme_dialog = ThemeDialog(self)
            # Mevcut temayı seç
            theme_dialog.set_current_theme(self.current_theme)
            theme_dialog.theme_changed.connect(self._change_theme)
            theme_dialog.exec()

    def _change_theme(self, theme_id: str) -> None:
        """Temayı değiştirir."""
        if theme_id in self.theme_colors:
            self.current_theme = theme_id
            colors = self.theme_colors[theme_id]
            
            # CSS'i yeniden yükle
            self.load_styles()
            
            # Playlist widget'ını da güncelle
            if hasattr(self, 'playlist_widget'):
                self.playlist_widget.update_theme(
                    colors["primary"],
                    colors["secondary"],
                    colors.get("panel", "rgba(255, 255, 255, 0.08)")
                )
            
            
            # Temayı kaydet
            self._save_theme_setting()
            
            self.show_toast(f"🎨 Theme changed: {theme_id.title()}", 2000)
            logger.info(f"Theme changed: {theme_id}")

    def _save_theme_setting(self) -> None:
        """Tema ayarını kaydeder."""
        success = self.theme_settings.save_theme(self.current_theme)
        if not success:
            logger.warning("Tema kaydedilemedi")

    def _load_theme_setting(self) -> None:
        """Kaydedilmiş tema ayarını yükler."""
        saved_theme = self.theme_settings.load_theme()
        
        if saved_theme in self.theme_colors:
            self.current_theme = saved_theme
        else:
            logger.warning(f"Geçersiz tema: {saved_theme}, varsayılan kullanılıyor")
            self.current_theme = "default"

    def _apply_loaded_theme(self) -> None:
        """Yüklenen temayı uygular."""
        try:
            # CSS'i yeniden yükle
            self.load_styles()
            
            # Playlist widget'ını da güncelle
            if hasattr(self, 'playlist_widget') and self.playlist_widget:
                colors = self.theme_colors[self.current_theme]
                self.playlist_widget.update_theme(
                    colors["primary"],
                    colors["secondary"],
                    colors.get("panel", "rgba(255, 255, 255, 0.08)")
                )
                
            logger.debug(f"Yüklenen tema uygulandı: {self.current_theme}")
            
        except Exception as e:
            logger.error(f"Tema uygulanırken hata: {e}")




    def _detect_active_wallpaper(self) -> Optional[str]:
        """Aktif çalışan wallpaper'ı tespit eder - SADECE GERÇEK PROCESS'LERE GÜVENIR."""
        try:
            import subprocess
            import psutil
            from pathlib import Path
            
            print("[DEBUG] 🔍 ========== WALLPAPER TESPİT BAŞLADI ==========")
            logger.info("🔍 Aktif wallpaper tespiti başlatıldı")
            
            # 1. WallpaperEngine'den al (öncelik) - ama sadece process varsa
            engine_wallpaper = self.wallpaper_engine.current_wallpaper
            print(f"[DEBUG] 1️⃣ WallpaperEngine.current_wallpaper: '{engine_wallpaper}'")
            
            if engine_wallpaper:
                # Process doğrulaması yap
                if self._verify_wallpaper_process_running(engine_wallpaper):
                    logger.info(f"✅ WallpaperEngine'den tespit edildi (process verified): {engine_wallpaper}")
                    return engine_wallpaper
                else:
                    print(f"[DEBUG] ❌ WallpaperEngine wallpaper'ı için process bulunamadı: {engine_wallpaper}")
                    # WallpaperEngine'deki cached state'i temizle
                    self.wallpaper_engine.current_wallpaper = None
            
            # 2. Process tabanlı tespit - linux-wallpaperengine
            detected_from_process = self._detect_from_linux_wallpaperengine_process()
            print(f"[DEBUG] 2️⃣ Process'ten tespit: '{detected_from_process}'")
            
            if detected_from_process:
                logger.info(f"✅ Process'ten tespit edildi: {detected_from_process}")
                return detected_from_process
            
            # 3. Video wallpaper tespit - mpvpaper/mpv
            detected_video = self._detect_from_video_wallpaper_process()
            print(f"[DEBUG] 3️⃣ Video process'ten tespit: '{detected_video}'")
            
            if detected_video:
                logger.info(f"✅ Video process'ten tespit edildi: {detected_video}")
                return detected_video
            
            # 4. swww wallpaper tespit
            detected_swww = self._detect_from_swww()
            print(f"[DEBUG] 4️⃣ swww'den tespit: '{detected_swww}'")
            
            if detected_swww:
                logger.info(f"✅ swww'den tespit edildi: {detected_swww}")
                return detected_swww
            
            # 5. SON ÇARE: PlaylistManager - ama SADECE process verification ile
            playlist_current = self.playlist_manager.get_current_wallpaper()
            print(f"[DEBUG] 5️⃣ PlaylistManager'dan: '{playlist_current}'")
            
            if playlist_current:
                # KRITIK: Process doğrulaması yap - cached state'e güvenme!
                if self._verify_wallpaper_process_running(playlist_current):
                    logger.info(f"✅ PlaylistManager'dan tespit edildi (process verified): {playlist_current}")
                    return playlist_current
                else:
                    print(f"[DEBUG] ❌ PlaylistManager wallpaper'ı için process bulunamadı: {playlist_current}")
                    print(f"[DEBUG] 🧹 PlaylistManager cached state temizleniyor...")
                    
                    # PlaylistManager'daki cached state'i temizle
                    self.playlist_manager.clear_current_wallpaper()
                    self.playlist_manager.save_settings()
                    
                    logger.warning(f"PlaylistManager cached state temizlendi - process bulunamadı: {playlist_current}")
            
            logger.warning("❌ Hiçbir aktif wallpaper process'i bulunamadı")
            print("[DEBUG] ❌ Hiçbir aktif wallpaper process'i bulunamadı")
            return None
            
        except Exception as e:
            logger.error(f"Wallpaper tespit hatası: {e}")
            print(f"[DEBUG] ❌ Wallpaper tespit hatası: {e}")
            return None
    
    def _detect_from_linux_wallpaperengine_process(self) -> Optional[str]:
        """linux-wallpaperengine process'lerinden wallpaper ID'sini tespit eder."""
        try:
            import psutil
            import re
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info.get('name', '')
                    cmdline = proc_info.get('cmdline', [])
                    
                    # linux-wallpaperengine process'i mi?
                    if ('linux-wallpaperengine' in proc_name or
                        any('linux-wallpaperengine' in str(cmd) for cmd in cmdline)):
                        
                        # Cmdline'dan wallpaper ID'sini çıkar
                        cmdline_str = ' '.join(cmdline) if cmdline else ''
                        print(f"[DEBUG] 🔍 linux-wallpaperengine cmdline: {cmdline_str}")
                        
                        # Workshop ID pattern'i ara (sayısal ID)
                        workshop_pattern = r'(?:--dir\s+|/)(\d{8,12})(?:/|\s|$)'
                        match = re.search(workshop_pattern, cmdline_str)
                        
                        if match:
                            wallpaper_id = match.group(1)
                            print(f"[DEBUG] ✅ Process'ten wallpaper ID bulundu: {wallpaper_id}")
                            return wallpaper_id
                        
                        # Custom medya pattern'i ara
                        custom_pattern = r'(?:--dir\s+|/)(custom_\d+|gif_\d+)(?:/|\s|$)'
                        custom_match = re.search(custom_pattern, cmdline_str)
                        
                        if custom_match:
                            wallpaper_id = custom_match.group(1)
                            print(f"[DEBUG] ✅ Process'ten custom wallpaper ID bulundu: {wallpaper_id}")
                            return wallpaper_id
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            print("[DEBUG] ❌ linux-wallpaperengine process'i bulunamadı")
            return None
            
        except Exception as e:
            print(f"[DEBUG] ❌ Process tespit hatası: {e}")
            return None
    
    def _detect_from_video_wallpaper_process(self) -> Optional[str]:
        """mpvpaper/mpv process'lerinden video wallpaper ID'sini tespit eder."""
        try:
            import psutil
            import re
            from pathlib import Path
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info.get('name', '')
                    cmdline = proc_info.get('cmdline', [])
                    
                    # mpvpaper veya mpv wallpaper process'i mi?
                    if ('mpvpaper' in proc_name or
                        any('mpvpaper' in str(cmd) for cmd in cmdline) or
                        (proc_name == 'mpv' and any('wallpaper' in str(cmd).lower() for cmd in cmdline))):
                        
                        cmdline_str = ' '.join(cmdline) if cmdline else ''
                        print(f"[DEBUG] 🔍 Video wallpaper cmdline: {cmdline_str}")
                        
                        # Steam Workshop path'inden ID çıkar
                        workshop_pattern = r'/steamapps/workshop/content/431960/(\w+)/'
                        match = re.search(workshop_pattern, cmdline_str)
                        
                        if match:
                            wallpaper_id = match.group(1)
                            print(f"[DEBUG] ✅ Video process'ten wallpaper ID bulundu: {wallpaper_id}")
                            return wallpaper_id
                        
                        # Direkt dosya path'inden ID çıkarmaya çalış
                        for arg in cmdline:
                            if isinstance(arg, str) and '/431960/' in arg:
                                path_obj = Path(arg)
                                # Parent directory'nin adı wallpaper ID'si olabilir
                                potential_id = path_obj.parent.name
                                if potential_id and (potential_id.isdigit() or potential_id.startswith('custom_')):
                                    print(f"[DEBUG] ✅ Video path'ten wallpaper ID bulundu: {potential_id}")
                                    return potential_id
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            print("[DEBUG] ❌ Video wallpaper process'i bulunamadı")
            return None
            
        except Exception as e:
            print(f"[DEBUG] ❌ Video tespit hatası: {e}")
            return None
    
    def _verify_wallpaper_process_running(self, wallpaper_id: str) -> bool:
        """Belirtilen wallpaper ID'si için gerçekten bir process çalışıyor mu kontrol eder."""
        try:
            import psutil
            import re
            
            print(f"[DEBUG] 🔍 Process verification başlatılıyor: {wallpaper_id}")
            
            # 1. linux-wallpaperengine process'lerini kontrol et
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info.get('name', '')
                    cmdline = proc_info.get('cmdline', [])
                    
                    # linux-wallpaperengine process'i mi?
                    if ('linux-wallpaperengine' in proc_name or
                        any('linux-wallpaperengine' in str(cmd) for cmd in cmdline)):
                        
                        cmdline_str = ' '.join(cmdline) if cmdline else ''
                        
                        # Bu process belirtilen wallpaper_id'yi çalıştırıyor mu?
                        if wallpaper_id in cmdline_str:
                            print(f"[DEBUG] ✅ linux-wallpaperengine process bulundu: {wallpaper_id}")
                            return True
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            # 2. Video wallpaper process'lerini kontrol et (mpvpaper/mpv)
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info.get('name', '')
                    cmdline = proc_info.get('cmdline', [])
                    
                    # mpvpaper veya mpv wallpaper process'i mi?
                    if ('mpvpaper' in proc_name or
                        any('mpvpaper' in str(cmd) for cmd in cmdline) or
                        (proc_name == 'mpv' and any('wallpaper' in str(cmd).lower() for cmd in cmdline))):
                        
                        cmdline_str = ' '.join(cmdline) if cmdline else ''
                        
                        # Bu process belirtilen wallpaper_id'yi çalıştırıyor mu?
                        if wallpaper_id in cmdline_str:
                            print(f"[DEBUG] ✅ Video wallpaper process bulundu: {wallpaper_id}")
                            return True
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            # 3. swww ile çalışan wallpaper'ı kontrol et
            if self._is_swww_wallpaper_active(wallpaper_id):
                print(f"[DEBUG] ✅ swww wallpaper aktif: {wallpaper_id}")
                return True
            
            print(f"[DEBUG] ❌ Hiçbir process bulunamadı: {wallpaper_id}")
            return False
            
        except Exception as e:
            print(f"[DEBUG] ❌ Process verification hatası: {e}")
            return False
    
    def _detect_from_swww(self) -> Optional[str]:
        """swww'den aktif wallpaper'ı tespit eder."""
        try:
            import subprocess
            import re
            from pathlib import Path
            
            # swww query ile aktif wallpaper'ı al
            try:
                result = subprocess.run(['swww', 'query'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    output = result.stdout.strip()
                    print(f"[DEBUG] 🔍 swww query output: {output}")
                    
                    # Output'tan wallpaper path'ini çıkar
                    # Örnek: "eDP-1: /home/user/.steam/steam/steamapps/workshop/content/431960/123456789/scene.pkg"
                    lines = output.split('\n')
                    for line in lines:
                        if ':' in line and '/431960/' in line:
                            # Steam Workshop path'inden ID çıkar
                            workshop_pattern = r'/steamapps/workshop/content/431960/(\w+)/'
                            match = re.search(workshop_pattern, line)
                            
                            if match:
                                wallpaper_id = match.group(1)
                                print(f"[DEBUG] ✅ swww'den wallpaper ID bulundu: {wallpaper_id}")
                                return wallpaper_id
                            
                            # Alternatif: path'den ID çıkarmaya çalış
                            path_parts = line.split('/')
                            for i, part in enumerate(path_parts):
                                if part == '431960' and i + 1 < len(path_parts):
                                    potential_id = path_parts[i + 1]
                                    if potential_id and (potential_id.isdigit() or potential_id.startswith('custom_')):
                                        print(f"[DEBUG] ✅ swww path'ten wallpaper ID bulundu: {potential_id}")
                                        return potential_id
                    
                    print(f"[DEBUG] ❌ swww output'tan wallpaper ID çıkarılamadı")
                    return None
                else:
                    print(f"[DEBUG] ❌ swww query başarısız: {result.stderr}")
                    return None
                    
            except subprocess.TimeoutExpired:
                print(f"[DEBUG] ❌ swww query timeout")
                return None
            except FileNotFoundError:
                print(f"[DEBUG] ❌ swww komutu bulunamadı")
                return None
            
        except Exception as e:
            print(f"[DEBUG] ❌ swww tespit hatası: {e}")
            return None
    
    def _is_swww_wallpaper_active(self, wallpaper_id: str) -> bool:
        """Belirtilen wallpaper ID'si swww ile aktif mi kontrol eder."""
        try:
            detected_swww = self._detect_from_swww()
            return detected_swww == wallpaper_id
        except Exception as e:
            print(f"[DEBUG] ❌ swww aktiflik kontrolü hatası: {e}")
            return False

    def _hex_to_rgba(self, hex_color: str) -> str:
        """Hex rengi rgba formatına çevirir."""
        try:
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return f"{r}, {g}, {b}"
        except:
            return "0, 212, 255"  # Varsayılan mavi

    def _restore_app_state(self) -> None:
        """App restart sonrası state'i restore eder - GÜÇLENDİRİLMİŞ WALLPAPER TESPİTİ."""
        try:
            print("[DEBUG] ========== APP STATE RESTORE BAŞLADI ==========")
            logger.info("=== APP STATE RESTORE BAŞLADI ===")
            
            # Debug: Current state'i logla
            print(f"[DEBUG] PlaylistManager current_playlist: {len(self.playlist_manager.current_playlist)} wallpaper")
            print(f"[DEBUG] PlaylistManager is_playing: {self.playlist_manager.is_playing}")
            print(f"[DEBUG] PlaylistManager current_index: {self.playlist_manager.current_index}")
            print(f"[DEBUG] WallpaperEngine current_wallpaper: {self.wallpaper_engine.current_wallpaper}")
            
            logger.info(f"PlaylistManager current_playlist: {len(self.playlist_manager.current_playlist)} wallpaper")
            logger.info(f"PlaylistManager is_playing: {self.playlist_manager.is_playing}")
            logger.info(f"PlaylistManager current_index: {self.playlist_manager.current_index}")
            logger.info(f"WallpaperEngine current_wallpaper: {self.wallpaper_engine.current_wallpaper}")
            
            # 1. Playlist state'ini restore et
            if self.playlist_manager.current_playlist:
                logger.info(f"Playlist restore ediliyor: {len(self.playlist_manager.current_playlist)} wallpaper")
                
                # Current index'i doğrula
                if (self.playlist_manager.current_index >= len(self.playlist_manager.current_playlist) or
                    self.playlist_manager.current_index < 0):
                    logger.warning(f"Geçersiz current_index: {self.playlist_manager.current_index}, 0'a ayarlanıyor")
                    self.playlist_manager.current_index = 0
                    self.playlist_manager.save_settings()
                
                # Random mode'u restore et
                logger.info(f"Random mode restore ediliyor: {self.playlist_manager.is_random}")
                self.playlist_widget.set_random_mode(self.playlist_manager.is_random)
                
                # Playlist çalıyor muydu?
                if self.playlist_manager.is_playing:
                    logger.info("Playlist çalıyordu - timer restart ediliyor")
                    self.playlist_widget.set_playing_state(True)
                    self.playlist_timer.start(self.playlist_manager.timer_interval * 1000)
                    
                    # Current wallpaper'ı da restore et eğer varsa
                    current_in_playlist = self.playlist_manager.get_current_wallpaper()
                    if current_in_playlist:
                        logger.info(f"Playlist'ten current wallpaper restore ediliyor: {current_in_playlist}")
                        self.playlist_widget.set_current_wallpaper(current_in_playlist)
                else:
                    logger.info("Playlist durdurulmuş durumdaydı")
                    self.playlist_widget.set_playing_state(False)
            else:
                logger.info("Restore edilecek playlist yok")
            
            # 2. GÜÇLENDİRİLMİŞ WALLPAPER TESPİTİ - Çoklu yöntem
            current_wallpaper = self._detect_active_wallpaper()
            print(f"[DEBUG] Final current_wallpaper after enhanced detection: {current_wallpaper}")
            
            if current_wallpaper:
                logger.info(f"✅ DETECTED: Current wallpaper bulundu: {current_wallpaper}")
                print(f"[DEBUG] ✅ DETECTED: Current wallpaper bulundu: {current_wallpaper}")
                
                # SMART SYNC: Önce playlist durumunu kontrol et
                playlist_items = self.playlist_widget.get_playlist_items()
                wallpaper_in_playlist = current_wallpaper in playlist_items
                
                # DEBUG: Detaylı durum kontrolü
                print(f"[DEBUG] 🔍 SMART SYNC ANALYSIS:")
                print(f"[DEBUG]   - is_playing: {self.playlist_manager.is_playing}")
                print(f"[DEBUG]   - current_wallpaper: '{current_wallpaper}'")
                print(f"[DEBUG]   - playlist_items: {playlist_items}")
                print(f"[DEBUG]   - playlist_items (first 3): {playlist_items[:3] if playlist_items else []}")
                
                # ID karşılaştırması detaylı göster (tüm playlist)
                match_found_at = -1
                for i, item in enumerate(playlist_items):
                    match = item == current_wallpaper
                    if match:
                        match_found_at = i
                        print(f"[DEBUG]   - playlist[{i}]: '{item}' == '{current_wallpaper}' → ✅ MATCH!")
                    elif i < 10:  # İlk 10'unu göster
                        print(f"[DEBUG]   - playlist[{i}]: '{item}' == '{current_wallpaper}' → {match}")
                
                if match_found_at >= 0:
                    print(f"[DEBUG] ✅ FOUND AT INDEX: {match_found_at}")
                else:
                    print(f"[DEBUG] ❌ NOT FOUND in playlist")
                
                print(f"[DEBUG]   - wallpaper_in_playlist: {wallpaper_in_playlist}")
                print(f"[DEBUG]   - current_index: {self.playlist_manager.current_index}")
                
                # DOĞRU MANTIK: is_playing durumu kritik!
                if self.playlist_manager.is_playing and wallpaper_in_playlist:
                    # ✅ PLAYLIST AKTIF VE WALLPAPER PLAYLIST'TE
                    correct_index = playlist_items.index(current_wallpaper)
                    print(f"[DEBUG] 🎵 PLAYLIST MODE: Aktif playlist, index={correct_index}")
                    
                    self.playlist_manager.current_index = correct_index
                    self.playlist_manager.save_settings()
                    
                    # Continue timer
                    self.playlist_widget.set_playing_state(True)
                    self.playlist_timer.start(self.playlist_manager.timer_interval * 1000)
                    toast_msg = f"🎵 Playlist continuing: {self.playlist_widget.get_wallpaper_name(current_wallpaper)}"
                    logger.info(f"Playlist mode restored: index {correct_index}")
                    
                elif self.playlist_manager.is_playing and not wallpaper_in_playlist:
                    # ❌ PLAYLIST AKTIF AMA WALLPAPER PLAYLIST DIŞI - playlist'i durdur
                    print(f"[DEBUG] ⚠️ CONFLICT: Playlist aktifti ama wallpaper playlist dışında - durdur")
                    self.playlist_manager.is_playing = False
                    self.playlist_widget.set_playing_state(False)
                    self.playlist_timer.stop()
                    self.playlist_manager.save_settings()
                    
                    toast_msg = f"🎯 Manuel wallpaper (playlist durduruldu): {self.playlist_widget.get_wallpaper_name(current_wallpaper)}"
                    logger.info(f"Playlist conflict - stopped because wallpaper not in playlist")
                    
                else:
                    # 🎯 MANUEL MODE (playlist durmuş)
                    if wallpaper_in_playlist:
                        print(f"[DEBUG] 🎯 MANUEL: Playlist'teki wallpaper manuel çalıştırılmış")
                        toast_msg = f"🎯 Manuel (playlist'ten): {self.playlist_widget.get_wallpaper_name(current_wallpaper)}"
                    else:
                        print(f"[DEBUG] 🎯 MANUEL: Playlist dışından çalıştırılmış")
                        toast_msg = f"🎯 Manuel (galeri): {self.playlist_widget.get_wallpaper_name(current_wallpaper)}"
                    
                    # Playlist durumunu koruy (zaten durmuş)
                    self.playlist_widget.set_playing_state(False)
                    self.playlist_timer.stop()
                    
                    # Manuel mod için playlist'i de kaydet
                    self.playlist_manager.is_playing = False
                    self.playlist_manager.save_settings()
                    
                    logger.info(f"Manual mode detected: playlist stopped, current={current_wallpaper}")
                
                # UI güncelle
                self.playlist_widget.set_current_wallpaper(current_wallpaper)
                
                # Wallpaper button'ını GÜVENLİ şekilde seçili yap
                try:
                    if current_wallpaper in self.wallpaper_buttons:
                        # Önceki seçimi temizle
                        try:
                            if self.selected_wallpaper_button:
                                self.selected_wallpaper_button.set_selected(False)
                        except RuntimeError:
                            # Widget zaten silinmiş
                            pass
                        
                        # Yeni seçimi yap
                        button = self.wallpaper_buttons[current_wallpaper]
                        try:
                            button.set_selected(True)
                            self.selected_wallpaper_button = button
                            logger.info(f"Wallpaper button seçili olarak işaretlendi: {current_wallpaper}")
                            print(f"[DEBUG] ✅ Wallpaper button seçili işaretlendi: {current_wallpaper}")
                        except RuntimeError:
                            # Widget silinmiş, dictionary'den çıkar
                            del self.wallpaper_buttons[current_wallpaper]
                            self.selected_wallpaper_button = None
                            logger.warning(f"Wallpaper button silinmiş: {current_wallpaper}")
                    else:
                        logger.warning(f"Wallpaper button bulunamadı: {current_wallpaper}")
                        print(f"[DEBUG] ❌ Wallpaper button bulunamadı: {current_wallpaper}")
                        self.selected_wallpaper_button = None
                except Exception as e:
                    logger.warning(f"Wallpaper button güncelleme hatası (normal): {e}")
                    self.selected_wallpaper_button = None
                
                # Toast mesajı
                self.show_toast(toast_msg, 4000)
                print(f"[DEBUG] ✅ Toast: {toast_msg}")
                
            else:
                logger.info("❌ Çalışan wallpaper bulunamadı")
                print(f"[DEBUG] ❌ Çalışan wallpaper bulunamadı")
                self.show_toast("🔄 App başlatıldı - aktif wallpaper yok", 2000)
            
            logger.info("=== APP STATE RESTORE TAMAMLANDI ===")
            
        except Exception as e:
            logger.error(f"App state restore hatası: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.show_toast("❌ State restore hatası!", 3000)
