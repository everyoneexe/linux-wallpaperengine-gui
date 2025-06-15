"""
Wallpaper önizleme butonu widget'ı
"""
import logging
from typing import Optional, Callable
from pathlib import Path

from PySide6.QtWidgets import QPushButton, QMenu, QLabel
from PySide6.QtGui import QPixmap, QIcon, QAction, QMouseEvent, QPainter, QColor, QFont
from PySide6.QtCore import Qt, Signal, QRect

from utils import WALLPAPER_BUTTON_SIZE

logger = logging.getLogger(__name__)


class WallpaperButton(QPushButton):
    """
    Wallpaper önizleme butonu.
    
    Signals:
        wallpaper_selected: Wallpaper seçildiğinde emit edilir
        add_to_playlist_requested: Playlist'e ekleme istendiğinde emit edilir
    """
    
    wallpaper_selected = Signal(str)  # wallpaper_id
    add_to_playlist_requested = Signal(str)  # wallpaper_id
    delete_wallpaper_requested = Signal(str)  # wallpaper_id
    
    def __init__(self,
                 folder_id: str,
                 preview_path: Path,
                 parent=None):
        """
        Wallpaper butonu oluşturur.
        
        Args:
            folder_id: Wallpaper klasör ID'si
            preview_path: Önizleme resmi yolu
            parent: Üst widget
        """
        super().__init__(parent)
        
        self.folder_id = folder_id
        self.preview_path = preview_path
        self._is_selected = False
        self.wallpaper_title = None
        self._original_pixmap = None  # Overlay eklemeden önceki orijinal pixmap
        
        self.setup_ui()
        self.load_preview_image()
        self.setup_connections()
        self.load_wallpaper_metadata()

    def setup_ui(self) -> None:
        """UI'ı kurar."""
        self.setFixedSize(WALLPAPER_BUTTON_SIZE, WALLPAPER_BUTTON_SIZE)
        self.setObjectName("WallpaperButton")
        
        # Başlangıç tooltip'i
        self.update_tooltip()
        
        # Modern styling - kare çerçeve ile uyumlu
        self.setStyleSheet("""
            QPushButton#WallpaperButton {
                border: 3px solid #444;
                border-radius: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2b2b2b, stop:1 #1b1b1b);
                margin: 3px;
                padding: 2px;
            }
            QPushButton#WallpaperButton:hover {
                border: 3px solid #00d4ff;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3b3b3b, stop:1 #2b2b2b);
            }
            QPushButton#WallpaperButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1b1b1b, stop:1 #0b0b0b);
                border: 3px solid #0099cc;
            }
            QPushButton#WallpaperButton[selected="true"] {
                border: 3px solid #00ff88;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2b4b2b, stop:1 #1b3b1b);
            }
        """)

    def load_preview_image(self) -> bool:
        """
        Önizleme resmini yükler (video dosyaları için ilk frame).
        
        Returns:
            bool: Yükleme başarılı ise True
        """
        try:
            if not self.preview_path.exists():
                logger.warning(f"Önizleme dosyası bulunamadı: {self.preview_path}")
                return False
            
            # Video dosyası mı kontrol et
            if self.preview_path.suffix.lower() in ['.mp4', '.webm', '.mov']:
                return self._load_video_thumbnail()
            else:
                # Normal resim/GIF yükleme
                return self._load_image_preview()
                
        except Exception as e:
            logger.error(f"Önizleme yüklenirken hata ({self.folder_id}): {e}")
            return False
    
    def _load_image_preview(self) -> bool:
        """Normal resim/GIF önizlemesi yükler."""
        try:
            # Resmi yükle ve boyutlandır
            pixmap = QPixmap(str(self.preview_path))
            if pixmap.isNull():
                logger.warning(f"Geçersiz resim dosyası: {self.preview_path}")
                return False
                
            # Boyutlandır
            scaled_pixmap = pixmap.scaled(
                WALLPAPER_BUTTON_SIZE - 10,  # Border için biraz küçült
                WALLPAPER_BUTTON_SIZE - 10,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # Orijinal pixmap'i sakla
            self._original_pixmap = scaled_pixmap
            
            # Title overlay ekle
            final_pixmap = self._add_title_overlay(scaled_pixmap)
            
            # Icon olarak ayarla
            self.setIcon(QIcon(final_pixmap))
            self.setIconSize(final_pixmap.size())
            
            logger.debug(f"Resim önizlemesi yüklendi: {self.folder_id}")
            return True
            
        except Exception as e:
            logger.error(f"Resim önizleme hatası ({self.folder_id}): {e}")
            return False
    
    def _load_video_thumbnail(self) -> bool:
        """Video dosyası için thumbnail oluşturur."""
        try:
            import subprocess
            import tempfile
            import os
            
            # FFmpeg ile video thumbnail oluştur
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                thumbnail_path = tmp_file.name
            
            try:
                # FFmpeg komutu - ilk frame'i jpg olarak çıkar
                cmd = [
                    'ffmpeg',
                    '-i', str(self.preview_path),
                    '-ss', '00:00:01',  # 1. saniyeden frame al
                    '-vframes', '1',    # Sadece 1 frame
                    '-q:v', '2',        # Yüksek kalite
                    '-y',               # Üzerine yaz
                    thumbnail_path
                ]
                
                result = subprocess.run(
                    cmd,
                    timeout=10,
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL
                )
                
                if result.returncode == 0 and os.path.exists(thumbnail_path):
                    # Oluşturulan thumbnail'i yükle
                    pixmap = QPixmap(thumbnail_path)
                    if not pixmap.isNull():
                        # Boyutlandır
                        scaled_pixmap = pixmap.scaled(
                            WALLPAPER_BUTTON_SIZE - 10,
                            WALLPAPER_BUTTON_SIZE - 10,
                            Qt.KeepAspectRatio,
                            Qt.SmoothTransformation
                        )
                        
                        # Orijinal pixmap'i sakla
                        self._original_pixmap = scaled_pixmap
                        
                        # Title overlay ekle
                        final_pixmap = self._add_title_overlay(scaled_pixmap)
                        
                        # Icon olarak ayarla
                        self.setIcon(QIcon(final_pixmap))
                        self.setIconSize(final_pixmap.size())
                        
                        logger.debug(f"Video thumbnail oluşturuldu: {self.folder_id}")
                        return True
                
            except subprocess.TimeoutExpired:
                logger.warning(f"FFmpeg timeout: {self.folder_id}")
            except FileNotFoundError:
                logger.warning("FFmpeg bulunamadı - video thumbnail oluşturulamıyor")
            finally:
                # Geçici dosyayı temizle
                try:
                    if os.path.exists(thumbnail_path):
                        os.unlink(thumbnail_path)
                except:
                    pass
            
            # FFmpeg başarısız olursa, video icon göster
            return self._load_video_icon()
            
        except Exception as e:
            logger.error(f"Video thumbnail hatası ({self.folder_id}): {e}")
            return self._load_video_icon()
    
    def _load_video_icon(self) -> bool:
        """Video dosyası için varsayılan icon gösterir."""
        try:
            # Video play icon oluştur
            from PySide6.QtGui import QPainter, QBrush, QPen
            from PySide6.QtCore import QRect
            
            # Boş pixmap oluştur
            pixmap = QPixmap(WALLPAPER_BUTTON_SIZE - 10, WALLPAPER_BUTTON_SIZE - 10)
            pixmap.fill(Qt.black)
            
            # Painter ile video icon çiz
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Gradient background
            from PySide6.QtGui import QLinearGradient
            gradient = QLinearGradient(0, 0, 0, pixmap.height())
            gradient.setColorAt(0, Qt.darkGray)
            gradient.setColorAt(1, Qt.black)
            painter.fillRect(pixmap.rect(), QBrush(gradient))
            
            # Play button çiz (üçgen)
            painter.setPen(QPen(Qt.white, 3))
            painter.setBrush(QBrush(Qt.white))
            
            center_x = pixmap.width() // 2
            center_y = pixmap.height() // 2
            size = min(pixmap.width(), pixmap.height()) // 3
            
            # Üçgen koordinatları
            from PySide6.QtGui import QPolygon
            from PySide6.QtCore import QPoint
            triangle = QPolygon([
                QPoint(center_x - size//2, center_y - size//2),
                QPoint(center_x - size//2, center_y + size//2),
                QPoint(center_x + size//2, center_y)
            ])
            
            painter.drawPolygon(triangle)
            
            # Video text
            painter.setPen(QPen(Qt.lightGray, 1))
            painter.drawText(QRect(0, pixmap.height() - 20, pixmap.width(), 20),
                           Qt.AlignCenter, "VIDEO")
            
            painter.end()
            
            # Orijinal pixmap'i sakla
            self._original_pixmap = pixmap
            
            # Title overlay ekle
            final_pixmap = self._add_title_overlay(pixmap)
            
            # Icon olarak ayarla
            self.setIcon(QIcon(final_pixmap))
            self.setIconSize(final_pixmap.size())
            
            logger.debug(f"Video icon oluşturuldu: {self.folder_id}")
            return True
            
        except Exception as e:
            logger.error(f"Video icon hatası ({self.folder_id}): {e}")
            return False

    def _add_title_overlay(self, pixmap: QPixmap) -> QPixmap:
        """
        Pixmap'e title overlay ekler (Windows Wallpaper Engine tarzı).
        
        Args:
            pixmap: Orijinal pixmap
            
        Returns:
            QPixmap: Title overlay'li pixmap
        """
        try:
            if not self.wallpaper_title:
                return pixmap
            
            # Yeni pixmap oluştur
            overlay_pixmap = QPixmap(pixmap.size())
            overlay_pixmap.fill(Qt.transparent)
            
            # Painter ile overlay çiz
            painter = QPainter(overlay_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.TextAntialiasing)
            
            # Önce orijinal resmi çiz
            painter.drawPixmap(0, 0, pixmap)
            
            # Title text'i hazırla
            title_text = self.wallpaper_title
            if len(title_text) > 25:  # Çok uzunsa kısalt
                title_text = title_text[:22] + "..."
            
            # Font ayarları
            font = QFont("Segoe UI", 9, QFont.Bold)
            painter.setFont(font)
            
            # Text boyutlarını hesapla
            font_metrics = painter.fontMetrics()
            text_rect = font_metrics.boundingRect(title_text)
            
            # Overlay pozisyonu (alt kısım)
            overlay_height = max(24, text_rect.height() + 8)
            overlay_rect = QRect(
                0,
                pixmap.height() - overlay_height,
                pixmap.width(),
                overlay_height
            )
            
            # Yarı saydam siyah background
            overlay_color = QColor(0, 0, 0, 180)  # %70 opacity
            painter.fillRect(overlay_rect, overlay_color)
            
            # Text pozisyonu (ortalanmış)
            text_x = (pixmap.width() - text_rect.width()) // 2
            text_y = pixmap.height() - (overlay_height - text_rect.height()) // 2 - 2
            
            # Beyaz text çiz
            painter.setPen(QColor(255, 255, 255, 255))
            painter.drawText(text_x, text_y, title_text)
            
            painter.end()
            
            return overlay_pixmap
            
        except Exception as e:
            logger.error(f"Title overlay hatası ({self.folder_id}): {e}")
            return pixmap

    def _refresh_title_overlay(self) -> None:
        """Title overlay'i yeniden çizer."""
        try:
            if self._original_pixmap and self.wallpaper_title:
                # Overlay'li yeni pixmap oluştur
                final_pixmap = self._add_title_overlay(self._original_pixmap)
                
                # Icon'u güncelle
                self.setIcon(QIcon(final_pixmap))
                self.setIconSize(final_pixmap.size())
                
                logger.debug(f"Title overlay yenilendi: {self.folder_id}")
                
        except Exception as e:
            logger.error(f"Title overlay yenileme hatası ({self.folder_id}): {e}")

    def setup_connections(self) -> None:
        """Sinyal bağlantılarını kurar."""
        self.clicked.connect(self._on_clicked)

    def _on_clicked(self) -> None:
        """Buton tıklandığında çağrılır."""
        self.wallpaper_selected.emit(self.folder_id)
        logger.debug(f"Wallpaper seçildi: {self.folder_id}")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Mouse basma olayını işler."""
        if event.button() == Qt.RightButton:
            # Sağ tık ile context menü göster
            self._show_context_menu(event.globalPos())
        else:
            super().mousePressEvent(event)
    
    def _show_context_menu(self, position) -> None:
        """Context menüsünü gösterir."""
        try:
            menu = QMenu(self)
            
            # Uygula
            apply_action = QAction("🎨 Uygula", self)
            apply_action.triggered.connect(lambda: self.wallpaper_selected.emit(self.folder_id))
            menu.addAction(apply_action)
            
            # Playlist'e ekle
            playlist_action = QAction("➕ Playlist'e Ekle", self)
            playlist_action.triggered.connect(lambda: self.add_to_playlist_requested.emit(self.folder_id))
            menu.addAction(playlist_action)
            
            # Özel wallpaper'lar için silme seçeneği
            if self.folder_id.startswith('custom_') or self.folder_id.startswith('gif_'):
                menu.addSeparator()
                delete_action = QAction("🗑️ Sil", self)
                delete_action.triggered.connect(lambda: self.delete_wallpaper_requested.emit(self.folder_id))
                menu.addAction(delete_action)
            
            menu.exec(position)
            
        except Exception as e:
            logger.error(f"Context menü hatası: {e}")

    def mouseDoubleClickEvent(self, event) -> None:
        """Çift tık olayını işler - artık kullanılmıyor."""
        # Çift tık devre dışı, sadece tek tık ve sağ tık
        super().mouseDoubleClickEvent(event)

    def set_selected(self, selected: bool) -> None:
        """
        Seçili durumunu ayarlar.
        
        Args:
            selected: Seçili olup olmadığı
        """
        if self._is_selected != selected:
            self._is_selected = selected
            self.setProperty("selected", selected)
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()

    def is_selected(self) -> bool:
        """
        Seçili durumunu döner.
        
        Returns:
            bool: Seçili ise True
        """
        return self._is_selected

    def get_wallpaper_id(self) -> str:
        """
        Wallpaper ID'sini döner.
        
        Returns:
            str: Wallpaper ID'si
        """
        return self.folder_id

    def get_preview_path(self) -> Path:
        """
        Önizleme dosya yolunu döner.
        
        Returns:
            Path: Önizleme dosya yolu
        """
        return self.preview_path

    def refresh_preview(self) -> bool:
        """
        Önizlemeyi yeniden yükler.
        
        Returns:
            bool: Yenileme başarılı ise True
        """
        success = self.load_preview_image()
        if success and self.wallpaper_title:
            # Title overlay'i yeniden çiz
            self._refresh_title_overlay()
        return success

    def load_wallpaper_metadata(self) -> None:
        """Wallpaper metadata'sını yükler."""
        try:
            from utils.metadata_manager import metadata_manager
            
            # Metadata henüz yüklenmemişse yükle
            if not metadata_manager.wallpapers:
                logger.debug("Metadata yükleniyor...")
                metadata_manager.scan_wallpapers()
            
            metadata = metadata_manager.get_metadata(self.folder_id)
            
            if metadata and metadata.title and metadata.title.strip():
                self.wallpaper_title = metadata.title.strip()
            else:
                self.wallpaper_title = f"Wallpaper {self.folder_id}"
                
            # Title overlay'i yeniden çiz
            self._refresh_title_overlay()
                
            # Tooltip'i güncelle
            self.update_tooltip()
            
        except Exception as e:
            logger.debug(f"Metadata yükleme hatası {self.folder_id}: {e}")
            self.wallpaper_title = f"Wallpaper {self.folder_id}"
            self.update_tooltip()

    def update_tooltip(self) -> None:
        """Tooltip'i günceller - eski çok satırlı format."""
        try:
            if self.wallpaper_title:
                title_text = self.wallpaper_title
                if len(title_text) > 50:
                    title_text = title_text[:47] + "..."
            else:
                title_text = f"Wallpaper {self.folder_id}"
            
            # Güncellenmiş format
            tooltip = (
                f"📝 {title_text}\n"
                f"🆔 ID: {self.folder_id}\n\n"
                f"🖱️ Sol tık: Uygula\n"
                f"🖱️ Sağ tık: Menü"
            )
            
            # Özel wallpaper'lar için ek bilgi
            if self.folder_id.startswith('custom_') or self.folder_id.startswith('gif_'):
                tooltip += "\n🗑️ Silinebilir özel medya"
            
            self.setToolTip(tooltip)
            
        except Exception as e:
            logger.error(f"Tooltip güncelleme hatası: {e}")

    def set_tooltip_info(self, additional_info: str = "") -> None:
        """
        Tooltip bilgisini günceller.
        
        Args:
            additional_info: Ek bilgi metni
        """
        self.update_tooltip()
        
        if additional_info:
            current_tooltip = self.toolTip()
            self.setToolTip(f"{current_tooltip}\n\n{additional_info}")

    def __repr__(self) -> str:
        """String representation."""
        return f"WallpaperButton(id='{self.folder_id}', selected={self._is_selected})"