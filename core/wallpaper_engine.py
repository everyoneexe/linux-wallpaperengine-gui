"""
Wallpaper Engine işlemlerini yöneten sınıf
"""
import subprocess
import logging
import json
from typing import List, Optional, Dict, Any
from pathlib import Path

from utils import (
    WALLPAPER_ENGINE_BINARY,
    kill_existing_wallpapers,
    validate_wallpaper_path,
    get_wallpaper_info,
    SETTINGS_FILE
)

logger = logging.getLogger(__name__)


class WallpaperEngine:
    """
    Wallpaper Engine işlemlerini yöneten sınıf.
    
    Attributes:
        current_wallpaper: Currently active wallpaper ID
        current_process: Running wallpaper process
        last_settings: Last used settings
    """
    
    def __init__(self):
        self.current_wallpaper: Optional[str] = None
        self.current_process: Optional[subprocess.Popen] = None
        self.last_settings: Dict[str, Any] = {}
        
        # State'i restore et ve live detection
        self._load_state()
        self._detect_running_wallpaper()

    def apply_wallpaper(self, 
                       wallpaper_id: str,
                       screen: str = "eDP-1",
                       volume: int = 50,
                       fps: int = 60,
                       noautomute: bool = False,
                       no_audio_processing: bool = False,
                       disable_mouse: bool = False) -> bool:
        """
        Wallpaper uygular.
        
        Args:
            wallpaper_id: Uygulanacak wallpaper ID'si
            screen: Hedef ekran
            volume: Ses seviyesi (0-100)
            fps: FPS değeri
            noautomute: Otomatik ses kısma kapalı
            no_audio_processing: Ses işleme kapalı
            disable_mouse: Fare etkileşimi kapalı
            
        Returns:
            bool: True if application successful
        """
        if not wallpaper_id:
            logger.error("Wallpaper ID boş")
            return False
            
        if not validate_wallpaper_path(wallpaper_id):
            logger.error(f"Geçersiz wallpaper ID: {wallpaper_id}")
            return False
            
        if not WALLPAPER_ENGINE_BINARY.exists():
            logger.error(f"Wallpaper Engine binary not found: {WALLPAPER_ENGINE_BINARY}")
            return False

        try:
            # Terminate existing wallpapers - ONLY system-wide ones
            kill_existing_wallpapers()
            
            # Komut oluştur
            cmd = [
                str(WALLPAPER_ENGINE_BINARY),
                "--screen-root", screen,
                "--bg", wallpaper_id,
                "--volume", str(max(0, min(100, volume))),
                "--fps", str(max(10, min(144, fps)))
            ]
            
            # Opsiyonel parametreler
            if noautomute:
                cmd.append("--noautomute")
            if no_audio_processing:
                cmd.append("--no-audio-processing")
            if disable_mouse:
                cmd.append("--disable-mouse")
                
            logger.info(f"Wallpaper uygulanıyor: {wallpaper_id} -> Hedef ekran: {screen}")
            logger.debug(f"Komut: {' '.join(cmd)}")
            
            # Debug: Mevcut monitörleri de logla
            try:
                import subprocess
                xrandr_result = subprocess.run(["xrandr", "--listactivemonitors"],
                                             capture_output=True, text=True, timeout=5)
                if xrandr_result.returncode == 0:
                    logger.debug(f"Active monitors:\n{xrandr_result.stdout}")
                else:
                    logger.warning("xrandr --listactivemonitors başarısız")
            except Exception as e:
                logger.warning(f"Monitör listesi alınamadı: {e}")
            
            # Start process completely independent (detached process)
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                preexec_fn=None if hasattr(subprocess, 'CREATE_NEW_PROCESS_GROUP') else lambda: None
            )
            
            # Clear process reference immediately - let wallpaper run independently
            process_pid = self.current_process.pid
            self.current_process = None
            logger.info(f"Wallpaper started as independent process (PID: {process_pid})")
            
            # Ayarları kaydet
            self.current_wallpaper = wallpaper_id
            self.last_settings = {
                "screen": screen,
                "volume": volume,
                "fps": fps,
                "noautomute": noautomute,
                "no_audio_processing": no_audio_processing,
                "disable_mouse": disable_mouse
            }
            
            logger.info(f"Wallpaper başarıyla uygulandı: {wallpaper_id}")
            
            # State'i kaydet
            self._save_state()
            return True
            
        except FileNotFoundError:
            logger.error("Wallpaper Engine binary not found")
            return False
        except PermissionError:
            logger.error("No permission to run Wallpaper Engine")
            return False
        except Exception as e:
            logger.error(f"Wallpaper uygularken hata: {e}")
            return False

    def stop_current_wallpaper(self) -> bool:
        """
        Clears wallpaper reference but doesn't terminate process.
        
        Returns:
            bool: Always True (only reference clearing)
        """
        # We no longer have process reference, just clear current_wallpaper
        if self.current_wallpaper:
            logger.info(f"Wallpaper reference cleared: {self.current_wallpaper}")
            self.current_wallpaper = None
        
        return True

    def is_running(self) -> bool:
        """
        Checks if wallpaper is running.
        
        Returns:
            bool: Wallpaper ID'si varsa True (bağımsız süreç olduğu için)
        """
        # We no longer have process reference, assume running if wallpaper ID exists
        return self.current_wallpaper is not None

    def get_current_wallpaper_info(self) -> Optional[Dict[str, Any]]:
        """
        Şu anki wallpaper hakkında bilgi döner.
        
        Returns:
            dict: Wallpaper bilgileri veya None
        """
        if not self.current_wallpaper:
            return None
            
        info = get_wallpaper_info(self.current_wallpaper)
        if info:
            info.update({
                "is_running": self.is_running(),
                "settings": self.last_settings.copy()
            })
            
        return info

    def restart_with_new_settings(self, **kwargs) -> bool:
        """
        Restarts current wallpaper with new settings.
        
        Args:
            **kwargs: Yeni ayarlar
            
        Returns:
            bool: True if restart successful
        """
        if not self.current_wallpaper:
            logger.warning("No wallpaper to restart")
            return False
            
        # Mevcut ayarları güncelle
        new_settings = self.last_settings.copy()
        new_settings.update(kwargs)
        
        return self.apply_wallpaper(self.current_wallpaper, **new_settings)

    def get_process_status(self) -> Dict[str, Any]:
        """
        Süreç durumu hakkında bilgi döner.
        
        Returns:
            dict: Süreç durumu bilgileri
        """
        status = {
            "current_wallpaper": self.current_wallpaper,
            "is_running": self.is_running(),
            "process_id": "detached",  # Bağımsız süreç
            "last_settings": self.last_settings.copy()
        }
            
        return status

    def validate_settings(self, **kwargs) -> Dict[str, Any]:
        """
        Ayarları doğrular ve düzeltir.
        
        Args:
            **kwargs: Doğrulanacak ayarlar
            
        Returns:
            dict: Doğrulanmış ayarlar
        """
        validated = {}
        
        # Volume kontrolü
        if "volume" in kwargs:
            validated["volume"] = max(0, min(100, int(kwargs["volume"])))
            
        # FPS kontrolü
        if "fps" in kwargs:
            validated["fps"] = max(10, min(144, int(kwargs["fps"])))
            
        # Boolean değerler
        for key in ["noautomute", "no_audio_processing", "disable_mouse"]:
            if key in kwargs:
                validated[key] = bool(kwargs[key])
                
        # String değerler
        for key in ["screen", "wallpaper_id"]:
            if key in kwargs and kwargs[key]:
                validated[key] = str(kwargs[key])
                
        return validated

    def _load_state(self) -> None:
        """App restart sonrası state'i restore eder."""
        try:
            print(f"[DEBUG] WallpaperEngine._load_state() called")
            print(f"[DEBUG] Settings file: {SETTINGS_FILE}")
            print(f"[DEBUG] Dosya var mı? {SETTINGS_FILE.exists()}")
            
            if SETTINGS_FILE.exists():
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                print(f"[DEBUG] Settings data keys: {list(data.keys())}")
                
                # Wallpaper state'ini restore et
                wallpaper_state = data.get('wallpaper_state', {})
                print(f"[DEBUG] Wallpaper state: {wallpaper_state}")
                
                self.current_wallpaper = wallpaper_state.get('current_wallpaper')
                self.last_settings = wallpaper_state.get('last_settings', {})
                
                print(f"[DEBUG] Restore edilen current_wallpaper: {self.current_wallpaper}")
                print(f"[DEBUG] Restore edilen last_settings: {self.last_settings}")
                
                if self.current_wallpaper:
                    logger.info(f"State restore edildi: {self.current_wallpaper}")
                    print(f"[DEBUG] ✅ State başarıyla restore edildi: {self.current_wallpaper}")
                else:
                    print(f"[DEBUG] ❌ Current wallpaper restore edilemedi")
            else:
                print(f"[DEBUG] ❌ Settings file not found")
                    
        except Exception as e:
            logger.error(f"State restore hatası: {e}")
            print(f"[DEBUG] ❌ State restore hatası: {e}")
            import traceback
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
    
    def _save_state(self) -> None:
        """Current state'i settings dosyasına kaydet."""
        try:
            # Mevcut settings'i oku
            data = {}
            if SETTINGS_FILE.exists():
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            # Wallpaper state'ini ekle
            data['wallpaper_state'] = {
                'current_wallpaper': self.current_wallpaper,
                'last_settings': self.last_settings
            }
            
            # Geri kaydet
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logger.debug(f"Wallpaper state kaydedildi: {self.current_wallpaper}")
            
        except Exception as e:
            logger.error(f"State kaydetme hatası: {e}")

    def _detect_running_wallpaper(self) -> None:
        """Detects running wallpaper in real-time."""
        try:
            print(f"[DEBUG] _detect_running_wallpaper() started")
            
            import psutil
            detected_wallpaper = None
            
            # Tüm linux-wallpaperengine process'lerini bul
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info.get('name', '')
                    cmdline = proc_info.get('cmdline', [])
                    
                    # linux-wallpaperengine process'i mi?
                    if 'wallpaperengine' in proc_name.lower() or 'wallpaper-engine' in proc_name.lower():
                        print(f"[DEBUG] Wallpaper process bulundu: PID={proc_info['pid']}, name={proc_name}")
                        print(f"[DEBUG] Command line: {cmdline}")
                        
                        # Command line'dan --bg parametresini bul
                        if cmdline and '--bg' in cmdline:
                            try:
                                bg_index = cmdline.index('--bg')
                                if bg_index + 1 < len(cmdline):
                                    detected_wallpaper = cmdline[bg_index + 1]
                                    print(f"[DEBUG] ✅ Running wallpaper detected: {detected_wallpaper}")
                                    break
                            except (ValueError, IndexError):
                                continue
                                
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            if detected_wallpaper:
                # Dosya yolunu folder ID'ye çevir
                detected_id = self._extract_folder_id_from_path(detected_wallpaper)
                if detected_id:
                    print(f"[DEBUG] ✅ Live detection: {detected_id}")
                    self.current_wallpaper = detected_id
                    # State'i güncelle
                    self._save_state()
                    logger.info(f"Live wallpaper detection: {detected_id}")
                else:
                    print(f"[DEBUG] ❌ Could not extract folder ID: {detected_wallpaper}")
            else:
                print(f"[DEBUG] ❌ No running wallpaper found")
                
        except Exception as e:
            logger.error(f"Wallpaper detection hatası: {e}")
            print(f"[DEBUG] ❌ Wallpaper detection hatası: {e}")
    
    def _extract_folder_id_from_path(self, wallpaper_path: str) -> Optional[str]:
        """Wallpaper path'inden folder ID'sini çıkarır."""
        try:
            # Örnek path: /home/user/.steam/steam/steamapps/workshop/content/431960/123456789
            # Folder ID: 123456789
            from pathlib import Path
            path_obj = Path(wallpaper_path)
            
            # Steam workshop path kontrolü
            if "431960" in str(path_obj):
                # Steam workshop wallpaper'ı
                parts = path_obj.parts
                for i, part in enumerate(parts):
                    if part == "431960" and i + 1 < len(parts):
                        folder_id = parts[i + 1]
                        print(f"[DEBUG] Steam workshop folder ID: {folder_id}")
                        return folder_id
            
            # Yerel wallpaper path'i de kontrol edebiliriz
            # /path/to/wallpapers/folder_name gibi
            folder_name = path_obj.name
            if folder_name and folder_name != "." and folder_name != "..":
                print(f"[DEBUG] Local wallpaper folder: {folder_name}")
                return folder_name
                
            return None
            
        except Exception as e:
            logger.error(f"Path'den folder ID çıkarma hatası: {e}")
            return None

    def __del__(self):
        """Destructor - do nothing, let wallpaper run independently"""
        try:
            # Hiçbir şey yapma - wallpaper tamamen bağımsız
            pass
        except Exception:
            pass  # Destructor'da hata fırlatmayalım