"""
Steam Workshop klasörü için file system monitoring
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
    Steam Workshop klasörünü izleyen thread.
    Yeni wallpaper klasörleri oluştuğunda sinyal gönderir.
    """
    
    # Yeni wallpaper tespit edildiğinde emit edilir
    new_wallpaper_detected = Signal(str)  # workshop_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.monitoring = False
        self.known_folders: Set[str] = set()
        self.check_interval = 5.0  # 5 saniye
        self._initialize_known_folders()
        
    def _initialize_known_folders(self) -> None:
        """Mevcut wallpaper klasörlerini başlangıç listesi olarak kaydet."""
        try:
            if STEAM_WORKSHOP_PATH.exists():
                self.known_folders = {
                    folder.name for folder in STEAM_WORKSHOP_PATH.iterdir() 
                    if folder.is_dir() and folder.name.isdigit()
                }
                logger.info(f"Steam Workshop monitor başlatıldı: {len(self.known_folders)} mevcut wallpaper")
            else:
                logger.warning(f"Steam Workshop klasörü bulunamadı: {STEAM_WORKSHOP_PATH}")
                self.known_folders = set()
        except Exception as e:
            logger.error(f"Steam Workshop klasörleri taranırken hata: {e}")
            self.known_folders = set()
    
    def start_monitoring(self) -> None:
        """Monitoring'i başlat."""
        if not self.monitoring:
            self.monitoring = True
            self.start()
            logger.info("Steam Workshop monitoring başlatıldı")
    
    def stop_monitoring(self) -> None:
        """Monitoring'i durdur."""
        if self.monitoring:
            self.monitoring = False
            self.quit()
            self.wait(3000)  # 3 saniye bekle
            logger.info("Steam Workshop monitoring durduruldu")
    
    def run(self) -> None:
        """Ana monitoring döngüsü."""
        while self.monitoring:
            try:
                self._check_for_new_wallpapers()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Steam Workshop monitoring hatası: {e}")
                time.sleep(self.check_interval)
    
    def _check_for_new_wallpapers(self) -> None:
        """Yeni wallpaper klasörlerini kontrol et."""
        try:
            if not STEAM_WORKSHOP_PATH.exists():
                return
            
            current_folders = {
                folder.name for folder in STEAM_WORKSHOP_PATH.iterdir() 
                if folder.is_dir() and folder.name.isdigit()
            }
            
            # Yeni klasörler var mı?
            new_folders = current_folders - self.known_folders
            
            if new_folders:
                for workshop_id in new_folders:
                    # Klasörün tam olarak oluştuğundan emin ol (preview.jpg vs. kontrol et)
                    if self._is_wallpaper_complete(workshop_id):
                        logger.info(f"Yeni Steam wallpaper tespit edildi: {workshop_id}")
                        self.new_wallpaper_detected.emit(workshop_id)
                        self.known_folders.add(workshop_id)
                    else:
                        logger.debug(f"Wallpaper henüz tamamlanmamış: {workshop_id}")
                        
        except Exception as e:
            logger.error(f"Yeni wallpaper kontrolü sırasında hata: {e}")
    
    def _is_wallpaper_complete(self, workshop_id: str) -> bool:
        """
        Wallpaper'ın tamamen indirilip indirilmediğini kontrol eder.
        Preview dosyası ve project.json varlığını kontrol eder.
        """
        try:
            wallpaper_path = STEAM_WORKSHOP_PATH / workshop_id
            
            # Preview dosyası var mı?
            preview_exists = any(
                (wallpaper_path / f"preview.{ext}").exists() 
                for ext in ["jpg", "jpeg", "png", "gif"]
            )
            
            # project.json var mı?
            project_exists = (wallpaper_path / "project.json").exists()
            
            # En az preview olmalı
            return preview_exists
            
        except Exception as e:
            logger.error(f"Wallpaper tamamlanma kontrolü hatası ({workshop_id}): {e}")
            return False
    
    def refresh_known_folders(self) -> None:
        """Bilinen klasörler listesini yenile (manuel yenileme sonrası)."""
        self._initialize_known_folders()
        logger.debug("Bilinen klasörler listesi yenilendi")


class SteamWorkshopWatcher:
    """
    Steam Workshop monitoring için ana sınıf.
    MainWindow ile entegrasyon için kullanılır.
    """
    
    def __init__(self, callback: Callable[[str], None]):
        """
        Args:
            callback: Yeni wallpaper tespit edildiğinde çağrılacak fonksiyon
        """
        self.callback = callback
        self.monitor: Optional[SteamWorkshopMonitor] = None
        self.enabled = True
        
    def start(self) -> None:
        """Monitoring'i başlat."""
        if self.enabled and not self.monitor:
            try:
                self.monitor = SteamWorkshopMonitor()
                self.monitor.new_wallpaper_detected.connect(self._on_new_wallpaper)
                self.monitor.start_monitoring()
                logger.info("Steam Workshop watcher başlatıldı")
            except Exception as e:
                logger.error(f"Steam Workshop watcher başlatılamadı: {e}")
    
    def stop(self) -> None:
        """Monitoring'i durdur."""
        if self.monitor:
            try:
                self.monitor.stop_monitoring()
                self.monitor = None
                logger.info("Steam Workshop watcher durduruldu")
            except Exception as e:
                logger.error(f"Steam Workshop watcher durdurulamadı: {e}")
    
    def _on_new_wallpaper(self, workshop_id: str) -> None:
        """Yeni wallpaper tespit edildiğinde çağrılır."""
        try:
            if self.callback:
                self.callback(workshop_id)
        except Exception as e:
            logger.error(f"Yeni wallpaper callback hatası: {e}")
    
    def set_enabled(self, enabled: bool) -> None:
        """Monitoring'i etkinleştir/devre dışı bırak."""
        self.enabled = enabled
        if not enabled and self.monitor:
            self.stop()
        elif enabled and not self.monitor:
            self.start()
    
    def refresh(self) -> None:
        """Manuel yenileme sonrası bilinen klasörleri güncelle."""
        if self.monitor:
            self.monitor.refresh_known_folders()