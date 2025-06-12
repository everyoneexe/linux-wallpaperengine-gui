"""
Wallpaper preview button widget
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
    Wallpaper preview button.
    
    Signals:
        wallpaper_selected: Emitted when wallpaper is selected
        add_to_playlist_requested: Emitted when adding to playlist is requested
    """
    
    wallpaper_selected = Signal(str)  # wallpaper_id
    add_to_playlist_requested = Signal(str)  # wallpaper_id
    delete_wallpaper_requested = Signal(str)  # wallpaper_id
    
    def __init__(self,
                 folder_id: str,
                 preview_path: Path,
                 parent=None):
        """
        Creates wallpaper button.
        
        Args:
            folder_id: Wallpaper folder ID
            preview_path: Preview image path
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.folder_id = folder_id
        self.preview_path = preview_path
        self._is_selected = False
        self.wallpaper_title = None
        self._original_pixmap = None  # Original pixmap before adding overlay
        
        self.setup_ui()
        self.load_preview_image()
        self.setup_connections()
        self.load_wallpaper_metadata()

    def setup_ui(self) -> None:
        """Sets up UI."""
        self.setFixedSize(WALLPAPER_BUTTON_SIZE, WALLPAPER_BUTTON_SIZE)
        self.setObjectName("WallpaperButton")
        
        # Initial tooltip
        self.update_tooltip()
        
        # Modern styling - compatible with square frame
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
        Loads preview image (first frame for video files).
        
        Returns:
            bool: True if loading successful
        """
        try:
            if not self.preview_path.exists():
                logger.warning(f"Preview file not found: {self.preview_path}")
                return False
            
            # Check if it's a video file
            if self.preview_path.suffix.lower() in ['.mp4', '.webm', '.mov']:
                return self._load_video_thumbnail()
            else:
                # Normal image/GIF loading
                return self._load_image_preview()
                
        except Exception as e:
            logger.error(f"Error loading preview ({self.folder_id}): {e}")
            return False
    
    def _load_image_preview(self) -> bool:
        """Loads normal image/GIF preview."""
        try:
            # Load and resize image
            pixmap = QPixmap(str(self.preview_path))
            if pixmap.isNull():
                logger.warning(f"Invalid image file: {self.preview_path}")
                return False
                
            # Resize
            scaled_pixmap = pixmap.scaled(
                WALLPAPER_BUTTON_SIZE - 10,  # Make slightly smaller for border
                WALLPAPER_BUTTON_SIZE - 10,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # Store original pixmap
            self._original_pixmap = scaled_pixmap
            
            # Add title overlay
            final_pixmap = self._add_title_overlay(scaled_pixmap)
            
            # Set as icon
            self.setIcon(QIcon(final_pixmap))
            self.setIconSize(final_pixmap.size())
            
            logger.debug(f"Image preview loaded: {self.folder_id}")
            return True
            
        except Exception as e:
            logger.error(f"Image preview error ({self.folder_id}): {e}")
            return False
    
    def _load_video_thumbnail(self) -> bool:
        """Creates thumbnail for video file."""
        try:
            import subprocess
            import tempfile
            import os
            
            # Create video thumbnail with FFmpeg
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                thumbnail_path = tmp_file.name
            
            try:
                # FFmpeg command - extract first frame as jpg
                cmd = [
                    'ffmpeg',
                    '-i', str(self.preview_path),
                    '-ss', '00:00:01',  # Take frame from 1st second
                    '-vframes', '1',    # Only 1 frame
                    '-q:v', '2',        # High quality
                    '-y',               # Overwrite
                    thumbnail_path
                ]
                
                result = subprocess.run(
                    cmd,
                    timeout=10,
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL
                )
                
                if result.returncode == 0 and os.path.exists(thumbnail_path):
                    # Load created thumbnail
                    pixmap = QPixmap(thumbnail_path)
                    if not pixmap.isNull():
                        # Resize
                        scaled_pixmap = pixmap.scaled(
                            WALLPAPER_BUTTON_SIZE - 10,
                            WALLPAPER_BUTTON_SIZE - 10,
                            Qt.KeepAspectRatio,
                            Qt.SmoothTransformation
                        )
                        
                        # Store original pixmap
                        self._original_pixmap = scaled_pixmap
                        
                        # Add title overlay
                        final_pixmap = self._add_title_overlay(scaled_pixmap)
                        
                        # Set as icon
                        self.setIcon(QIcon(final_pixmap))
                        self.setIconSize(final_pixmap.size())
                        
                        logger.debug(f"Video thumbnail created: {self.folder_id}")
                        return True
                
            except subprocess.TimeoutExpired:
                logger.warning(f"FFmpeg timeout: {self.folder_id}")
            except FileNotFoundError:
                logger.warning("FFmpeg not found - cannot create video thumbnail")
            finally:
                # Clean up temporary file
                try:
                    if os.path.exists(thumbnail_path):
                        os.unlink(thumbnail_path)
                except:
                    pass
            
            # If FFmpeg fails, show video icon
            return self._load_video_icon()
            
        except Exception as e:
            logger.error(f"Video thumbnail error ({self.folder_id}): {e}")
            return self._load_video_icon()
    
    def _load_video_icon(self) -> bool:
        """Shows default icon for video file."""
        try:
            # Create video play icon
            from PySide6.QtGui import QPainter, QBrush, QPen
            from PySide6.QtCore import QRect
            
            # Create empty pixmap
            pixmap = QPixmap(WALLPAPER_BUTTON_SIZE - 10, WALLPAPER_BUTTON_SIZE - 10)
            pixmap.fill(Qt.black)
            
            # Draw video icon with painter
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Gradient background
            from PySide6.QtGui import QLinearGradient
            gradient = QLinearGradient(0, 0, 0, pixmap.height())
            gradient.setColorAt(0, Qt.darkGray)
            gradient.setColorAt(1, Qt.black)
            painter.fillRect(pixmap.rect(), QBrush(gradient))
            
            # Draw play button (triangle)
            painter.setPen(QPen(Qt.white, 3))
            painter.setBrush(QBrush(Qt.white))
            
            center_x = pixmap.width() // 2
            center_y = pixmap.height() // 2
            size = min(pixmap.width(), pixmap.height()) // 3
            
            # Triangle coordinates
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
            
            # Store original pixmap
            self._original_pixmap = pixmap
            
            # Add title overlay
            final_pixmap = self._add_title_overlay(pixmap)
            
            # Set as icon
            self.setIcon(QIcon(final_pixmap))
            self.setIconSize(final_pixmap.size())
            
            logger.debug(f"Video icon created: {self.folder_id}")
            return True
            
        except Exception as e:
            logger.error(f"Video icon error ({self.folder_id}): {e}")
            return False

    def _add_title_overlay(self, pixmap: QPixmap) -> QPixmap:
        """
        Adds title overlay to pixmap (Windows Wallpaper Engine style).
        
        Args:
            pixmap: Original pixmap
            
        Returns:
            QPixmap: Pixmap with title overlay
        """
        try:
            if not self.wallpaper_title:
                return pixmap
            
            # Create new pixmap
            overlay_pixmap = QPixmap(pixmap.size())
            overlay_pixmap.fill(Qt.transparent)
            
            # Draw overlay with painter
            painter = QPainter(overlay_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.TextAntialiasing)
            
            # First draw original image
            painter.drawPixmap(0, 0, pixmap)
            
            # Prepare title text
            title_text = self.wallpaper_title
            if len(title_text) > 25:  # Shorten if too long
                title_text = title_text[:22] + "..."
            
            # Font settings
            font = QFont("Segoe UI", 9, QFont.Bold)
            painter.setFont(font)
            
            # Calculate text dimensions
            font_metrics = painter.fontMetrics()
            text_rect = font_metrics.boundingRect(title_text)
            
            # Overlay position (bottom part)
            overlay_height = max(24, text_rect.height() + 8)
            overlay_rect = QRect(
                0,
                pixmap.height() - overlay_height,
                pixmap.width(),
                overlay_height
            )
            
            # Semi-transparent black background
            overlay_color = QColor(0, 0, 0, 180)  # 70% opacity
            painter.fillRect(overlay_rect, overlay_color)
            
            # Text position (centered)
            text_x = (pixmap.width() - text_rect.width()) // 2
            text_y = pixmap.height() - (overlay_height - text_rect.height()) // 2 - 2
            
            # Draw white text
            painter.setPen(QColor(255, 255, 255, 255))
            painter.drawText(text_x, text_y, title_text)
            
            painter.end()
            
            return overlay_pixmap
            
        except Exception as e:
            logger.error(f"Title overlay error ({self.folder_id}): {e}")
            return pixmap

    def _refresh_title_overlay(self) -> None:
        """Redraws title overlay."""
        try:
            if self._original_pixmap and self.wallpaper_title:
                # Create new pixmap with overlay
                final_pixmap = self._add_title_overlay(self._original_pixmap)
                
                # Update icon
                self.setIcon(QIcon(final_pixmap))
                self.setIconSize(final_pixmap.size())
                
                logger.debug(f"Title overlay refreshed: {self.folder_id}")
                
        except Exception as e:
            logger.error(f"Title overlay refresh error ({self.folder_id}): {e}")

    def setup_connections(self) -> None:
        """Sets up signal connections."""
        self.clicked.connect(self._on_clicked)

    def _on_clicked(self) -> None:
        """Called when button is clicked."""
        self.wallpaper_selected.emit(self.folder_id)
        logger.debug(f"Wallpaper selected: {self.folder_id}")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handles mouse press event."""
        if event.button() == Qt.RightButton:
            # Show context menu on right click
            self._show_context_menu(event.globalPos())
        else:
            super().mousePressEvent(event)
    
    def _show_context_menu(self, position) -> None:
        """Shows context menu."""
        try:
            menu = QMenu(self)
            
            # Apply
            apply_action = QAction("🎨 Apply", self)
            apply_action.triggered.connect(lambda: self.wallpaper_selected.emit(self.folder_id))
            menu.addAction(apply_action)
            
            # Add to playlist
            playlist_action = QAction("➕ Add to Playlist", self)
            playlist_action.triggered.connect(lambda: self.add_to_playlist_requested.emit(self.folder_id))
            menu.addAction(playlist_action)
            
            # Delete option for custom wallpapers
            if self.folder_id.startswith('custom_') or self.folder_id.startswith('gif_'):
                menu.addSeparator()
                delete_action = QAction("🗑️ Delete", self)
                delete_action.triggered.connect(lambda: self.delete_wallpaper_requested.emit(self.folder_id))
                menu.addAction(delete_action)
            
            menu.exec(position)
            
        except Exception as e:
            logger.error(f"Context menu error: {e}")

    def mouseDoubleClickEvent(self, event) -> None:
        """Handles double click event - no longer used."""
        # Double click disabled, only single click and right click
        super().mouseDoubleClickEvent(event)

    def set_selected(self, selected: bool) -> None:
        """
        Sets selected state.
        
        Args:
            selected: Whether selected or not
        """
        if self._is_selected != selected:
            self._is_selected = selected
            self.setProperty("selected", selected)
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()

    def is_selected(self) -> bool:
        """
        Returns selected state.
        
        Returns:
            bool: True if selected
        """
        return self._is_selected

    def get_wallpaper_id(self) -> str:
        """
        Returns wallpaper ID.
        
        Returns:
            str: Wallpaper ID
        """
        return self.folder_id

    def get_preview_path(self) -> Path:
        """
        Returns preview file path.
        
        Returns:
            Path: Preview file path
        """
        return self.preview_path

    def refresh_preview(self) -> bool:
        """
        Reloads preview.
        
        Returns:
            bool: True if refresh successful
        """
        success = self.load_preview_image()
        if success and self.wallpaper_title:
            # Redraw title overlay
            self._refresh_title_overlay()
        return success

    def load_wallpaper_metadata(self) -> None:
        """Loads wallpaper metadata."""
        try:
            from utils.metadata_manager import metadata_manager
            
            # Load metadata if not yet loaded
            if not metadata_manager.wallpapers:
                logger.debug("Loading metadata...")
                metadata_manager.scan_wallpapers()
            
            metadata = metadata_manager.get_metadata(self.folder_id)
            
            if metadata and metadata.title and metadata.title.strip():
                self.wallpaper_title = metadata.title.strip()
            else:
                self.wallpaper_title = f"Wallpaper {self.folder_id}"
                
            # Redraw title overlay
            self._refresh_title_overlay()
                
            # Update tooltip
            self.update_tooltip()
            
        except Exception as e:
            logger.debug(f"Metadata loading error {self.folder_id}: {e}")
            self.wallpaper_title = f"Wallpaper {self.folder_id}"
            self.update_tooltip()

    def update_tooltip(self) -> None:
        """Updates tooltip - old multi-line format."""
        try:
            if self.wallpaper_title:
                title_text = self.wallpaper_title
                if len(title_text) > 50:
                    title_text = title_text[:47] + "..."
            else:
                title_text = f"Wallpaper {self.folder_id}"
            
            # Updated format
            tooltip = (
                f"📝 {title_text}\n"
                f"🆔 ID: {self.folder_id}\n\n"
                f"🖱️ Left click: Apply\n"
                f"🖱️ Right click: Menu"
            )
            
            # Additional info for custom wallpapers
            if self.folder_id.startswith('custom_') or self.folder_id.startswith('gif_'):
                tooltip += "\n🗑️ Deletable custom media"
            
            self.setToolTip(tooltip)
            
        except Exception as e:
            logger.error(f"Tooltip update error: {e}")

    def set_tooltip_info(self, additional_info: str = "") -> None:
        """
        Updates tooltip information.
        
        Args:
            additional_info: Additional info text
        """
        self.update_tooltip()
        
        if additional_info:
            current_tooltip = self.toolTip()
            self.setToolTip(f"{current_tooltip}\n\n{additional_info}")

    def __repr__(self) -> str:
        """String representation."""
        return f"WallpaperButton(id='{self.folder_id}', selected={self._is_selected})"