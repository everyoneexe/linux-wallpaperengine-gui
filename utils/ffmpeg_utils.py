"""
FFmpeg tabanlı medya işleme utilities
Sixel yaklaşımı ile uniform medya desteği
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
    """FFmpeg tabanlı medya işleme sınıfı"""
    
    def __init__(self):
        self.ffmpeg_available = self._check_ffmpeg()
        self.ffprobe_available = self._check_ffprobe()
        
    def _check_ffmpeg(self) -> bool:
        """FFmpeg kurulu mu kontrol et"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"], 
                capture_output=True, 
                timeout=5
            )
            available = result.returncode == 0
            if available:
                logger.info("FFmpeg bulundu ve kullanıma hazır")
            else:
                logger.warning("FFmpeg bulunamadı - bazı özellikler çalışmayabilir")
            return available
        except Exception as e:
            logger.warning(f"FFmpeg kontrolü başarısız: {e}")
            return False
    
    def _check_ffprobe(self) -> bool:
        """FFprobe kurulu mu kontrol et"""
        try:
            result = subprocess.run(
                ["ffprobe", "-version"], 
                capture_output=True, 
                timeout=5
            )
            available = result.returncode == 0
            if available:
                logger.info("FFprobe bulundu ve kullanıma hazır")
            else:
                logger.warning("FFprobe bulunamadı - metadata özellikleri çalışmayabilir")
            return available
        except Exception as e:
            logger.warning(f"FFprobe kontrolü başarısız: {e}")
            return False
    
    def get_media_info(self, media_path: Union[str, Path]) -> Optional[Dict]:
        """
        Medya dosyası hakkında detaylı bilgi al
        
        Args:
            media_path: Medya dosyası yolu
            
        Returns:
            Dict: Medya bilgileri veya None
        """
        if not self.ffprobe_available:
            logger.warning("FFprobe mevcut değil - temel bilgiler döndürülüyor")
            return self._get_basic_info(media_path)
        
        try:
            media_path = Path(media_path)
            if not media_path.exists():
                logger.error(f"Medya dosyası bulunamadı: {media_path}")
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
                logger.error(f"FFprobe hatası: {result.stderr}")
                return self._get_basic_info(media_path)
            
            data = json.loads(result.stdout)
            return self._parse_media_info(data, media_path)
            
        except Exception as e:
            logger.error(f"Medya bilgisi alınırken hata: {e}")
            return self._get_basic_info(media_path)
    
    def _get_basic_info(self, media_path: Union[str, Path]) -> Dict:
        """FFprobe olmadan temel bilgileri al"""
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
        """FFprobe çıktısını parse et"""
        format_info = data.get("format", {})
        streams = data.get("streams", [])
        
        # Video stream bul
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
        
        # Video bilgileri
        if video_stream:
            info.update({
                "width": video_stream.get("width", 0),
                "height": video_stream.get("height", 0),
                "fps": self._parse_fps(video_stream.get("r_frame_rate", "0/1")),
                "video_codec": video_stream.get("codec_name", "unknown"),
                "pixel_format": video_stream.get("pix_fmt", "unknown")
            })
        
        # Audio bilgileri
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
        """Dosya uzantısından medya tipini tespit et"""
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
        """FPS string'ini parse et (örn: "30/1" -> 30.0)"""
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
        Video/GIF'den thumbnail oluştur
        
        Args:
            media_path: Kaynak medya dosyası
            output_path: Çıktı thumbnail yolu
            size: Thumbnail boyutu (width, height)
            timestamp: Video'dan hangi saniyede thumbnail al
            
        Returns:
            bool: İşlem başarılı ise True
        """
        if not self.ffmpeg_available:
            logger.warning("FFmpeg mevcut değil - thumbnail oluşturulamıyor")
            return False
        
        try:
            media_path = Path(media_path)
            output_path = Path(output_path)
            
            if not media_path.exists():
                logger.error(f"Kaynak dosya bulunamadı: {media_path}")
                return False
            
            # Output dizinini oluştur
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
                logger.debug(f"Thumbnail oluşturuldu: {output_path}")
                return True
            else:
                logger.error(f"Thumbnail oluşturulamadı: {result.stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Thumbnail oluşturulurken hata: {e}")
            return False
    
    def convert_media(self, input_path: Union[str, Path],
                     output_path: Union[str, Path],
                     target_format: str = "mp4",
                     options: Optional[Dict] = None) -> bool:
        """
        Medya formatını dönüştür
        
        Args:
            input_path: Kaynak dosya
            output_path: Hedef dosya
            target_format: Hedef format (mp4, webm, gif)
            options: Ek FFmpeg seçenekleri
            
        Returns:
            bool: İşlem başarılı ise True
        """
        if not self.ffmpeg_available:
            logger.warning("FFmpeg mevcut değil - format dönüştürme yapılamıyor")
            return False
        
        try:
            input_path = Path(input_path)
            output_path = Path(output_path)
            
            if not input_path.exists():
                logger.error(f"Kaynak dosya bulunamadı: {input_path}")
                return False
            
            # Output dizinini oluştur
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Temel komut
            cmd = ["ffmpeg", "-y", "-i", str(input_path)]
            
            # Format özel ayarlar
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
            
            # Ek seçenekler
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
                logger.info(f"Format dönüştürme başarılı: {output_path}")
                return True
            else:
                logger.error(f"Format dönüştürme başarısız: {result.stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Format dönüştürülürken hata: {e}")
            return False
    
    def optimize_for_wallpaper(self, input_path: Union[str, Path],
                              output_path: Union[str, Path],
                              max_resolution: Tuple[int, int] = (1920, 1080),
                              max_fps: int = 30) -> bool:
        """
        Video'yu wallpaper için optimize et
        
        Args:
            input_path: Kaynak video
            output_path: Optimize edilmiş video
            max_resolution: Maksimum çözünürlük
            max_fps: Maksimum FPS
            
        Returns:
            bool: İşlem başarılı ise True
        """
        if not self.ffmpeg_available:
            logger.warning("FFmpeg mevcut değil - optimizasyon yapılamıyor")
            return False
        
        try:
            input_path = Path(input_path)
            output_path = Path(output_path)
            
            # Medya bilgisini al
            info = self.get_media_info(input_path)
            if not info:
                return False
            
            # Output dizinini oluştur
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            cmd = ["ffmpeg", "-y", "-i", str(input_path)]
            
            # Video filtreleri
            filters = []
            
            # Çözünürlük kontrolü
            if info.get("width", 0) > max_resolution[0] or info.get("height", 0) > max_resolution[1]:
                filters.append(f"scale={max_resolution[0]}:{max_resolution[1]}:force_original_aspect_ratio=decrease")
            
            # FPS kontrolü
            if info.get("fps", 0) > max_fps:
                filters.append(f"fps={max_fps}")
            
            if filters:
                cmd.extend(["-vf", ",".join(filters)])
            
            # Codec ayarları (wallpaper için optimize)
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "28",  # Biraz daha sıkıştır
                "-profile:v", "high",
                "-level", "4.0",
                "-pix_fmt", "yuv420p"
            ])
            
            # Audio'yu kaldır (wallpaper'da gereksiz)
            cmd.extend(["-an"])
            
            cmd.append(str(output_path))
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=600  # 10 dakika timeout
            )
            
            if result.returncode == 0 and output_path.exists():
                logger.info(f"Video optimizasyonu başarılı: {output_path}")
                return True
            else:
                logger.error(f"Video optimizasyonu başarısız: {result.stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Video optimize edilirken hata: {e}")
            return False
    
    def extract_audio(self, input_path: Union[str, Path],
                     output_path: Union[str, Path]) -> bool:
        """
        Video'dan audio'yu ayır
        
        Args:
            input_path: Kaynak video
            output_path: Çıktı audio dosyası
            
        Returns:
            bool: İşlem başarılı ise True
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
            logger.error(f"Audio ayırılırken hata: {e}")
            return False


class SixelWallpaperProcessor:
    """Sixel tabanlı wallpaper işleme sınıfı - platform bağımsız"""
    
    def __init__(self):
        self.ffmpeg_processor = FFmpegProcessor()
        self.sixel_available = self._check_sixel_support()
        self.terminal_size = self._get_terminal_size()
        
    def _check_sixel_support(self) -> bool:
        """Terminal sixel desteği var mı kontrol et"""
        try:
            # TERM environment variable kontrolü
            term = os.environ.get('TERM', '')
            if 'xterm' in term or 'screen' in term or 'tmux' in term:
                # Sixel test komutu
                result = subprocess.run(
                    ['printf', '\033[?1;1;0S'],
                    capture_output=True,
                    timeout=2
                )
                # Basit sixel desteği varsayımı
                logger.info("Sixel desteği tespit edildi (terminal-based)")
                return True
            else:
                logger.warning("Sixel desteği belirsiz - fallback modda çalışılacak")
                return False
        except Exception as e:
            logger.warning(f"Sixel kontrolü başarısız: {e}")
            return False
    
    def _get_terminal_size(self) -> Tuple[int, int]:
        """Terminal boyutunu al"""
        try:
            import shutil
            size = shutil.get_terminal_size()
            return (size.columns, size.lines)
        except:
            return (80, 24)  # Varsayılan
    
    def apply_media_wallpaper_sixel(self, media_path: Union[str, Path],
                                   screen: str = "default") -> bool:
        """
        Medya dosyasını sixel ile wallpaper olarak uygula
        
        Args:
            media_path: Medya dosyası yolu
            screen: Hedef ekran (sixel için önemsiz)
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            media_path = Path(media_path)
            if not media_path.exists():
                logger.error(f"Medya dosyası bulunamadı: {media_path}")
                return False
            
            # Medya tipini tespit et
            media_info = self.ffmpeg_processor.get_media_info(media_path)
            if not media_info:
                logger.error("Medya bilgisi alınamadı")
                return False
            
            media_type = media_info.get("type", "unknown")
            
            if media_type == "video" or media_type == "animated_image":
                return self._apply_animated_sixel_wallpaper(media_path, media_info)
            elif media_type == "image":
                return self._apply_static_sixel_wallpaper(media_path, media_info)
            else:
                logger.error(f"Desteklenmeyen medya tipi: {media_type}")
                return False
                
        except Exception as e:
            logger.error(f"Sixel wallpaper uygulama hatası: {e}")
            return False
    
    def _apply_static_sixel_wallpaper(self, media_path: Path, media_info: Dict) -> bool:
        """Statik resim için sixel wallpaper"""
        try:
            # Terminal boyutuna göre resmi optimize et
            temp_dir = Path(tempfile.mkdtemp())
            optimized_path = temp_dir / f"sixel_optimized{media_path.suffix}"
            
            # Terminal boyutuna uygun resize
            cols, rows = self.terminal_size
            target_width = min(cols * 8, 1920)  # Pixel genişliği
            target_height = min(rows * 16, 1080)  # Pixel yüksekliği
            
            # FFmpeg ile resize
            cmd = [
                "ffmpeg", "-y",
                "-i", str(media_path),
                "-vf", f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease",
                "-q:v", "2",  # Yüksek kalite
                str(optimized_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            if result.returncode != 0:
                logger.error(f"Resim optimize edilemedi: {result.stderr.decode()}")
                return False
            
            # Sixel ile wallpaper uygula
            success = self._display_sixel_image(optimized_path)
            
            # Temp dosyayı temizle
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return success
            
        except Exception as e:
            logger.error(f"Statik sixel wallpaper hatası: {e}")
            return False
    
    def _apply_animated_sixel_wallpaper(self, media_path: Path, media_info: Dict) -> bool:
        """Animasyonlu medya için sixel wallpaper"""
        try:
            # Video/GIF'i frame'lere ayır
            temp_dir = Path(tempfile.mkdtemp())
            frames_dir = temp_dir / "frames"
            frames_dir.mkdir()
            
            # Terminal boyutuna göre optimize et
            cols, rows = self.terminal_size
            target_width = min(cols * 6, 1280)  # Biraz daha küçük (performans için)
            target_height = min(rows * 12, 720)
            
            # FFmpeg ile frame extraction
            cmd = [
                "ffmpeg", "-y",
                "-i", str(media_path),
                "-vf", f"fps=10,scale={target_width}:{target_height}:force_original_aspect_ratio=decrease",
                "-q:v", "3",
                str(frames_dir / "frame_%04d.png")
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            if result.returncode != 0:
                logger.error(f"Frame extraction başarısız: {result.stderr.decode()}")
                return False
            
            # Frame'leri sixel ile animate et
            success = self._animate_sixel_frames(frames_dir)
            
            # Temp dosyaları temizle
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return success
            
        except Exception as e:
            logger.error(f"Animasyonlu sixel wallpaper hatası: {e}")
            return False
    
    def _display_sixel_image(self, image_path: Path) -> bool:
        """Tek resmi sixel ile göster"""
        try:
            # ImageMagick ile sixel dönüştürme dene
            try:
                cmd = ["convert", str(image_path), "sixel:-"]
                result = subprocess.run(cmd, capture_output=True, timeout=10)
                if result.returncode == 0:
                    # Terminal'e sixel çıktısını gönder
                    print(result.stdout.decode(), end='', flush=True)
                    logger.info(f"Sixel resim gösterildi: {image_path.name}")
                    return True
            except FileNotFoundError:
                logger.warning("ImageMagick bulunamadı, FFmpeg sixel deneniyor...")
            
            # FFmpeg sixel desteği dene (eğer varsa)
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
                    logger.info(f"FFmpeg sixel resim gösterildi: {image_path.name}")
                    return True
            except:
                pass
            
            # libsixel dene
            try:
                cmd = ["img2sixel", str(image_path)]
                result = subprocess.run(cmd, capture_output=True, timeout=10)
                if result.returncode == 0:
                    print(result.stdout.decode(), end='', flush=True)
                    logger.info(f"img2sixel ile resim gösterildi: {image_path.name}")
                    return True
            except FileNotFoundError:
                pass
            
            logger.error("Hiçbir sixel tool'u bulunamadı")
            return False
            
        except Exception as e:
            logger.error(f"Sixel resim gösterme hatası: {e}")
            return False
    
    def _animate_sixel_frames(self, frames_dir: Path) -> bool:
        """Frame'leri sixel ile animate et"""
        try:
            # Frame dosyalarını listele
            frame_files = sorted(frames_dir.glob("frame_*.png"))
            if not frame_files:
                logger.error("Hiç frame bulunamadı")
                return False
            
            logger.info(f"Sixel animasyon başlatılıyor: {len(frame_files)} frame")
            
            # Background process olarak animasyon döngüsü başlat
            import threading
            import time
            
            def animate_loop():
                try:
                    while True:
                        for frame_file in frame_files:
                            # Terminal'i temizle
                            print("\033[2J\033[H", end='', flush=True)
                            
                            # Frame'i göster
                            if self._display_sixel_image(frame_file):
                                time.sleep(0.1)  # 10 FPS
                            else:
                                break
                except KeyboardInterrupt:
                    logger.info("Sixel animasyon durduruldu")
                except Exception as e:
                    logger.error(f"Sixel animasyon hatası: {e}")
            
            # Background thread'de başlat
            animation_thread = threading.Thread(target=animate_loop, daemon=True)
            animation_thread.start()
            
            logger.info("Sixel animasyon background'da başlatıldı")
            return True
            
        except Exception as e:
            logger.error(f"Sixel animasyon hatası: {e}")
            return False


# Global instances
ffmpeg_processor = FFmpegProcessor()
sixel_processor = SixelWallpaperProcessor()


def get_media_info(media_path: Union[str, Path]) -> Optional[Dict]:
    """Medya dosyası bilgilerini al"""
    return ffmpeg_processor.get_media_info(media_path)


def generate_thumbnail(media_path: Union[str, Path],
                      output_path: Union[str, Path],
                      size: Tuple[int, int] = (300, 200),
                      timestamp: float = 1.0) -> bool:
    """Video/GIF'den thumbnail oluştur"""
    return ffmpeg_processor.generate_thumbnail(media_path, output_path, size, timestamp)


def optimize_for_wallpaper(input_path: Union[str, Path],
                          output_path: Union[str, Path]) -> bool:
    """Video'yu wallpaper için optimize et"""
    return ffmpeg_processor.optimize_for_wallpaper(input_path, output_path)


def apply_sixel_wallpaper(media_path: Union[str, Path], screen: str = "default") -> bool:
    """Sixel ile wallpaper uygula"""
    return sixel_processor.apply_media_wallpaper_sixel(media_path, screen)


def is_ffmpeg_available() -> bool:
    """FFmpeg mevcut mu?"""
    return ffmpeg_processor.ffmpeg_available


def is_sixel_available() -> bool:
    """Sixel desteği mevcut mu?"""
    return sixel_processor.sixel_available