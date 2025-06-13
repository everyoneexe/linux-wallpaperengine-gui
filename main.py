"""
Wallpaper Engine - Main application organized with Template Architecture

Main Application Flow:
1. App.main() - Entry point
2. Flow.* - Core algorithms
3. Utils.* - Helper functions
4. State.* - Shared data
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
    """Shared state management"""
    argv = []
    logger = None
    app_instance = None
    main_window = None
    lock_file = None
    is_locked = False

class Utils:
    """Utility functions"""
    
    @staticmethod
    def setup_logging():
        """Sets up logging system."""
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
        logger.info(f"{APP_NAME} v{APP_VERSION} starting...")
        return logger
    
    @staticmethod
    def acquire_lock():
        """Acquires single instance lock."""
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
        """Releases the lock."""
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
        """Returns the PID of running instance."""
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
        """Sets up QApplication."""
        State.app_instance = QApplication(State.argv)
        
        # Application properties
        State.app_instance.setApplicationName(APP_NAME)
        State.app_instance.setApplicationVersion(APP_VERSION)
        State.app_instance.setOrganizationName(ORGANIZATION_NAME)
        QSettings.setDefaultFormat(QSettings.IniFormat)
        
        # Theme
        Utils.setup_theme()
        
        if State.logger:
            State.logger.debug("Application properties configured")
    
    @staticmethod
    def setup_theme():
        """Sets up dark theme."""
        if not State.app_instance:
            return
            
        try:
            State.app_instance.setStyle('Fusion')
            palette = State.app_instance.palette()
            
            # Main colors
            palette.setColor(QPalette.Window, QColor(23, 23, 35))
            palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
            palette.setColor(QPalette.Base, QColor(42, 42, 42))
            palette.setColor(QPalette.AlternateBase, QColor(66, 66, 66))
            palette.setColor(QPalette.ToolTipBase, QColor(0, 0, 0))
            palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
            palette.setColor(QPalette.Text, QColor(255, 255, 255))
            
            # Button colors
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
            palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
            
            # Selection colors
            palette.setColor(QPalette.Link, QColor(42, 130, 218))
            palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
            
            # Disabled colors
            palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(127, 127, 127))
            palette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
            palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))
            
            State.app_instance.setPalette(palette)
            
            if State.logger:
                State.logger.debug("Global theme configured")
                
        except Exception as e:
            if State.logger:
                State.logger.error(f"Error setting up theme: {e}")

class Flow:
    """Main flow algorithms"""
    
    @staticmethod
    def initialize_system():
        """System initialization."""
        State.argv = sys.argv
        State.logger = Utils.setup_logging()
    
    @staticmethod
    def check_single_instance():
        """Single instance check."""
        if not Utils.acquire_lock():
            running_pid = Utils.get_running_pid()
            
            # Show message
            temp_app = QApplication(State.argv)
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Wallpaper Engine")
            msg.setText("🚫 Wallpaper Engine is already running!")
            
            if running_pid > 0:
                msg.setInformativeText(f"Running instance PID: {running_pid}\n\n"
                                     "Opening multiple instances simultaneously wastes RAM unnecessarily.\n"
                                     "Use the existing window or close it first.")
            else:
                msg.setInformativeText("Opening multiple instances simultaneously wastes RAM unnecessarily.\n"
                                     "Use the existing window or close it first.")
            
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            
            print("❌ Wallpaper Engine is already running! New instance not started.")
            return False
        
        return True
    
    @staticmethod
    def create_application():
        """Application creation."""
        Utils.setup_application()
        State.main_window = MainWindow()
        
        if State.logger:
            State.logger.info("Application started successfully")
    
    @staticmethod
    def run_application():
        """Run the application."""
        try:
            State.main_window.show()
            
            if State.logger:
                State.logger.info("Main window displayed")
            
            return State.app_instance.exec()
            
        except Exception as e:
            if State.logger:
                State.logger.error(f"Error displaying main window: {e}")
            return 1

class App:
    """Main flow control"""
    
    @staticmethod
    def main():
        """Template-based main function."""
        try:
            # 1. System initialization
            Flow.initialize_system()
            
            # 2. Single instance check
            if not Flow.check_single_instance():
                return 1
            
            # 3. Application creation
            Flow.create_application()
            
            # 4. Run application
            exit_code = Flow.run_application()
            
            # 5. Cleanup
            Utils.release_lock()
            return exit_code
            
        except KeyboardInterrupt:
            print("\nApplication terminated by user.")
            Utils.release_lock()
            return 0
        except Exception as e:
            print(f"Critical error: {e}")
            if State.logger:
                State.logger.error(f"Critical error: {e}", exc_info=True)
            Utils.release_lock()
            return 1

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main function."""
    exit_code = App.main()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()