"""
System-related utility functions
"""
import subprocess
import logging
from pathlib import Path
from typing import List, Tuple, Optional

from utils.constants import STEAM_WORKSHOP_PATH, SUPPORTED_IMAGE_FORMATS

logger = logging.getLogger(__name__)


def get_preview_paths() -> List[Tuple[str, Path]]:
    """
    Gets Steam Workshop wallpaper previews (with STRONG DUPLICATE PREVENTION).

    Returns:
        List[Tuple[str, Path]]: List of (folder_id, preview_path) tuples
    """
    try:
        folders = [f for f in STEAM_WORKSHOP_PATH.iterdir() if f.is_dir()]
        previews = []
        seen_folder_ids = set()  # For duplicate control
        
        # All supported formats (image + video + FFmpeg enhanced)
        basic_video_formats = ["mp4", "webm", "mov"]
        
        # Extended format support if FFmpeg is available
        try:
            from utils.ffmpeg_utils import is_ffmpeg_available
            if is_ffmpeg_available():
                extended_video_formats = ["mp4", "webm", "mov", "avi", "mkv", "flv", "wmv"]
                all_supported_formats = SUPPORTED_IMAGE_FORMATS + extended_video_formats
                logger.debug("FFmpeg available - extended format support active")
            else:
                all_supported_formats = SUPPORTED_IMAGE_FORMATS + basic_video_formats
                logger.debug("FFmpeg not available - basic format support")
        except ImportError:
            all_supported_formats = SUPPORTED_IMAGE_FORMATS + basic_video_formats
            logger.debug("FFmpeg utils could not be imported - basic format support")
        
        for folder in folders:
            folder_id = folder.name
            
            # STRONG DUPLICATE CONTROL - Check first
            if folder_id in seen_folder_ids:
                logger.warning(f"Duplicate folder ID skipped: {folder_id}")
                continue
            
            # Mark folder ID immediately (to prevent duplicates)
            seen_folder_ids.add(folder_id)
            
            preview_found = False
            selected_preview = None
            
            # 1. FIRST SEARCH FOR STANDARD PREVIEW FILES
            for ext in all_supported_formats:
                preview_file = folder / f"preview.{ext}"
                if preview_file.exists():
                    selected_preview = preview_file
                    preview_found = True
                    break  # Take the first one found, exit
            
            # 2. IF PREVIEW NOT FOUND, SEARCH FOR CUSTOM MEDIA FILE
            if not preview_found:
                # Search for custom media files (starting with folder ID)
                for media_file in folder.iterdir():
                    if (media_file.is_file() and
                        media_file.suffix.lower() in ['.gif', '.mp4', '.webm', '.mov'] and
                        media_file.stem.startswith(folder_id)):
                        selected_preview = media_file
                        preview_found = True
                        break
            
            # 3. IF STILL NOT FOUND, USE ANY MEDIA FILE
            if not preview_found:
                for media_file in folder.iterdir():
                    if (media_file.is_file() and
                        media_file.suffix.lower() in ['.gif', '.mp4', '.webm', '.mov']):
                        selected_preview = media_file
                        preview_found = True
                        break
            
            # ADD ONLY ONE PREVIEW
            if preview_found and selected_preview:
                previews.append((folder_id, selected_preview))
                logger.debug(f"Preview eklendi: {folder_id} -> {selected_preview.name}")
            else:
                logger.debug(f"Preview not found: {folder_id}")
                # Remove folder ID from set (because preview not found)
                seen_folder_ids.discard(folder_id)
                    
        logger.info(f"{len(previews)} wallpaper previews found (strong duplicate prevention)")
        
        # FINAL DUPLICATE CHECK - To be sure
        final_previews = []
        final_seen = set()
        for folder_id, preview_path in previews:
            if folder_id not in final_seen:
                final_previews.append((folder_id, preview_path))
                final_seen.add(folder_id)
            else:
                logger.warning(f"Final duplicate check: {folder_id} skipped")
        
        logger.info(f"Final: {len(final_previews)} benzersiz wallpaper")
        return final_previews
        
    except Exception as e:
        logger.error(f"Error loading wallpaper previews: {e}")
        return []


def get_screens() -> List[str]:
    """
    Gets active screens.

    Returns:
        List[str]: List of screen names
    """
    try:
        result = subprocess.run(
            ["xrandr", "--listactivemonitors"], 
            capture_output=True, 
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            logger.warning("xrandr command failed, using default screen")
            return ["eDP-1"]
            
        lines = result.stdout.strip().split('\n')[1:]
        screens = [line.split()[-1] for line in lines if line.strip()]
        
        if not screens:
            logger.warning("No active screen found, using default screen")
            return ["eDP-1"]
            
        logger.info(f"Bulunan ekranlar: {screens}")
        return screens
        
    except subprocess.TimeoutExpired:
        logger.error("xrandr command timed out")
        return ["eDP-1"]
    except Exception as e:
        logger.error(f"Error getting screens: {e}")
        return ["eDP-1"]


def kill_existing_wallpapers() -> bool:
    """
    Terminates running wallpaper engine processes.

    Returns:
        bool: True if operation successful
    """
    try:
        result = subprocess.run(
            ["pkill", "-f", "linux-wallpaperengine"],
            capture_output=True,
            timeout=5
        )
        
        if result.returncode == 0:
            logger.info("Current wallpaper processes terminated")
        else:
            logger.info("No wallpaper process found to terminate")
            
        return True
        
    except subprocess.TimeoutExpired:
        logger.error("Process termination timed out")
        return False
    except Exception as e:
        logger.error(f"Error terminating process: {e}")
        return False


def validate_wallpaper_path(wallpaper_id: str) -> bool:
    """
    Checks if wallpaper ID is valid.

    Args:
        wallpaper_id: Wallpaper ID to check

    Returns:
        bool: True if valid
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
        
        # Get additional info if project.json file exists
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
                logger.warning(f"project.json could not be read ({wallpaper_id}): {e}")
                
        return info
        
    except Exception as e:
        logger.error(f"Error getting wallpaper info ({wallpaper_id}): {e}")
        return None