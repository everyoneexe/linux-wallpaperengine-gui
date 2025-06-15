"""
Core Engine Management - Template-based Refactored Version
Wallpaper engine core functionality with clear flow organization
"""

import logging
import subprocess
import json
import random
from typing import Optional, List, Dict, Any
from pathlib import Path

from utils import validate_wallpaper_path, kill_existing_wallpapers, WALLPAPER_ENGINE_BINARY


class App:
    """
    Core application flow controller.
    Manages wallpaper engine operations and playlist functionality.
    """
    
    @staticmethod
    def StartWallpaper(_wallpaper_id: str, **_kwargs):
        """Starts wallpaper with specified parameters"""
        Flow.WallpaperEngine.Validate_Wallpaper(_wallpaper_id)
        Flow.WallpaperEngine.Prepare_Command(_wallpaper_id, **_kwargs)
        Flow.WallpaperEngine.Execute_Wallpaper()
        Flow.WallpaperEngine.Update_State(_wallpaper_id)
    
    @staticmethod
    def ManagePlaylist():
        """Manages playlist operations"""
        Flow.PlaylistManager.Load_Settings()
        Flow.PlaylistManager.Initialize_State()
        Flow.PlaylistManager.Setup_Persistence()
    
    @staticmethod
    def ControlWallpaper():
        """Manages dynamic wallpaper control"""
        Flow.WallpaperController.Initialize_Controller()
        Flow.WallpaperController.Setup_Dynamic_Controls()
        Flow.WallpaperController.Monitor_Process()


class Flow:
    """
    Core algorithm implementations.
    Each class represents a major functional area with clear responsibilities.
    """
    
    class WallpaperEngine:
        """Wallpaper engine execution and management flow"""
        
        @staticmethod
        def Validate_Wallpaper(_wallpaper_id: str) -> bool:
            """
            Validates wallpaper exists and is accessible.
            Checks file system paths and wallpaper integrity.
            """
            if not _wallpaper_id:
                logging.error("Wallpaper ID is empty")
                return False
            
            _is_valid = validate_wallpaper_path(_wallpaper_id)
            if not _is_valid:
                logging.error(f"Invalid wallpaper: {_wallpaper_id}")
                return False
            
            Alias.WallpaperState.validated_wallpaper = _wallpaper_id
            logging.info(f"Wallpaper validated: {_wallpaper_id}")
            return True
        
        @staticmethod
        def Prepare_Command(_wallpaper_id: str, **_kwargs):
            """
            Prepares wallpaper engine command with all parameters.
            Builds command line arguments based on user settings.
            """
            _base_cmd = [WALLPAPER_ENGINE_BINARY]
            
            # Add wallpaper path
            _wallpaper_path = Bundle.PathResolver.get_wallpaper_path(_wallpaper_id)
            _base_cmd.extend(["--dir", str(_wallpaper_path)])
            
            # Add screen parameter
            _screen = _kwargs.get("screen", "eDP-1")
            _base_cmd.extend(["--screen-root", _screen])
            
            # Add audio settings
            _volume = _kwargs.get("volume", 50)
            _base_cmd.extend(["--volume", str(_volume)])
            
            # Add FPS setting
            _fps = _kwargs.get("fps", 60)
            _base_cmd.extend(["--fps", str(_fps)])
            
            # Add boolean flags
            if _kwargs.get("noautomute", False):
                _base_cmd.append("--noautomute")
            
            if _kwargs.get("no_audio_processing", False):
                _base_cmd.append("--no-audio-processing")
            
            if _kwargs.get("disable_mouse", False):
                _base_cmd.append("--disable-mouse")
            
            Alias.WallpaperState.prepared_command = _base_cmd
            Alias.WallpaperState.command_kwargs = _kwargs.copy()
            
            logging.info(f"Command prepared: {' '.join(_base_cmd)}")
        
        @staticmethod
        def Execute_Wallpaper() -> bool:
            """
            Executes wallpaper engine with prepared command.
            Handles process management and error handling.
            """
            if not hasattr(Alias.WallpaperState, 'prepared_command'):
                logging.error("No command prepared for execution")
                return False
            
            try:
                # Kill existing wallpaper processes
                Flow.WallpaperEngine._Kill_Existing_Processes()
                
                # Start new wallpaper process
                _cmd = Alias.WallpaperState.prepared_command
                _process = subprocess.Popen(
                    _cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True  # Detached process
                )
                
                Alias.WallpaperState.current_process = _process
                Alias.WallpaperState.process_pid = _process.pid
                
                logging.info(f"Wallpaper process started: PID {_process.pid}")
                return True
                
            except Exception as e:
                logging.error(f"Failed to execute wallpaper: {e}")
                return False
        
        @staticmethod
        def Update_State(_wallpaper_id: str):
            """
            Updates wallpaper engine state after successful execution.
            Records current wallpaper and execution parameters.
            """
            Alias.WallpaperState.current_wallpaper = _wallpaper_id
            Alias.WallpaperState.is_running = True
            Alias.WallpaperState.last_applied_time = Bundle.TimeUtils.get_current_timestamp()
            
            # Store execution history
            _execution_record = {
                "wallpaper_id": _wallpaper_id,
                "timestamp": Alias.WallpaperState.last_applied_time,
                "command": Alias.WallpaperState.prepared_command,
                "kwargs": Alias.WallpaperState.command_kwargs
            }
            
            Collect.ExecutionHistory.recent_executions.append(_execution_record)
            
            # Keep only last 10 executions
            if len(Collect.ExecutionHistory.recent_executions) > 10:
                Collect.ExecutionHistory.recent_executions.pop(0)
            
            logging.info(f"Wallpaper state updated: {_wallpaper_id}")
        
        @staticmethod
        def _Kill_Existing_Processes():
            """Kills existing wallpaper engine processes"""
            try:
                _killed = kill_existing_wallpapers()
                if _killed:
                    logging.info("Existing wallpaper processes terminated")
                    # Reset state
                    Alias.WallpaperState.current_process = None
                    Alias.WallpaperState.process_pid = None
                    Alias.WallpaperState.is_running = False
            except Exception as e:
                logging.warning(f"Failed to kill existing processes: {e}")
    
    class PlaylistManager:
        """Playlist management and persistence flow"""
        
        @staticmethod
        def Load_Settings():
            """
            Loads playlist settings from persistent storage.
            Initializes playlist state and user preferences.
            """
            _settings_path = Bundle.PathResolver.get_settings_path()
            
            try:
                if _settings_path.exists():
                    with open(_settings_path, 'r', encoding='utf-8') as f:
                        _data = json.load(f)
                    
                    # Load playlist settings
                    Alias.PlaylistState.timer_interval = _data.get('timer_interval', 30)
                    Alias.PlaylistState.is_random = _data.get('is_random', False)
                    Alias.PlaylistState.is_playing = _data.get('is_playing', False)
                    Alias.PlaylistState.current_index = _data.get('current_index', 0)
                    
                    # Load playlists
                    Collect.PlaylistData.saved_playlists = _data.get('playlists', {})
                    Collect.PlaylistData.recent_wallpapers = _data.get('recent', [])
                    
                    # Load current playlist
                    _current_playlist = _data.get('current_playlist', [])
                    Alias.PlaylistState.current_playlist = _current_playlist
                    
                    logging.info(f"Playlist settings loaded: {len(_current_playlist)} items")
                else:
                    Flow.PlaylistManager._Initialize_Default_Settings()
                    
            except Exception as e:
                logging.error(f"Failed to load playlist settings: {e}")
                Flow.PlaylistManager._Initialize_Default_Settings()
        
        @staticmethod
        def Initialize_State():
            """
            Initializes playlist manager state.
            Sets up internal data structures and validates loaded data.
            """
            # Validate current index
            _playlist_length = len(Alias.PlaylistState.current_playlist)
            if Alias.PlaylistState.current_index >= _playlist_length:
                Alias.PlaylistState.current_index = 0
            
            # Initialize runtime state
            Alias.PlaylistState.last_wallpaper = None
            Alias.PlaylistState.shuffle_history = []
            
            logging.info("Playlist manager state initialized")
        
        @staticmethod
        def Setup_Persistence():
            """
            Sets up automatic persistence for playlist changes.
            Ensures settings are saved when modified.
            """
            # This would be called whenever playlist state changes
            # Implementation depends on UI framework integration
            pass
        
        @staticmethod
        def Add_To_Current_Playlist(_wallpaper_id: str) -> bool:
            """
            Adds wallpaper to current playlist.
            Prevents duplicates and maintains playlist integrity.
            """
            if _wallpaper_id in Alias.PlaylistState.current_playlist:
                logging.debug(f"Wallpaper already in playlist: {_wallpaper_id}")
                return False
            
            Alias.PlaylistState.current_playlist.append(_wallpaper_id)
            Flow.PlaylistManager._Save_Settings()
            
            logging.info(f"Added to playlist: {_wallpaper_id}")
            return True
        
        @staticmethod
        def Remove_From_Current_Playlist(_index: int) -> Optional[str]:
            """
            Removes wallpaper from current playlist by index.
            Adjusts current index if necessary.
            """
            if 0 <= _index < len(Alias.PlaylistState.current_playlist):
                _removed = Alias.PlaylistState.current_playlist.pop(_index)
                
                # Adjust current index if necessary
                if Alias.PlaylistState.current_index >= _index:
                    Alias.PlaylistState.current_index = max(0, Alias.PlaylistState.current_index - 1)
                
                Flow.PlaylistManager._Save_Settings()
                logging.info(f"Removed from playlist: {_removed}")
                return _removed
            
            return None
        
        @staticmethod
        def Get_Next_Wallpaper(_is_random: bool = False) -> Optional[str]:
            """
            Gets next wallpaper from playlist.
            Supports both sequential and random playback modes.
            """
            if not Alias.PlaylistState.current_playlist:
                return None
            
            _playlist_length = len(Alias.PlaylistState.current_playlist)
            
            if _is_random:
                return Flow.PlaylistManager._Get_Random_Wallpaper()
            else:
                return Flow.PlaylistManager._Get_Sequential_Wallpaper()
        
        @staticmethod
        def Get_Previous_Wallpaper() -> Optional[str]:
            """
            Gets previous wallpaper in sequential mode.
            Only works in sequential playback mode.
            """
            if not Alias.PlaylistState.current_playlist:
                return None
            
            _playlist_length = len(Alias.PlaylistState.current_playlist)
            Alias.PlaylistState.current_index = (Alias.PlaylistState.current_index - 1) % _playlist_length
            
            Flow.PlaylistManager._Save_Settings()
            return Alias.PlaylistState.current_playlist[Alias.PlaylistState.current_index]
        
        @staticmethod
        def Add_To_Recent(_wallpaper_id: str):
            """
            Adds wallpaper to recent history.
            Maintains a limited history of recently played wallpapers.
            """
            if _wallpaper_id in Collect.PlaylistData.recent_wallpapers:
                Collect.PlaylistData.recent_wallpapers.remove(_wallpaper_id)
            
            Collect.PlaylistData.recent_wallpapers.insert(0, _wallpaper_id)
            
            # Keep only last 20 recent wallpapers
            if len(Collect.PlaylistData.recent_wallpapers) > 20:
                Collect.PlaylistData.recent_wallpapers = Collect.PlaylistData.recent_wallpapers[:20]
            
            Flow.PlaylistManager._Save_Settings()
        
        @staticmethod
        def _Initialize_Default_Settings():
            """Initializes default playlist settings"""
            Alias.PlaylistState.timer_interval = 30
            Alias.PlaylistState.is_random = False
            Alias.PlaylistState.is_playing = False
            Alias.PlaylistState.current_index = 0
            Alias.PlaylistState.current_playlist = []
            Collect.PlaylistData.saved_playlists = {}
            Collect.PlaylistData.recent_wallpapers = []
            
            logging.info("Default playlist settings initialized")
        
        @staticmethod
        def _Get_Random_Wallpaper() -> str:
            """Gets random wallpaper avoiding recent repeats"""
            _playlist = Alias.PlaylistState.current_playlist
            _available = [w for w in _playlist if w not in Alias.PlaylistState.shuffle_history[-5:]]
            
            if not _available:
                _available = _playlist
                Alias.PlaylistState.shuffle_history.clear()
            
            _selected = random.choice(_available)
            Alias.PlaylistState.shuffle_history.append(_selected)
            
            # Keep shuffle history limited
            if len(Alias.PlaylistState.shuffle_history) > 10:
                Alias.PlaylistState.shuffle_history.pop(0)
            
            Flow.PlaylistManager._Save_Settings()
            return _selected
        
        @staticmethod
        def _Get_Sequential_Wallpaper() -> str:
            """Gets next wallpaper in sequential order"""
            _playlist_length = len(Alias.PlaylistState.current_playlist)
            Alias.PlaylistState.current_index = (Alias.PlaylistState.current_index + 1) % _playlist_length
            
            Flow.PlaylistManager._Save_Settings()
            return Alias.PlaylistState.current_playlist[Alias.PlaylistState.current_index]
        
        @staticmethod
        def _Save_Settings():
            """Saves current playlist settings to persistent storage"""
            try:
                _settings_path = Bundle.PathResolver.get_settings_path()
                _settings_path.parent.mkdir(parents=True, exist_ok=True)
                
                _data = {
                    'timer_interval': Alias.PlaylistState.timer_interval,
                    'is_random': Alias.PlaylistState.is_random,
                    'is_playing': Alias.PlaylistState.is_playing,
                    'current_index': Alias.PlaylistState.current_index,
                    'current_playlist': Alias.PlaylistState.current_playlist,
                    'playlists': Collect.PlaylistData.saved_playlists,
                    'recent': Collect.PlaylistData.recent_wallpapers
                }
                
                with open(_settings_path, 'w', encoding='utf-8') as f:
                    json.dump(_data, f, indent=2, ensure_ascii=False)
                
                logging.debug("Playlist settings saved")
                
            except Exception as e:
                logging.error(f"Failed to save playlist settings: {e}")
    
    class WallpaperController:
        """Dynamic wallpaper control and monitoring flow"""
        
        @staticmethod
        def Initialize_Controller():
            """
            Initializes wallpaper controller for dynamic control.
            Sets up process monitoring and control capabilities.
            """
            Alias.ControllerState.is_initialized = True
            Alias.ControllerState.control_presets = Bundle.PresetManager.load_control_presets()
            
            logging.info("Wallpaper controller initialized")
        
        @staticmethod
        def Setup_Dynamic_Controls():
            """
            Sets up dynamic control capabilities.
            Enables real-time wallpaper parameter modification.
            """
            # Initialize control state
            Alias.ControllerState.current_volume = 50
            Alias.ControllerState.current_fps = 60
            Alias.ControllerState.is_muted = False
            Alias.ControllerState.mouse_disabled = False
            
            logging.info("Dynamic controls setup completed")
        
        @staticmethod
        def Monitor_Process():
            """
            Monitors wallpaper engine process health.
            Tracks process state and resource usage.
            """
            if Alias.WallpaperState.current_process:
                try:
                    _return_code = Alias.WallpaperState.current_process.poll()
                    if _return_code is not None:
                        # Process has terminated
                        Alias.WallpaperState.is_running = False
                        Alias.WallpaperState.current_process = None
                        logging.warning(f"Wallpaper process terminated with code: {_return_code}")
                except Exception as e:
                    logging.error(f"Process monitoring error: {e}")
        
        @staticmethod
        def Set_Volume(_volume: int) -> bool:
            """
            Sets wallpaper volume dynamically.
            Sends volume control commands to running wallpaper.
            """
            if not Flow.WallpaperController._Is_Wallpaper_Running():
                return False
            
            try:
                # Implementation would send volume control signal
                # This is a placeholder for actual volume control
                Alias.ControllerState.current_volume = _volume
                logging.info(f"Volume set to: {_volume}%")
                return True
            except Exception as e:
                logging.error(f"Failed to set volume: {e}")
                return False
        
        @staticmethod
        def Set_FPS(_fps: int) -> bool:
            """
            Sets wallpaper FPS dynamically.
            Adjusts frame rate of running wallpaper.
            """
            if not Flow.WallpaperController._Is_Wallpaper_Running():
                return False
            
            try:
                # Implementation would send FPS control signal
                # This is a placeholder for actual FPS control
                Alias.ControllerState.current_fps = _fps
                logging.info(f"FPS set to: {_fps}")
                return True
            except Exception as e:
                logging.error(f"Failed to set FPS: {e}")
                return False
        
        @staticmethod
        def Toggle_Mute() -> bool:
            """
            Toggles wallpaper audio mute state.
            Mutes or unmutes wallpaper audio.
            """
            if not Flow.WallpaperController._Is_Wallpaper_Running():
                return False
            
            try:
                Alias.ControllerState.is_muted = not Alias.ControllerState.is_muted
                _state = "muted" if Alias.ControllerState.is_muted else "unmuted"
                logging.info(f"Audio {_state}")
                return True
            except Exception as e:
                logging.error(f"Failed to toggle mute: {e}")
                return False
        
        @staticmethod
        def Apply_Preset(_preset_name: str) -> bool:
            """
            Applies predefined control preset.
            Sets multiple parameters according to preset configuration.
            """
            if _preset_name not in Alias.ControllerState.control_presets:
                logging.error(f"Unknown preset: {_preset_name}")
                return False
            
            try:
                _preset = Alias.ControllerState.control_presets[_preset_name]
                
                # Apply preset settings
                if 'volume' in _preset:
                    Flow.WallpaperController.Set_Volume(_preset['volume'])
                
                if 'fps' in _preset:
                    Flow.WallpaperController.Set_FPS(_preset['fps'])
                
                if 'muted' in _preset:
                    if _preset['muted'] != Alias.ControllerState.is_muted:
                        Flow.WallpaperController.Toggle_Mute()
                
                logging.info(f"Preset applied: {_preset_name}")
                return True
                
            except Exception as e:
                logging.error(f"Failed to apply preset {_preset_name}: {e}")
                return False
        
        @staticmethod
        def _Is_Wallpaper_Running() -> bool:
            """Checks if wallpaper is currently running"""
            return (Alias.WallpaperState.is_running and 
                   Alias.WallpaperState.current_process is not None)


class Bundle:
    """
    Helper utilities and wrappers for core functionality.
    Provides abstraction for complex operations.
    """
    
    class PathResolver:
        """Path resolution utilities"""
        
        @staticmethod
        def get_wallpaper_path(_wallpaper_id: str) -> Path:
            """Resolves wallpaper ID to full filesystem path"""
            from utils import STEAM_WORKSHOP_PATH
            return Path(STEAM_WORKSHOP_PATH) / _wallpaper_id
        
        @staticmethod
        def get_settings_path() -> Path:
            """Gets playlist settings file path"""
            return Path.home() / ".config" / "wallpaper_engine" / "playlist_settings.json"
    
    class TimeUtils:
        """Time and timestamp utilities"""
        
        @staticmethod
        def get_current_timestamp() -> float:
            """Gets current timestamp"""
            import time
            return time.time()
    
    class PresetManager:
        """Control preset management"""
        
        @staticmethod
        def load_control_presets() -> Dict[str, Dict[str, Any]]:
            """Loads predefined control presets"""
            return {
                "performance": {"volume": 30, "fps": 30, "muted": False},
                "quality": {"volume": 70, "fps": 60, "muted": False},
                "silent": {"volume": 0, "fps": 30, "muted": True},
                "gaming": {"volume": 20, "fps": 144, "muted": False}
            }
    
    class ProcessManager:
        """Process management utilities"""
        
        @staticmethod
        def is_process_running(_pid: int) -> bool:
            """Checks if process with given PID is running"""
            try:
                import psutil
                return psutil.pid_exists(_pid)
            except:
                return False
        
        @staticmethod
        def get_process_info(_pid: int) -> Optional[Dict[str, Any]]:
            """Gets process information"""
            try:
                import psutil
                _process = psutil.Process(_pid)
                return {
                    "pid": _pid,
                    "name": _process.name(),
                    "cpu_percent": _process.cpu_percent(),
                    "memory_mb": _process.memory_info().rss / 1024 / 1024
                }
            except:
                return None


class Alias:
    """
    Core state management and shared variables.
    Organized by functional area for clarity.
    """
    
    class WallpaperState:
        """Current wallpaper engine state"""
        current_wallpaper: Optional[str] = None
        is_running: bool = False
        current_process: Optional[subprocess.Popen] = None
        process_pid: Optional[int] = None
        validated_wallpaper: Optional[str] = None
        prepared_command: Optional[List[str]] = None
        command_kwargs: Dict[str, Any] = {}
        last_applied_time: Optional[float] = None
    
    class PlaylistState:
        """Playlist manager state"""
        current_playlist: List[str] = []
        timer_interval: int = 30
        is_random: bool = False
        is_playing: bool = False
        current_index: int = 0
        last_wallpaper: Optional[str] = None
        shuffle_history: List[str] = []
    
    class ControllerState:
        """Wallpaper controller state"""
        is_initialized: bool = False
        current_volume: int = 50
        current_fps: int = 60
        is_muted: bool = False
        mouse_disabled: bool = False
        control_presets: Dict[str, Dict[str, Any]] = {}


class Collect:
    """
    Data collection and storage for core functionality.
    Organized by data type and source.
    """
    
    class ExecutionHistory:
        """Wallpaper execution history"""
        recent_executions: List[Dict[str, Any]] = []
        error_log: List[Dict[str, Any]] = []
    
    class PlaylistData:
        """Playlist and user data"""
        saved_playlists: Dict[str, List[str]] = {}
        recent_wallpapers: List[str] = []
        playlist_statistics: Dict[str, int] = {}
    
    class ProcessData:
        """Process monitoring data"""
        process_history: List[Dict[str, Any]] = []
        performance_metrics: Dict[str, List[float]] = {}
        resource_usage: Dict[str, float] = {}