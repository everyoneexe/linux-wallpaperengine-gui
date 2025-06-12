"""
Multi-monitor wallpaper management
"""
import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Callable
from enum import Enum

from PySide6.QtCore import QObject, Signal, QTimer

from utils.monitor_utils import MonitorInfo, get_detailed_monitor_info

logger = logging.getLogger(__name__)


class SlideshowMode(Enum):
    """Slideshow playback modes."""
    SYNCHRONIZED = "synchronized"  # All monitors synchronized
    INDEPENDENT = "independent"    # Each monitor independent
    MIXED = "mixed"               # Mixed mode (some sync, some independent)


@dataclass
class SlideshowConfig:
    """Slideshow configuration settings."""
    mode: SlideshowMode
    timer_interval: int  # seconds
    is_active: bool = False
    monitor_timers: Dict[str, int] = None  # monitor-based timers
    synchronized_monitors: List[str] = None  # monitors to be synchronized
    
    def __post_init__(self):
        if self.monitor_timers is None:
            self.monitor_timers = {}
        if self.synchronized_monitors is None:
            self.synchronized_monitors = []


@dataclass
class MonitorSettings:
    """Monitor settings."""
    monitor_name: str
    current_wallpaper: Optional[str] = None
    wallpaper_scaling: str = "fit"  # fit, fill, stretch, center
    slideshow_enabled: bool = False
    playlist: List[str] = None
    custom_timer: Optional[int] = None
    
    def __post_init__(self):
        if self.playlist is None:
            self.playlist = []


class MonitorManager(QObject):
    """
    Multi-monitor wallpaper management class.
    
    Signals:
        monitor_wallpaper_changed: Emitted when monitor wallpaper changes
        slideshow_state_changed: Emitted when slideshow state changes
        monitor_configuration_changed: Emitted when monitor configuration changes
    """
    
    monitor_wallpaper_changed = Signal(str, str)  # monitor_name, wallpaper_id
    slideshow_state_changed = Signal(bool)  # is_active
    monitor_configuration_changed = Signal()
    
    def __init__(self):
        super().__init__()
        
        # Monitor information and settings
        self.monitors: Dict[str, MonitorInfo] = {}
        self.monitor_settings: Dict[str, MonitorSettings] = {}
        
        # Slideshow settings
        self.slideshow_config = SlideshowConfig(
            mode=SlideshowMode.SYNCHRONIZED,
            timer_interval=300  # 5 minutes default
        )
        
        # Timers
        self.slideshow_timer = QTimer()
        self.slideshow_timer.timeout.connect(self._on_slideshow_timeout)
        
        self.monitor_timers: Dict[str, QTimer] = {}
        
        # Settings file
        self.settings_file = Path.home() / ".config" / "wallpaper_engine" / "monitor_settings.json"
        
        # Wallpaper engine reference
        self.wallpaper_engine = None
        
        # Initial setup
        self.refresh_monitors()
        self.load_settings()
        
        logger.info("MonitorManager started")
    
    def set_wallpaper_engine(self, wallpaper_engine):
        """Sets WallpaperEngine reference."""
        self.wallpaper_engine = wallpaper_engine
        logger.debug("WallpaperEngine reference set")
    
    def refresh_monitors(self) -> None:
        """Refreshes monitor information."""
        try:
            new_monitors = get_detailed_monitor_info()
            
            # Check monitor changes
            old_monitor_names = set(self.monitors.keys())
            new_monitor_names = set(m.name for m in new_monitors)
            
            # Newly added monitors
            added_monitors = new_monitor_names - old_monitor_names
            # Removed monitors
            removed_monitors = old_monitor_names - new_monitor_names
            
            if added_monitors or removed_monitors:
                logger.info(f"Monitor change: +{added_monitors}, -{removed_monitors}")
                self.monitor_configuration_changed.emit()
            
            # Update monitor information
            self.monitors = {m.name: m for m in new_monitors}
            
            # Create settings for new monitors
            for monitor_name in added_monitors:
                if monitor_name not in self.monitor_settings:
                    self.monitor_settings[monitor_name] = MonitorSettings(monitor_name=monitor_name)
            
            # Clean timers for removed monitors
            for monitor_name in removed_monitors:
                if monitor_name in self.monitor_timers:
                    self.monitor_timers[monitor_name].stop()
                    del self.monitor_timers[monitor_name]
            
            logger.debug(f"Monitor information updated: {len(self.monitors)} active monitors")
            
        except Exception as e:
            logger.error(f"Error refreshing monitor information: {e}")
    
    def assign_wallpaper(self, monitor_name: str, wallpaper_id: str) -> bool:
        """
        Assigns wallpaper to a specific monitor.
        
        Args:
            monitor_name: Monitor name
            wallpaper_id: Wallpaper ID
            
        Returns:
            bool: True if operation successful
        """
        try:
            if monitor_name not in self.monitors:
                logger.warning(f"Unknown monitor: {monitor_name}")
                return False
            
            if not self.monitors[monitor_name].is_active:
                logger.warning(f"Monitor not active: {monitor_name}")
                return False
            
            # Update monitor settings
            if monitor_name not in self.monitor_settings:
                self.monitor_settings[monitor_name] = MonitorSettings(monitor_name=monitor_name)
            
            self.monitor_settings[monitor_name].current_wallpaper = wallpaper_id
            
            # Also update MonitorInfo
            self.monitors[monitor_name].current_wallpaper = wallpaper_id
            
            # Apply wallpaper (through WallpaperEngine)
            success = self._apply_wallpaper_to_monitor(monitor_name, wallpaper_id)
            
            if success:
                self.monitor_wallpaper_changed.emit(monitor_name, wallpaper_id)
                logger.info(f"Wallpaper assigned: {monitor_name} -> {wallpaper_id}")
                return True
            else:
                logger.error(f"Wallpaper could not be applied: {monitor_name} -> {wallpaper_id}")
                return False
                
        except Exception as e:
            logger.error(f"Wallpaper assignment error ({monitor_name}, {wallpaper_id}): {e}")
            return False
    
    def start_slideshow(self, config: Optional[SlideshowConfig] = None) -> bool:
        """
        Starts slideshow.
        
        Args:
            config: Slideshow configuration (if None, current config is used)
            
        Returns:
            bool: True if operation successful
        """
        try:
            if config:
                self.slideshow_config = config
            
            if self.slideshow_config.is_active:
                logger.warning("Slideshow already active")
                return True
            
            # Check active monitors
            active_monitors = [name for name, monitor in self.monitors.items() if monitor.is_active]
            if not active_monitors:
                logger.warning("No active monitor found")
                return False
            
            self.slideshow_config.is_active = True
            
            # Start timers according to slideshow mode
            if self.slideshow_config.mode == SlideshowMode.SYNCHRONIZED:
                self._start_synchronized_slideshow()
            elif self.slideshow_config.mode == SlideshowMode.INDEPENDENT:
                self._start_independent_slideshow()
            elif self.slideshow_config.mode == SlideshowMode.MIXED:
                self._start_mixed_slideshow()
            
            self.slideshow_state_changed.emit(True)
            logger.info(f"Slideshow started: {self.slideshow_config.mode.value}")
            return True
            
        except Exception as e:
            logger.error(f"Slideshow start error: {e}")
            return False
    
    def stop_slideshow(self) -> bool:
        """
        Stops slideshow.
        
        Returns:
            bool: True if operation successful
        """
        try:
            if not self.slideshow_config.is_active:
                logger.warning("Slideshow already stopped")
                return True
            
            # Stop all timers
            self.slideshow_timer.stop()
            for timer in self.monitor_timers.values():
                timer.stop()
            
            self.slideshow_config.is_active = False
            self.slideshow_state_changed.emit(False)
            
            logger.info("Slideshow stopped")
            return True
            
        except Exception as e:
            logger.error(f"Slideshow stop error: {e}")
            return False
    
    def sync_slideshows(self) -> bool:
        """
        Synchronizes slideshows (switches to same wallpaper).
        
        Returns:
            bool: True if operation successful
        """
        try:
            active_monitors = [name for name, monitor in self.monitors.items() if monitor.is_active]
            if len(active_monitors) < 2:
                logger.warning("Not enough monitors to synchronize")
                return False
            
            # Get wallpaper from primary monitor
            primary_monitor = None
            for monitor in self.monitors.values():
                if monitor.is_primary and monitor.is_active:
                    primary_monitor = monitor
                    break
            
            if not primary_monitor or not primary_monitor.current_wallpaper:
                logger.warning("Primary monitor wallpaper not found")
                return False
            
            # Apply same wallpaper to other monitors
            success_count = 0
            for monitor_name in active_monitors:
                if monitor_name != primary_monitor.name:
                    if self.assign_wallpaper(monitor_name, primary_monitor.current_wallpaper):
                        success_count += 1
            
            logger.info(f"Slideshow synchronization: {success_count}/{len(active_monitors)-1} successful")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Slideshow synchronization error: {e}")
            return False
    
    def get_monitor_info(self, monitor_name: str) -> Optional[MonitorInfo]:
        """
        Returns monitor information.
        
        Args:
            monitor_name: Monitor name
            
        Returns:
            MonitorInfo: Monitor information or None
        """
        return self.monitors.get(monitor_name)
    
    def get_active_monitors(self) -> List[MonitorInfo]:
        """
        Returns list of active monitors.
        
        Returns:
            List[MonitorInfo]: Active monitors
        """
        return [monitor for monitor in self.monitors.values() if monitor.is_active]
    
    def get_monitor_settings(self, monitor_name: str) -> Optional[MonitorSettings]:
        """
        Returns monitor settings.
        
        Args:
            monitor_name: Monitor name
            
        Returns:
            MonitorSettings: Monitor settings or None
        """
        return self.monitor_settings.get(monitor_name)
    
    def save_settings(self) -> bool:
        """
        Saves monitor settings to file.
        
        Returns:
            bool: True if operation successful
        """
        try:
            # Create directory
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Serialize settings
            settings_data = {
                "slideshow_config": asdict(self.slideshow_config),
                "monitor_settings": {
                    name: asdict(settings) for name, settings in self.monitor_settings.items()
                }
            }
            
            # Write to JSON
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=2, ensure_ascii=False)
                f.flush()
            
            logger.info("Monitor settings saved")
            return True
            
        except Exception as e:
            logger.error(f"Error saving monitor settings: {e}")
            return False
    
    def load_settings(self) -> bool:
        """
        Loads monitor settings from file.
        
        Returns:
            bool: True if operation successful
        """
        try:
            if not self.settings_file.exists():
                logger.debug("Monitor settings file not found, using default settings")
                return False
            
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)
            
            # Load slideshow config
            if "slideshow_config" in settings_data:
                config_data = settings_data["slideshow_config"]
                config_data["mode"] = SlideshowMode(config_data["mode"])
                self.slideshow_config = SlideshowConfig(**config_data)
            
            # Load monitor settings
            if "monitor_settings" in settings_data:
                for monitor_name, settings_data_item in settings_data["monitor_settings"].items():
                    self.monitor_settings[monitor_name] = MonitorSettings(**settings_data_item)
            
            logger.info("Monitor settings loaded")
            return True
            
        except Exception as e:
            logger.error(f"Error loading monitor settings: {e}")
            return False
    
    def _apply_wallpaper_to_monitor(self, monitor_name: str, wallpaper_id: str) -> bool:
        """
        Applies wallpaper to specific monitor (through WallpaperEngine).
        
        Args:
            monitor_name: Monitor name
            wallpaper_id: Wallpaper ID
            
        Returns:
            bool: True if operation successful
        """
        try:
            if not self.wallpaper_engine:
                logger.warning("No WallpaperEngine reference, wallpaper cannot be applied")
                return False
            
            # Currently single monitor support - will be extended for multi-monitor in future
            success = self.wallpaper_engine.apply_wallpaper(
                wallpaper_id=wallpaper_id,
                screen=monitor_name,
                volume=50,  # default
                fps=60,     # default
                noautomute=False,
                no_audio_processing=False,
                disable_mouse=False
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error applying wallpaper ({monitor_name}, {wallpaper_id}): {e}")
            return False
    
    def _start_synchronized_slideshow(self) -> None:
        """Starts synchronized slideshow."""
        self.slideshow_timer.start(self.slideshow_config.timer_interval * 1000)
        logger.debug("Synchronized slideshow started")
    
    def _start_independent_slideshow(self) -> None:
        """Starts independent slideshow."""
        active_monitors = [name for name, monitor in self.monitors.items() if monitor.is_active]
        
        for monitor_name in active_monitors:
            if monitor_name not in self.monitor_timers:
                timer = QTimer()
                timer.timeout.connect(lambda mn=monitor_name: self._on_monitor_slideshow_timeout(mn))
                self.monitor_timers[monitor_name] = timer
            
            # Get monitor-specific timer interval
            settings = self.monitor_settings.get(monitor_name)
            interval = settings.custom_timer if settings and settings.custom_timer else self.slideshow_config.timer_interval
            
            self.monitor_timers[monitor_name].start(interval * 1000)
        
        logger.debug(f"Independent slideshow started: {len(active_monitors)} monitors")
    
    def _start_mixed_slideshow(self) -> None:
        """Starts mixed slideshow."""
        # Main timer for synchronized monitors
        if self.slideshow_config.synchronized_monitors:
            self.slideshow_timer.start(self.slideshow_config.timer_interval * 1000)
        
        # Separate timers for independent monitors
        active_monitors = [name for name, monitor in self.monitors.items() if monitor.is_active]
        independent_monitors = [m for m in active_monitors if m not in self.slideshow_config.synchronized_monitors]
        
        for monitor_name in independent_monitors:
            if monitor_name not in self.monitor_timers:
                timer = QTimer()
                timer.timeout.connect(lambda mn=monitor_name: self._on_monitor_slideshow_timeout(mn))
                self.monitor_timers[monitor_name] = timer
            
            settings = self.monitor_settings.get(monitor_name)
            interval = settings.custom_timer if settings and settings.custom_timer else self.slideshow_config.timer_interval
            
            self.monitor_timers[monitor_name].start(interval * 1000)
        
        logger.debug("Mixed slideshow started")
    
    def _on_slideshow_timeout(self) -> None:
        """Synchronized slideshow timeout."""
        try:
            # Get synchronized monitors
            if self.slideshow_config.mode == SlideshowMode.SYNCHRONIZED:
                target_monitors = [name for name, monitor in self.monitors.items() if monitor.is_active]
            else:  # MIXED mode
                target_monitors = self.slideshow_config.synchronized_monitors
            
            if not target_monitors:
                return
            
            # TODO: Get next wallpaper from playlist and apply
            # Placeholder for now
            logger.debug(f"Synchronized slideshow tick: {len(target_monitors)} monitors")
            
        except Exception as e:
            logger.error(f"Slideshow timeout error: {e}")
    
    def _on_monitor_slideshow_timeout(self, monitor_name: str) -> None:
        """Monitor-specific slideshow timeout."""
        try:
            if monitor_name not in self.monitors or not self.monitors[monitor_name].is_active:
                return
            
            # TODO: Get next wallpaper from playlist for this monitor and apply
            # Placeholder for now
            logger.debug(f"Independent slideshow tick: {monitor_name}")
            
        except Exception as e:
            logger.error(f"Monitor slideshow timeout error ({monitor_name}): {e}")