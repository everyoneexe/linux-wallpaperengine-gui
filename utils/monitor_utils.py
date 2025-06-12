"""
Extended monitor management functions
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
    """Dataclass that holds monitor information."""
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
    Gets detailed monitor information.

    Returns:
        List[MonitorInfo]: List of monitor information
    """
    monitors = []
    
    try:
        # Get monitor information with xrandr
        result = subprocess.run(
            ["xrandr", "--query"], 
            capture_output=True, 
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            logger.warning("xrandr query failed, returning simple info")
            return get_simple_monitor_info()
        
        # Parse xrandr output
        monitors = parse_xrandr_output(result.stdout)
        
        # Also get active monitors
        active_monitors = get_active_monitors()
        
        # Merge active monitor information
        for monitor in monitors:
            monitor.is_active = monitor.name in active_monitors
            
        logger.info(f"Detailed monitor info obtained: {len(monitors)} monitors")
        return monitors
        
    except subprocess.TimeoutExpired:
        logger.error("xrandr command timed out")
        return get_simple_monitor_info()
    except Exception as e:
        logger.error(f"Error getting detailed monitor info: {e}")
        return get_simple_monitor_info()


def parse_xrandr_output(xrandr_output: str) -> List[MonitorInfo]:
    """
    Parses xrandr output and returns MonitorInfo list.

    Args:
        xrandr_output: Output of xrandr command

    Returns:
        List[MonitorInfo]: Parsed monitor information
    """
    monitors = []
    lines = xrandr_output.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Find monitor lines (format: "NAME connected/disconnected ...")
        monitor_match = re.match(r'^(\S+)\s+(connected|disconnected)(.*)$', line)
        if not monitor_match:
            continue
            
        monitor_name = monitor_match.group(1)
        is_connected = monitor_match.group(2) == "connected"
        rest_info = monitor_match.group(3).strip()
        
        if not is_connected:
            # Disconnected monitor
            monitors.append(MonitorInfo(
                name=monitor_name,
                resolution=(0, 0),
                position=(0, 0),
                is_active=False,
                is_primary=False,
                connection_type=get_connection_type(monitor_name)
            ))
            continue
        
        # Parse details for connected monitor
        resolution = (1920, 1080)  # default
        position = (0, 0)  # default
        is_primary = "primary" in rest_info
        refresh_rate = None
        
        # Find resolution and position information
        # Format: "1920x1080+0+0" or "1920x1080+1920+0"
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
    Returns simple monitor info (fallback).

    Returns:
        List[MonitorInfo]: Simple monitor information
    """
    try:
        # Get screens from existing system utils
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
        logger.error(f"Error getting simple monitor info: {e}")
        # Most basic fallback
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
    Returns names of active monitors.

    Returns:
        List[str]: Active monitor names
    """
    try:
        result = subprocess.run(
            ["xrandr", "--listactivemonitors"], 
            capture_output=True, 
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            logger.warning("Could not get active monitors list")
            return []
            
        lines = result.stdout.strip().split('\n')[1:]  # Skip first line
        active_monitors = [line.split()[-1] for line in lines if line.strip()]
        
        return active_monitors
        
    except Exception as e:
        logger.error(f"Error getting active monitors: {e}")
        return []


def get_connection_type(monitor_name: str) -> str:
    """
    Estimates connection type from monitor name.

    Args:
        monitor_name: Monitor name

    Returns:
        str: Connection type
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
    Gets resolution of a specific monitor.

    Args:
        monitor_name: Monitor name

    Returns:
        Tuple[int, int]: (width, height)
    """
    monitors = get_detailed_monitor_info()
    for monitor in monitors:
        if monitor.name == monitor_name and monitor.is_active:
            return monitor.resolution
    
    return (1920, 1080)  # default


def get_monitor_position(monitor_name: str) -> Tuple[int, int]:
    """
    Gets position of a specific monitor.

    Args:
        monitor_name: Monitor name

    Returns:
        Tuple[int, int]: (x, y) position
    """
    monitors = get_detailed_monitor_info()
    for monitor in monitors:
        if monitor.name == monitor_name and monitor.is_active:
            return monitor.position
    
    return (0, 0)  # default


def detect_monitor_changes() -> bool:
    """
    Checks if there are changes in monitor configuration.

    Returns:
        bool: True if there are changes
    """
    try:
        # This function can work with cache system
        # Simple implementation for now
        current_monitors = get_detailed_monitor_info()
        return len(current_monitors) > 0
        
    except Exception as e:
        logger.error(f"Monitor change check error: {e}")
        return False


def set_wallpaper_per_monitor(monitor_name: str, wallpaper_id: str) -> bool:
    """
    Applies wallpaper to a specific monitor.

    Args:
        monitor_name: Monitor name
        wallpaper_id: Wallpaper ID

    Returns:
        bool: True if operation successful
    """
    try:
        # This function will integrate with WallpaperEngine
        # Placeholder implementation for now
        logger.info(f"Applying wallpaper {wallpaper_id} for monitor {monitor_name}")

        # TODO: Monitor parameter will be added to WallpaperEngine
        # wallpaper_engine.apply_wallpaper_to_monitor(wallpaper_id, monitor_name)
        
        return True
        
    except Exception as e:
        logger.error(f"Error applying wallpaper to monitor ({monitor_name}, {wallpaper_id}): {e}")
        return False


def get_available_resolutions(monitor_name: str) -> List[Tuple[int, int]]:
    """
    Gets resolutions supported by the monitor.

    Args:
        monitor_name: Monitor name

    Returns:
        List[Tuple[int, int]]: Supported resolutions
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
            
            # Find monitor section
            if line.startswith(monitor_name + ' '):
                in_monitor_section = True
                continue
            elif in_monitor_section and line and not line.startswith(' '):
                # Moved to another monitor section
                break
            elif in_monitor_section and line.startswith('   '):
                # Resolution line
                res_match = re.match(r'\s+(\d+)x(\d+)', line)
                if res_match:
                    width, height = int(res_match.group(1)), int(res_match.group(2))
                    resolutions.append((width, height))
        
        return resolutions if resolutions else [(1920, 1080)]
        
    except Exception as e:
        logger.error(f"Error getting resolutions ({monitor_name}): {e}")
        return [(1920, 1080)]


def validate_monitor_setup() -> Dict[str, any]:
    """
    Validates monitor setup and reports system status.
    
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
        logger.error(f"Monitor setup validation error: {e}")
        return {
            "total_monitors": 0,
            "active_monitors": 0,
            "primary_monitors": 0,
            "is_valid": False,
            "monitors": []
        }