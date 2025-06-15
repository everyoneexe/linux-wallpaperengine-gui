"""
Çoklu monitör wallpaper yönetimi
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
    """Slideshow çalma modları."""
    SYNCHRONIZED = "synchronized"  # Tüm monitörler senkronize
    INDEPENDENT = "independent"    # Her monitör bağımsız
    MIXED = "mixed"               # Karışık mod (bazı senkron, bazı bağımsız)


@dataclass
class SlideshowConfig:
    """Slideshow konfigürasyon ayarları."""
    mode: SlideshowMode
    timer_interval: int  # saniye
    is_active: bool = False
    monitor_timers: Dict[str, int] = None  # monitör bazında timer'lar
    synchronized_monitors: List[str] = None  # senkronize edilecek monitörler
    
    def __post_init__(self):
        if self.monitor_timers is None:
            self.monitor_timers = {}
        if self.synchronized_monitors is None:
            self.synchronized_monitors = []


@dataclass
class MonitorSettings:
    """Monitör ayarları."""
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
    Çoklu monitör wallpaper yönetimi sınıfı.
    
    Signals:
        monitor_wallpaper_changed: Monitör wallpaper'ı değiştiğinde emit edilir
        slideshow_state_changed: Slideshow durumu değiştiğinde emit edilir
        monitor_configuration_changed: Monitör konfigürasyonu değiştiğinde emit edilir
    """
    
    monitor_wallpaper_changed = Signal(str, str)  # monitor_name, wallpaper_id
    slideshow_state_changed = Signal(bool)  # is_active
    monitor_configuration_changed = Signal()
    
    def __init__(self):
        super().__init__()
        
        # Monitör bilgileri ve ayarları
        self.monitors: Dict[str, MonitorInfo] = {}
        self.monitor_settings: Dict[str, MonitorSettings] = {}
        
        # Slideshow ayarları
        self.slideshow_config = SlideshowConfig(
            mode=SlideshowMode.SYNCHRONIZED,
            timer_interval=300  # 5 dakika default
        )
        
        # Timer'lar
        self.slideshow_timer = QTimer()
        self.slideshow_timer.timeout.connect(self._on_slideshow_timeout)
        
        self.monitor_timers: Dict[str, QTimer] = {}
        
        # Ayarlar dosyası
        self.settings_file = Path.home() / ".config" / "wallpaper_engine" / "monitor_settings.json"
        
        # Wallpaper engine referansı
        self.wallpaper_engine = None
        
        # Başlangıç kurulumu
        self.refresh_monitors()
        self.load_settings()
        
        logger.info("MonitorManager başlatıldı")
    
    def set_wallpaper_engine(self, wallpaper_engine):
        """WallpaperEngine referansını ayarlar."""
        self.wallpaper_engine = wallpaper_engine
        logger.debug("WallpaperEngine referansı ayarlandı")
    
    def refresh_monitors(self) -> None:
        """Monitör bilgilerini yeniler."""
        try:
            new_monitors = get_detailed_monitor_info()
            
            # Monitör değişikliklerini kontrol et
            old_monitor_names = set(self.monitors.keys())
            new_monitor_names = set(m.name for m in new_monitors)
            
            # Yeni eklenen monitörler
            added_monitors = new_monitor_names - old_monitor_names
            # Çıkarılan monitörler
            removed_monitors = old_monitor_names - new_monitor_names
            
            if added_monitors or removed_monitors:
                logger.info(f"Monitör değişikliği: +{added_monitors}, -{removed_monitors}")
                self.monitor_configuration_changed.emit()
            
            # Monitör bilgilerini güncelle
            self.monitors = {m.name: m for m in new_monitors}
            
            # Yeni monitörler için ayarlar oluştur
            for monitor_name in added_monitors:
                if monitor_name not in self.monitor_settings:
                    self.monitor_settings[monitor_name] = MonitorSettings(monitor_name=monitor_name)
            
            # Kaldırılan monitörler için timer'ları temizle
            for monitor_name in removed_monitors:
                if monitor_name in self.monitor_timers:
                    self.monitor_timers[monitor_name].stop()
                    del self.monitor_timers[monitor_name]
            
            logger.debug(f"Monitör bilgileri güncellendi: {len(self.monitors)} aktif monitör")
            
        except Exception as e:
            logger.error(f"Monitör bilgileri yenilenirken hata: {e}")
    
    def assign_wallpaper(self, monitor_name: str, wallpaper_id: str) -> bool:
        """
        Belirli bir monitöre wallpaper atar.
        
        Args:
            monitor_name: Monitör adı
            wallpaper_id: Wallpaper ID'si
            
        Returns:
            bool: İşlem başarılı ise True
        """
        try:
            if monitor_name not in self.monitors:
                logger.warning(f"Bilinmeyen monitör: {monitor_name}")
                return False
            
            if not self.monitors[monitor_name].is_active:
                logger.warning(f"Monitör aktif değil: {monitor_name}")
                return False
            
            # Monitör ayarlarını güncelle
            if monitor_name not in self.monitor_settings:
                self.monitor_settings[monitor_name] = MonitorSettings(monitor_name=monitor_name)
            
            self.monitor_settings[monitor_name].current_wallpaper = wallpaper_id
            
            # MonitorInfo'yu da güncelle
            self.monitors[monitor_name].current_wallpaper = wallpaper_id
            
            # Wallpaper'ı uygula (WallpaperEngine üzerinden)
            success = self._apply_wallpaper_to_monitor(monitor_name, wallpaper_id)
            
            if success:
                self.monitor_wallpaper_changed.emit(monitor_name, wallpaper_id)
                logger.info(f"Wallpaper atandı: {monitor_name} -> {wallpaper_id}")
                return True
            else:
                logger.error(f"Wallpaper uygulanamadı: {monitor_name} -> {wallpaper_id}")
                return False
                
        except Exception as e:
            logger.error(f"Wallpaper atama hatası ({monitor_name}, {wallpaper_id}): {e}")
            return False
    
    def start_slideshow(self, config: Optional[SlideshowConfig] = None) -> bool:
        """
        Slideshow'u başlatır.
        
        Args:
            config: Slideshow konfigürasyonu (None ise mevcut config kullanılır)
            
        Returns:
            bool: İşlem başarılı ise True
        """
        try:
            if config:
                self.slideshow_config = config
            
            if self.slideshow_config.is_active:
                logger.warning("Slideshow zaten aktif")
                return True
            
            # Aktif monitörleri kontrol et
            active_monitors = [name for name, monitor in self.monitors.items() if monitor.is_active]
            if not active_monitors:
                logger.warning("Aktif monitör bulunamadı")
                return False
            
            self.slideshow_config.is_active = True
            
            # Slideshow moduna göre timer'ları başlat
            if self.slideshow_config.mode == SlideshowMode.SYNCHRONIZED:
                self._start_synchronized_slideshow()
            elif self.slideshow_config.mode == SlideshowMode.INDEPENDENT:
                self._start_independent_slideshow()
            elif self.slideshow_config.mode == SlideshowMode.MIXED:
                self._start_mixed_slideshow()
            
            self.slideshow_state_changed.emit(True)
            logger.info(f"Slideshow başlatıldı: {self.slideshow_config.mode.value}")
            return True
            
        except Exception as e:
            logger.error(f"Slideshow başlatma hatası: {e}")
            return False
    
    def stop_slideshow(self) -> bool:
        """
        Slideshow'u durdurur.
        
        Returns:
            bool: İşlem başarılı ise True
        """
        try:
            if not self.slideshow_config.is_active:
                logger.warning("Slideshow zaten durmuş")
                return True
            
            # Tüm timer'ları durdur
            self.slideshow_timer.stop()
            for timer in self.monitor_timers.values():
                timer.stop()
            
            self.slideshow_config.is_active = False
            self.slideshow_state_changed.emit(False)
            
            logger.info("Slideshow durduruldu")
            return True
            
        except Exception as e:
            logger.error(f"Slideshow durdurma hatası: {e}")
            return False
    
    def sync_slideshows(self) -> bool:
        """
        Slideshow'ları senkronize eder (aynı wallpaper'a geçirir).
        
        Returns:
            bool: İşlem başarılı ise True
        """
        try:
            active_monitors = [name for name, monitor in self.monitors.items() if monitor.is_active]
            if len(active_monitors) < 2:
                logger.warning("Senkronize edilecek yeterli monitör yok")
                return False
            
            # Primary monitördeki wallpaper'ı al
            primary_monitor = None
            for monitor in self.monitors.values():
                if monitor.is_primary and monitor.is_active:
                    primary_monitor = monitor
                    break
            
            if not primary_monitor or not primary_monitor.current_wallpaper:
                logger.warning("Primary monitör wallpaper'ı bulunamadı")
                return False
            
            # Diğer monitörlere aynı wallpaper'ı uygula
            success_count = 0
            for monitor_name in active_monitors:
                if monitor_name != primary_monitor.name:
                    if self.assign_wallpaper(monitor_name, primary_monitor.current_wallpaper):
                        success_count += 1
            
            logger.info(f"Slideshow senkronizasyonu: {success_count}/{len(active_monitors)-1} başarılı")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Slideshow senkronizasyon hatası: {e}")
            return False
    
    def get_monitor_info(self, monitor_name: str) -> Optional[MonitorInfo]:
        """
        Monitör bilgisini döner.
        
        Args:
            monitor_name: Monitör adı
            
        Returns:
            MonitorInfo: Monitör bilgisi veya None
        """
        return self.monitors.get(monitor_name)
    
    def get_active_monitors(self) -> List[MonitorInfo]:
        """
        Aktif monitörlerin listesini döner.
        
        Returns:
            List[MonitorInfo]: Aktif monitörler
        """
        return [monitor for monitor in self.monitors.values() if monitor.is_active]
    
    def get_monitor_settings(self, monitor_name: str) -> Optional[MonitorSettings]:
        """
        Monitör ayarlarını döner.
        
        Args:
            monitor_name: Monitör adı
            
        Returns:
            MonitorSettings: Monitör ayarları veya None
        """
        return self.monitor_settings.get(monitor_name)
    
    def save_settings(self) -> bool:
        """
        Monitör ayarlarını dosyaya kaydeder.
        
        Returns:
            bool: İşlem başarılı ise True
        """
        try:
            # Dizini oluştur
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Ayarları serialize et
            settings_data = {
                "slideshow_config": asdict(self.slideshow_config),
                "monitor_settings": {
                    name: asdict(settings) for name, settings in self.monitor_settings.items()
                }
            }
            
            # JSON'a yaz
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=2, ensure_ascii=False)
                f.flush()
            
            logger.info("Monitör ayarları kaydedildi")
            return True
            
        except Exception as e:
            logger.error(f"Monitör ayarları kaydedilirken hata: {e}")
            return False
    
    def load_settings(self) -> bool:
        """
        Monitör ayarlarını dosyadan yükler.
        
        Returns:
            bool: İşlem başarılı ise True
        """
        try:
            if not self.settings_file.exists():
                logger.debug("Monitör ayarları dosyası bulunamadı, varsayılan ayarlar kullanılıyor")
                return False
            
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)
            
            # Slideshow config'i yükle
            if "slideshow_config" in settings_data:
                config_data = settings_data["slideshow_config"]
                config_data["mode"] = SlideshowMode(config_data["mode"])
                self.slideshow_config = SlideshowConfig(**config_data)
            
            # Monitör ayarlarını yükle
            if "monitor_settings" in settings_data:
                for monitor_name, settings_data_item in settings_data["monitor_settings"].items():
                    self.monitor_settings[monitor_name] = MonitorSettings(**settings_data_item)
            
            logger.info("Monitör ayarları yüklendi")
            return True
            
        except Exception as e:
            logger.error(f"Monitör ayarları yüklenirken hata: {e}")
            return False
    
    def _apply_wallpaper_to_monitor(self, monitor_name: str, wallpaper_id: str) -> bool:
        """
        Wallpaper'ı belirli monitöre uygular (WallpaperEngine üzerinden).
        
        Args:
            monitor_name: Monitör adı
            wallpaper_id: Wallpaper ID'si
            
        Returns:
            bool: İşlem başarılı ise True
        """
        try:
            if not self.wallpaper_engine:
                logger.warning("WallpaperEngine referansı yok, wallpaper uygulanamadı")
                return False
            
            # Şimdilik single monitor support - gelecekte multi-monitor için extend edilecek
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
            logger.error(f"Wallpaper uygulanırken hata ({monitor_name}, {wallpaper_id}): {e}")
            return False
    
    def _start_synchronized_slideshow(self) -> None:
        """Senkronize slideshow'u başlatır."""
        self.slideshow_timer.start(self.slideshow_config.timer_interval * 1000)
        logger.debug("Senkronize slideshow başlatıldı")
    
    def _start_independent_slideshow(self) -> None:
        """Bağımsız slideshow'u başlatır."""
        active_monitors = [name for name, monitor in self.monitors.items() if monitor.is_active]
        
        for monitor_name in active_monitors:
            if monitor_name not in self.monitor_timers:
                timer = QTimer()
                timer.timeout.connect(lambda mn=monitor_name: self._on_monitor_slideshow_timeout(mn))
                self.monitor_timers[monitor_name] = timer
            
            # Monitor-specific timer interval'ı al
            settings = self.monitor_settings.get(monitor_name)
            interval = settings.custom_timer if settings and settings.custom_timer else self.slideshow_config.timer_interval
            
            self.monitor_timers[monitor_name].start(interval * 1000)
        
        logger.debug(f"Bağımsız slideshow başlatıldı: {len(active_monitors)} monitör")
    
    def _start_mixed_slideshow(self) -> None:
        """Karışık slideshow'u başlatır."""
        # Senkronize monitörler için ana timer
        if self.slideshow_config.synchronized_monitors:
            self.slideshow_timer.start(self.slideshow_config.timer_interval * 1000)
        
        # Bağımsız monitörler için ayrı timer'lar
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
        
        logger.debug("Karışık slideshow başlatıldı")
    
    def _on_slideshow_timeout(self) -> None:
        """Senkronize slideshow timeout'u."""
        try:
            # Senkronize monitörleri al
            if self.slideshow_config.mode == SlideshowMode.SYNCHRONIZED:
                target_monitors = [name for name, monitor in self.monitors.items() if monitor.is_active]
            else:  # MIXED mode
                target_monitors = self.slideshow_config.synchronized_monitors
            
            if not target_monitors:
                return
            
            # TODO: Playlist'ten bir sonraki wallpaper'ı al ve uygula
            # Şimdilik placeholder
            logger.debug(f"Senkronize slideshow tick: {len(target_monitors)} monitör")
            
        except Exception as e:
            logger.error(f"Slideshow timeout hatası: {e}")
    
    def _on_monitor_slideshow_timeout(self, monitor_name: str) -> None:
        """Monitör-specific slideshow timeout'u."""
        try:
            if monitor_name not in self.monitors or not self.monitors[monitor_name].is_active:
                return
            
            # TODO: Bu monitör için playlist'ten sonraki wallpaper'ı al ve uygula
            # Şimdilik placeholder
            logger.debug(f"Bağımsız slideshow tick: {monitor_name}")
            
        except Exception as e:
            logger.error(f"Monitör slideshow timeout hatası ({monitor_name}): {e}")