"""
Utilities Management - Template-based Refactored Version
System utilities, metadata management, and helper functions
"""

import logging
import subprocess
import json
import os
import time
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass


class App:
    """
    Utility application flow controller.
    Manages system utilities, metadata, and helper operations.
    """
    
    @staticmethod
    def ScanWallpapers():
        """Scans and indexes available wallpapers"""
        Flow.WallpaperScanner.Discover_Wallpapers()
        Flow.WallpaperScanner.Extract_Metadata()
        Flow.WallpaperScanner.Build_Search_Index()
    
    @staticmethod
    def MonitorSystem():
        """Monitors system resources and processes"""
        Flow.SystemMonitor.Check_Processes()
        Flow.SystemMonitor.Monitor_Resources()
        Flow.SystemMonitor.Update_Statistics()
    
    @staticmethod
    def ManageFiles():
        """Manages file operations and monitoring"""
        Flow.FileManager.Monitor_Changes()
        Flow.FileManager.Validate_Paths()
        Flow.FileManager.Cleanup_Temporary()


class Flow:
    """
    Utility algorithm implementations.
    Clear, descriptive functions for system operations.
    """
    
    class WallpaperScanner:
        """Wallpaper discovery and metadata extraction flow"""
        
        @staticmethod
        def Discover_Wallpapers():
            """
            Discovers available wallpapers in Steam Workshop directories.
            Scans filesystem for valid wallpaper installations.
            """
            _workshop_paths = Bundle.PathResolver.get_workshop_paths()
            Collect.WallpaperData.discovered_wallpapers.clear()
            
            for _workshop_path in _workshop_paths:
                if _workshop_path.exists():
                    Flow.WallpaperScanner._Scan_Workshop_Directory(_workshop_path)
            
            _count = len(Collect.WallpaperData.discovered_wallpapers)
            logging.info(f"Discovered {_count} wallpapers")
        
        @staticmethod
        def Extract_Metadata():
            """
            Extracts metadata from discovered wallpapers.
            Reads project.json files and builds metadata cache.
            """
            _metadata_count = 0
            
            for _wallpaper_id, _wallpaper_path in Collect.WallpaperData.discovered_wallpapers:
                _metadata = Flow.WallpaperScanner._Extract_Wallpaper_Metadata(_wallpaper_path)
                if _metadata:
                    Collect.MetadataCache.wallpaper_metadata[_wallpaper_id] = _metadata
                    _metadata_count += 1
            
            logging.info(f"Extracted metadata for {_metadata_count} wallpapers")
        
        @staticmethod
        def Build_Search_Index():
            """
            Builds search index for fast wallpaper lookup.
            Creates searchable index based on titles, tags, and descriptions.
            """
            Collect.SearchIndex.title_index.clear()
            Collect.SearchIndex.tag_index.clear()
            Collect.SearchIndex.description_index.clear()
            
            for _wallpaper_id, _metadata in Collect.MetadataCache.wallpaper_metadata.items():
                Flow.WallpaperScanner._Index_Wallpaper_Metadata(_wallpaper_id, _metadata)
            
            _indexed_count = len(Collect.SearchIndex.title_index)
            logging.info(f"Built search index for {_indexed_count} wallpapers")
        
        @staticmethod
        def _Scan_Workshop_Directory(_workshop_path: Path):
            """Scans a Steam Workshop directory for wallpapers"""
            try:
                for _item in _workshop_path.iterdir():
                    if _item.is_dir() and _item.name.isdigit():
                        _wallpaper_id = _item.name
                        if Bundle.WallpaperValidator.is_valid_wallpaper(_item):
                            Collect.WallpaperData.discovered_wallpapers.append((_wallpaper_id, _item))
                            
            except Exception as e:
                logging.error(f"Error scanning workshop directory {_workshop_path}: {e}")
        
        @staticmethod
        def _Extract_Wallpaper_Metadata(_wallpaper_path: Path) -> Optional[Dict[str, Any]]:
            """Extracts metadata from wallpaper directory"""
            try:
                _project_file = _wallpaper_path / "project.json"
                if _project_file.exists():
                    with open(_project_file, 'r', encoding='utf-8') as f:
                        _project_data = json.load(f)
                    
                    return {
                        "title": _project_data.get("title", "Unknown"),
                        "description": _project_data.get("description", ""),
                        "tags": _project_data.get("tags", []),
                        "type": _project_data.get("type", "unknown"),
                        "file": _project_data.get("file", ""),
                        "preview": _project_data.get("preview", ""),
                        "workshop_id": _wallpaper_path.name
                    }
                    
            except Exception as e:
                logging.debug(f"Failed to extract metadata from {_wallpaper_path}: {e}")
            
            return None
        
        @staticmethod
        def _Index_Wallpaper_Metadata(_wallpaper_id: str, _metadata: Dict[str, Any]):
            """Indexes wallpaper metadata for search"""
            # Index by title
            _title = _metadata.get("title", "").lower()
            if _title:
                if _title not in Collect.SearchIndex.title_index:
                    Collect.SearchIndex.title_index[_title] = []
                Collect.SearchIndex.title_index[_title].append(_wallpaper_id)
            
            # Index by tags
            _tags = _metadata.get("tags", [])
            for _tag in _tags:
                _tag_lower = _tag.lower()
                if _tag_lower not in Collect.SearchIndex.tag_index:
                    Collect.SearchIndex.tag_index[_tag_lower] = []
                Collect.SearchIndex.tag_index[_tag_lower].append(_wallpaper_id)
            
            # Index by description keywords
            _description = _metadata.get("description", "").lower()
            if _description:
                _keywords = _description.split()
                for _keyword in _keywords:
                    if len(_keyword) > 3:  # Only index meaningful words
                        if _keyword not in Collect.SearchIndex.description_index:
                            Collect.SearchIndex.description_index[_keyword] = []
                        Collect.SearchIndex.description_index[_keyword].append(_wallpaper_id)
    
    class SystemMonitor:
        """System monitoring and process management flow"""
        
        @staticmethod
        def Check_Processes():
            """
            Checks running wallpaper engine processes.
            Monitors process health and resource usage.
            """
            _running_processes = Bundle.ProcessScanner.find_wallpaper_processes()
            Collect.SystemData.running_processes = _running_processes
            
            # Update process statistics
            for _process_info in _running_processes:
                Flow.SystemMonitor._Update_Process_Statistics(_process_info)
            
            logging.debug(f"Found {len(_running_processes)} wallpaper processes")
        
        @staticmethod
        def Monitor_Resources():
            """
            Monitors system resource usage.
            Tracks CPU, memory, and GPU utilization.
            """
            try:
                _cpu_usage = Bundle.ResourceMonitor.get_cpu_usage()
                _memory_usage = Bundle.ResourceMonitor.get_memory_usage()
                _gpu_usage = Bundle.ResourceMonitor.get_gpu_usage()
                
                # Store current readings
                Collect.SystemData.current_cpu = _cpu_usage
                Collect.SystemData.current_memory = _memory_usage
                Collect.SystemData.current_gpu = _gpu_usage
                
                # Update history
                Flow.SystemMonitor._Update_Resource_History(_cpu_usage, _memory_usage, _gpu_usage)
                
            except Exception as e:
                logging.error(f"Resource monitoring error: {e}")
        
        @staticmethod
        def Update_Statistics():
            """
            Updates system statistics and metrics.
            Calculates averages and trends.
            """
            # Calculate CPU average
            if Collect.SystemData.cpu_history:
                _cpu_avg = sum(Collect.SystemData.cpu_history) / len(Collect.SystemData.cpu_history)
                Collect.SystemData.cpu_average = _cpu_avg
            
            # Calculate memory average
            if Collect.SystemData.memory_history:
                _mem_avg = sum(Collect.SystemData.memory_history) / len(Collect.SystemData.memory_history)
                Collect.SystemData.memory_average = _mem_avg
            
            # Update timestamp
            Collect.SystemData.last_update = time.time()
        
        @staticmethod
        def _Update_Process_Statistics(_process_info: Dict[str, Any]):
            """Updates statistics for a specific process"""
            _pid = _process_info.get("pid")
            if _pid:
                if _pid not in Collect.SystemData.process_stats:
                    Collect.SystemData.process_stats[_pid] = {
                        "cpu_samples": [],
                        "memory_samples": [],
                        "start_time": time.time()
                    }
                
                _stats = Collect.SystemData.process_stats[_pid]
                _stats["cpu_samples"].append(_process_info.get("cpu_percent", 0))
                _stats["memory_samples"].append(_process_info.get("memory_mb", 0))
                
                # Keep only last 100 samples
                if len(_stats["cpu_samples"]) > 100:
                    _stats["cpu_samples"].pop(0)
                if len(_stats["memory_samples"]) > 100:
                    _stats["memory_samples"].pop(0)
        
        @staticmethod
        def _Update_Resource_History(_cpu: float, _memory: float, _gpu: str):
            """Updates resource usage history"""
            # Add to history
            Collect.SystemData.cpu_history.append(_cpu)
            Collect.SystemData.memory_history.append(_memory)
            
            # Keep only last 60 readings (2 minutes at 2-second intervals)
            if len(Collect.SystemData.cpu_history) > 60:
                Collect.SystemData.cpu_history.pop(0)
            if len(Collect.SystemData.memory_history) > 60:
                Collect.SystemData.memory_history.pop(0)
    
    class FileManager:
        """File management and monitoring flow"""
        
        @staticmethod
        def Monitor_Changes():
            """
            Monitors file system changes in wallpaper directories.
            Detects new wallpaper installations and removals.
            """
            _workshop_paths = Bundle.PathResolver.get_workshop_paths()
            _current_wallpapers = set()
            
            for _workshop_path in _workshop_paths:
                if _workshop_path.exists():
                    _wallpapers = Flow.FileManager._Get_Directory_Wallpapers(_workshop_path)
                    _current_wallpapers.update(_wallpapers)
            
            # Compare with previous scan
            _previous_wallpapers = set(Collect.FileSystemData.known_wallpapers)
            _new_wallpapers = _current_wallpapers - _previous_wallpapers
            _removed_wallpapers = _previous_wallpapers - _current_wallpapers
            
            if _new_wallpapers:
                logging.info(f"New wallpapers detected: {len(_new_wallpapers)}")
                Collect.FileSystemData.new_wallpapers.extend(_new_wallpapers)
            
            if _removed_wallpapers:
                logging.info(f"Wallpapers removed: {len(_removed_wallpapers)}")
                Collect.FileSystemData.removed_wallpapers.extend(_removed_wallpapers)
            
            # Update known wallpapers
            Collect.FileSystemData.known_wallpapers = list(_current_wallpapers)
        
        @staticmethod
        def Validate_Paths():
            """
            Validates wallpaper paths and accessibility.
            Checks for corrupted or inaccessible wallpapers.
            """
            _invalid_count = 0
            
            for _wallpaper_id in Collect.FileSystemData.known_wallpapers:
                if not Bundle.WallpaperValidator.validate_wallpaper_path(_wallpaper_id):
                    Collect.FileSystemData.invalid_wallpapers.append(_wallpaper_id)
                    _invalid_count += 1
            
            if _invalid_count > 0:
                logging.warning(f"Found {_invalid_count} invalid wallpapers")
        
        @staticmethod
        def Cleanup_Temporary():
            """
            Cleans up temporary files and caches.
            Removes old log files and temporary data.
            """
            try:
                _temp_dir = Bundle.PathResolver.get_temp_directory()
                if _temp_dir.exists():
                    _cleaned_files = 0
                    for _file in _temp_dir.iterdir():
                        if _file.is_file() and Flow.FileManager._Should_Clean_File(_file):
                            _file.unlink()
                            _cleaned_files += 1
                    
                    if _cleaned_files > 0:
                        logging.info(f"Cleaned {_cleaned_files} temporary files")
                        
            except Exception as e:
                logging.error(f"Cleanup error: {e}")
        
        @staticmethod
        def _Get_Directory_Wallpapers(_directory: Path) -> List[str]:
            """Gets wallpaper IDs from directory"""
            _wallpapers = []
            try:
                for _item in _directory.iterdir():
                    if _item.is_dir() and _item.name.isdigit():
                        _wallpapers.append(_item.name)
            except Exception as e:
                logging.error(f"Error reading directory {_directory}: {e}")
            return _wallpapers
        
        @staticmethod
        def _Should_Clean_File(_file: Path) -> bool:
            """Determines if file should be cleaned up"""
            try:
                # Clean files older than 7 days
                _file_age = time.time() - _file.stat().st_mtime
                return _file_age > (7 * 24 * 3600)  # 7 days in seconds
            except:
                return False
    
    class SearchEngine:
        """Search functionality flow"""
        
        @staticmethod
        def Search_Wallpapers(_query: str, _filters: Dict[str, Any] = None) -> List[str]:
            """
            Searches wallpapers based on query and filters.
            Returns list of matching wallpaper IDs.
            """
            if not _query.strip():
                return []
            
            _query_lower = _query.lower()
            _results = set()
            
            # Search in titles
            _title_matches = Flow.SearchEngine._Search_In_Index(
                _query_lower, Collect.SearchIndex.title_index
            )
            _results.update(_title_matches)
            
            # Search in tags
            _tag_matches = Flow.SearchEngine._Search_In_Index(
                _query_lower, Collect.SearchIndex.tag_index
            )
            _results.update(_tag_matches)
            
            # Search in descriptions
            _desc_matches = Flow.SearchEngine._Search_In_Index(
                _query_lower, Collect.SearchIndex.description_index
            )
            _results.update(_desc_matches)
            
            # Apply filters if provided
            if _filters:
                _results = Flow.SearchEngine._Apply_Filters(_results, _filters)
            
            return list(_results)
        
        @staticmethod
        def _Search_In_Index(_query: str, _index: Dict[str, List[str]]) -> List[str]:
            """Searches for query in specific index"""
            _matches = []
            for _key, _wallpaper_ids in _index.items():
                if _query in _key:
                    _matches.extend(_wallpaper_ids)
            return _matches
        
        @staticmethod
        def _Apply_Filters(_results: set, _filters: Dict[str, Any]) -> set:
            """Applies filters to search results"""
            _filtered_results = set()
            
            for _wallpaper_id in _results:
                _metadata = Collect.MetadataCache.wallpaper_metadata.get(_wallpaper_id)
                if _metadata and Flow.SearchEngine._Matches_Filters(_metadata, _filters):
                    _filtered_results.add(_wallpaper_id)
            
            return _filtered_results
        
        @staticmethod
        def _Matches_Filters(_metadata: Dict[str, Any], _filters: Dict[str, Any]) -> bool:
            """Checks if metadata matches filters"""
            # Type filter
            if "type" in _filters:
                if _metadata.get("type") != _filters["type"]:
                    return False
            
            # Tag filter
            if "tags" in _filters:
                _required_tags = _filters["tags"]
                _wallpaper_tags = _metadata.get("tags", [])
                if not any(_tag in _wallpaper_tags for _tag in _required_tags):
                    return False
            
            return True


class Bundle:
    """
    Utility wrappers and helper functions.
    Provides abstraction for system operations.
    """
    
    class PathResolver:
        """Path resolution utilities"""
        
        @staticmethod
        def get_workshop_paths() -> List[Path]:
            """Gets Steam Workshop paths"""
            from utils.constants import STEAM_WORKSHOP_PATH
            _base_path = Path(STEAM_WORKSHOP_PATH)
            return [_base_path] if _base_path.exists() else []
        
        @staticmethod
        def get_temp_directory() -> Path:
            """Gets temporary directory path"""
            return Path.home() / ".config" / "wallpaper_engine" / "temp"
        
        @staticmethod
        def get_cache_directory() -> Path:
            """Gets cache directory path"""
            return Path.home() / ".config" / "wallpaper_engine" / "cache"
    
    class WallpaperValidator:
        """Wallpaper validation utilities"""
        
        @staticmethod
        def is_valid_wallpaper(_wallpaper_path: Path) -> bool:
            """Checks if directory contains valid wallpaper"""
            try:
                # Check for project.json
                _project_file = _wallpaper_path / "project.json"
                if not _project_file.exists():
                    return False
                
                # Check for scene.pkg or main wallpaper file
                _scene_file = _wallpaper_path / "scene.pkg"
                if _scene_file.exists():
                    return True
                
                # Check for other common wallpaper files
                _common_files = ["index.html", "main.exe", "wallpaper.mp4"]
                for _file_name in _common_files:
                    if (_wallpaper_path / _file_name).exists():
                        return True
                
                return False
                
            except Exception:
                return False
        
        @staticmethod
        def validate_wallpaper_path(_wallpaper_id: str) -> bool:
            """Validates wallpaper path by ID"""
            from utils.system_utils import validate_wallpaper_path
            return validate_wallpaper_path(_wallpaper_id)
    
    class ProcessScanner:
        """Process scanning utilities"""
        
        @staticmethod
        def find_wallpaper_processes() -> List[Dict[str, Any]]:
            """Finds running wallpaper engine processes"""
            try:
                import psutil
                _processes = []
                
                for _proc in psutil.process_iter(['pid', 'name', 'cmdline', 'exe']):
                    try:
                        _proc_info = _proc.info
                        _proc_name = _proc_info.get('name', '')
                        
                        if Bundle.ProcessScanner._is_wallpaper_process(_proc_info):
                            _process_data = {
                                "pid": _proc_info['pid'],
                                "name": _proc_name,
                                "exe": _proc_info.get('exe', 'N/A'),
                                "cpu_percent": _proc.cpu_percent(),
                                "memory_mb": _proc.memory_info().rss / 1024 / 1024
                            }
                            _processes.append(_process_data)
                            
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
                
                return _processes
                
            except Exception as e:
                logging.error(f"Process scanning error: {e}")
                return []
        
        @staticmethod
        def _is_wallpaper_process(_proc_info: Dict[str, Any]) -> bool:
            """Checks if process is a wallpaper engine process"""
            _proc_name = _proc_info.get('name', '').lower()
            _cmdline = _proc_info.get('cmdline', [])
            _exe = _proc_info.get('exe', '').lower()
            
            # Check process name
            if 'wallpaperengine' in _proc_name or 'wallpaper-engine' in _proc_name:
                return True
            
            # Check command line
            if _cmdline:
                _cmdline_str = ' '.join(_cmdline).lower()
                if 'wallpaperengine' in _cmdline_str or 'wallpaper-engine' in _cmdline_str:
                    return True
            
            # Check executable path
            if 'wallpaperengine' in _exe:
                return True
            
            return False
    
    class ResourceMonitor:
        """System resource monitoring utilities"""
        
        @staticmethod
        def get_cpu_usage() -> float:
            """Gets system CPU usage percentage"""
            try:
                import psutil
                return psutil.cpu_percent(interval=0.1)
            except:
                return 0.0
        
        @staticmethod
        def get_memory_usage() -> float:
            """Gets system memory usage percentage"""
            try:
                import psutil
                return psutil.virtual_memory().percent
            except:
                return 0.0
        
        @staticmethod
        def get_gpu_usage() -> str:
            """Gets GPU usage information"""
            try:
                # Try NVIDIA first
                _nvidia_info = Bundle.ResourceMonitor._get_nvidia_usage()
                if _nvidia_info:
                    return _nvidia_info
                
                # Try AMD
                _amd_info = Bundle.ResourceMonitor._get_amd_usage()
                if _amd_info:
                    return _amd_info
                
                # Try Intel
                _intel_info = Bundle.ResourceMonitor._get_intel_usage()
                if _intel_info:
                    return _intel_info
                
                return "N/A"
                
            except Exception:
                return "Error"
        
        @staticmethod
        def _get_nvidia_usage() -> Optional[str]:
            """Gets NVIDIA GPU usage"""
            try:
                _result = subprocess.run(
                    ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
                    capture_output=True, text=True, timeout=2
                )
                if _result.returncode == 0:
                    _usage = _result.stdout.strip()
                    if _usage and _usage.isdigit():
                        return f"{_usage}%"
            except:
                pass
            return None
        
        @staticmethod
        def _get_amd_usage() -> Optional[str]:
            """Gets AMD GPU usage"""
            try:
                _result = subprocess.run(
                    ['rocm-smi', '--showuse'],
                    capture_output=True, text=True, timeout=2
                )
                if _result.returncode == 0 and '%' in _result.stdout:
                    _lines = _result.stdout.strip().split('\n')
                    for _line in _lines:
                        if 'GPU' in _line and '%' in _line:
                            _parts = _line.split()
                            for _part in _parts:
                                if '%' in _part and _part.replace('%', '').isdigit():
                                    return _part
            except:
                pass
            return None
        
        @staticmethod
        def _get_intel_usage() -> Optional[str]:
            """Gets Intel GPU usage"""
            try:
                _result = subprocess.run(
                    ['intel_gpu_top', '-s', '1000'],
                    capture_output=True, text=True, timeout=2
                )
                if _result.returncode == 0 and 'Render/3D' in _result.stdout:
                    _lines = _result.stdout.strip().split('\n')
                    for _line in _lines:
                        if 'Render/3D' in _line and '%' in _line:
                            _parts = _line.split()
                            for _part in _parts:
                                if '%' in _part:
                                    return _part
            except:
                pass
            return None


class Alias:
    """
    Shared utility variables and state.
    Provides global state for utility operations.
    """
    
    class ScannerState:
        """Wallpaper scanner state"""
        is_scanning: bool = False
        last_scan_time: Optional[float] = None
        scan_progress: float = 0.0
    
    class MonitorState:
        """System monitor state"""
        monitoring_enabled: bool = True
        update_interval: int = 2000  # milliseconds
        last_update: Optional[float] = None
    
    class SearchState:
        """Search engine state"""
        last_query: str = ""
        last_results: List[str] = []
        search_time: Optional[float] = None


class Collect:
    """
    Data collection for utility operations.
    Organized by data type and functionality.
    """
    
    class WallpaperData:
        """Discovered wallpaper data"""
        discovered_wallpapers: List[Tuple[str, Path]] = []
        preview_paths: List[Tuple[str, Path]] = []
    
    class MetadataCache:
        """Wallpaper metadata cache"""
        wallpaper_metadata: Dict[str, Dict[str, Any]] = {}
        metadata_timestamps: Dict[str, float] = {}
    
    class SearchIndex:
        """Search index data"""
        title_index: Dict[str, List[str]] = {}
        tag_index: Dict[str, List[str]] = {}
        description_index: Dict[str, List[str]] = {}
    
    class SystemData:
        """System monitoring data"""
        running_processes: List[Dict[str, Any]] = []
        current_cpu: float = 0.0
        current_memory: float = 0.0
        current_gpu: str = "N/A"
        cpu_history: List[float] = []
        memory_history: List[float] = []
        cpu_average: float = 0.0
        memory_average: float = 0.0
        last_update: Optional[float] = None
        process_stats: Dict[int, Dict[str, Any]] = {}
    
    class FileSystemData:
        """File system monitoring data"""
        known_wallpapers: List[str] = []
        new_wallpapers: List[str] = []
        removed_wallpapers: List[str] = []
        invalid_wallpapers: List[str] = []
        last_scan: Optional[float] = None


@dataclass
class WallpaperMetadata:
    """Wallpaper metadata structure"""
    workshop_id: str
    title: str
    description: str
    tags: List[str]
    type: str
    file: str
    preview: str
    
    def matches_query(self, _query: str) -> bool:
        """Checks if metadata matches search query"""
        _query_lower = _query.lower()
        return (
            _query_lower in self.title.lower() or
            _query_lower in self.description.lower() or
            any(_query_lower in _tag.lower() for _tag in self.tags) or
            _query_lower in self.workshop_id
        )