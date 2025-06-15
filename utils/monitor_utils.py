"""
Genişletilmiş monitör yönetimi fonksiyonları
"""
import subprocess
import logging
import re
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MonitorInfo:
    """Monitör bilgilerini tutan dataclass."""
    name: str
    resolution: Tuple[int, int]
    position: Tuple[int, int]
    is_active: bool
    is_primary: bool
    current_wallpaper: Optional[str] = None
    refresh_rate: Optional[float] = None
    connection_type: Optional[str] = None
    

def get_detailed_monitor_info() -> List[MonitorInfo]:
    """
    Detaylı monitör bilgilerini getirir.
    
    Returns:
        List[MonitorInfo]: Monitör bilgileri listesi
    """
    monitors = []
    
    try:
        # xrandr ile monitör bilgilerini al
        result = subprocess.run(
            ["xrandr", "--query"], 
            capture_output=True, 
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            logger.warning("xrandr query başarısız, basit bilgi döndürülüyor")
            return get_simple_monitor_info()
        
        # xrandr çıktısını parse et
        monitors = parse_xrandr_output(result.stdout)
        
        # Aktif monitörleri de al
        active_monitors = get_active_monitors()
        
        # Aktif monitör bilgilerini birleştir
        for monitor in monitors:
            monitor.is_active = monitor.name in active_monitors
            
        logger.info(f"Detaylı monitör bilgisi alındı: {len(monitors)} monitör")
        return monitors
        
    except subprocess.TimeoutExpired:
        logger.error("xrandr komutu zaman aşımına uğradı")
        return get_simple_monitor_info()
    except Exception as e:
        logger.error(f"Detaylı monitör bilgisi alınırken hata: {e}")
        return get_simple_monitor_info()


def parse_xrandr_output(xrandr_output: str) -> List[MonitorInfo]:
    """
    xrandr çıktısını parse ederek MonitorInfo listesi döner.
    
    Args:
        xrandr_output: xrandr komutunun çıktısı
        
    Returns:
        List[MonitorInfo]: Parse edilmiş monitör bilgileri
    """
    monitors = []
    lines = xrandr_output.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Monitör satırlarını bul (format: "NAME connected/disconnected ...")
        monitor_match = re.match(r'^(\S+)\s+(connected|disconnected)(.*)$', line)
        if not monitor_match:
            continue
            
        monitor_name = monitor_match.group(1)
        is_connected = monitor_match.group(2) == "connected"
        rest_info = monitor_match.group(3).strip()
        
        if not is_connected:
            # Bağlı olmayan monitör
            monitors.append(MonitorInfo(
                name=monitor_name,
                resolution=(0, 0),
                position=(0, 0),
                is_active=False,
                is_primary=False,
                connection_type=get_connection_type(monitor_name)
            ))
            continue
        
        # Bağlı monitör için detayları parse et
        resolution = (1920, 1080)  # default
        position = (0, 0)  # default
        is_primary = "primary" in rest_info
        refresh_rate = None
        
        # Çözünürlük ve pozisyon bilgisini bul
        # Format: "1920x1080+0+0" veya "1920x1080+1920+0"
        res_pos_match = re.search(r'(\d+)x(\d+)\+(\d+)\+(\d+)', rest_info)
        if res_pos_match:
            resolution = (int(res_pos_match.group(1)), int(res_pos_match.group(2)))
            position = (int(res_pos_match.group(3)), int(res_pos_match.group(4)))
        
        # Refresh rate bilgisini bul
        refresh_match = re.search(r'(\d+\.\d+)\*', rest_info)
        if refresh_match:
            refresh_rate = float(refresh_match.group(1))
        
        monitors.append(MonitorInfo(
            name=monitor_name,
            resolution=resolution,
            position=position,
            is_active=True,
            is_primary=is_primary,
            refresh_rate=refresh_rate,
            connection_type=get_connection_type(monitor_name)
        ))
    
    return monitors


def get_simple_monitor_info() -> List[MonitorInfo]:
    """
    Basit monitör bilgisi döner (fallback).
    
    Returns:
        List[MonitorInfo]: Basit monitör bilgileri
    """
    try:
        # Mevcut sistem utils'den ekranları al
        from utils.system_utils import get_screens
        screen_names = get_screens()
        
        monitors = []
        for i, screen_name in enumerate(screen_names):
            monitors.append(MonitorInfo(
                name=screen_name,
                resolution=(1920, 1080),  # default
                position=(i * 1920, 0),  # side by side
                is_active=True,
                is_primary=(i == 0),
                connection_type=get_connection_type(screen_name)
            ))
            
        return monitors
        
    except Exception as e:
        logger.error(f"Basit monitör bilgisi alınırken hata: {e}")
        # En basit fallback
        return [MonitorInfo(
            name="eDP-1",
            resolution=(1920, 1080),
            position=(0, 0),
            is_active=True,
            is_primary=True,
            connection_type="eDP"
        )]


def get_active_monitors() -> List[str]:
    """
    Aktif monitörlerin isimlerini döner.
    
    Returns:
        List[str]: Aktif monitör isimleri
    """
    try:
        result = subprocess.run(
            ["xrandr", "--listactivemonitors"], 
            capture_output=True, 
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            logger.warning("Active monitors listesi alınamadı")
            return []
            
        lines = result.stdout.strip().split('\n')[1:]  # İlk satırı atla
        active_monitors = [line.split()[-1] for line in lines if line.strip()]
        
        return active_monitors
        
    except Exception as e:
        logger.error(f"Aktif monitörler alınırken hata: {e}")
        return []


def get_connection_type(monitor_name: str) -> str:
    """
    Monitör adından bağlantı tipini tahmin eder.
    
    Args:
        monitor_name: Monitör adı
        
    Returns:
        str: Bağlantı tipi
    """
    name_lower = monitor_name.lower()
    
    if 'edp' in name_lower:
        return "eDP (Dahili)"
    elif 'hdmi' in name_lower:
        return "HDMI"
    elif 'dp' in name_lower or 'displayport' in name_lower:
        return "DisplayPort"
    elif 'vga' in name_lower:
        return "VGA"
    elif 'dvi' in name_lower:
        return "DVI"
    elif 'usb' in name_lower:
        return "USB-C"
    else:
        return "Bilinmeyen"


def get_monitor_resolution(monitor_name: str) -> Tuple[int, int]:
    """
    Belirli bir monitörün çözünürlüğünü getirir.
    
    Args:
        monitor_name: Monitör adı
        
    Returns:
        Tuple[int, int]: (genişlik, yükseklik)
    """
    monitors = get_detailed_monitor_info()
    for monitor in monitors:
        if monitor.name == monitor_name and monitor.is_active:
            return monitor.resolution
    
    return (1920, 1080)  # default


def get_monitor_position(monitor_name: str) -> Tuple[int, int]:
    """
    Belirli bir monitörün pozisyonunu getirir.
    
    Args:
        monitor_name: Monitör adı
        
    Returns:
        Tuple[int, int]: (x, y) pozisyonu
    """
    monitors = get_detailed_monitor_info()
    for monitor in monitors:
        if monitor.name == monitor_name and monitor.is_active:
            return monitor.position
    
    return (0, 0)  # default


def detect_monitor_changes() -> bool:
    """
    Monitör konfigürasyonunda değişiklik olup olmadığını kontrol eder.
    
    Returns:
        bool: Değişiklik varsa True
    """
    try:
        # Bu fonksiyon cache sistemi ile çalışabilir
        # Şimdilik basit bir implementasyon
        current_monitors = get_detailed_monitor_info()
        return len(current_monitors) > 0
        
    except Exception as e:
        logger.error(f"Monitör değişiklik kontrolü hatası: {e}")
        return False


def set_wallpaper_per_monitor(monitor_name: str, wallpaper_id: str) -> bool:
    """
    Belirli bir monitöre wallpaper uygular.
    
    Args:
        monitor_name: Monitör adı
        wallpaper_id: Wallpaper ID'si
        
    Returns:
        bool: İşlem başarılı ise True
    """
    try:
        # Bu fonksiyon WallpaperEngine ile entegre olacak
        # Şimdilik placeholder implementasyon
        logger.info(f"Monitör {monitor_name} için wallpaper {wallpaper_id} uygulanıyor")
        
        # TODO: WallpaperEngine'e monitör parametresi eklenecek
        # wallpaper_engine.apply_wallpaper_to_monitor(wallpaper_id, monitor_name)
        
        return True
        
    except Exception as e:
        logger.error(f"Monitöre wallpaper uygulama hatası ({monitor_name}, {wallpaper_id}): {e}")
        return False


def get_available_resolutions(monitor_name: str) -> List[Tuple[int, int]]:
    """
    Monitörün desteklediği çözünürlükleri getirir.
    
    Args:
        monitor_name: Monitör adı
        
    Returns:
        List[Tuple[int, int]]: Desteklenen çözünürlükler
    """
    try:
        result = subprocess.run(
            ["xrandr", "--query"], 
            capture_output=True, 
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return [(1920, 1080)]  # default
        
        resolutions = []
        in_monitor_section = False
        
        for line in result.stdout.split('\n'):
            line = line.strip()
            
            # Monitör bölümünü bul
            if line.startswith(monitor_name + ' '):
                in_monitor_section = True
                continue
            elif in_monitor_section and line and not line.startswith(' '):
                # Başka monitör bölümüne geçildi
                break
            elif in_monitor_section and line.startswith('   '):
                # Çözünürlük satırı
                res_match = re.match(r'\s+(\d+)x(\d+)', line)
                if res_match:
                    width, height = int(res_match.group(1)), int(res_match.group(2))
                    resolutions.append((width, height))
        
        return resolutions if resolutions else [(1920, 1080)]
        
    except Exception as e:
        logger.error(f"Çözünürlükler alınırken hata ({monitor_name}): {e}")
        return [(1920, 1080)]


def validate_monitor_setup() -> Dict[str, any]:
    """
    Monitör kurulumunu doğrular ve sistem durumunu rapor eder.
    
    Returns:
        Dict: Durum raporu
    """
    try:
        monitors = get_detailed_monitor_info()
        active_count = sum(1 for m in monitors if m.is_active)
        primary_count = sum(1 for m in monitors if m.is_primary)
        
        return {
            "total_monitors": len(monitors),
            "active_monitors": active_count,
            "primary_monitors": primary_count,
            "is_valid": active_count > 0 and primary_count == 1,
            "monitors": monitors
        }
        
    except Exception as e:
        logger.error(f"Monitör kurulum doğrulaması hatası: {e}")
        return {
            "total_monitors": 0,
            "active_monitors": 0,
            "primary_monitors": 0,
            "is_valid": False,
            "monitors": []
        }