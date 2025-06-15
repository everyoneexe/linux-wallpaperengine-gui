"""
Wallpaper Engine - Template Architecture ile organize edilmiş ana uygulama
"""
import sys
import logging
import os
import fcntl
import atexit
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import QSettings

from ui import MainWindow
from utils import APP_NAME, APP_VERSION, ORGANIZATION_NAME

# =============================================================================
# TEMPLATE ARCHITECTURE - Human Cognition-Optimized
# =============================================================================

class State:
    """Paylaşılan durum yönetimi"""
    argv = []
    logger = None
    app_instance = None
    main_window = None
    lock_file = None
    is_locked = False

class Utils:
    """Yardımcı fonksiyonlar"""
    
    @staticmethod
    def setup_logging():
        """Logging sistemini kurar."""
        log_dir = Path.home() / ".config" / "wallpaper_engine"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "wallpaper_engine.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        logging.getLogger("PySide6").setLevel(logging.WARNING)
        logger = logging.getLogger(__name__)
        logger.info(f"{APP_NAME} v{APP_VERSION} başlatılıyor...")
        return logger
    
    @staticmethod
    def acquire_lock():
        """Single instance lock alır."""
        lock_path = Path.home() / ".config" / "wallpaper_engine" / "wallpaper_engine.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            State.lock_file = open(lock_path, 'w')
            fcntl.flock(State.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            State.lock_file.write(str(os.getpid()))
            State.lock_file.flush()
            State.is_locked = True
            atexit.register(Utils.release_lock)
            return True
        except (IOError, OSError):
            if State.lock_file:
                State.lock_file.close()
                State.lock_file = None
            return False
    
    @staticmethod
    def release_lock():
        """Lock'u serbest bırakır."""
        if State.is_locked and State.lock_file:
            try:
                fcntl.flock(State.lock_file.fileno(), fcntl.LOCK_UN)
                State.lock_file.close()
                lock_path = Path.home() / ".config" / "wallpaper_engine" / "wallpaper_engine.lock"
                if lock_path.exists():
                    lock_path.unlink()
                State.is_locked = False
            except (IOError, OSError):
                pass
    
    @staticmethod
    def get_running_pid():
        """Çalışan instance PID'sini döner."""
        try:
            lock_path = Path.home() / ".config" / "wallpaper_engine" / "wallpaper_engine.lock"
            if lock_path.exists():
                with open(lock_path, 'r') as f:
                    return int(f.read().strip())
        except (IOError, ValueError):
            pass
        return -1
    
    @staticmethod
    def setup_application():
        """QApplication'ı kurar."""
        State.app_instance = QApplication(State.argv)
        
        # Uygulama özellikleri
        State.app_instance.setApplicationName(APP_NAME)
        State.app_instance.setApplicationVersion(APP_VERSION)
        State.app_instance.setOrganizationName(ORGANIZATION_NAME)
        QSettings.setDefaultFormat(QSettings.IniFormat)
        
        # Tema
        Utils.setup_theme()
        
        if State.logger:
            State.logger.debug("Uygulama özellikleri ayarlandı")
    
    @staticmethod
    def setup_theme():
        """Koyu tema ayarlar."""
        if not State.app_instance:
            return
            
        try:
            State.app_instance.setStyle('Fusion')
            palette = State.app_instance.palette()
            
            # Ana renkler
            palette.setColor(QPalette.Window, QColor(23, 23, 35))
            palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
            palette.setColor(QPalette.Base, QColor(42, 42, 42))
            palette.setColor(QPalette.AlternateBase, QColor(66, 66, 66))
            palette.setColor(QPalette.ToolTipBase, QColor(0, 0, 0))
            palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
            palette.setColor(QPalette.Text, QColor(255, 255, 255))
            
            # Buton renkleri
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
            palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
            
            # Seçim renkleri
            palette.setColor(QPalette.Link, QColor(42, 130, 218))
            palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
            
            # Devre dışı renkler
            palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(127, 127, 127))
            palette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
            palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))
            
            State.app_instance.setPalette(palette)
            
            if State.logger:
                State.logger.debug("Global tema ayarlandı")
                
        except Exception as e:
            if State.logger:
                State.logger.error(f"Tema ayarlanırken hata: {e}")

class Flow:
    """Ana akış algoritmaları"""
    
    @staticmethod
    def initialize_system():
        """Sistem başlatma."""
        State.argv = sys.argv
        State.logger = Utils.setup_logging()
    
    @staticmethod
    def check_single_instance():
        """Single instance kontrolü."""
        if not Utils.acquire_lock():
            running_pid = Utils.get_running_pid()
            
            # Mesaj göster
            temp_app = QApplication(State.argv)
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Wallpaper Engine")
            msg.setText("🚫 Wallpaper Engine zaten çalışıyor!")
            
            if running_pid > 0:
                msg.setInformativeText(f"Çalışan instance PID: {running_pid}\n\n"
                                     "Aynı anda birden fazla instance açmak RAM'i gereksiz yere tüketir.\n"
                                     "Mevcut pencereyi kullanın veya önce onu kapatın.")
            else:
                msg.setInformativeText("Aynı anda birden fazla instance açmak RAM'i gereksiz yere tüketir.\n"
                                     "Mevcut pencereyi kullanın veya önce onu kapatın.")
            
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            
            print("❌ Wallpaper Engine zaten çalışıyor! Yeni instance başlatılmadı.")
            return False
        
        return True
    
    @staticmethod
    def create_application():
        """Uygulama oluşturma."""
        Utils.setup_application()
        State.main_window = MainWindow()
        
        if State.logger:
            State.logger.info("Uygulama başarıyla başlatıldı")
    
    @staticmethod
    def run_application():
        """Uygulamayı çalıştır."""
        try:
            State.main_window.show()
            
            if State.logger:
                State.logger.info("Ana pencere gösterildi")
            
            return State.app_instance.exec()
            
        except Exception as e:
            if State.logger:
                State.logger.error(f"Ana pencere gösterilirken hata: {e}")
            return 1

class App:
    """Ana akış kontrolü"""
    
    @staticmethod
    def main():
        """Template-based ana fonksiyon."""
        try:
            # 1. Sistem başlatma
            Flow.initialize_system()
            
            # 2. Single instance kontrolü
            if not Flow.check_single_instance():
                return 1
            
            # 3. Uygulama oluşturma
            Flow.create_application()
            
            # 4. Uygulamayı çalıştır
            exit_code = Flow.run_application()
            
            # 5. Temizlik
            Utils.release_lock()
            return exit_code
            
        except KeyboardInterrupt:
            print("\nUygulama kullanıcı tarafından sonlandırıldı.")
            Utils.release_lock()
            return 0
        except Exception as e:
            print(f"Kritik hata: {e}")
            if State.logger:
                State.logger.error(f"Kritik hata: {e}", exc_info=True)
            Utils.release_lock()
            return 1

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Ana fonksiyon."""
    exit_code = App.main()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()