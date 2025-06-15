"""
Ayarlar penceresi widget'ı
"""
import logging
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QKeySequenceEdit
)
from PySide6.QtCore import Qt, Signal, QSettings
from PySide6.QtGui import QKeySequence

from utils import DEFAULT_HOTKEYS

logger = logging.getLogger(__name__)


class SettingsWidget(QWidget):
    """
    Ayarlar penceresi widget'ı.
    
    Signals:
        settings_saved: Ayarlar kaydedildiğinde emit edilir
        settings_reset: Ayarlar sıfırlandığında emit edilir
    """
    
    settings_saved = Signal(dict)  # settings dict
    settings_reset = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.parent_window = parent
        self._settings = QSettings()
        
        self.setup_ui()
        self.setup_connections()
        self.setup_styles()

    def setup_ui(self) -> None:
        """UI'ı kurar."""
        self.setWindowTitle("⚙️ Ayarlar")
        self.setFixedSize(500, 400)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self.setObjectName("SettingsWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        self.title_label = QLabel("⚙️ AYARLAR")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setObjectName("SettingsTitle")
        layout.addWidget(self.title_label)

        # Hotkeys group
        self.setup_hotkeys_group(layout)

        # Buttons
        self.setup_buttons(layout)
        
        layout.addStretch()

    def setup_hotkeys_group(self, parent_layout: QVBoxLayout) -> None:
        """Kısayol tuşları grubunu kurar."""
        hotkeys_group = QGroupBox("🎮 Kısayol Tuşları")
        hotkeys_group.setObjectName("HotkeysGroup")
        hotkeys_layout = QVBoxLayout(hotkeys_group)
        hotkeys_layout.setSpacing(10)

        # Play/Pause hotkey
        play_layout = QHBoxLayout()
        play_label = QLabel("Oynat/Duraklat:")
        play_label.setMinimumWidth(120)
        play_label.setObjectName("HotkeyLabel")
        
        self.play_hotkey = QKeySequenceEdit()
        self.play_hotkey.setKeySequence(QKeySequence(DEFAULT_HOTKEYS["play"]))
        self.play_hotkey.setObjectName("HotkeyEdit")
        
        play_layout.addWidget(play_label)
        play_layout.addWidget(self.play_hotkey)
        hotkeys_layout.addLayout(play_layout)

        # Next hotkey
        next_layout = QHBoxLayout()
        next_label = QLabel("Sonraki:")
        next_label.setMinimumWidth(120)
        next_label.setObjectName("HotkeyLabel")
        
        self.next_hotkey = QKeySequenceEdit()
        self.next_hotkey.setKeySequence(QKeySequence(DEFAULT_HOTKEYS["next"]))
        self.next_hotkey.setObjectName("HotkeyEdit")
        
        next_layout.addWidget(next_label)
        next_layout.addWidget(self.next_hotkey)
        hotkeys_layout.addLayout(next_layout)

        # Previous hotkey
        prev_layout = QHBoxLayout()
        prev_label = QLabel("Önceki:")
        prev_label.setMinimumWidth(120)
        prev_label.setObjectName("HotkeyLabel")
        
        self.prev_hotkey = QKeySequenceEdit()
        self.prev_hotkey.setKeySequence(QKeySequence(DEFAULT_HOTKEYS["prev"]))
        self.prev_hotkey.setObjectName("HotkeyEdit")
        
        prev_layout.addWidget(prev_label)
        prev_layout.addWidget(self.prev_hotkey)
        hotkeys_layout.addLayout(prev_layout)

        parent_layout.addWidget(hotkeys_group)

    def setup_buttons(self, parent_layout: QVBoxLayout) -> None:
        """Butonları kurar."""
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.reset_btn = QPushButton("🔄 Sıfırla")
        self.cancel_btn = QPushButton("❌ İptal")
        self.save_btn = QPushButton("💾 Kaydet")
        
        # Button styling
        for btn in [self.reset_btn, self.cancel_btn, self.save_btn]:
            btn.setObjectName("SettingsButton")
        
        buttons_layout.addWidget(self.reset_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.cancel_btn)
        buttons_layout.addWidget(self.save_btn)

        parent_layout.addLayout(buttons_layout)

    def setup_connections(self) -> None:
        """Sinyal bağlantılarını kurar."""
        self.save_btn.clicked.connect(self.save_settings)
        self.cancel_btn.clicked.connect(self.close)
        self.reset_btn.clicked.connect(self.reset_settings)

    def setup_styles(self) -> None:
        """Widget stillerini ayarlar."""
        self.setStyleSheet("""
            QWidget#SettingsWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f0f23, stop:1 #1a1a2e);
                color: white;
                font-family: 'Segoe UI', 'Arial', sans-serif;
            }
            
            QLabel#SettingsTitle {
                font-size: 24px;
                font-weight: bold;
                color: #00d4ff;
                background: rgba(0, 212, 255, 0.1);
                border: 2px solid rgba(0, 212, 255, 0.3);
                border-radius: 10px;
                padding: 15px;
                margin-bottom: 10px;
            }
            
            QGroupBox#HotkeysGroup {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #555;
                border-radius: 10px;
                margin: 15px 0;
                padding-top: 15px;
                color: #00d4ff;
            }
            
            QGroupBox#HotkeysGroup::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #00d4ff;
            }
            
            QLabel#HotkeyLabel {
                color: white;
                font-weight: 500;
            }
            
            QKeySequenceEdit#HotkeyEdit {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #404040, stop:1 #2a2a2a);
                border: 2px solid #555;
                border-radius: 8px;
                padding: 8px;
                color: white;
                font-weight: 500;
            }
            
            QKeySequenceEdit#HotkeyEdit:focus {
                border: 2px solid #00d4ff;
            }
            
            QPushButton#SettingsButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #00d4ff, stop:1 #0099cc);
                border: none;
                border-radius: 10px;
                color: white;
                font-weight: bold;
                padding: 12px 20px;
                font-size: 13px;
            }
            
            QPushButton#SettingsButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #00ffff, stop:1 #00aadd);
                transform: scale(1.05);
            }
            
            QPushButton#SettingsButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0099cc, stop:1 #006699);
            }
        """)

    def save_settings(self) -> None:
        """Ayarları kaydeder."""
        try:
            # Hotkey ayarlarını kaydet
            settings_dict = {
                "hotkey_play": self.play_hotkey.keySequence().toString(),
                "hotkey_next": self.next_hotkey.keySequence().toString(),
                "hotkey_prev": self.prev_hotkey.keySequence().toString()
            }
            
            # QSettings'e kaydet
            for key, value in settings_dict.items():
                self._settings.setValue(key, value)
            
            # Signal emit et
            self.settings_saved.emit(settings_dict)
            
            # Parent window'a bildir
            if self.parent_window and hasattr(self.parent_window, 'show_toast'):
                self.parent_window.show_toast("✅ Ayarlar kaydedildi!", 2000)
            
            logger.info("Ayarlar kaydedildi")
            self.close()
            
        except Exception as e:
            logger.error(f"Ayarlar kaydedilirken hata: {e}")
            if self.parent_window and hasattr(self.parent_window, 'show_toast'):
                self.parent_window.show_toast("❌ Ayarlar kaydedilemedi!", 3000)

    def reset_settings(self) -> None:
        """Ayarları varsayılan değerlere sıfırlar."""
        try:
            self.play_hotkey.setKeySequence(QKeySequence(DEFAULT_HOTKEYS["play"]))
            self.next_hotkey.setKeySequence(QKeySequence(DEFAULT_HOTKEYS["next"]))
            self.prev_hotkey.setKeySequence(QKeySequence(DEFAULT_HOTKEYS["prev"]))
            
            self.settings_reset.emit()
            logger.info("Ayarlar sıfırlandı")
            
            if self.parent_window and hasattr(self.parent_window, 'show_toast'):
                self.parent_window.show_toast("🔄 Ayarlar sıfırlandı!", 2000)
                
        except Exception as e:
            logger.error(f"Ayarlar sıfırlanırken hata: {e}")

    def load_settings(self) -> None:
        """Kaydedilmiş ayarları yükler."""
        try:
            play_hotkey = self._settings.value("hotkey_play", DEFAULT_HOTKEYS["play"])
            next_hotkey = self._settings.value("hotkey_next", DEFAULT_HOTKEYS["next"])
            prev_hotkey = self._settings.value("hotkey_prev", DEFAULT_HOTKEYS["prev"])
            
            self.play_hotkey.setKeySequence(QKeySequence(play_hotkey))
            self.next_hotkey.setKeySequence(QKeySequence(next_hotkey))
            self.prev_hotkey.setKeySequence(QKeySequence(prev_hotkey))
            
            logger.debug("Ayarlar yüklendi")
            
        except Exception as e:
            logger.error(f"Ayarlar yüklenirken hata: {e}")
            self.reset_settings()

    def get_current_settings(self) -> Dict[str, str]:
        """
        Mevcut ayarları döner.
        
        Returns:
            dict: Ayarlar sözlüğü
        """
        return {
            "hotkey_play": self.play_hotkey.keySequence().toString(),
            "hotkey_next": self.next_hotkey.keySequence().toString(),
            "hotkey_prev": self.prev_hotkey.keySequence().toString()
        }

    def set_hotkeys(self, hotkeys: Dict[str, str]) -> None:
        """
        Kısayol tuşlarını ayarlar.
        
        Args:
            hotkeys: Kısayol tuşları sözlüğü
        """
        try:
            if "play" in hotkeys:
                self.play_hotkey.setKeySequence(QKeySequence(hotkeys["play"]))
            if "next" in hotkeys:
                self.next_hotkey.setKeySequence(QKeySequence(hotkeys["next"]))
            if "prev" in hotkeys:
                self.prev_hotkey.setKeySequence(QKeySequence(hotkeys["prev"]))
                
        except Exception as e:
            logger.error(f"Kısayol tuşları ayarlanırken hata: {e}")

    def validate_hotkeys(self) -> bool:
        """
        Kısayol tuşlarının geçerli olup olmadığını kontrol eder.
        
        Returns:
            bool: Geçerli ise True
        """
        try:
            sequences = [
                self.play_hotkey.keySequence(),
                self.next_hotkey.keySequence(),
                self.prev_hotkey.keySequence()
            ]
            
            # Boş sequence kontrolü
            for seq in sequences:
                if seq.isEmpty():
                    return False
            
            # Duplicate kontrolü
            sequence_strings = [seq.toString() for seq in sequences]
            if len(set(sequence_strings)) != len(sequence_strings):
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Kısayol tuşları doğrulanırken hata: {e}")
            return False

    def showEvent(self, event) -> None:
        """Pencere gösterildiğinde çağrılır."""
        self.load_settings()
        super().showEvent(event)

    def closeEvent(self, event) -> None:
        """Pencere kapatılırken çağrılır."""
        # Değişiklik var mı kontrol et
        current_settings = self.get_current_settings()
        saved_settings = {
            "hotkey_play": self._settings.value("hotkey_play", DEFAULT_HOTKEYS["play"]),
            "hotkey_next": self._settings.value("hotkey_next", DEFAULT_HOTKEYS["next"]),
            "hotkey_prev": self._settings.value("hotkey_prev", DEFAULT_HOTKEYS["prev"])
        }
        
        if current_settings != saved_settings:
            logger.debug("Kaydedilmemiş değişiklikler var")
        
        super().closeEvent(event)