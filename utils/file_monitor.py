"""
File system monitoring for Steam Workshop folder
"""
import logging
import time
from pathlib import Path
from typing import Callable, Optional, Set
from PySide6.QtCore import QThread, Signal, QTimer
from utils.constants import STEAM_WORKSHOP_PATH

logger = logging.getLogger(__name__)


class SteamWorkshopMonitor(QThread):
    """
    Thread that monitors Steam Workshop folder.
    Sends signal when new wallpaper folders are created.
    """

    # Emitted when new wallpaper is detected
    new_wallpaper_detected = Signal(str)  # workshop_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.monitoring = False
        self.known_folders: Set[str] = set()
        self.check_interval = 5.0  # 5 saniye
        self._initialize_known_folders()
        
    def _initialize_known_folders(self) -> None:
        """Save existing wallpaper folders as initial list."""
        try:
            if STEAM_WORKSHOP_PATH.exists():
                self.known_folders = {
                    folder.name for folder in STEAM_WORKSHOP_PATH.iterdir() 
                    if folder.is_dir() and folder.name.isdigit()
                }
                logger.info(f"Steam Workshop monitor started: {len(self.known_folders)} existing wallpapers")
            else:
                logger.warning(f"Steam Workshop folder not found: {STEAM_WORKSHOP_PATH}")
                self.known_folders = set()
        except Exception as e:
            logger.error(f"Error scanning Steam Workshop folders: {e}")
            self.known_folders = set()
    
    def start_monitoring(self) -> None:
        """Start monitoring."""
        if not self.monitoring:
            self.monitoring = True
            self.start()
            logger.info("Steam Workshop monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        if self.monitoring:
            self.monitoring = False
            self.quit()
            self.wait(3000)  # Wait 3 seconds
            logger.info("Steam Workshop monitoring stopped")
    
    def run(self) -> None:
        """Main monitoring loop."""
        while self.monitoring:
            try:
                self._check_for_new_wallpapers()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Steam Workshop monitoring error: {e}")
                time.sleep(self.check_interval)
    
    def _check_for_new_wallpapers(self) -> None:
        """Check for new wallpaper folders."""
        try:
            if not STEAM_WORKSHOP_PATH.exists():
                return
            
            current_folders = {
                folder.name for folder in STEAM_WORKSHOP_PATH.iterdir() 
                if folder.is_dir() and folder.name.isdigit()
            }
            
            # Are there new folders?
            new_folders = current_folders - self.known_folders
            
            if new_folders:
                for workshop_id in new_folders:
                    # Make sure folder is completely created (check preview.jpg etc.)
                    if self._is_wallpaper_complete(workshop_id):
                        logger.info(f"New Steam wallpaper detected: {workshop_id}")
                        self.new_wallpaper_detected.emit(workshop_id)
                        self.known_folders.add(workshop_id)
                    else:
                        logger.debug(f"Wallpaper not yet complete: {workshop_id}")
                        
        except Exception as e:
            logger.error(f"Error during new wallpaper check: {e}")
    
    def _is_wallpaper_complete(self, workshop_id: str) -> bool:
        """
        Checks if wallpaper is completely downloaded.
        Checks existence of preview file and project.json.
        """
        try:
            wallpaper_path = STEAM_WORKSHOP_PATH / workshop_id
            
            # Does preview file exist?
            preview_exists = any(
                (wallpaper_path / f"preview.{ext}").exists() 
                for ext in ["jpg", "jpeg", "png", "gif"]
            )
            
            # Does project.json exist?
            project_exists = (wallpaper_path / "project.json").exists()
            
            # At least preview should exist
            return preview_exists
            
        except Exception as e:
            logger.error(f"Wallpaper completion check error ({workshop_id}): {e}")
            return False
    
    def refresh_known_folders(self) -> None:
        """Refresh known folders list (after manual refresh)."""
        self._initialize_known_folders()
        logger.debug("Known folders list refreshed")


class SteamWorkshopWatcher:
    """
    Main class for Steam Workshop monitoring.
    Used for integration with MainWindow.
    """
    
    def __init__(self, callback: Callable[[str], None]):
        """
        Args:
            callback: Function to be called when new wallpaper is detected
        """
        self.callback = callback
        self.monitor: Optional[SteamWorkshopMonitor] = None
        self.enabled = True
        
    def start(self) -> None:
        """Start monitoring."""
        if self.enabled and not self.monitor:
            try:
                self.monitor = SteamWorkshopMonitor()
                self.monitor.new_wallpaper_detected.connect(self._on_new_wallpaper)
                self.monitor.start_monitoring()
                logger.info("Steam Workshop watcher started")
            except Exception as e:
                logger.error(f"Steam Workshop watcher could not be started: {e}")
    
    def stop(self) -> None:
        """Stop monitoring."""
        if self.monitor:
            try:
                self.monitor.stop_monitoring()
                self.monitor = None
                logger.info("Steam Workshop watcher stopped")
            except Exception as e:
                logger.error(f"Steam Workshop watcher could not be stopped: {e}")
    
    def _on_new_wallpaper(self, workshop_id: str) -> None:
        """Called when new wallpaper is detected."""
        try:
            if self.callback:
                self.callback(workshop_id)
        except Exception as e:
            logger.error(f"New wallpaper callback error: {e}")
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable monitoring."""
        self.enabled = enabled
        if not enabled and self.monitor:
            self.stop()
        elif enabled and not self.monitor:
            self.start()
    
    def refresh(self) -> None:
        """Update known folders after manual refresh."""
        if self.monitor:
            self.monitor.refresh_known_folders()