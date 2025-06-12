"""
Playlist control widget
"""
import logging
from typing import Optional, List

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QRadioButton, QPushButton, QListWidget, QListWidgetItem,
    QGroupBox, QMessageBox, QSpinBox, QCheckBox, QSlider,
    QDialog, QDialogButtonBox, QFormLayout
)
from PySide6.QtCore import Qt, Signal

from utils import TIMER_INTERVALS

logger = logging.getLogger(__name__)


class CustomTimerDialog(QDialog):
    """Custom timer setup dialog."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⏰ Custom Timer Setup")
        self.setFixedSize(350, 250)
        self.setModal(True)
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("⏰ Set Custom Timer Duration")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #00d4ff; margin: 10px;")
        layout.addWidget(title)
        
        # Form layout
        form_layout = QFormLayout()
        
        # Hours
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(0, 23)
        self.hours_spin.setSuffix(" hours")
        self.hours_spin.setMinimumWidth(100)
        form_layout.addRow("🕐 Hours:", self.hours_spin)
        
        # Minutes
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 59)
        self.minutes_spin.setValue(1)  # Default 1 minute
        self.minutes_spin.setSuffix(" minutes")
        self.minutes_spin.setMinimumWidth(100)
        form_layout.addRow("⏰ Minutes:", self.minutes_spin)
        
        # Seconds
        self.seconds_spin = QSpinBox()
        self.seconds_spin.setRange(0, 59)
        self.seconds_spin.setSuffix(" seconds")
        self.seconds_spin.setMinimumWidth(100)
        form_layout.addRow("⏱️ Seconds:", self.seconds_spin)
        
        layout.addLayout(form_layout)
        
        # Quick options
        quick_layout = QHBoxLayout()
        quick_label = QLabel("🚀 Quick Options:")
        quick_label.setStyleSheet("font-weight: bold; color: #00d4ff;")
        layout.addWidget(quick_label)
        
        quick_15min = QPushButton("15 min")
        quick_30min = QPushButton("30 min")
        quick_1hour = QPushButton("1 hour")
        quick_2hour = QPushButton("2 hours")
        
        quick_15min.clicked.connect(lambda: self.set_quick_time(0, 15, 0))
        quick_30min.clicked.connect(lambda: self.set_quick_time(0, 30, 0))
        quick_1hour.clicked.connect(lambda: self.set_quick_time(1, 0, 0))
        quick_2hour.clicked.connect(lambda: self.set_quick_time(2, 0, 0))
        
        for btn in [quick_15min, quick_30min, quick_1hour, quick_2hour]:
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(0, 212, 255, 0.2);
                    border: 1px solid #00d4ff;
                    border-radius: 6px;
                    padding: 6px 12px;
                    color: #00d4ff;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: rgba(0, 212, 255, 0.4);
                }
            """)
            quick_layout.addWidget(btn)
        
        layout.addLayout(quick_layout)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def set_quick_time(self, hours: int, minutes: int, seconds: int):
        """Quick time setting."""
        self.hours_spin.setValue(hours)
        self.minutes_spin.setValue(minutes)
        self.seconds_spin.setValue(seconds)
        
    def get_interval(self) -> int:
        """Returns interval in total seconds."""
        hours = self.hours_spin.value()
        minutes = self.minutes_spin.value()
        seconds = self.seconds_spin.value()
        
        total_seconds = hours * 3600 + minutes * 60 + seconds
        return total_seconds
        
    def get_display_text(self) -> str:
        """Returns display text."""
        hours = self.hours_spin.value()
        minutes = self.minutes_spin.value()
        seconds = self.seconds_spin.value()
        
        parts = []
        if hours > 0:
            parts.append(f"{hours} hours")
        if minutes > 0:
            parts.append(f"{minutes} min")
        if seconds > 0:
            parts.append(f"{seconds} sec")
            
        if not parts:
            return "Custom: 0 seconds"
            
        return f"Custom: {' '.join(parts)}"


class PlaylistWidget(QFrame):
    """
    Playlist control panel widget.
    
    Signals:
        play_pause_requested: When play/pause operation is requested
        next_requested: When next wallpaper is requested
        prev_requested: When previous wallpaper is requested
        add_current_requested: When adding current wallpaper to playlist is requested
        remove_selected_requested: When removing selected wallpaper is requested
        clear_playlist_requested: When clearing playlist is requested
        timer_interval_changed: When timer interval changes
        play_mode_changed: When play mode changes
    """
    
    play_pause_requested = Signal()
    next_requested = Signal()
    prev_requested = Signal()
    add_current_requested = Signal()
    remove_selected_requested = Signal()
    clear_playlist_requested = Signal()
    timer_interval_changed = Signal(int)  # seconds
    play_mode_changed = Signal(bool)  # is_random
    wallpaper_selected = Signal(str)  # wallpaper_id - when selected from playlist
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._is_playing = False
        self._current_wallpaper = None
        self._parent_window = parent
        
        self.setup_ui()
        self.setup_connections()
        self.setup_styles()

    def setup_ui(self) -> None:
        """Sets up UI."""
        self.setFrameStyle(QFrame.StyledPanel)
        self.setMaximumWidth(400)
        self.setMinimumWidth(350)
        self.setObjectName("PlaylistWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Playlist title - more modern
        self.title_label = QLabel("🎵 PLAYLIST CONTROL")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setObjectName("PlaylistTitle")
        layout.addWidget(self.title_label)

        # Current playing info - more elegant
        self.current_label = QLabel("🎧 Now: None")
        self.current_label.setObjectName("CurrentPlaying")
        layout.addWidget(self.current_label)

        # Timer controls group
        self.setup_timer_group(layout)

        # Control buttons
        self.setup_control_buttons(layout)

        # Playlist
        self.setup_playlist_section(layout)

        # Management buttons
        self.setup_management_buttons(layout)

    def setup_timer_group(self, parent_layout: QVBoxLayout) -> None:
        """Sets up timer control group."""
        timer_group = QGroupBox("⏰ Timer Settings")
        timer_group.setObjectName("TimerGroup")
        timer_layout = QVBoxLayout(timer_group)
        timer_layout.setSpacing(10)

        # Timer interval combo
        self.timer_combo = QComboBox()
        self.timer_combo.addItems(list(TIMER_INTERVALS.keys()))
        self.timer_combo.setCurrentIndex(1)  # 1 minute default
        timer_layout.addWidget(self.timer_combo)


        # Play mode
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(15)
        
        self.sequential_radio = QRadioButton("Sequential")
        self.random_radio = QRadioButton("Random")
        self.sequential_radio.setChecked(True)
        
        mode_layout.addWidget(self.sequential_radio)
        mode_layout.addWidget(self.random_radio)
        timer_layout.addLayout(mode_layout)

        parent_layout.addWidget(timer_group)

    def setup_control_buttons(self, parent_layout: QVBoxLayout) -> None:
        """Sets up control buttons."""
        controls_label = QLabel("🎮 Controls")
        controls_label.setObjectName("ControlsLabel")
        parent_layout.addWidget(controls_label)
        
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)
        
        self.play_btn = QPushButton("▶️")
        self.prev_btn = QPushButton("⏮️")
        self.next_btn = QPushButton("⏭️")

        for btn in [self.prev_btn, self.play_btn, self.next_btn]:
            btn.setFixedSize(50, 50)
            btn.setObjectName("ControlButton")
            controls_layout.addWidget(btn)

        parent_layout.addLayout(controls_layout)

    def setup_playlist_section(self, parent_layout: QVBoxLayout) -> None:
        """Sets up playlist section."""
        playlist_label = QLabel("📋 Playlist")
        playlist_label.setObjectName("PlaylistLabel")
        parent_layout.addWidget(playlist_label)
        
        self.playlist_widget = QListWidget()
        self.playlist_widget.setMinimumHeight(200)
        self.playlist_widget.setObjectName("PlaylistList")
        parent_layout.addWidget(self.playlist_widget)

    def setup_management_buttons(self, parent_layout: QVBoxLayout) -> None:
        """Sets up management buttons."""
        playlist_btns = QHBoxLayout()
        playlist_btns.setSpacing(8)
        
        self.add_btn = QPushButton("➕ Add")
        self.remove_btn = QPushButton("➖ Remove")
        self.clear_btn = QPushButton("🗑️ Clear")

        for btn in [self.add_btn, self.remove_btn, self.clear_btn]:
            btn.setFixedHeight(40)
            btn.setObjectName("ManagementButton")
            playlist_btns.addWidget(btn)

        parent_layout.addLayout(playlist_btns)

    def setup_connections(self) -> None:
        """Sets up signal connections."""
        # Control buttons
        self.play_btn.clicked.connect(self.play_pause_requested.emit)
        self.next_btn.clicked.connect(self.next_requested.emit)
        self.prev_btn.clicked.connect(self.prev_requested.emit)
        
        # Management buttons
        self.add_btn.clicked.connect(self.add_current_requested.emit)
        self.remove_btn.clicked.connect(self.remove_selected_requested.emit)
        self.clear_btn.clicked.connect(self._on_clear_requested)
        
        # Timer and mode changes
        self.timer_combo.currentTextChanged.connect(self._on_timer_changed)
        self.sequential_radio.toggled.connect(self._on_mode_changed)
        
        # Playlist item click
        self.playlist_widget.itemClicked.connect(self._on_playlist_item_clicked)

    def setup_styles(self) -> None:
        """Sets up widget styles."""
        self.setStyleSheet("""
            QFrame#PlaylistWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.08), stop:1 rgba(255, 255, 255, 0.03));
                border: 2px solid #444;
                border-radius: 15px;
                margin: 5px;
                padding: 10px;
            }
            
            QLabel#PlaylistTitle {
                font-size: 18px;
                font-weight: bold;
                color: #00d4ff;
                background: rgba(0, 212, 255, 0.1);
                border: 2px solid rgba(0, 212, 255, 0.3);
                border-radius: 10px;
                padding: 12px;
                margin: 5px;
            }
            
            QLabel#CurrentPlaying {
                color: #00ff88;
                font-weight: bold;
                font-size: 14px;
                background: rgba(0, 255, 136, 0.1);
                border: 1px solid rgba(0, 255, 136, 0.3);
                border-radius: 8px;
                padding: 8px;
                margin: 5px;
            }
            
            QLabel#ControlsLabel, QLabel#PlaylistLabel, QLabel#ManagementLabel {
                color: #00d4ff;
                font-weight: bold;
                font-size: 14px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.08), stop:1 rgba(255, 255, 255, 0.03));
                border: 1px solid #444;
                border-radius: 6px;
                padding: 6px 10px;
                margin: 5px 0px;
            }
            
            
            
            /* GroupBox için toolbar benzeri arka plan */
            QGroupBox#TimerGroup {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.08), stop:1 rgba(255, 255, 255, 0.03));
                border: 2px solid #444;
                border-radius: 10px;
                padding: 8px;
                margin: 2px;
                font-weight: bold;
                font-size: 14px;
                color: #00d4ff;
                padding-top: 15px;
            }
            
            QGroupBox#TimerGroup::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #00d4ff;
            }
            
            /* ComboBox için toolbar benzeri arka plan */
            QComboBox {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.08), stop:1 rgba(255, 255, 255, 0.03));
                border: 1px solid #444;
                border-radius: 6px;
                padding: 6px 10px;
                margin: 2px;
                color: white;
                font-weight: 500;
            }
            
            /* RadioButton için toolbar benzeri arka plan */
            QRadioButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.08), stop:1 rgba(255, 255, 255, 0.03));
                border: 1px solid #444;
                border-radius: 6px;
                padding: 6px 10px;
                margin: 2px;
                color: white;
                font-weight: 500;
            }
            
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border-radius: 8px;
                border: 2px solid #555;
                background: #2a2a2a;
            }
            
            QRadioButton::indicator:hover {
                border: 2px solid #00d4ff;
            }
            
            QRadioButton::indicator:checked {
                background: qradial-gradient(cx:0.5, cy:0.5, radius:0.5,
                    stop:0 #00d4ff, stop:0.6 #00d4ff, stop:0.7 transparent);
                border: 2px solid #00d4ff;
            }
            
            /* Control buttons için toolbar benzeri arka plan */
            QPushButton#ControlButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.08), stop:1 rgba(255, 255, 255, 0.03));
                border: 1px solid #444;
                border-radius: 6px;
                padding: 4px;
                margin: 2px;
                color: white;
                font-size: 16px;
            }
            
            QPushButton#ControlButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 212, 255, 0.2), stop:1 rgba(0, 212, 255, 0.1));
                border: 1px solid #00d4ff;
            }
            
            /* Management buttons için toolbar benzeri arka plan */
            QPushButton#ManagementButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.08), stop:1 rgba(255, 255, 255, 0.03));
                border: 1px solid #444;
                border-radius: 6px;
                padding: 8px 12px;
                margin: 2px;
                color: #00d4ff;
                font-weight: bold;
            }
            
            QPushButton#ManagementButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 212, 255, 0.2), stop:1 rgba(0, 212, 255, 0.1));
                border: 1px solid #00d4ff;
            }
            
            QListWidget#PlaylistList {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e1e1e, stop:1 #0e0e0e);
                border: 2px solid #555;
                border-radius: 10px;
                color: white;
                selection-background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #00d4ff, stop:1 #0099cc);
                padding: 5px;
            }
            
            QListWidget#PlaylistList::item {
                padding: 8px;
                border-bottom: 1px solid #333;
                border-radius: 5px;
                margin: 2px;
            }
            
            QListWidget#PlaylistList::item:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(0, 212, 255, 0.2), stop:1 rgba(0, 153, 204, 0.2));
            }
            
            QListWidget#PlaylistList::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #00d4ff, stop:1 #0099cc);
                color: white;
                font-weight: bold;
            }
        """)

    def _on_timer_changed(self, text: str) -> None:
        """Called when timer interval changes."""
        if text == "Custom...":
            # Open custom timer dialog
            self._show_custom_timer_dialog()
        elif text.startswith("Custom:"):
            # Custom timer value - get real value from PlaylistManager
            if self._parent_window and hasattr(self._parent_window, 'playlist_manager'):
                interval, _ = self._parent_window.playlist_manager.get_custom_timer_info()
                if interval:
                    self.timer_interval_changed.emit(interval)
                    logger.info(f"Using custom timer: '{text}' = {interval} seconds ({interval/60:.1f} minutes)")
                    return
            # Fallback - use default if custom timer not found
            interval = 60
            self.timer_interval_changed.emit(interval)
            logger.warning(f"Custom timer not found, using default: {interval} seconds")
        else:
            # Normal timer values
            interval = TIMER_INTERVALS.get(text, 60)
            self.timer_interval_changed.emit(interval)
            logger.info(f"Timer interval changed: '{text}' = {interval} seconds ({interval/60:.1f} minutes)")
    
    def _show_custom_timer_dialog(self) -> None:
        """Shows custom timer setup dialog."""
        dialog = CustomTimerDialog(self)
        if dialog.exec() == QDialog.Accepted:
            custom_interval = dialog.get_interval()
            if custom_interval > 0:
                # Add custom value to combo
                custom_text = dialog.get_display_text()
                
                # Remove previous custom value
                for i in range(self.timer_combo.count()):
                    if self.timer_combo.itemText(i).startswith("Custom:"):
                        self.timer_combo.removeItem(i)
                        break
                
                # Add new custom value
                self.timer_combo.insertItem(self.timer_combo.count() - 1, custom_text)
                self.timer_combo.setCurrentText(custom_text)
                
                # Also save to PlaylistManager (through parent window)
                if self._parent_window and hasattr(self._parent_window, 'playlist_manager'):
                    self._parent_window.playlist_manager.set_custom_timer(custom_interval, custom_text)
                
                # Apply custom interval - call at the END
                self.timer_interval_changed.emit(custom_interval)
                
                logger.info(f"Custom timer set: '{custom_text}' = {custom_interval} seconds ({custom_interval/60:.1f} minutes)")
        else:
            # Cancelled, restore previous selection
            self.timer_combo.setCurrentIndex(1)  # 1 minute default

    def _on_mode_changed(self, checked: bool) -> None:
        """Called when play mode changes."""
        if checked:  # Sequential radio checked
            is_random = False
        else:
            is_random = self.random_radio.isChecked()
        
        self.play_mode_changed.emit(is_random)
        logger.debug(f"Play mode changed: {'Random' if is_random else 'Sequential'}")

    def _on_clear_requested(self) -> None:
        """Called when playlist clear is requested."""
        if self.playlist_widget.count() > 0:
            reply = QMessageBox.question(
                self, 
                "Confirmation",
                "Are you sure you want to clear the entire playlist?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.clear_playlist_requested.emit()

    def _on_playlist_item_clicked(self, item: QListWidgetItem) -> None:
        """Called when playlist item is clicked."""
        wallpaper_id = item.data(Qt.UserRole)
        if wallpaper_id:
            logger.debug(f"Wallpaper selected from playlist: {wallpaper_id}")
            self.wallpaper_selected.emit(wallpaper_id)

    def add_wallpaper_to_playlist(self, wallpaper_id: str) -> bool:
        """
        Adds wallpaper to playlist.
        
        Args:
            wallpaper_id: Wallpaper ID to add
            
        Returns:
            bool: True if addition successful
        """
        if not wallpaper_id:
            return False
            
        # Check if already exists - safer check
        existing_ids = self.get_playlist_items()
        if wallpaper_id in existing_ids:
            logger.debug(f"Wallpaper already in playlist: {wallpaper_id}")
            # Inform user
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Information",
                f"This wallpaper is already in the playlist!\n\n📝 {self.get_wallpaper_name(wallpaper_id)}"
            )
            return False
        
        # Get wallpaper name
        wallpaper_name = self.get_wallpaper_name(wallpaper_id)
        
        # Determine wallpaper type
        if wallpaper_id.startswith('custom_') or wallpaper_id.startswith('gif_'):
            # Video/GIF wallpaper
            media_icon = "🎬"
            media_type = "Video/GIF"
        else:
            # Normal wallpaper engine wallpaper
            media_icon = "🖼️"
            media_type = "Wallpaper"
        
        # Add new item - show name, show ID on hover
        item = QListWidgetItem(f"{media_icon} {wallpaper_name}")
        item.setData(Qt.UserRole, wallpaper_id)
        item.setToolTip(f"🆔 ID: {wallpaper_id}\n📝 Name: {wallpaper_name}\n🎭 Type: {media_type}")
        self.playlist_widget.addItem(item)
        
        logger.debug(f"Wallpaper added to playlist: {wallpaper_id}")
        return True
    
    def get_wallpaper_name(self, wallpaper_id: str) -> str:
        """Gets wallpaper name from ID."""
        try:
            from utils.metadata_manager import metadata_manager
            
            # Load metadata if not yet loaded
            if not metadata_manager.wallpapers:
                logger.debug("Loading metadata...")
                metadata_manager.scan_wallpapers()
            
            metadata = metadata_manager.get_metadata(wallpaper_id)
            
            if metadata and metadata.title and metadata.title.strip():
                # İsmi kısalt (playlist için uygun boyut)
                title = metadata.title.strip()
                if len(title) > 30:
                    title = title[:27] + "..."
                return title
            else:
                logger.debug(f"Metadata not found or title empty: {wallpaper_id}")
                return f"Wallpaper {wallpaper_id}"
                
        except Exception as e:
            logger.error(f"Error getting wallpaper name {wallpaper_id}: {e}")
            return f"Wallpaper {wallpaper_id}"

    def remove_wallpaper_from_playlist(self, index: int) -> Optional[str]:
        """
        Removes wallpaper from playlist.
        
        Args:
            index: Index of item to remove
            
        Returns:
            str: Removed wallpaper ID or None
        """
        if 0 <= index < self.playlist_widget.count():
            item = self.playlist_widget.takeItem(index)
            wallpaper_id = item.data(Qt.UserRole)
            logger.debug(f"Wallpaper removed from playlist: {wallpaper_id}")
            return wallpaper_id
        return None

    def clear_playlist(self) -> None:
        """Clears playlist."""
        self.playlist_widget.clear()
        self.set_playing_state(False)
        logger.info("Playlist cleared")

    def get_playlist_items(self) -> List[str]:
        """
        Returns wallpaper IDs in playlist.
        
        Returns:
            List[str]: Wallpaper IDs
        """
        items = []
        for i in range(self.playlist_widget.count()):
            item = self.playlist_widget.item(i)
            wallpaper_id = item.data(Qt.UserRole)
            if wallpaper_id:
                items.append(wallpaper_id)
        return items

    def set_current_wallpaper(self, wallpaper_id: Optional[str]) -> None:
        """
        Sets current wallpaper (with video wallpaper support).
        
        Args:
            wallpaper_id: Wallpaper ID or None
        """
        self._current_wallpaper = wallpaper_id
        if wallpaper_id:
            wallpaper_name = self.get_wallpaper_name(wallpaper_id)
            
            # Determine wallpaper type
            if wallpaper_id.startswith('custom_') or wallpaper_id.startswith('gif_'):
                # Video/GIF wallpaper
                media_icon = "🎬"
            else:
                # Normal wallpaper engine wallpaper
                media_icon = "🖼️"
            
            self.current_label.setText(f"{media_icon} Now: {wallpaper_name}")
        else:
            self.current_label.setText("🎧 Now: None")

    def set_playing_state(self, is_playing: bool) -> None:
        """
        Sets playing state.
        
        Args:
            is_playing: Is playing
        """
        self._is_playing = is_playing
        if is_playing:
            self.play_btn.setText("⏸️")
        else:
            self.play_btn.setText("▶️")

    def get_selected_index(self) -> int:
        """
        Returns selected item index.
        
        Returns:
            int: Selected index or -1
        """
        return self.playlist_widget.currentRow()

    def get_playlist_count(self) -> int:
        """
        Returns number of items in playlist.
        
        Returns:
            int: Item count
        """
        return self.playlist_widget.count()

    def is_random_mode(self) -> bool:
        """
        Checks if random mode is active.
        
        Returns:
            bool: True if random mode is active
        """
        return self.random_radio.isChecked()

    def set_random_mode(self, is_random: bool) -> None:
        """
        Sets random mode state.
        
        Args:
            is_random: Should random mode be active
        """
        if is_random:
            self.random_radio.setChecked(True)
        else:
            self.sequential_radio.setChecked(True)
        logger.debug(f"Random mode set: {is_random}")

    def set_timer_interval(self, interval_text: str) -> None:
        """
        Sets timer interval.
        
        Args:
            interval_text: Interval text
        """
        index = self.timer_combo.findText(interval_text)
        if index >= 0:
            self.timer_combo.setCurrentIndex(index)

    def load_custom_timer_from_settings(self) -> None:
        """Loads saved custom timer setting."""
        try:
            if self._parent_window and hasattr(self._parent_window, 'playlist_manager'):
                interval, custom_text = self._parent_window.playlist_manager.get_custom_timer_info()
                
                if interval and custom_text:
                    # Remove previous custom value
                    for i in range(self.timer_combo.count()):
                        if self.timer_combo.itemText(i).startswith("Custom:"):
                            self.timer_combo.removeItem(i)
                            break
                    
                    # Add saved custom value
                    self.timer_combo.insertItem(self.timer_combo.count() - 1, custom_text)
                    self.timer_combo.setCurrentText(custom_text)
                    
                    logger.info(f"Saved custom timer loaded: {custom_text} ({interval} seconds)")
                    return True
                    
        except Exception as e:
            logger.error(f"Error loading custom timer: {e}")
            
        return False

    def update_theme(self, primary_color: str, secondary_color: str, theme_panel: str) -> None:
        """Updates theme colors."""
        def hex_to_rgba(hex_color: str) -> str:
            try:
                hex_color = hex_color.lstrip('#')
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                return f"{r}, {g}, {b}"
            except:
                return "0, 212, 255"
        
        # Tema renklerini CSS'e uygula
        theme_css = f"""
            QFrame#PlaylistWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {theme_panel}, stop:1 rgba({hex_to_rgba(primary_color)}, 0.05));
                border: 2px solid rgba({hex_to_rgba(primary_color)}, 0.4);
                border-radius: 20px;
                margin: 8px;
                padding: 15px;
            }}
            
            QLabel#PlaylistTitle {{
                font-size: 16px;
                font-weight: bold;
                color: {primary_color};
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba({hex_to_rgba(primary_color)}, 0.2),
                    stop:1 rgba({hex_to_rgba(secondary_color)}, 0.1));
                border: 2px solid rgba({hex_to_rgba(primary_color)}, 0.5);
                border-radius: 12px;
                padding: 12px 20px;
                margin: 8px 0px;
                letter-spacing: 1px;
            }}
            
            QLabel#CurrentPlaying {{
                color: {secondary_color};
                font-weight: bold;
                font-size: 13px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba({hex_to_rgba(secondary_color)}, 0.15),
                    stop:1 rgba({hex_to_rgba(primary_color)}, 0.05));
                border: 2px solid rgba({hex_to_rgba(secondary_color)}, 0.4);
                border-radius: 10px;
                padding: 10px 15px;
                margin: 8px 0px;
            }}
            
            QLabel#ControlsLabel, QLabel#PlaylistLabel {{
                color: {primary_color};
                font-weight: bold;
                font-size: 14px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {theme_panel}, stop:1 rgba({hex_to_rgba(primary_color)}, 0.03));
                border: 1px solid rgba({hex_to_rgba(primary_color)}, 0.3);
                border-radius: 6px;
                padding: 6px 10px;
                margin: 10px 0px 5px 0px;
            }}
            
            QGroupBox#TimerGroup {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {theme_panel}, stop:1 rgba({hex_to_rgba(primary_color)}, 0.03));
                border: 2px solid rgba({hex_to_rgba(primary_color)}, 0.3);
                border-radius: 10px;
                padding: 8px;
                margin: 2px;
                font-weight: bold;
                font-size: 14px;
                color: {primary_color};
                padding-top: 15px;
            }}
            
            QGroupBox#TimerGroup::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: {primary_color};
            }}
            
            QComboBox {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {theme_panel}, stop:1 rgba({hex_to_rgba(primary_color)}, 0.03));
                border: 1px solid rgba({hex_to_rgba(primary_color)}, 0.3);
                border-radius: 6px;
                padding: 6px 10px;
                margin: 2px;
                color: white;
                font-weight: 500;
            }}
            
            QRadioButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {theme_panel}, stop:1 rgba({hex_to_rgba(primary_color)}, 0.03));
                border: 1px solid rgba({hex_to_rgba(primary_color)}, 0.3);
                border-radius: 6px;
                padding: 6px 10px;
                margin: 2px;
                color: white;
                font-weight: 500;
            }}
            
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 8px;
                border: 2px solid rgba({hex_to_rgba(primary_color)}, 0.5);
                background: #2a2a2a;
            }}
            
            QRadioButton::indicator:hover {{
                border: 2px solid {primary_color};
            }}
            
            QRadioButton::indicator:checked {{
                background: qradial-gradient(cx:0.5, cy:0.5, radius:0.5,
                    stop:0 {primary_color}, stop:0.6 {primary_color}, stop:0.7 transparent);
                border: 2px solid {primary_color};
            }}
            
            QPushButton#ControlButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba({hex_to_rgba(primary_color)}, 0.2),
                    stop:1 rgba({hex_to_rgba(primary_color)}, 0.1));
                border: 2px solid rgba({hex_to_rgba(primary_color)}, 0.4);
                border-radius: 12px;
                padding: 8px;
                margin: 4px;
                color: white;
                font-size: 18px;
                font-weight: bold;
            }}
            
            QPushButton#ControlButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba({hex_to_rgba(primary_color)}, 0.4),
                    stop:1 rgba({hex_to_rgba(primary_color)}, 0.2));
                border: 2px solid {primary_color};
            }}
            
            QPushButton#ManagementButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba({hex_to_rgba(primary_color)}, 0.15),
                    stop:1 rgba({hex_to_rgba(secondary_color)}, 0.1));
                border: 2px solid rgba({hex_to_rgba(primary_color)}, 0.4);
                border-radius: 10px;
                padding: 10px 15px;
                margin: 4px;
                color: {primary_color};
                font-weight: bold;
                font-size: 12px;
            }}
            
            QPushButton#ManagementButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba({hex_to_rgba(primary_color)}, 0.3),
                    stop:1 rgba({hex_to_rgba(secondary_color)}, 0.2));
                border: 2px solid {primary_color};
                color: white;
            }}
            
            QListWidget#PlaylistList {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e1e1e, stop:1 #0e0e0e);
                border: 2px solid rgba({hex_to_rgba(primary_color)}, 0.5);
                border-radius: 10px;
                color: white;
                selection-background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {primary_color}, stop:1 {secondary_color});
                padding: 5px;
            }}
            
            QListWidget#PlaylistList::item {{
                padding: 8px;
                border-bottom: 1px solid #333;
                border-radius: 5px;
                margin: 2px;
            }}
            
            QListWidget#PlaylistList::item:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba({hex_to_rgba(primary_color)}, 0.2), stop:1 rgba({hex_to_rgba(secondary_color)}, 0.2));
            }}
            
            QListWidget#PlaylistList::item:selected {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {primary_color}, stop:1 {secondary_color});
                color: white;
                font-weight: bold;
            }}
        """
        
        self.setStyleSheet(theme_css)