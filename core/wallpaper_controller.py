"""
Wallpaper Engine dinamik kontrol sistemi
"""
import logging
import os
import subprocess
import signal
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class WallpaperController:
    """
    Wallpaper Engine için dinamik kontrol sistemi.
    Mevcut wallpaper'ın ayarlarını anlık olarak değiştirir.
    """
    
    def __init__(self, wallpaper_engine):
        self.wallpaper_engine = wallpaper_engine
        
        # Video wallpaper process yönetimi
        self.video_processes = {}  # {screen: process_info}
        
        # Preset'ler kaldırıldı - gereksiz
        
        logger.info("WallpaperController başlatıldı")
    
    def is_wallpaper_running(self) -> bool:
        """Wallpaper çalışıyor mu kontrol eder."""
        return self.wallpaper_engine.current_wallpaper is not None
    
    def get_current_settings(self) -> Dict[str, Any]:
        """Mevcut wallpaper ayarlarını döner."""
        if not self.is_wallpaper_running():
            return {}
        return self.wallpaper_engine.last_settings.copy()
    
    def set_volume(self, volume: int) -> bool:
        """
        Wallpaper ses seviyesini değiştirir (sadece ayarları günceller, restart yok).
        
        Args:
            volume: Ses seviyesi (0-100)
            
        Returns:
            bool: Başarılı ise True
        """
        if not self.is_wallpaper_running():
            logger.warning("Wallpaper çalışmıyor, ses değiştirilemedi")
            return False
        
        volume = max(0, min(100, volume))
        
        # Sadece ayarları güncelle, restart yapma
        self.wallpaper_engine.last_settings["volume"] = volume
        self.wallpaper_engine._save_state()
        
        logger.info(f"Ses seviyesi ayarı güncellendi: {volume}% (restart yok)")
        return True
    
    def toggle_silent(self) -> bool:
        """
        Sessiz modunu açar/kapatır.
        
        Returns:
            bool: Başarılı ise True
        """
        if not self.is_wallpaper_running():
            logger.warning("Wallpaper çalışmıyor, sessiz toggle edilemedi")
            return False
        
        current_volume = self.wallpaper_engine.last_settings.get("volume", 50)
        new_volume = 0 if current_volume > 0 else 50
        
        success = self.wallpaper_engine.restart_with_new_settings(volume=new_volume)
        
        if success:
            status = "açıldı" if new_volume == 0 else "kapatıldı"
            logger.info(f"Sessiz mod {status}")
        else:
            logger.error("Sessiz mod toggle edilemedi")
            
        return success
    
    def set_fps(self, fps: int) -> bool:
        """
        Wallpaper FPS'ini değiştirir (sadece ayarları günceller, restart yok).
        
        Args:
            fps: FPS değeri (10-144)
            
        Returns:
            bool: Başarılı ise True
        """
        if not self.is_wallpaper_running():
            logger.warning("Wallpaper çalışmıyor, FPS değiştirilemedi")
            return False
        
        fps = max(10, min(144, fps))
        
        # Sadece ayarları güncelle, restart yapma
        self.wallpaper_engine.last_settings["fps"] = fps
        self.wallpaper_engine._save_state()
        
        logger.info(f"FPS ayarı güncellendi: {fps} (restart yok)")
        return True
    
    def toggle_mouse(self) -> bool:
        """
        Mouse etkileşimini açar/kapatır (sadece ayarları günceller).
        
        Returns:
            bool: Başarılı ise True
        """
        if not self.is_wallpaper_running():
            logger.warning("Wallpaper çalışmıyor, mouse toggle edilemedi")
            return False
        
        current_mouse = self.wallpaper_engine.last_settings.get("disable_mouse", False)
        new_mouse = not current_mouse
        
        # Sadece ayarları güncelle
        self.wallpaper_engine.last_settings["disable_mouse"] = new_mouse
        self.wallpaper_engine._save_state()
        
        status = "kapatıldı" if new_mouse else "açıldı"
        logger.info(f"Mouse etkileşimi ayarı {status} (restart yok)")
        return True
    
    def toggle_audio_processing(self) -> bool:
        """
        Ses işleme özelliğini açar/kapatır (sadece ayarları günceller).
        
        Returns:
            bool: Başarılı ise True
        """
        if not self.is_wallpaper_running():
            logger.warning("Wallpaper çalışmıyor, audio processing toggle edilemedi")
            return False
        
        current_proc = self.wallpaper_engine.last_settings.get("no_audio_processing", False)
        new_proc = not current_proc
        
        # Sadece ayarları güncelle
        self.wallpaper_engine.last_settings["no_audio_processing"] = new_proc
        self.wallpaper_engine._save_state()
        
        status = "kapatıldı" if new_proc else "açıldı"
        logger.info(f"Ses işleme ayarı {status} (restart yok)")
        return True
    
    def toggle_auto_mute(self) -> bool:
        """
        Otomatik ses kısma özelliğini açar/kapatır (sadece ayarları günceller).
        
        Returns:
            bool: Başarılı ise True
        """
        if not self.is_wallpaper_running():
            logger.warning("Wallpaper çalışmıyor, auto mute toggle edilemedi")
            return False
        
        current_mute = self.wallpaper_engine.last_settings.get("noautomute", False)
        new_mute = not current_mute
        
        # Sadece ayarları güncelle
        self.wallpaper_engine.last_settings["noautomute"] = new_mute
        self.wallpaper_engine._save_state()
        
        status = "kapatıldı" if new_mute else "açıldı"
        logger.info(f"Otomatik ses kısma ayarı {status} (restart yok)")
        return True
    
    # Preset fonksiyonları kaldırıldı - gereksiz
    
    def is_silent(self) -> bool:
        """Wallpaper sessiz modda mı kontrol eder."""
        if not self.is_wallpaper_running():
            return False
        return self.wallpaper_engine.last_settings.get("volume", 50) == 0
    
    def get_volume(self) -> int:
        """Mevcut ses seviyesini döner."""
        if not self.is_wallpaper_running():
            return 0
        return self.wallpaper_engine.last_settings.get("volume", 50)
    
    def get_fps(self) -> int:
        """Mevcut FPS değerini döner."""
        if not self.is_wallpaper_running():
            return 60
        return self.wallpaper_engine.last_settings.get("fps", 60)
    
    def apply_media_wallpaper(self, media_path: str, screen: str = "eDP-1") -> bool:
        """
        GIF/Video wallpaper'ı platform uyumlu şekilde uygular.
        
        Args:
            media_path: Medya dosyası path'i
            screen: Hedef ekran
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            import subprocess
            import os
            from pathlib import Path
            
            media_file = Path(media_path)
            if not media_file.exists():
                logger.error(f"Medya dosyası bulunamadı: {media_path}")
                return False
            
            # Önce mevcut wallpaper engine process'lerini durdur
            self._stop_existing_wallpaper_processes()
            
            # Platform ve desktop environment tespiti
            desktop_env = self._detect_desktop_environment()
            logger.info(f"Desktop environment tespit edildi: {desktop_env}")
            
            # Platform uyumlu wallpaper uygulaması
            if desktop_env == "wayland_hyprland":
                return self._apply_with_swww(media_file, screen)
            elif desktop_env == "kde_plasma":
                return self._apply_with_kde_plasma(media_file, screen)
            elif desktop_env == "gnome":
                return self._apply_with_gnome(media_file, screen)
            elif desktop_env == "xfce":
                return self._apply_with_xfce(media_file, screen)
            else:
                # Fallback: feh veya nitrogen
                return self._apply_with_fallback(media_file, screen)
                
        except Exception as e:
            logger.error(f"Medya wallpaper uygulama hatası: {e}")
            return False
    
    def _stop_existing_wallpaper_processes(self) -> None:
        """Mevcut wallpaper engine process'lerini durdurur."""
        try:
            import subprocess
            
            # Linux wallpaper engine process'lerini durdur
            try:
                result = subprocess.run(['pkill', '-f', 'linux-wallpaperengine'],
                                      capture_output=True, timeout=5)
                if result.returncode == 0:
                    logger.info("Mevcut linux-wallpaperengine process'leri durduruldu")
            except:
                pass
            
            # Swww process'lerini durdur (GIF/video uygulanırken)
            try:
                subprocess.run(['pkill', '-f', 'swww'], capture_output=True, timeout=5)
                logger.info("Swww process'leri durduruldu (GIF/video uygulama için)")
            except:
                pass
            
            # Video wallpaper process'lerini durdur
            self.stop_video_wallpaper("all")
            
            # Kısa bekleme
            import time
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Wallpaper process durdurma hatası: {e}")
    
    def _detect_desktop_environment(self) -> str:
        """Desktop environment'ı tespit eder."""
        try:
            import os
            import subprocess
            
            # Wayland kontrolü
            if os.environ.get('WAYLAND_DISPLAY'):
                # Hyprland kontrolü
                if os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'):
                    return "wayland_hyprland"
                # Sway kontrolü
                elif os.environ.get('SWAYSOCK'):
                    return "wayland_sway"
                else:
                    return "wayland_generic"
            
            # X11 desktop environment kontrolü
            desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
            session = os.environ.get('DESKTOP_SESSION', '').lower()
            
            if 'kde' in desktop or 'plasma' in desktop:
                return "kde_plasma"
            elif 'gnome' in desktop:
                return "gnome"
            elif 'xfce' in desktop:
                return "xfce"
            elif 'mate' in desktop:
                return "mate"
            elif 'cinnamon' in desktop:
                return "cinnamon"
            else:
                return "x11_generic"
                
        except Exception as e:
            logger.error(f"Desktop environment tespit hatası: {e}")
            return "unknown"
    
    def _apply_with_swww(self, media_file: Path, screen: str) -> bool:
        """Swww ile wallpaper uygular (Wayland/Hyprland) - Sixel fallback ile."""
        try:
            import subprocess
            
            # Video dosyası mı kontrol et
            if media_file.suffix.lower() in ['.mp4', '.webm', '.mov']:
                # Swww video desteklemiyor, önce Sixel dene
                logger.info(f"Video dosyası tespit edildi, Sixel öncelikli fallback: {media_file.name}")
                if self._apply_sixel_wallpaper(media_file, screen):
                    return True
                # Sixel başarısızsa MPV kullan
                return self._apply_mpv_video_wallpaper(media_file, screen)
            
            # Swww kontrolü (sadece resim/GIF için)
            try:
                subprocess.run(['swww', 'query'],
                             capture_output=True, check=True, timeout=5)
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Daemon başlat dene
                logger.info("Swww daemon başlatılıyor...")
                try:
                    subprocess.Popen(['swww', 'init'],
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
                    import time
                    time.sleep(2)
                except FileNotFoundError:
                    logger.warning("Swww bulunamadı, Sixel fallback deneniyor...")
                    return self._apply_sixel_wallpaper(media_file, screen)
            
            # GIF/Resim wallpaper uygula
            cmd = ['swww', 'img', str(media_file)]
            
            if screen and screen != "all":
                cmd.extend(['--outputs', screen])
            
            cmd.extend(['--transition-type', 'fade', '--transition-duration', '1'])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logger.info(f"Swww ile medya wallpaper uygulandı: {media_file.name}")
                return True
            else:
                logger.error(f"Swww hatası: {result.stderr}")
                # Swww başarısız olursa Sixel fallback dene
                logger.info("Swww başarısız, Sixel fallback deneniyor...")
                if self._apply_sixel_wallpaper(media_file, screen):
                    return True
                # Son çare olarak MPV
                if media_file.suffix.lower() in ['.gif']:
                    logger.info("Sixel de başarısız, MPV fallback deneniyor...")
                    return self._apply_mpv_video_wallpaper(media_file, screen)
                return False
                
        except Exception as e:
            logger.error(f"Swww uygulama hatası: {e}")
            # Exception durumunda da Sixel fallback dene
            logger.info("Exception sonrası Sixel fallback deneniyor...")
            return self._apply_sixel_wallpaper(media_file, screen)
    
    def _apply_with_kde_plasma(self, media_file: Path, screen: str) -> bool:
        """KDE Plasma ile wallpaper uygular."""
        try:
            import subprocess
            
            # Video dosyası mı kontrol et
            if media_file.suffix.lower() in ['.mp4', '.webm', '.mov']:
                # KDE için video wallpaper plugin dene
                return self._apply_kde_video_wallpaper(media_file, screen)
            else:
                # Normal resim/GIF için qdbus kullan
                cmd = [
                    'qdbus', 'org.kde.plasmashell', '/PlasmaShell',
                    'org.kde.PlasmaShell.evaluateScript',
                    f'''
                    var allDesktops = desktops();
                    for (i=0;i<allDesktops.length;i++) {{
                        d = allDesktops[i];
                        d.wallpaperPlugin = "org.kde.image";
                        d.currentConfigGroup = Array("Wallpaper", "org.kde.image", "General");
                        d.writeConfig("Image", "file://{media_file}");
                    }}
                    '''
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    logger.info(f"KDE Plasma ile medya wallpaper uygulandı: {media_file.name}")
                    return True
                else:
                    logger.error(f"KDE Plasma hatası: {result.stderr}")
                    return False
                
        except Exception as e:
            logger.error(f"KDE Plasma uygulama hatası: {e}")
            return False
    
    def _apply_kde_video_wallpaper(self, media_file: Path, screen: str) -> bool:
        """KDE Plasma için video wallpaper uygular."""
        try:
            import subprocess
            
            # KDE video wallpaper plugin kontrolü
            try:
                # Smart Video Wallpaper plugin dene
                cmd = [
                    'qdbus', 'org.kde.plasmashell', '/PlasmaShell',
                    'org.kde.PlasmaShell.evaluateScript',
                    f'''
                    var allDesktops = desktops();
                    for (i=0;i<allDesktops.length;i++) {{
                        d = allDesktops[i];
                        d.wallpaperPlugin = "com.github.casout.smartVideoWallpaper";
                        d.currentConfigGroup = Array("Wallpaper", "com.github.casout.smartVideoWallpaper", "General");
                        d.writeConfig("Video", "file://{media_file}");
                    }}
                    '''
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    logger.info(f"KDE Smart Video Wallpaper ile uygulandı: {media_file.name}")
                    return True
                    
            except Exception:
                pass
            
            # Fallback: mpv ile video wallpaper
            return self._apply_mpv_video_wallpaper(media_file, screen)
                
        except Exception as e:
            logger.error(f"KDE video wallpaper hatası: {e}")
            return False
    
    def _apply_mpv_video_wallpaper(self, media_file: Path, screen: str) -> bool:
        """MPV ile video wallpaper uygular (evrensel çözüm)."""
        try:
            # Desktop environment'ı tespit et
            desktop_env = self._detect_desktop_environment()
            
            # Mevcut video process'ini durdur
            self._stop_video_process(screen)
            
            # Genel video wallpaper process'lerini de durdur
            try:
                subprocess.run(['pkill', '-f', '(mpv|mpvpaper).*wallpaper'], timeout=5)
            except:
                pass
            
            # Hyprland için mpvpaper dene
            if desktop_env == "wayland_hyprland":
                try:
                    # mpvpaper kontrolü
                    subprocess.run(['mpvpaper', '--help'], capture_output=True, timeout=5)
                    
                    # mpvpaper ile wallpaper uygula - tam ekran ve doğru scaling
                    cmd = [
                        'mpvpaper',
                        '-o', 'loop=inf --no-audio --really-quiet --video-zoom=0 --panscan=1.0 --video-aspect-override=no',
                        screen if screen != "all" else "*",
                        str(media_file)
                    ]
                    
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        preexec_fn=os.setsid
                    )
                    
                    # Process bilgisini kaydet
                    self.video_processes[screen] = {
                        'process': process,
                        'file_path': str(media_file),
                        'method': 'mpvpaper',
                        'desktop_env': desktop_env
                    }
                    
                    logger.info(f"mpvpaper ile video wallpaper başlatıldı: {media_file.name} (PID: {process.pid})")
                    return True
                    
                except FileNotFoundError:
                    logger.info("mpvpaper bulunamadı, standart MPV deneniyor...")
                except Exception as e:
                    logger.warning(f"mpvpaper hatası: {e}, standart MPV deneniyor...")
            
            # Standart MPV fallback
            try:
                subprocess.run(['mpv', '--version'], capture_output=True, timeout=5)
            except FileNotFoundError:
                logger.error("MPV bulunamadı - video wallpaper için gerekli")
                return False
            
            # Desktop environment'a göre MPV parametrelerini ayarla
            if desktop_env == "wayland_hyprland":
                # Hyprland için layer shell deneme
                cmd = [
                    'mpv',
                    '--loop=inf',
                    '--no-audio',
                    '--no-input-default-bindings',
                    '--no-osc',
                    '--no-border',
                    '--really-quiet',
                    '--vo=gpu',
                    '--gpu-context=wayland',
                    '--wayland-app-id=mpv-wallpaper',
                    '--no-focus-on-open',
                    '--geometry=100%x100%+0+0',
                    '--on-all-workspaces',
                    '--keep-open=yes',
                    str(media_file)
                ]
                
                # Hyprland window rule ekle
                try:
                    subprocess.run([
                        'hyprctl', 'keyword', 'windowrule',
                        'float,^(mpv-wallpaper)$'
                    ], capture_output=True, timeout=5)
                    subprocess.run([
                        'hyprctl', 'keyword', 'windowrule',
                        'pin,^(mpv-wallpaper)$'
                    ], capture_output=True, timeout=5)
                    subprocess.run([
                        'hyprctl', 'keyword', 'windowrule',
                        'noblur,^(mpv-wallpaper)$'
                    ], capture_output=True, timeout=5)
                    subprocess.run([
                        'hyprctl', 'keyword', 'windowrule',
                        'noshadow,^(mpv-wallpaper)$'
                    ], capture_output=True, timeout=5)
                    subprocess.run([
                        'hyprctl', 'keyword', 'windowrule',
                        'noborder,^(mpv-wallpaper)$'
                    ], capture_output=True, timeout=5)
                except:
                    pass
                    
            elif desktop_env.startswith("wayland"):
                # Diğer Wayland compositor'lar için
                cmd = [
                    'mpv',
                    '--loop=inf',
                    '--no-audio',
                    '--no-input-default-bindings',
                    '--no-osc',
                    '--no-border',
                    '--fullscreen',
                    '--really-quiet',
                    '--vo=gpu',
                    '--gpu-context=wayland',
                    '--wayland-app-id=mpv-wallpaper',
                    '--no-focus-on-open',
                    str(media_file)
                ]
            else:
                # X11 için parametreler
                cmd = [
                    'mpv',
                    '--loop=inf',
                    '--no-audio',
                    '--wid=0',  # Root window
                    '--no-input-default-bindings',
                    '--no-osc',
                    '--no-border',
                    '--geometry=100%x100%+0+0',
                    '--really-quiet',
                    str(media_file)
                ]
            
            # Background process olarak başlat
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid  # Yeni process group
            )
            
            # Process bilgisini kaydet
            self.video_processes[screen] = {
                'process': process,
                'file_path': str(media_file),
                'method': 'mpv',
                'desktop_env': desktop_env
            }
            
            logger.info(f"MPV ile video wallpaper başlatıldı: {media_file.name} (PID: {process.pid}, Screen: {screen})")
            return True
                
        except Exception as e:
            logger.error(f"MPV video wallpaper hatası: {e}")
            return False
    
    def _apply_with_gnome(self, media_file: Path, screen: str) -> bool:
        """GNOME ile wallpaper uygular."""
        try:
            import subprocess
            
            # Video dosyası mı kontrol et
            if media_file.suffix.lower() in ['.mp4', '.webm', '.mov']:
                # GNOME için video wallpaper çözümü
                return self._apply_gnome_video_wallpaper(media_file, screen)
            else:
                # Normal resim/GIF için gsettings kullan
                cmd = [
                    'gsettings', 'set', 'org.gnome.desktop.background',
                    'picture-uri', f'file://{media_file}'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    logger.info(f"GNOME ile medya wallpaper uygulandı: {media_file.name}")
                    return True
                else:
                    logger.error(f"GNOME hatası: {result.stderr}")
                    return False
                
        except Exception as e:
            logger.error(f"GNOME uygulama hatası: {e}")
            return False
    
    def _apply_gnome_video_wallpaper(self, media_file: Path, screen: str) -> bool:
        """GNOME için video wallpaper uygular."""
        try:
            import subprocess
            
            # GNOME Shell extension kontrolü (Wallpaper Slideshow)
            try:
                # Hidamari extension dene
                cmd = [
                    'gsettings', 'set', 'org.gnome.shell.extensions.hidamari',
                    'video-path', str(media_file)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    logger.info(f"GNOME Hidamari extension ile video uygulandı: {media_file.name}")
                    return True
                    
            except Exception:
                pass
            
            # Fallback: mpv ile video wallpaper
            return self._apply_mpv_video_wallpaper(media_file, screen)
                
        except Exception as e:
            logger.error(f"GNOME video wallpaper hatası: {e}")
            return False
    
    def _apply_with_xfce(self, media_file: Path, screen: str) -> bool:
        """XFCE ile wallpaper uygular."""
        try:
            import subprocess
            
            # XFCE için xfconf-query kullan
            cmd = [
                'xfconf-query', '-c', 'xfce4-desktop',
                '-p', '/backdrop/screen0/monitor0/workspace0/last-image',
                '-s', str(media_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logger.info(f"XFCE ile medya wallpaper uygulandı: {media_file.name}")
                return True
            else:
                logger.error(f"XFCE hatası: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"XFCE uygulama hatası: {e}")
            return False
    
    def _apply_with_fallback(self, media_file: Path, screen: str) -> bool:
        """Fallback wallpaper uygulaması (feh/nitrogen) - Sixel fallback ile."""
        try:
            import subprocess
            
            # Video/GIF için önce Sixel dene
            if media_file.suffix.lower() in ['.mp4', '.webm', '.mov', '.gif']:
                logger.info(f"Video/GIF tespit edildi, Sixel öncelikli: {media_file.name}")
                if self._apply_sixel_wallpaper(media_file, screen):
                    return True
                # Sixel başarısızsa MPV dene
                logger.info("Sixel başarısız, MPV fallback deneniyor...")
                return self._apply_mpv_video_wallpaper(media_file, screen)
            
            # Statik resimler için geleneksel yöntemler
            # Feh dene
            try:
                cmd = ['feh', '--bg-scale', str(media_file)]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    logger.info(f"Feh ile medya wallpaper uygulandı: {media_file.name}")
                    return True
            except FileNotFoundError:
                pass
            
            # Nitrogen dene
            try:
                cmd = ['nitrogen', '--set-scaled', str(media_file)]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    logger.info(f"Nitrogen ile medya wallpaper uygulandı: {media_file.name}")
                    return True
            except FileNotFoundError:
                pass
            
            # Son çare: Sixel (statik resimler için de)
            logger.info("Geleneksel tool'lar başarısız, Sixel fallback deneniyor...")
            if self._apply_sixel_wallpaper(media_file, screen):
                return True
            
            logger.error("Hiçbir wallpaper tool'u bulunamadı (feh, nitrogen, sixel)")
            return False
                
        except Exception as e:
            logger.error(f"Fallback uygulama hatası: {e}")
            # Exception durumunda da Sixel dene
            logger.info("Exception sonrası Sixel fallback deneniyor...")
            return self._apply_sixel_wallpaper(media_file, screen)
    
    def delete_custom_wallpaper(self, wallpaper_id: str) -> bool:
        """
        Özel eklenen wallpaper'ı siler.
        
        Args:
            wallpaper_id: Silinecek wallpaper ID'si
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            import shutil
            from pathlib import Path
            
            # Custom wallpaper'ları kontrol et (custom_ ile başlayanlar)
            if not wallpaper_id.startswith('custom_') and not wallpaper_id.startswith('gif_'):
                logger.warning(f"Sadece özel wallpaper'lar silinebilir: {wallpaper_id}")
                return False
            
            # Steam Workshop klasörü path'i
            steam_workshop_path = Path.home() / ".steam" / "steam" / "steamapps" / "workshop" / "content" / "431960"
            
            if not steam_workshop_path.exists():
                steam_workshop_path = Path.home() / ".local" / "share" / "Steam" / "steamapps" / "workshop" / "content" / "431960"
            
            wallpaper_path = steam_workshop_path / wallpaper_id
            
            if wallpaper_path.exists() and wallpaper_path.is_dir():
                shutil.rmtree(wallpaper_path)
                logger.info(f"Özel wallpaper silindi: {wallpaper_id}")
                return True
            else:
                logger.warning(f"Wallpaper klasörü bulunamadı: {wallpaper_path}")
                return False
                
        except Exception as e:
            logger.error(f"Wallpaper silme hatası: {e}")
            return False
    
    def stop_video_wallpaper(self, screen: str = "all") -> bool:
        """
        Video wallpaper process'lerini durdurur.
        
        Args:
            screen: Durdurulacak ekran ("all" tüm ekranlar için)
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            stopped_count = 0
            
            if screen == "all":
                # Tüm video process'leri durdur
                for screen_name in list(self.video_processes.keys()):
                    if self._stop_video_process(screen_name):
                        stopped_count += 1
            else:
                # Belirli ekran için durdur
                if self._stop_video_process(screen):
                    stopped_count += 1
            
            # MPV wallpaper process'lerini de durdur
            try:
                result = subprocess.run(['pkill', '-f', 'mpv.*wallpaper'],
                                      capture_output=True, timeout=5)
                if result.returncode == 0:
                    stopped_count += 1
                    logger.info("MPV wallpaper process'leri durduruldu")
            except:
                pass
            
            if stopped_count > 0:
                logger.info(f"{stopped_count} video wallpaper process'i durduruldu")
                return True
            else:
                logger.info("Durdurulacak video wallpaper process'i bulunamadı")
                return False
                
        except Exception as e:
            logger.error(f"Video wallpaper durdurma hatası: {e}")
            return False
    
    def _stop_video_process(self, screen: str) -> bool:
        """Belirli ekran için video process'ini durdurur."""
        try:
            if screen not in self.video_processes:
                return False
            
            process_info = self.video_processes[screen]
            process = process_info.get('process')
            
            if process and process.poll() is None:  # Process hala çalışıyor
                try:
                    # Önce SIGTERM gönder
                    process.terminate()
                    
                    # 3 saniye bekle
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        # Zorla öldür
                        process.kill()
                        process.wait()
                    
                    logger.info(f"Video process durduruldu: {screen}")
                    
                except Exception as e:
                    logger.error(f"Process durdurma hatası: {e}")
                    return False
            
            # Process bilgisini temizle
            del self.video_processes[screen]
            return True
            
        except Exception as e:
            logger.error(f"Video process durdurma hatası: {e}")
            return False
    
    def get_video_wallpaper_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Aktif video wallpaper'ların durumunu döner.
        
        Returns:
            Dict: {screen: {process_info, file_path, status}}
        """
        try:
            status = {}
            
            for screen, process_info in self.video_processes.items():
                process = process_info.get('process')
                file_path = process_info.get('file_path', 'Unknown')
                
                if process and process.poll() is None:
                    # Process çalışıyor
                    status[screen] = {
                        'status': 'running',
                        'file_path': file_path,
                        'pid': process.pid,
                        'method': process_info.get('method', 'unknown')
                    }
                else:
                    # Process durmuş
                    status[screen] = {
                        'status': 'stopped',
                        'file_path': file_path,
                        'pid': None,
                        'method': process_info.get('method', 'unknown')
                    }
            
            return status
            
        except Exception as e:
            logger.error(f"Video wallpaper durum kontrolü hatası: {e}")
            return {}
    
    def cleanup_dead_processes(self) -> int:
        """
        Ölü video process'lerini temizler.
        
        Returns:
            int: Temizlenen process sayısı
        """
        try:
            cleaned_count = 0
            dead_screens = []
            
            for screen, process_info in self.video_processes.items():
                process = process_info.get('process')
                
                if process and process.poll() is not None:  # Process ölmüş
                    dead_screens.append(screen)
                    cleaned_count += 1
            
            # Ölü process'leri temizle
            for screen in dead_screens:
                del self.video_processes[screen]
                logger.info(f"Ölü video process temizlendi: {screen}")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Ölü process temizleme hatası: {e}")
            return 0
    
    def _apply_sixel_wallpaper(self, media_file: Path, screen: str) -> bool:
        """Sixel ile wallpaper uygular - platform bağımsız çözüm."""
        try:
            from utils.ffmpeg_utils import apply_sixel_wallpaper, is_sixel_available
            
            # Sixel desteği kontrol et
            if not is_sixel_available():
                logger.warning("Sixel desteği mevcut değil")
                return False
            
            logger.info(f"Sixel ile wallpaper uygulanıyor: {media_file.name}")
            success = apply_sixel_wallpaper(media_file, screen)
            
            if success:
                logger.info(f"Sixel wallpaper başarıyla uygulandı: {media_file.name}")
                return True
            else:
                logger.error(f"Sixel wallpaper uygulanamadı: {media_file.name}")
                return False
                
        except Exception as e:
            logger.error(f"Sixel wallpaper uygulama hatası: {e}")
            return False