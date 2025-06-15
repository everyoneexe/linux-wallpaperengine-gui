"""
UI Management - Template-based Refactored Version
Organized UI flows and components for better maintainability
"""

import logging
import psutil
import os
from typing import Optional, Dict, List, Tuple
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


class App:
    """UI Application flow controller"""
    
    @staticmethod
    def CreateMainWindow():
        """Creates and configures the main window"""
        Flow.MainWindow.Initialize_Components()
        Flow.MainWindow.Setup_Layout()
        Flow.MainWindow.Load_Wallpapers()
        Flow.MainWindow.Connect_Signals()
        return Alias.UI.main_window
    
    @staticmethod
    def ShowPerformanceMonitor():
        """Shows/hides performance monitor"""
        Flow.Performance.Toggle_Visibility()
        Flow.Performance.Update_Display()
    
    @staticmethod
    def ChangeTheme(_theme_id: str):
        """Changes application theme"""
        Flow.Theme.Validate_Theme(_theme_id)
        Flow.Theme.Apply_Theme(_theme_id)
        Flow.Theme.Save_Theme_Setting(_theme_id)


class Flow:
    """UI algorithm implementations"""
    
    class MainWindow:
        """Main window setup and management flow"""
        
        @staticmethod
        def Initialize_Components():
            """
            Initializes all main window components.
            Creates core managers, UI widgets, and performance monitor.
            """
            # Core components
            Alias.Core.playlist_manager = PlaylistManager()
            Alias.Core.wallpaper_engine = WallpaperEngine()
            Alias.Core.wallpaper_controller = WallpaperController(Alias.Core.wallpaper_engine)
            
            # UI components
            Alias.UI.wallpaper_buttons = {}
            Alias.UI.selected_wallpaper_button = None
            
            # Settings
            Collect.SystemInfo.screens = get_screens()
            Alias.Settings.selected_screen = Collect.SystemInfo.screens[0] if Collect.SystemInfo.screens else "eDP-1"
            
            # Timers
            Alias.Runtime.playlist_timer = QTimer()
            Alias.Runtime.playlist_timer.timeout.connect(Flow.Playlist.Next_Wallpaper)
            
            # Performance monitor
            Alias.Runtime.performance_monitor = Bundle.PerformanceMonitor.create_monitor()
            Alias.Runtime.perf_timer = QTimer()
            Alias.Runtime.perf_timer.timeout.connect(Flow.Performance.Update_Display)
            Alias.Runtime.perf_timer.start(2000)  # 2 second intervals
            
            # Theme system
            Alias.UI.theme_settings = Bundle.ThemeManager.create_settings_manager()
            Flow.Theme.Load_Current_Theme()
        
        @staticmethod
        def Setup_Layout():
            """
            Sets up the main window layout structure.
            Creates tabbed interface with wallpaper gallery and Steam browser.
            """
            _main_window = Bundle.MainWindow.create_window()
            Alias.UI.main_window = _main_window
            
            # Create main layout components
            Flow.MainWindow._Create_Header_Section()
            Flow.MainWindow._Create_Tabbed_Interface()
            Flow.MainWindow._Create_Playlist_Panel()
            Flow.MainWindow._Apply_Styles()
        
        @staticmethod
        def Load_Wallpapers():
            """
            Loads wallpaper previews and creates wallpaper buttons.
            Organizes wallpapers in flow layout for responsive design.
            """
            _previews = get_preview_paths()
            Alias.UI.wallpaper_buttons.clear()
            
            # Sort wallpapers for consistent ordering
            _previews.sort(key=lambda x: x[0])
            
            for _folder_id, _preview_path in _previews:
                _btn = Bundle.WallpaperButton.create_button(_folder_id, _preview_path)
                _btn.wallpaper_selected.connect(Flow.Wallpaper.Select_Wallpaper)
                _btn.add_to_playlist_requested.connect(Flow.Playlist.Add_To_Playlist)
                
                Alias.UI.wallpaper_buttons[_folder_id] = _btn
                Flow.MainWindow._Add_Wallpaper_To_Layout(_btn)
            
            logging.info(f"{len(_previews)} wallpapers loaded")
        
        @staticmethod
        def Connect_Signals():
            """
            Connects all UI signals to their respective handlers.
            Establishes communication between UI components.
            """
            # Playlist widget connections
            _playlist_widget = Alias.UI.playlist_widget
            _playlist_widget.play_pause_requested.connect(Flow.Playlist.Toggle_Playback)
            _playlist_widget.next_requested.connect(Flow.Playlist.Next_Wallpaper)
            _playlist_widget.prev_requested.connect(Flow.Playlist.Previous_Wallpaper)
            _playlist_widget.add_current_requested.connect(Flow.Playlist.Add_Current_To_Playlist)
            _playlist_widget.remove_selected_requested.connect(Flow.Playlist.Remove_From_Playlist)
            _playlist_widget.clear_playlist_requested.connect(Flow.Playlist.Clear_Playlist)
            _playlist_widget.timer_interval_changed.connect(Flow.Playlist.Change_Timer_Interval)
            _playlist_widget.play_mode_changed.connect(Flow.Playlist.Change_Play_Mode)
            _playlist_widget.wallpaper_selected.connect(Flow.Wallpaper.Select_From_Playlist)
        
        @staticmethod
        def _Create_Header_Section():
            """Creates the header section with title and controls"""
            # Implementation details moved to Bundle
            Bundle.HeaderSection.create_title_section()
            Bundle.HeaderSection.create_toolbar_section()
            Bundle.HeaderSection.create_search_section()
        
        @staticmethod
        def _Create_Tabbed_Interface():
            """Creates the tabbed interface for wallpapers and Steam browser"""
            Bundle.TabbedInterface.create_wallpaper_tab()
            Bundle.TabbedInterface.create_steam_browser_tab()
        
        @staticmethod
        def _Create_Playlist_Panel():
            """Creates the playlist management panel"""
            Alias.UI.playlist_widget = Bundle.PlaylistPanel.create_playlist_widget()
        
        @staticmethod
        def _Apply_Styles():
            """Applies CSS styles based on current theme"""
            Flow.Theme.Apply_Current_Styles()
        
        @staticmethod
        def _Add_Wallpaper_To_Layout(_btn):
            """Adds wallpaper button to the layout"""
            Bundle.WallpaperLayout.add_button_to_flow_layout(_btn)
    
    class Theme:
        """Theme management flow"""
        
        @staticmethod
        def Load_Current_Theme():
            """
            Loads the currently saved theme from settings.
            Falls back to default theme if none found.
            """
            _saved_theme = Alias.UI.theme_settings.load_theme()
            if _saved_theme in Collect.ThemeData.available_themes:
                Alias.Settings.current_theme = _saved_theme
            else:
                Alias.Settings.current_theme = "default"
                logging.warning(f"Invalid theme: {_saved_theme}, using default")
        
        @staticmethod
        def Validate_Theme(_theme_id: str) -> bool:
            """Validates if theme exists"""
            return _theme_id in Collect.ThemeData.available_themes
        
        @staticmethod
        def Apply_Theme(_theme_id: str):
            """
            Applies the specified theme to all UI components.
            Updates colors, styles, and visual elements.
            """
            if not Flow.Theme.Validate_Theme(_theme_id):
                logging.error(f"Invalid theme: {_theme_id}")
                return
            
            Alias.Settings.current_theme = _theme_id
            _colors = Collect.ThemeData.theme_colors[_theme_id]
            
            # Apply to main window
            Bundle.StyleManager.apply_main_window_styles(_colors)
            
            # Apply to playlist widget
            if hasattr(Alias.UI, 'playlist_widget'):
                Bundle.StyleManager.apply_playlist_styles(Alias.UI.playlist_widget, _colors)
            
            logging.info(f"Theme applied: {_theme_id}")
        
        @staticmethod
        def Apply_Current_Styles():
            """Applies styles for the current theme"""
            Flow.Theme.Apply_Theme(Alias.Settings.current_theme)
        
        @staticmethod
        def Save_Theme_Setting(_theme_id: str):
            """Saves theme setting to persistent storage"""
            _success = Alias.UI.theme_settings.save_theme(_theme_id)
            if not _success:
                logging.warning("Failed to save theme setting")
    
    class Performance:
        """Performance monitoring flow"""
        
        @staticmethod
        def Toggle_Visibility():
            """
            Toggles performance monitor visibility.
            Shows/hides system resource usage information.
            """
            Alias.UI.perf_visible = not getattr(Alias.UI, 'perf_visible', False)
            
            if hasattr(Alias.UI, 'perf_label'):
                Alias.UI.perf_label.setVisible(Alias.UI.perf_visible)
            
            _status = "açıldı" if Alias.UI.perf_visible else "kapatıldı"
            Bundle.ToastManager.show_toast(f"📊 Performans göstergesi {_status}", 2000)
        
        @staticmethod
        def Update_Display():
            """
            Updates performance display with current system metrics.
            Shows wallpaper engine and system resource usage.
            """
            if not getattr(Alias.UI, 'perf_visible', False):
                return
            
            if not hasattr(Alias.UI, 'perf_label'):
                return
            
            try:
                _monitor = Alias.Runtime.performance_monitor
                _we_ram = _monitor.get_memory_usage()
                _we_cpu = _monitor.get_cpu_usage()
                _sys_cpu = _monitor.get_system_cpu_usage()
                _gpu_info = _monitor.get_gpu_info()
                
                if _we_ram == 0.0 and _we_cpu == 0.0:
                    _perf_text = f"📊 WE: Stopped | SYS-CPU: {_sys_cpu:.1f}% | {_gpu_info}"
                    # Clear current wallpaper info
                    if hasattr(Alias.UI, 'playlist_widget'):
                        Alias.UI.playlist_widget.set_current_wallpaper(None)
                else:
                    _perf_text = f"📊 WE-RAM: {_we_ram:.1f}MB | WE-CPU: {_we_cpu:.1f}% | SYS-CPU: {_sys_cpu:.1f}% | {_gpu_info}"
                
                Alias.UI.perf_label.setText(_perf_text)
                
            except Exception as e:
                logging.debug(f"Performance update error: {e}")
    
    class Playlist:
        """Playlist management flow"""
        
        @staticmethod
        def Toggle_Playback():
            """
            Toggles playlist playback state.
            Starts or stops automatic wallpaper switching.
            """
            if Alias.UI.playlist_widget.get_playlist_count() == 0:
                Bundle.ToastManager.show_toast("❌ Playlist boş!", 2000)
                return
            
            if Alias.Core.playlist_manager.is_playing:
                Flow.Playlist._Stop_Playback()
            else:
                Flow.Playlist._Start_Playback()
        
        @staticmethod
        def _Start_Playback():
            """Starts playlist playback"""
            _is_random = Alias.UI.playlist_widget.is_random_mode()
            Alias.Core.playlist_manager.is_random = _is_random
            
            _wallpaper_id = Alias.Core.playlist_manager.get_next_wallpaper(_is_random)
            if _wallpaper_id:
                Flow.Wallpaper.Apply_Wallpaper(_wallpaper_id)
            
            Alias.Runtime.playlist_timer.start(Alias.Core.playlist_manager.timer_interval * 1000)
            Alias.Core.playlist_manager.is_playing = True
            Alias.UI.playlist_widget.set_playing_state(True)
            
            _mode_text = "rastgele" if _is_random else "sıralı"
            Bundle.ToastManager.show_toast(f"▶️ Playlist başlatıldı ({_mode_text} mod)", 2000)
        
        @staticmethod
        def _Stop_Playback():
            """Stops playlist playback"""
            Alias.Runtime.playlist_timer.stop()
            Alias.Core.playlist_manager.is_playing = False
            Alias.UI.playlist_widget.set_playing_state(False)
            Bundle.ToastManager.show_toast("⏸️ Playlist durduruldu", 2000)
        
        @staticmethod
        def Next_Wallpaper():
            """Switches to next wallpaper in playlist"""
            if Alias.UI.playlist_widget.get_playlist_count() == 0:
                return
            
            _wallpaper_id = Alias.Core.playlist_manager.get_next_wallpaper(
                Alias.UI.playlist_widget.is_random_mode()
            )
            if _wallpaper_id:
                Flow.Wallpaper.Apply_Wallpaper(_wallpaper_id)
        
        @staticmethod
        def Previous_Wallpaper():
            """Switches to previous wallpaper in playlist"""
            if Alias.UI.playlist_widget.get_playlist_count() == 0:
                return
            
            if not Alias.UI.playlist_widget.is_random_mode():
                _wallpaper_id = Alias.Core.playlist_manager.get_previous_wallpaper()
                if _wallpaper_id:
                    Flow.Wallpaper.Apply_Wallpaper(_wallpaper_id)
        
        @staticmethod
        def Add_To_Playlist(_wallpaper_id: str):
            """Adds wallpaper to current playlist"""
            if Alias.UI.playlist_widget.add_wallpaper_to_playlist(_wallpaper_id):
                Alias.Core.playlist_manager.add_to_current_playlist(_wallpaper_id)
                Flow.Playlist._Save_Current_Playlist()
                Bundle.ToastManager.show_toast(f"'{_wallpaper_id}' playlist'e eklendi!", 2000)
        
        @staticmethod
        def Add_Current_To_Playlist():
            """Adds currently playing wallpaper to playlist"""
            _current_wallpaper = Alias.Core.wallpaper_engine.current_wallpaper
            if _current_wallpaper:
                Flow.Playlist.Add_To_Playlist(_current_wallpaper)
            else:
                Bundle.ToastManager.show_toast("❌ Önce bir wallpaper seçin!", 2000)
        
        @staticmethod
        def Remove_From_Playlist():
            """Removes selected wallpaper from playlist"""
            _index = Alias.UI.playlist_widget.get_selected_index()
            if _index >= 0:
                _wallpaper_id = Alias.UI.playlist_widget.remove_wallpaper_from_playlist(_index)
                if _wallpaper_id:
                    Alias.Core.playlist_manager.remove_from_current_playlist(_index)
                    Flow.Playlist._Save_Current_Playlist()
                    Bundle.ToastManager.show_toast(f"🗑️ '{_wallpaper_id}' playlist'ten kaldırıldı", 2000)
            else:
                Bundle.ToastManager.show_toast("❌ Silinecek öğe seçin!", 2000)
        
        @staticmethod
        def Clear_Playlist():
            """Clears entire playlist"""
            Alias.UI.playlist_widget.clear_playlist()
            Alias.Runtime.playlist_timer.stop()
            Alias.Core.playlist_manager.is_playing = False
            Alias.Core.playlist_manager.clear_current_playlist()
            Flow.Playlist._Save_Current_Playlist()
            Bundle.ToastManager.show_toast("🗑️ Playlist temizlendi", 2000)
        
        @staticmethod
        def Change_Timer_Interval(_interval: int):
            """Changes playlist timer interval"""
            Alias.Core.playlist_manager.timer_interval = _interval
            Alias.Core.playlist_manager.save_settings()
            
            if Alias.Core.playlist_manager.is_playing:
                Alias.Runtime.playlist_timer.stop()
                Alias.Runtime.playlist_timer.start(_interval * 1000)
                logging.info(f"Timer restarted: {_interval} seconds")
        
        @staticmethod
        def Change_Play_Mode(_is_random: bool):
            """Changes playlist play mode (random/sequential)"""
            Alias.Core.playlist_manager.is_random = _is_random
            Alias.Core.playlist_manager.save_settings()
        
        @staticmethod
        def _Save_Current_Playlist():
            """Saves current playlist to persistent storage"""
            if Alias.Core.playlist_manager.current_playlist:
                Alias.Core.playlist_manager.create_playlist("current", Alias.Core.playlist_manager.current_playlist)
            else:
                if "current" in Alias.Core.playlist_manager.playlists:
                    Alias.Core.playlist_manager.delete_playlist("current")
    
    class Wallpaper:
        """Wallpaper management flow"""
        
        @staticmethod
        def Select_Wallpaper(_wallpaper_id: str):
            """
            Selects and applies a wallpaper.
            Updates UI state and applies wallpaper to desktop.
            """
            Flow.Wallpaper.Apply_Wallpaper(_wallpaper_id)
        
        @staticmethod
        def Select_From_Playlist(_wallpaper_id: str):
            """Selects wallpaper from playlist"""
            logging.debug(f"Wallpaper selected from playlist: {_wallpaper_id}")
            Flow.Wallpaper.Apply_Wallpaper(_wallpaper_id)
        
        @staticmethod
        def Apply_Wallpaper(_wallpaper_id: str) -> bool:
            """
            Applies wallpaper with current settings.
            Updates UI state and shows feedback to user.
            """
            try:
                _success = Alias.Core.wallpaper_engine.apply_wallpaper(
                    wallpaper_id=_wallpaper_id,
                    screen=Alias.Settings.selected_screen,
                    volume=Bundle.UIControls.get_volume_value(),
                    fps=Bundle.UIControls.get_fps_value(),
                    noautomute=Bundle.UIControls.get_noautomute_state(),
                    no_audio_processing=Bundle.UIControls.get_noaudioproc_state(),
                    disable_mouse=Bundle.UIControls.get_disable_mouse_state()
                )
                
                if _success:
                    Flow.Wallpaper._Update_UI_State(_wallpaper_id)
                    _wallpaper_name = Bundle.WallpaperUtils.get_wallpaper_display_name(_wallpaper_id)
                    Bundle.ToastManager.show_toast(f"✅ {_wallpaper_name}", 3000)
                    return True
                else:
                    Bundle.ToastManager.show_toast("❌ Wallpaper uygulanamadı!", 3000)
                    return False
                    
            except Exception as e:
                logging.error(f"Wallpaper application error: {e}")
                Bundle.ToastManager.show_toast(f"❌ Hata: {e}", 5000)
                return False
        
        @staticmethod
        def _Update_UI_State(_wallpaper_id: str):
            """Updates UI state after wallpaper application"""
            # Update playlist widget
            Alias.UI.playlist_widget.set_current_wallpaper(_wallpaper_id)
            Alias.Core.playlist_manager.add_to_recent(_wallpaper_id)
            
            # Update selected button
            if Alias.UI.selected_wallpaper_button:
                Alias.UI.selected_wallpaper_button.set_selected(False)
            
            if _wallpaper_id in Alias.UI.wallpaper_buttons:
                Alias.UI.selected_wallpaper_button = Alias.UI.wallpaper_buttons[_wallpaper_id]
                Alias.UI.selected_wallpaper_button.set_selected(True)


class Bundle:
    """UI component wrappers and helper utilities"""
    
    class MainWindow:
        """Main window creation and management"""
        
        @staticmethod
        def create_window():
            """Creates the main application window"""
            # Import here to avoid circular imports
            from ui.main_window import MainWindow
            return MainWindow()
    
    class PerformanceMonitor:
        """Performance monitoring wrapper"""
        
        @staticmethod
        def create_monitor():
            """Creates performance monitor instance"""
            # Import here to avoid circular imports
            from ui.main_window import PerformanceMonitor
            return PerformanceMonitor()
    
    class ThemeManager:
        """Theme management wrapper"""
        
        @staticmethod
        def create_settings_manager():
            """Creates theme settings manager"""
            # Import here to avoid circular imports
            from ui.main_window import ThemeSettingsManager
            return ThemeSettingsManager()
    
    class WallpaperButton:
        """Wallpaper button creation wrapper"""
        
        @staticmethod
        def create_button(_folder_id: str, _preview_path: Path):
            """Creates wallpaper button widget"""
            from ui.wallpaper_button import WallpaperButton
            return WallpaperButton(_folder_id, _preview_path)
    
    class PlaylistPanel:
        """Playlist panel creation wrapper"""
        
        @staticmethod
        def create_playlist_widget():
            """Creates playlist widget"""
            from ui.playlist_widget import PlaylistWidget
            return PlaylistWidget()
    
    class ToastManager:
        """Toast notification wrapper"""
        
        @staticmethod
        def show_toast(_message: str, _duration: int = 3000):
            """Shows toast notification"""
            if hasattr(Alias.UI, 'main_window'):
                Alias.UI.main_window.show_toast(_message, _duration)
    
    class UIControls:
        """UI control value getters"""
        
        @staticmethod
        def get_volume_value() -> int:
            """Gets current volume slider value"""
            if hasattr(Alias.UI, 'main_window'):
                return Alias.UI.main_window.vol_slider.value()
            return DEFAULT_VOLUME
        
        @staticmethod
        def get_fps_value() -> int:
            """Gets current FPS slider value"""
            if hasattr(Alias.UI, 'main_window'):
                return Alias.UI.main_window.fps_slider.value()
            return DEFAULT_FPS
        
        @staticmethod
        def get_noautomute_state() -> bool:
            """Gets no auto mute checkbox state"""
            if hasattr(Alias.UI, 'main_window'):
                return Alias.UI.main_window.noautomute_cb.isChecked()
            return False
        
        @staticmethod
        def get_noaudioproc_state() -> bool:
            """Gets no audio processing checkbox state"""
            if hasattr(Alias.UI, 'main_window'):
                return Alias.UI.main_window.noaudioproc_cb.isChecked()
            return False
        
        @staticmethod
        def get_disable_mouse_state() -> bool:
            """Gets disable mouse checkbox state"""
            if hasattr(Alias.UI, 'main_window'):
                return Alias.UI.main_window.disable_mouse_cb.isChecked()
            return False
    
    class WallpaperUtils:
        """Wallpaper utility functions"""
        
        @staticmethod
        def get_wallpaper_display_name(_wallpaper_id: str) -> str:
            """Gets display name for wallpaper"""
            if hasattr(Alias.UI, 'playlist_widget'):
                return Alias.UI.playlist_widget.get_wallpaper_name(_wallpaper_id)
            return _wallpaper_id
    
    class HeaderSection:
        """Header section creation"""
        
        @staticmethod
        def create_title_section():
            """Creates title section with performance monitor"""
            # Implementation delegated to existing main window
            pass
        
        @staticmethod
        def create_toolbar_section():
            """Creates toolbar with controls"""
            # Implementation delegated to existing main window
            pass
        
        @staticmethod
        def create_search_section():
            """Creates search input section"""
            # Implementation delegated to existing main window
            pass
    
    class TabbedInterface:
        """Tabbed interface creation"""
        
        @staticmethod
        def create_wallpaper_tab():
            """Creates wallpaper gallery tab"""
            # Implementation delegated to existing main window
            pass
        
        @staticmethod
        def create_steam_browser_tab():
            """Creates Steam Workshop browser tab"""
            # Implementation delegated to existing main window
            pass
    
    class WallpaperLayout:
        """Wallpaper layout management"""
        
        @staticmethod
        def add_button_to_flow_layout(_btn):
            """Adds button to flow layout"""
            if hasattr(Alias.UI, 'main_window') and hasattr(Alias.UI.main_window, 'wallpapers_layout'):
                Alias.UI.main_window.wallpapers_layout.addWidget(_btn)
    
    class StyleManager:
        """Style management utilities"""
        
        @staticmethod
        def apply_main_window_styles(_colors: Dict[str, str]):
            """Applies styles to main window"""
            if hasattr(Alias.UI, 'main_window'):
                Alias.UI.main_window.load_styles()
        
        @staticmethod
        def apply_playlist_styles(_playlist_widget, _colors: Dict[str, str]):
            """Applies styles to playlist widget"""
            _playlist_widget.update_theme(
                _colors["primary"],
                _colors["secondary"],
                _colors.get("panel", "rgba(255, 255, 255, 0.08)")
            )


class Alias:
    """Shared UI variables and state management"""
    
    class UI:
        """UI component references"""
        main_window: Optional[QWidget] = None
        playlist_widget: Optional[QWidget] = None
        wallpaper_buttons: Dict[str, QWidget] = {}
        selected_wallpaper_button: Optional[QWidget] = None
        theme_settings: Optional[object] = None
        perf_label: Optional[QLabel] = None
        perf_visible: bool = False
    
    class Core:
        """Core component references"""
        playlist_manager: Optional[PlaylistManager] = None
        wallpaper_engine: Optional[WallpaperEngine] = None
        wallpaper_controller: Optional[WallpaperController] = None
    
    class Runtime:
        """Runtime state"""
        playlist_timer: Optional[QTimer] = None
        performance_monitor: Optional[object] = None
        perf_timer: Optional[QTimer] = None
    
    class Settings:
        """UI settings state"""
        current_theme: str = "default"
        selected_screen: str = "eDP-1"


class Collect:
    """UI-related data collection"""
    
    class SystemInfo:
        """System information for UI"""
        screens: List[str] = []
        wallpaper_previews: List[Tuple[str, Path]] = []
    
    class ThemeData:
        """Theme configuration data"""
        available_themes: List[str] = ["default", "gaming", "matrix", "minimal"]
        theme_colors: Dict[str, Dict[str, str]] = {
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
    
    class UserInteraction:
        """User interaction data"""
        recent_wallpapers: List[str] = []
        search_history: List[str] = []
        performance_stats: Dict[str, float] = {}