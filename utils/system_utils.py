"""
Sistem ile ilgili yardımcı fonksiyonlar
"""
import subprocess
import logging
from pathlib import Path
from typing import List, Tuple, Optional

from utils.constants import STEAM_WORKSHOP_PATH, SUPPORTED_IMAGE_FORMATS

logger = logging.getLogger(__name__)


def get_preview_paths() -> List[Tuple[str, Path]]:
    """
    Steam Workshop wallpaper önizlemelerini getirir (GÜÇLÜ DUPLICATE ÖNLEME ile).
    
    Returns:
        List[Tuple[str, Path]]: (folder_id, preview_path) tuple'ları listesi
    """
    try:
        folders = [f for f in STEAM_WORKSHOP_PATH.iterdir() if f.is_dir()]
        previews = []
        seen_folder_ids = set()  # Duplicate kontrolü için
        
        # Desteklenen tüm formatlar (resim + video + FFmpeg enhanced)
        basic_video_formats = ["mp4", "webm", "mov"]
        
        # FFmpeg varsa genişletilmiş format desteği
        try:
            from utils.ffmpeg_utils import is_ffmpeg_available
            if is_ffmpeg_available():
                extended_video_formats = ["mp4", "webm", "mov", "avi", "mkv", "flv", "wmv"]
                all_supported_formats = SUPPORTED_IMAGE_FORMATS + extended_video_formats
                logger.debug("FFmpeg mevcut - genişletilmiş format desteği aktif")
            else:
                all_supported_formats = SUPPORTED_IMAGE_FORMATS + basic_video_formats
                logger.debug("FFmpeg yok - temel format desteği")
        except ImportError:
            all_supported_formats = SUPPORTED_IMAGE_FORMATS + basic_video_formats
            logger.debug("FFmpeg utils import edilemedi - temel format desteği")
        
        for folder in folders:
            folder_id = folder.name
            
            # GÜÇLÜ DUPLICATE KONTROLÜ - Önce kontrol et
            if folder_id in seen_folder_ids:
                logger.warning(f"Duplicate folder ID atlandı: {folder_id}")
                continue
            
            # Folder ID'yi hemen işaretle (duplicate önlemek için)
            seen_folder_ids.add(folder_id)
            
            preview_found = False
            selected_preview = None
            
            # 1. ÖNCE STANDART PREVIEW DOSYALARINI ARA
            for ext in all_supported_formats:
                preview_file = folder / f"preview.{ext}"
                if preview_file.exists():
                    selected_preview = preview_file
                    preview_found = True
                    break  # İlk bulduğunu al, çık
            
            # 2. EĞER PREVIEW BULUNAMAZSA, CUSTOM MEDYA DOSYASINI ARA
            if not preview_found:
                # Custom medya dosyalarını ara (folder ID ile başlayanlar)
                for media_file in folder.iterdir():
                    if (media_file.is_file() and
                        media_file.suffix.lower() in ['.gif', '.mp4', '.webm', '.mov'] and
                        media_file.stem.startswith(folder_id)):
                        selected_preview = media_file
                        preview_found = True
                        break
            
            # 3. HALA BULUNAMAZSA, HERHANGİ BİR MEDYA DOSYASINI KULLAN
            if not preview_found:
                for media_file in folder.iterdir():
                    if (media_file.is_file() and
                        media_file.suffix.lower() in ['.gif', '.mp4', '.webm', '.mov']):
                        selected_preview = media_file
                        preview_found = True
                        break
            
            # SADECE TEK BİR PREVIEW EKLE
            if preview_found and selected_preview:
                previews.append((folder_id, selected_preview))
                logger.debug(f"Preview eklendi: {folder_id} -> {selected_preview.name}")
            else:
                logger.debug(f"Preview bulunamadı: {folder_id}")
                # Folder ID'yi set'ten çıkar (preview bulunamadığı için)
                seen_folder_ids.discard(folder_id)
                    
        logger.info(f"{len(previews)} wallpaper önizlemesi bulundu (güçlü duplicate önleme)")
        
        # FINAL DUPLICATE CHECK - Emin olmak için
        final_previews = []
        final_seen = set()
        for folder_id, preview_path in previews:
            if folder_id not in final_seen:
                final_previews.append((folder_id, preview_path))
                final_seen.add(folder_id)
            else:
                logger.warning(f"Final duplicate check: {folder_id} atlandı")
        
        logger.info(f"Final: {len(final_previews)} benzersiz wallpaper")
        return final_previews
        
    except Exception as e:
        logger.error(f"Wallpaper önizlemeleri yüklenirken hata: {e}")
        return []


def get_screens() -> List[str]:
    """
    Aktif ekranları getirir.
    
    Returns:
        List[str]: Ekran adları listesi
    """
    try:
        result = subprocess.run(
            ["xrandr", "--listactivemonitors"], 
            capture_output=True, 
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            logger.warning("xrandr komutu başarısız, varsayılan ekran kullanılıyor")
            return ["eDP-1"]
            
        lines = result.stdout.strip().split('\n')[1:]
        screens = [line.split()[-1] for line in lines if line.strip()]
        
        if not screens:
            logger.warning("Aktif ekran bulunamadı, varsayılan ekran kullanılıyor")
            return ["eDP-1"]
            
        logger.info(f"Bulunan ekranlar: {screens}")
        return screens
        
    except subprocess.TimeoutExpired:
        logger.error("xrandr komutu zaman aşımına uğradı")
        return ["eDP-1"]
    except Exception as e:
        logger.error(f"Ekranlar alınırken hata: {e}")
        return ["eDP-1"]


def kill_existing_wallpapers() -> bool:
    """
    Çalışan wallpaper engine süreçlerini sonlandırır.
    
    Returns:
        bool: İşlem başarılı ise True
    """
    try:
        result = subprocess.run(
            ["pkill", "-f", "linux-wallpaperengine"],
            capture_output=True,
            timeout=5
        )
        
        if result.returncode == 0:
            logger.info("Mevcut wallpaper süreçleri sonlandırıldı")
        else:
            logger.info("Sonlandırılacak wallpaper süreci bulunamadı")
            
        return True
        
    except subprocess.TimeoutExpired:
        logger.error("Süreç sonlandırma zaman aşımına uğradı")
        return False
    except Exception as e:
        logger.error(f"Süreç sonlandırırken hata: {e}")
        return False


def validate_wallpaper_path(wallpaper_id: str) -> bool:
    """
    Wallpaper ID'sinin geçerli olup olmadığını kontrol eder.
    
    Args:
        wallpaper_id: Kontrol edilecek wallpaper ID'si
        
    Returns:
        bool: Geçerli ise True
    """
    try:
        wallpaper_path = STEAM_WORKSHOP_PATH / wallpaper_id
        return wallpaper_path.exists() and wallpaper_path.is_dir()
    except Exception:
        return False


def get_wallpaper_info(wallpaper_id: str) -> Optional[dict]:
    """
    Wallpaper hakkında bilgi getirir.
    
    Args:
        wallpaper_id: Bilgi alınacak wallpaper ID'si
        
    Returns:
        dict: Wallpaper bilgileri veya None
    """
    try:
        wallpaper_path = STEAM_WORKSHOP_PATH / wallpaper_id
        if not wallpaper_path.exists():
            return None
            
        info = {
            "id": wallpaper_id,
            "path": wallpaper_path,
            "size": sum(f.stat().st_size for f in wallpaper_path.rglob('*') if f.is_file()),
            "files": len(list(wallpaper_path.rglob('*')))
        }
        
        # project.json dosyası varsa ek bilgileri al
        project_file = wallpaper_path / "project.json"
        if project_file.exists():
            import json
            try:
                with open(project_file, 'r', encoding='utf-8') as f:
                    project_data = json.load(f)
                    info.update({
                        "title": project_data.get("title", wallpaper_id),
                        "description": project_data.get("description", ""),
                        "type": project_data.get("type", "unknown")
                    })
            except Exception as e:
                logger.warning(f"project.json okunamadı ({wallpaper_id}): {e}")
                
        return info
        
    except Exception as e:
        logger.error(f"Wallpaper bilgisi alınırken hata ({wallpaper_id}): {e}")
        return None