"""
FFmpeg-based media processing utilities
Uniform media support with Sixel approach
"""
import subprocess
import logging
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import shutil

logger = logging.getLogger(__name__)


class FFmpegProcessor:
    """FFmpeg-based media processing class"""
    
    def __init__(self):
        self.ffmpeg_available = self._check_ffmpeg()
        self.ffprobe_available = self._check_ffprobe()
        
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is installed"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                timeout=5
            )
            available = result.returncode == 0
            if available:
                logger.info("FFmpeg found and ready to use")
            else:
                logger.warning("FFmpeg not found - some features may not work")
            return available
        except Exception as e:
            logger.warning(f"FFmpeg check failed: {e}")
            return False
    
    def _check_ffprobe(self) -> bool:
        """Check if FFprobe is installed"""
        try:
            result = subprocess.run(
                ["ffprobe", "-version"],
                capture_output=True,
                timeout=5
            )
            available = result.returncode == 0
            if available:
                logger.info("FFprobe found and ready to use")
            else:
                logger.warning("FFprobe not found - metadata features may not work")
            return available
        except Exception as e:
            logger.warning(f"FFprobe check failed: {e}")
            return False
    
    def get_media_info(self, media_path: Union[str, Path]) -> Optional[Dict]:
        """
        Get detailed information about media file
        
        Args:
            media_path: Media file path
            
        Returns:
            Dict: Media information or None
        """
        if not self.ffprobe_available:
            logger.warning("FFprobe not available - returning basic info")
            return self._get_basic_info(media_path)
        
        try:
            media_path = Path(media_path)
            if not media_path.exists():
                logger.error(f"Media file not found: {media_path}")
                return None
            
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(media_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"FFprobe error: {result.stderr}")
                return self._get_basic_info(media_path)
            
            data = json.loads(result.stdout)
            return self._parse_media_info(data, media_path)
            
        except Exception as e:
            logger.error(f"Error getting media info: {e}")
            return self._get_basic_info(media_path)
    
    def _get_basic_info(self, media_path: Union[str, Path]) -> Dict:
        """Get basic info without FFprobe"""
        media_path = Path(media_path)
        return {
            "filename": media_path.name,
            "path": str(media_path),
            "size": media_path.stat().st_size if media_path.exists() else 0,
            "format": media_path.suffix.lower().lstrip('.'),
            "type": self._detect_media_type(media_path),
            "ffmpeg_available": False
        }
    
    def _parse_media_info(self, data: Dict, media_path: Path) -> Dict:
        """Parse FFprobe output"""
        format_info = data.get("format", {})
        streams = data.get("streams", [])
        
        # Find video stream
        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
        
        info = {
            "filename": media_path.name,
            "path": str(media_path),
            "size": int(format_info.get("size", 0)),
            "format": format_info.get("format_name", "unknown"),
            "duration": float(format_info.get("duration", 0)),
            "bitrate": int(format_info.get("bit_rate", 0)),
            "type": self._detect_media_type(media_path),
            "ffmpeg_available": True
        }
        
        # Video information
        if video_stream:
            info.update({
                "width": video_stream.get("width", 0),
                "height": video_stream.get("height", 0),
                "fps": self._parse_fps(video_stream.get("r_frame_rate", "0/1")),
                "video_codec": video_stream.get("codec_name", "unknown"),
                "pixel_format": video_stream.get("pix_fmt", "unknown")
            })
        
        # Audio information
        if audio_stream:
            info.update({
                "has_audio": True,
                "audio_codec": audio_stream.get("codec_name", "unknown"),
                "sample_rate": int(audio_stream.get("sample_rate", 0)),
                "channels": int(audio_stream.get("channels", 0))
            })
        else:
            info["has_audio"] = False
        
        return info
    
    def _detect_media_type(self, media_path: Path) -> str:
        """Detect media type from file extension"""
        ext = media_path.suffix.lower()
        if ext in ['.mp4', '.webm', '.mov', '.avi', '.mkv']:
            return "video"
        elif ext in ['.gif']:
            return "animated_image"
        elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
            return "image"
        else:
            return "unknown"
    
    def _parse_fps(self, fps_string: str) -> float:
        """Parse FPS string (e.g. "30/1" -> 30.0)"""
        try:
            if '/' in fps_string:
                num, den = fps_string.split('/')
                return float(num) / float(den) if float(den) != 0 else 0
            return float(fps_string)
        except:
            return 0.0
    
    def generate_thumbnail(self, media_path: Union[str, Path],
                          output_path: Union[str, Path],
                          size: Tuple[int, int] = (300, 200),
                          timestamp: float = 1.0) -> bool:
        """
        Generate thumbnail from video/GIF
        
        Args:
            media_path: Source media file
            output_path: Output thumbnail path
            size: Thumbnail size (width, height)
            timestamp: Which second to extract thumbnail from video
            
        Returns:
            bool: True if operation successful
        """
        if not self.ffmpeg_available:
            logger.warning("FFmpeg not available - cannot generate thumbnail")
            return False
        
        try:
            media_path = Path(media_path)
            output_path = Path(output_path)
            
            if not media_path.exists():
                logger.error(f"Source file not found: {media_path}")
                return False
            
            # Create output directory
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output
                "-i", str(media_path),
                "-ss", str(timestamp),  # Seek to timestamp
                "-vframes", "1",  # Extract 1 frame
                "-vf", f"scale={size[0]}:{size[1]}:force_original_aspect_ratio=decrease,pad={size[0]}:{size[1]}:(ow-iw)/2:(oh-ih)/2",
                "-q:v", "2",  # High quality
                str(output_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0 and output_path.exists():
                logger.debug(f"Thumbnail created: {output_path}")
                return True
            else:
                logger.error(f"Thumbnail could not be created: {result.stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating thumbnail: {e}")
            return False
    
    def convert_media(self, input_path: Union[str, Path],
                     output_path: Union[str, Path],
                     target_format: str = "mp4",
                     options: Optional[Dict] = None) -> bool:
        """
        Convert media format
        
        Args:
            input_path: Source file
            output_path: Target file
            target_format: Target format (mp4, webm, gif)
            options: Additional FFmpeg options
            
        Returns:
            bool: True if operation successful
        """
        if not self.ffmpeg_available:
            logger.warning("FFmpeg not available - cannot convert format")
            return False
        
        try:
            input_path = Path(input_path)
            output_path = Path(output_path)
            
            if not input_path.exists():
                logger.error(f"Source file not found: {input_path}")
                return False
            
            # Create output directory
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Base command
            cmd = ["ffmpeg", "-y", "-i", str(input_path)]
            
            # Format specific settings
            if target_format == "mp4":
                cmd.extend([
                    "-c:v", "libx264",
                    "-preset", "medium",
                    "-crf", "23",
                    "-c:a", "aac"
                ])
            elif target_format == "webm":
                cmd.extend([
                    "-c:v", "libvpx-vp9",
                    "-crf", "30",
                    "-b:v", "0",
                    "-c:a", "libopus"
                ])
            elif target_format == "gif":
                cmd.extend([
                    "-vf", "fps=15,scale=320:-1:flags=lanczos,palettegen=reserve_transparent=0",
                    "-f", "gif"
                ])
            
            # Additional options
            if options:
                for key, value in options.items():
                    cmd.extend([f"-{key}", str(value)])
            
            cmd.append(str(output_path))
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=300  # 5 dakika timeout
            )
            
            if result.returncode == 0 and output_path.exists():
                logger.info(f"Format conversion successful: {output_path}")
                return True
            else:
                logger.error(f"Format conversion failed: {result.stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error converting format: {e}")
            return False
    
    def optimize_for_wallpaper(self, input_path: Union[str, Path],
                              output_path: Union[str, Path],
                              max_resolution: Tuple[int, int] = (1920, 1080),
                              max_fps: int = 30) -> bool:
        """
        Optimize video for wallpaper
        
        Args:
            input_path: Source video
            output_path: Optimized video
            max_resolution: Maximum resolution
            max_fps: Maximum FPS
            
        Returns:
            bool: True if operation successful
        """
        if not self.ffmpeg_available:
            logger.warning("FFmpeg not available - cannot optimize")
            return False
        
        try:
            input_path = Path(input_path)
            output_path = Path(output_path)
            
            # Get media info
            info = self.get_media_info(input_path)
            if not info:
                return False
            
            # Create output directory
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            cmd = ["ffmpeg", "-y", "-i", str(input_path)]
            
            # Video filters
            filters = []
            
            # Resolution control
            if info.get("width", 0) > max_resolution[0] or info.get("height", 0) > max_resolution[1]:
                filters.append(f"scale={max_resolution[0]}:{max_resolution[1]}:force_original_aspect_ratio=decrease")
            
            # FPS control
            if info.get("fps", 0) > max_fps:
                filters.append(f"fps={max_fps}")
            
            if filters:
                cmd.extend(["-vf", ",".join(filters)])
            
            # Codec settings (optimized for wallpaper)
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "28",  # Compress a bit more
                "-profile:v", "high",
                "-level", "4.0",
                "-pix_fmt", "yuv420p"
            ])
            
            # Remove audio (unnecessary for wallpaper)
            cmd.extend(["-an"])
            
            cmd.append(str(output_path))
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=600  # 10 dakika timeout
            )
            
            if result.returncode == 0 and output_path.exists():
                logger.info(f"Video optimization successful: {output_path}")
                return True
            else:
                logger.error(f"Video optimization failed: {result.stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error optimizing video: {e}")
            return False
    
    def extract_audio(self, input_path: Union[str, Path],
                     output_path: Union[str, Path]) -> bool:
        """
        Extract audio from video
        
        Args:
            input_path: Source video
            output_path: Output audio file
            
        Returns:
            bool: True if operation successful
        """
        if not self.ffmpeg_available:
            return False
        
        try:
            input_path = Path(input_path)
            output_path = Path(output_path)
            
            if not input_path.exists():
                return False
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            cmd = [
                "ffmpeg", "-y",
                "-i", str(input_path),
                "-vn",  # No video
                "-acodec", "copy",
                str(output_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=120
            )
            
            return result.returncode == 0 and output_path.exists()
            
        except Exception as e:
            logger.error(f"Error extracting audio: {e}")
            return False


class SixelWallpaperProcessor:
    """Sixel-based wallpaper processing class - platform independent"""
    
    def __init__(self):
        self.ffmpeg_processor = FFmpegProcessor()
        self.sixel_available = self._check_sixel_support()
        self.terminal_size = self._get_terminal_size()
        
    def _check_sixel_support(self) -> bool:
        """Check if terminal has sixel support"""
        try:
            # TERM environment variable check
            term = os.environ.get('TERM', '')
            if 'xterm' in term or 'screen' in term or 'tmux' in term:
                # Sixel test command
                result = subprocess.run(
                    ['printf', '\033[?1;1;0S'],
                    capture_output=True,
                    timeout=2
                )
                # Simple sixel support assumption
                logger.info("Sixel support detected (terminal-based)")
                return True
            else:
                logger.warning("Sixel support uncertain - will work in fallback mode")
                return False
        except Exception as e:
            logger.warning(f"Sixel check failed: {e}")
            return False
    
    def _get_terminal_size(self) -> Tuple[int, int]:
        """Get terminal size"""
        try:
            import shutil
            size = shutil.get_terminal_size()
            return (size.columns, size.lines)
        except:
            return (80, 24)  # Default
    
    def apply_media_wallpaper_sixel(self, media_path: Union[str, Path],
                                   screen: str = "default") -> bool:
        """
        Apply media file as wallpaper using sixel
        
        Args:
            media_path: Media file path
            screen: Target screen (irrelevant for sixel)
            
        Returns:
            bool: True if successful
        """
        try:
            media_path = Path(media_path)
            if not media_path.exists():
                logger.error(f"Media file not found: {media_path}")
                return False
            
            # Detect media type
            media_info = self.ffmpeg_processor.get_media_info(media_path)
            if not media_info:
                logger.error("Could not get media info")
                return False
            
            media_type = media_info.get("type", "unknown")
            
            if media_type == "video" or media_type == "animated_image":
                return self._apply_animated_sixel_wallpaper(media_path, media_info)
            elif media_type == "image":
                return self._apply_static_sixel_wallpaper(media_path, media_info)
            else:
                logger.error(f"Unsupported media type: {media_type}")
                return False
                
        except Exception as e:
            logger.error(f"Sixel wallpaper application error: {e}")
            return False
    
    def _apply_static_sixel_wallpaper(self, media_path: Path, media_info: Dict) -> bool:
        """Sixel wallpaper for static images"""
        try:
            # Optimize image according to terminal size
            temp_dir = Path(tempfile.mkdtemp())
            optimized_path = temp_dir / f"sixel_optimized{media_path.suffix}"
            
            # Resize to fit terminal size
            cols, rows = self.terminal_size
            target_width = min(cols * 8, 1920)  # Pixel width
            target_height = min(rows * 16, 1080)  # Pixel height
            
            # Resize with FFmpeg
            cmd = [
                "ffmpeg", "-y",
                "-i", str(media_path),
                "-vf", f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease",
                "-q:v", "2",  # High quality
                str(optimized_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            if result.returncode != 0:
                logger.error(f"Image could not be optimized: {result.stderr.decode()}")
                return False
            
            # Apply wallpaper with sixel
            success = self._display_sixel_image(optimized_path)
            
            # Clean temp file
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return success
            
        except Exception as e:
            logger.error(f"Static sixel wallpaper error: {e}")
            return False
    
    def _apply_animated_sixel_wallpaper(self, media_path: Path, media_info: Dict) -> bool:
        """Sixel wallpaper for animated media"""
        try:
            # Split video/GIF into frames
            temp_dir = Path(tempfile.mkdtemp())
            frames_dir = temp_dir / "frames"
            frames_dir.mkdir()
            
            # Optimize according to terminal size
            cols, rows = self.terminal_size
            target_width = min(cols * 6, 1280)  # Slightly smaller (for performance)
            target_height = min(rows * 12, 720)
            
            # Frame extraction with FFmpeg
            cmd = [
                "ffmpeg", "-y",
                "-i", str(media_path),
                "-vf", f"fps=10,scale={target_width}:{target_height}:force_original_aspect_ratio=decrease",
                "-q:v", "3",
                str(frames_dir / "frame_%04d.png")
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            if result.returncode != 0:
                logger.error(f"Frame extraction failed: {result.stderr.decode()}")
                return False
            
            # Animate frames with sixel
            success = self._animate_sixel_frames(frames_dir)
            
            # Clean temp files
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return success
            
        except Exception as e:
            logger.error(f"Animated sixel wallpaper error: {e}")
            return False
    
    def _display_sixel_image(self, image_path: Path) -> bool:
        """Display single image with sixel"""
        try:
            # Try sixel conversion with ImageMagick
            try:
                cmd = ["convert", str(image_path), "sixel:-"]
                result = subprocess.run(cmd, capture_output=True, timeout=10)
                if result.returncode == 0:
                    # Send sixel output to terminal
                    print(result.stdout.decode(), end='', flush=True)
                    logger.info(f"Sixel image displayed: {image_path.name}")
                    return True
            except FileNotFoundError:
                logger.warning("ImageMagick not found, trying FFmpeg sixel...")
            
            # Try FFmpeg sixel support (if available)
            try:
                cmd = [
                    "ffmpeg", "-y",
                    "-i", str(image_path),
                    "-f", "sixel",
                    "-"
                ]
                result = subprocess.run(cmd, capture_output=True, timeout=10)
                if result.returncode == 0:
                    print(result.stdout.decode(), end='', flush=True)
                    logger.info(f"FFmpeg sixel image displayed: {image_path.name}")
                    return True
            except:
                pass
            
            # Try libsixel
            try:
                cmd = ["img2sixel", str(image_path)]
                result = subprocess.run(cmd, capture_output=True, timeout=10)
                if result.returncode == 0:
                    print(result.stdout.decode(), end='', flush=True)
                    logger.info(f"Image displayed with img2sixel: {image_path.name}")
                    return True
            except FileNotFoundError:
                pass
            
            logger.error("No sixel tool found")
            return False
            
        except Exception as e:
            logger.error(f"Sixel image display error: {e}")
            return False
    
    def _animate_sixel_frames(self, frames_dir: Path) -> bool:
        """Animate frames with sixel"""
        try:
            # List frame files
            frame_files = sorted(frames_dir.glob("frame_*.png"))
            if not frame_files:
                logger.error("No frames found")
                return False
            
            logger.info(f"Starting sixel animation: {len(frame_files)} frames")
            
            # Start animation loop as background process
            import threading
            import time
            
            def animate_loop():
                try:
                    while True:
                        for frame_file in frame_files:
                            # Clear terminal
                            print("\033[2J\033[H", end='', flush=True)
                            
                            # Display frame
                            if self._display_sixel_image(frame_file):
                                time.sleep(0.1)  # 10 FPS
                            else:
                                break
                except KeyboardInterrupt:
                    logger.info("Sixel animation stopped")
                except Exception as e:
                    logger.error(f"Sixel animation error: {e}")
            
            # Start in background thread
            animation_thread = threading.Thread(target=animate_loop, daemon=True)
            animation_thread.start()
            
            logger.info("Sixel animation started in background")
            return True
            
        except Exception as e:
            logger.error(f"Sixel animation error: {e}")
            return False


# Global instances
ffmpeg_processor = FFmpegProcessor()
sixel_processor = SixelWallpaperProcessor()


def get_media_info(media_path: Union[str, Path]) -> Optional[Dict]:
    """Get media file information"""
    return ffmpeg_processor.get_media_info(media_path)


def generate_thumbnail(media_path: Union[str, Path],
                      output_path: Union[str, Path],
                      size: Tuple[int, int] = (300, 200),
                      timestamp: float = 1.0) -> bool:
    """Generate thumbnail from video/GIF"""
    return ffmpeg_processor.generate_thumbnail(media_path, output_path, size, timestamp)


def optimize_for_wallpaper(input_path: Union[str, Path],
                          output_path: Union[str, Path]) -> bool:
    """Optimize video for wallpaper"""
    return ffmpeg_processor.optimize_for_wallpaper(input_path, output_path)


def apply_sixel_wallpaper(media_path: Union[str, Path], screen: str = "default") -> bool:
    """Apply wallpaper with sixel"""
    return sixel_processor.apply_media_wallpaper_sixel(media_path, screen)


def is_ffmpeg_available() -> bool:
    """Is FFmpeg available?"""
    return ffmpeg_processor.ffmpeg_available


def is_sixel_available() -> bool:
    """Is sixel support available?"""
    return sixel_processor.sixel_available