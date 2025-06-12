"""
Playlist yönetimi için sınıf
"""
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from utils import SETTINGS_FILE, DEFAULT_TIMER_INTERVAL

logger = logging.getLogger(__name__)


class PlaylistManager:
    """
    Wallpaper playlist'lerini yöneten sınıf.
    
    Attributes:
        current_playlist: Aktif playlist
        current_index: Şu anki wallpaper indeksi
        is_playing: Playlist çalıyor mu
        is_random: Rastgele çalma modu aktif mi
        timer_interval: Wallpaper değiştirme aralığı (saniye)
        recent_wallpapers: Son kullanılan wallpaper'lar
        playlists: Kaydedilmiş playlist'ler
    """
    
    def __init__(self):
        self.current_playlist: List[str] = []
        self.current_index: int = 0
        self.is_playing: bool = False
        self.is_random: bool = False
        self.timer_interval: int = DEFAULT_TIMER_INTERVAL
        self.custom_timer_text: Optional[str] = None  # Özel timer metni
        self.recent_wallpapers: List[str] = []
        self.playlists: Dict[str, List[str]] = {}
        
        self.load_settings()

    def load_settings(self) -> bool:
        """
        Ayarları dosyadan yükler.
        
        Returns:
            bool: Yükleme başarılı ise True
        """
        if not SETTINGS_FILE.exists():
            logger.info("Ayar dosyası bulunamadı, varsayılan ayarlar kullanılıyor")
            return False
            
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            self.playlists = data.get('playlists', {})
            self.recent_wallpapers = data.get('recent', [])
            self.timer_interval = data.get('timer_interval', DEFAULT_TIMER_INTERVAL)
            self.custom_timer_text = data.get('custom_timer_text', None)
            self.is_random = data.get('is_random', False)
            # State persistence için ekledik
            self.current_playlist = data.get('current_playlist', [])
            self.current_index = data.get('current_index', 0)
            self.is_playing = data.get('is_playing', False)
            
            logger.info("Ayarlar başarıyla yüklendi")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Ayar dosyası JSON formatında değil: {e}")
            return False
        except Exception as e:
            logger.error(f"Ayarlar yüklenirken hata: {e}")
            return False

    def save_settings(self) -> bool:
        """
        Ayarları dosyaya kaydeder.
        
        Returns:
            bool: Kaydetme başarılı ise True
        """
        try:
            # Dizini oluştur
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'playlists': self.playlists,
                'recent': self.recent_wallpapers[-20:],  # Son 20'yi sakla
                'timer_interval': self.timer_interval,
                'custom_timer_text': self.custom_timer_text,
                'is_random': self.is_random,
                # State persistence için ekledik
                'current_playlist': self.current_playlist,
                'current_index': self.current_index,
                'is_playing': self.is_playing
            }
            
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logger.info("Ayarlar başarıyla kaydedildi")
            return True
            
        except Exception as e:
            logger.error(f"Ayarlar kaydedilirken hata: {e}")
            return False

    def add_to_recent(self, wallpaper_id: str) -> None:
        """
        Wallpaper'ı son kullanılanlara ekler.
        
        Args:
            wallpaper_id: Eklenecek wallpaper ID'si
        """
        if not wallpaper_id:
            return
            
        # Eğer zaten varsa çıkar
        if wallpaper_id in self.recent_wallpapers:
            self.recent_wallpapers.remove(wallpaper_id)
            
        # En başa ekle
        self.recent_wallpapers.append(wallpaper_id)
        
        # Maksimum 20 tane sakla
        if len(self.recent_wallpapers) > 20:
            self.recent_wallpapers = self.recent_wallpapers[-20:]
            
        self.save_settings()
        logger.debug(f"'{wallpaper_id}' son kullanılanlara eklendi")

    def create_playlist(self, name: str, wallpapers: List[str]) -> bool:
        """
        Yeni playlist oluşturur.
        
        Args:
            name: Playlist adı
            wallpapers: Wallpaper ID'leri listesi
            
        Returns:
            bool: Oluşturma başarılı ise True
        """
        if not name or not wallpapers:
            logger.warning("Playlist adı veya wallpaper listesi boş")
            return False
            
        self.playlists[name] = wallpapers.copy()
        self.save_settings()
        logger.info(f"'{name}' playlist'i oluşturuldu ({len(wallpapers)} wallpaper)")
        return True

    def delete_playlist(self, name: str) -> bool:
        """
        Playlist'i siler.
        
        Args:
            name: Silinecek playlist adı
            
        Returns:
            bool: Silme başarılı ise True
        """
        if name not in self.playlists:
            logger.warning(f"'{name}' playlist'i bulunamadı")
            return False
            
        del self.playlists[name]
        self.save_settings()
        logger.info(f"'{name}' playlist'i silindi")
        return True

    def load_playlist(self, name: str) -> bool:
        """
        Kaydedilmiş playlist'i yükler.
        
        Args:
            name: Yüklenecek playlist adı
            
        Returns:
            bool: Yükleme başarılı ise True
        """
        if name not in self.playlists:
            logger.warning(f"'{name}' playlist'i bulunamadı")
            return False
            
        self.current_playlist = self.playlists[name].copy()
        self.current_index = 0
        self.save_settings()  # State'i kaydet
        logger.info(f"'{name}' playlist'i yüklendi ({len(self.current_playlist)} wallpaper)")
        return True

    def add_to_current_playlist(self, wallpaper_id: str) -> bool:
        """
        Aktif playlist'e wallpaper ekler.
        
        Args:
            wallpaper_id: Eklenecek wallpaper ID'si
            
        Returns:
            bool: Ekleme başarılı ise True
        """
        if not wallpaper_id:
            return False
            
        if wallpaper_id not in self.current_playlist:
            self.current_playlist.append(wallpaper_id)
            logger.debug(f"'{wallpaper_id}' aktif playlist'e eklendi")
            return True
        else:
            logger.debug(f"'{wallpaper_id}' zaten playlist'te mevcut")
            return False

    def remove_from_current_playlist(self, index: int) -> bool:
        """
        Aktif playlist'ten wallpaper çıkarır.
        
        Args:
            index: Çıkarılacak wallpaper'ın indeksi
            
        Returns:
            bool: Çıkarma başarılı ise True
        """
        if 0 <= index < len(self.current_playlist):
            removed = self.current_playlist.pop(index)
            
            # Eğer current_index etkilendiyse ayarla
            if index <= self.current_index and self.current_index > 0:
                self.current_index -= 1
            elif self.current_index >= len(self.current_playlist) and self.current_playlist:
                self.current_index = 0
                
            logger.debug(f"'{removed}' aktif playlist'ten çıkarıldı")
            return True
        else:
            logger.warning(f"Geçersiz indeks: {index}")
            return False

    def clear_current_playlist(self) -> None:
        """Aktif playlist'i temizler."""
        self.current_playlist.clear()
        self.current_index = 0
        self.is_playing = False
        logger.info("Aktif playlist temizlendi")

    def clear_current_wallpaper(self) -> None:
        """Cached current wallpaper state'ini temizler - process verification sonrası."""
        # Current index'i sıfırla ama playlist'i koruy
        self.current_index = 0
        # is_playing'i de durdur çünkü process yok
        self.is_playing = False
        logger.info("Cached current wallpaper state temizlendi (process verification failed)")

    def get_current_wallpaper(self) -> Optional[str]:
        """
        Şu anki wallpaper ID'sini döner.
        
        Returns:
            str: Wallpaper ID'si veya None
        """
        if self.current_playlist and 0 <= self.current_index < len(self.current_playlist):
            return self.current_playlist[self.current_index]
        return None

    def get_next_wallpaper(self, random_mode: bool = False) -> Optional[str]:
        """
        Sonraki wallpaper ID'sini döner.
        
        Args:
            random_mode: Rastgele seçim yapılsın mı
            
        Returns:
            str: Wallpaper ID'si veya None
        """
        if not self.current_playlist:
            return None
            
        if random_mode:
            import random
            self.current_index = random.randint(0, len(self.current_playlist) - 1)
        else:
            self.current_index = (self.current_index + 1) % len(self.current_playlist)
        
        self.save_settings()  # Index değişti, kaydet
        return self.get_current_wallpaper()

    def get_previous_wallpaper(self) -> Optional[str]:
        """
        Önceki wallpaper ID'sini döner.
        
        Returns:
            str: Wallpaper ID'si veya None
        """
        if not self.current_playlist:
            return None
            
        self.current_index = (self.current_index - 1) % len(self.current_playlist)
        self.save_settings()  # Index değişti, kaydet
        return self.get_current_wallpaper()

    def get_playlist_info(self) -> Dict[str, Any]:
        """
        Playlist bilgilerini döner.
        
        Returns:
            dict: Playlist bilgileri
        """
        return {
            "current_playlist_size": len(self.current_playlist),
            "current_index": self.current_index,
            "is_playing": self.is_playing,
            "is_random": self.is_random,
            "timer_interval": self.timer_interval,
            "saved_playlists": list(self.playlists.keys()),
            "recent_count": len(self.recent_wallpapers),
            "custom_timer_text": self.custom_timer_text
        }

    def set_custom_timer(self, interval: int, display_text: str) -> None:
        """
        Özel timer ayarlar ve kaydeder.
        
        Args:
            interval: Timer aralığı (saniye)
            display_text: Görüntülenecek metin
        """
        self.timer_interval = interval
        self.custom_timer_text = display_text
        self.save_settings()
        logger.info(f"Özel timer ayarlandı: {display_text} ({interval} saniye)")

    def get_custom_timer_info(self) -> tuple:
        """
        Özel timer bilgilerini döner.
        
        Returns:
            tuple: (interval, display_text) veya (None, None)
        """
        if self.custom_timer_text:
            return self.timer_interval, self.custom_timer_text
        return None, None

    def clear_custom_timer(self) -> None:
        """Özel timer ayarını temizler."""
        self.custom_timer_text = None
        self.save_settings()
        logger.debug("Özel timer ayarı temizlendi")