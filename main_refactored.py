"""
Wallpaper Engine - Template-based Refactored Version
Human cognition optimized structure for better maintainability
"""

import sys
import logging
import os
import fcntl
import atexit
from pathlib import Path
from typing import Optional, Dict, List, Tuple

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import QSettings, QTimer

from ui import MainWindow
from utils import APP_NAME, APP_VERSION, ORGANIZATION_NAME


class App:
    """
    Main application flow controller.
    By placing the flow implementations here, it becomes easy to understand "what is done and when" at a glance.
    """
    
    @staticmethod
    def Origin():
        """Main application entry point - calls functions from Flow class in sequence"""
        Flow.Origin.Check_SingleInstance()
        Flow.Origin.Initialize_Application()
        Flow.Origin.Setup_MainWindow()
        Flow.Origin.Start_EventLoop()
    
    @staticmethod
    def Emergency_Shutdown():
        """Emergency shutdown procedure"""
        Flow.Emergency.Release_Resources()
        Flow.Emergency.Clean_TempFiles()
        Flow.Emergency.Exit_Gracefully()


class Flow:
    """
    Algorithm implementations with clear, descriptive function names.
    This makes the flow readable and maintainable.
    """
    
    class Origin:
        """Main application startup flow"""
        
        @staticmethod
        def Check_SingleInstance():
            """
            Ensures only one instance of the application runs at a time.
            Uses file locking mechanism to prevent multiple instances.
            """
            _single_instance = Bundle.SingleInstance.create_instance("wallpaper_engine")
            
            if not _single_instance.acquire_lock():
                _running_pid = _single_instance.get_running_pid()
                Flow.Origin._Show_AlreadyRunning_Dialog(_running_pid)
                sys.exit(1)
            
            # Store instance for cleanup
            Alias.Runtime.single_instance = _single_instance
        
        @staticmethod
        def Initialize_Application():
            """
            Creates and configures the main QApplication instance.
            Sets up logging, application properties, and global theme.
            """
            Alias.Runtime.app = Bundle.WallpaperApp.create_application(sys.argv)
            Collect.SystemInfo.screens = Bundle.SystemUtils.get_available_screens()
            
        @staticmethod
        def Setup_MainWindow():
            """
            Creates and configures the main application window.
            Loads saved settings and initializes UI components.
            """
            Alias.Runtime.main_window = Alias.Runtime.app.get_main_window()
            Flow.Origin._Load_SavedSettings()
            Flow.Origin._Setup_SystemTray()
            
        @staticmethod
        def Start_EventLoop():
            """
            Displays the main window and starts the Qt event loop.
            Handles graceful shutdown on exit.
            """
            try:
                Alias.Runtime.app.show_main_window()
                _exit_code = Alias.Runtime.app.exec()
                Flow.Origin._Cleanup_Resources()
                sys.exit(_exit_code)
                
            except KeyboardInterrupt:
                Flow.Emergency.Handle_KeyboardInterrupt()
            except Exception as e:
                Flow.Emergency.Handle_CriticalError(e)
        
        @staticmethod
        def _Show_AlreadyRunning_Dialog(_running_pid: int):
            """Shows dialog when another instance is already running"""
            _temp_app = QApplication(sys.argv)
            _msg = Bundle.MessageBox.create_warning_dialog(
                title="Wallpaper Engine",
                text="🚫 Wallpaper Engine zaten çalışıyor!",
                info_text=Flow.Origin._Format_AlreadyRunning_Message(_running_pid)
            )
            _msg.exec()
            
        @staticmethod
        def _Format_AlreadyRunning_Message(_running_pid: int) -> str:
            """Formats the already running message with PID info"""
            if _running_pid > 0:
                return (f"Çalışan instance PID: {_running_pid}\n\n"
                       "Aynı anda birden fazla instance açmak RAM'i gereksiz yere tüketir.\n"
                       "Mevcut pencereyi kullanın veya önce onu kapatın.")
            else:
                return ("Aynı anda birden fazla instance açmak RAM'i gereksiz yere tüketir.\n"
                       "Mevcut pencereyi kullanın veya önce onu kapatın.")
        
        @staticmethod
        def _Load_SavedSettings():
            """Loads previously saved application settings"""
            Bundle.SettingsManager.load_theme_settings(Alias.Runtime.main_window)
            Bundle.SettingsManager.load_playlist_settings(Alias.Runtime.main_window)
            Bundle.SettingsManager.load_window_geometry(Alias.Runtime.main_window)
            
        @staticmethod
        def _Setup_SystemTray():
            """Configures system tray integration"""
            Bundle.SystemTray.setup_tray_icon(Alias.Runtime.main_window)
            Bundle.SystemTray.setup_tray_menu(Alias.Runtime.main_window)
            
        @staticmethod
        def _Cleanup_Resources():
            """Cleans up resources before application exit"""
            if hasattr(Alias.Runtime, 'single_instance'):
                Alias.Runtime.single_instance.release_lock()
    
    class Emergency:
        """Emergency shutdown and error handling procedures"""
        
        @staticmethod
        def Handle_KeyboardInterrupt():
            """Handles Ctrl+C graceful shutdown"""
            print("\nUygulama kullanıcı tarafından sonlandırıldı.")
            Flow.Emergency.Release_Resources()
            sys.exit(0)
            
        @staticmethod
        def Handle_CriticalError(_error: Exception):
            """Handles critical application errors"""
            print(f"Kritik hata: {_error}")
            logging.error(f"Kritik hata: {_error}", exc_info=True)
            Flow.Emergency.Release_Resources()
            sys.exit(1)
            
        @staticmethod
        def Release_Resources():
            """Releases all acquired resources"""
            if hasattr(Alias.Runtime, 'single_instance'):
                Alias.Runtime.single_instance.release_lock()
                
        @staticmethod
        def Clean_TempFiles():
            """Cleans up temporary files"""
            # Implementation for cleaning temp files
            pass
            
        @staticmethod
        def Exit_Gracefully():
            """Performs final cleanup and exits"""
            logging.info("Application shutdown completed")


class Bundle:
    """
    Wrappers and helper libraries for complex operations.
    Structured with classes for better organization.
    """
    
    class SingleInstance:
        """Single instance management wrapper"""
        
        @staticmethod
        def create_instance(_app_name: str):
            """Creates a new SingleInstance manager"""
            return _SingleInstanceManager(_app_name)
    
    class WallpaperApp:
        """QApplication wrapper with wallpaper-specific configurations"""
        
        @staticmethod
        def create_application(_argv: List[str]):
            """Creates configured WallpaperApp instance"""
            return _WallpaperApplication(_argv)
    
    class MessageBox:
        """Message dialog wrapper for consistent styling"""
        
        @staticmethod
        def create_warning_dialog(title: str, text: str, info_text: str = ""):
            """Creates a styled warning dialog"""
            _msg = QMessageBox()
            _msg.setIcon(QMessageBox.Warning)
            _msg.setWindowTitle(title)
            _msg.setText(text)
            if info_text:
                _msg.setInformativeText(info_text)
            _msg.setStandardButtons(QMessageBox.Ok)
            return _msg
    
    class SystemUtils:
        """System utility functions wrapper"""
        
        @staticmethod
        def get_available_screens() -> List[str]:
            """Gets list of available display screens"""
            from utils import get_screens
            return get_screens()
    
    class SettingsManager:
        """Application settings management wrapper"""
        
        @staticmethod
        def load_theme_settings(_main_window):
            """Loads saved theme settings"""
            # Implementation for loading theme settings
            pass
            
        @staticmethod
        def load_playlist_settings(_main_window):
            """Loads saved playlist settings"""
            # Implementation for loading playlist settings
            pass
            
        @staticmethod
        def load_window_geometry(_main_window):
            """Loads saved window geometry"""
            # Implementation for loading window geometry
            pass
    
    class SystemTray:
        """System tray integration wrapper"""
        
        @staticmethod
        def setup_tray_icon(_main_window):
            """Sets up system tray icon"""
            # Implementation for tray icon setup
            pass
            
        @staticmethod
        def setup_tray_menu(_main_window):
            """Sets up system tray context menu"""
            # Implementation for tray menu setup
            pass


class Alias:
    """
    Shared variables and communication variables used across the app.
    Provides global state management with clear naming.
    """
    
    class Runtime:
        """Runtime application state"""
        app: Optional[QApplication] = None
        main_window: Optional[MainWindow] = None
        single_instance: Optional[object] = None
        
    class Settings:
        """Application settings state"""
        current_theme: str = "default"
        window_geometry: Optional[Tuple[int, int, int, int]] = None
        last_wallpaper: Optional[str] = None
        
    class UI:
        """UI component references"""
        selected_wallpaper_button: Optional[object] = None
        performance_monitor_visible: bool = False
        
    class Wallpaper:
        """Wallpaper engine state"""
        current_wallpaper_id: Optional[str] = None
        is_playlist_playing: bool = False
        playlist_timer_interval: int = 30


class Collect:
    """
    Storage for externally obtained data and variables.
    Organized by data source for clarity.
    """
    
    class SystemInfo:
        """System information collected at runtime"""
        screens: List[str] = []
        available_wallpapers: List[Tuple[str, Path]] = []
        system_performance: Dict[str, float] = {}
        
    class UserData:
        """User-generated data and preferences"""
        playlists: Dict[str, List[str]] = {}
        recent_wallpapers: List[str] = []
        custom_settings: Dict[str, object] = {}
        
    class SteamWorkshop:
        """Steam Workshop related data"""
        workshop_items: List[Dict[str, object]] = []
        metadata_cache: Dict[str, object] = {}


# Implementation classes (internal, prefixed with _)
class _SingleInstanceManager:
    """Internal implementation of single instance management"""
    
    def __init__(self, _app_name: str):
        self._app_name = _app_name
        self._lock_file_path = Path.home() / ".config" / _app_name / f"{_app_name}.lock"
        self._lock_file = None
        self._is_locked = False
        self._lock_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def acquire_lock(self) -> bool:
        """Acquires application lock"""
        try:
            self._lock_file = open(self._lock_file_path, 'w')
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._lock_file.write(str(os.getpid()))
            self._lock_file.flush()
            self._is_locked = True
            atexit.register(self.release_lock)
            return True
        except (IOError, OSError):
            if self._lock_file:
                self._lock_file.close()
                self._lock_file = None
            return False
    
    def release_lock(self) -> None:
        """Releases application lock"""
        if self._is_locked and self._lock_file:
            try:
                fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
                self._lock_file.close()
                if self._lock_file_path.exists():
                    self._lock_file_path.unlink()
                self._is_locked = False
            except (IOError, OSError):
                pass
    
    def get_running_pid(self) -> int:
        """Gets PID of running instance"""
        try:
            if self._lock_file_path.exists():
                with open(self._lock_file_path, 'r') as f:
                    return int(f.read().strip())
        except (IOError, ValueError):
            pass
        return -1


class _WallpaperApplication(QApplication):
    """Internal implementation of wallpaper-specific QApplication"""
    
    def __init__(self, _argv: List[str]):
        super().__init__(_argv)
        self._logger = self._setup_logging()
        self._setup_application_properties()
        self._setup_global_theme()
        self._main_window = MainWindow()
        self._logger.info("Uygulama başarıyla başlatıldı")
    
    def _setup_logging(self):
        """Sets up application logging"""
        _log_dir = Path.home() / ".config" / "wallpaper_engine"
        _log_dir.mkdir(parents=True, exist_ok=True)
        _log_file = _log_dir / "wallpaper_engine.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(_log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        logging.getLogger("PySide6").setLevel(logging.WARNING)
        _logger = logging.getLogger(__name__)
        _logger.info(f"{APP_NAME} v{APP_VERSION} başlatılıyor...")
        return _logger
    
    def _setup_application_properties(self) -> None:
        """Sets up application properties"""
        self.setApplicationName(APP_NAME)
        self.setApplicationVersion(APP_VERSION)
        self.setOrganizationName(ORGANIZATION_NAME)
        QSettings.setDefaultFormat(QSettings.IniFormat)
        self._logger.debug("Uygulama özellikleri ayarlandı")
    
    def _setup_global_theme(self) -> None:
        """Sets up global dark theme"""
        try:
            self.setStyle('Fusion')
            _palette = self.palette()
            
            # Main colors
            _palette.setColor(QPalette.Window, QColor(23, 23, 35))
            _palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
            _palette.setColor(QPalette.Base, QColor(42, 42, 42))
            _palette.setColor(QPalette.AlternateBase, QColor(66, 66, 66))
            _palette.setColor(QPalette.ToolTipBase, QColor(0, 0, 0))
            _palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
            _palette.setColor(QPalette.Text, QColor(255, 255, 255))
            
            # Button colors
            _palette.setColor(QPalette.Button, QColor(53, 53, 53))
            _palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
            _palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
            
            # Selection colors
            _palette.setColor(QPalette.Link, QColor(42, 130, 218))
            _palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            _palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
            
            # Disabled colors
            _palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(127, 127, 127))
            _palette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
            _palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))
            
            self.setPalette(_palette)
            self._logger.debug("Global tema ayarlandı")
            
        except Exception as e:
            self._logger.error(f"Tema ayarlanırken hata: {e}")
    
    def show_main_window(self) -> None:
        """Shows the main window"""
        try:
            self._main_window.show()
            self._logger.info("Ana pencere gösterildi")
        except Exception as e:
            self._logger.error(f"Ana pencere gösterilirken hata: {e}")
    
    def get_main_window(self) -> MainWindow:
        """Returns main window reference"""
        return self._main_window


def main():
    """
    Main entry point.
    By calling App.Origin here, we enable a structured flow-based execution pattern.
    """
    App.Origin()


if __name__ == "__main__":
    main()