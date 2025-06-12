"""
Steam Workshop Browser Widget
"""
import logging
import re
from typing import Optional, List
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QProgressBar, QTextEdit,
    QSplitter, QFrame, QMessageBox
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PySide6.QtCore import Qt, Signal, QUrl, QTimer, QThread
from PySide6.QtGui import QIcon

logger = logging.getLogger(__name__)

class WorkshopDownloader(QThread):
    """Workshop item download thread"""
    
    download_started = Signal(str)  # workshop_id
    download_progress = Signal(str, int)  # workshop_id, progress
    download_finished = Signal(str, bool)  # workshop_id, success
    
    def __init__(self):
        super().__init__()
        self.download_queue: List[str] = []
        self.is_downloading = False
        
    def add_to_queue(self, workshop_id: str):
        """Add to download queue"""
        if workshop_id not in self.download_queue:
            self.download_queue.append(workshop_id)
            logger.info(f"Workshop item added to queue: {workshop_id}")
            
    def run(self):
        """Start download process"""
        while self.download_queue:
            workshop_id = self.download_queue.pop(0)
            self.is_downloading = True
            
            try:
                self.download_started.emit(workshop_id)
                success = self._download_workshop_item(workshop_id)
                self.download_finished.emit(workshop_id, success)
                
            except Exception as e:
                logger.error(f"Download error {workshop_id}: {e}")
                self.download_finished.emit(workshop_id, False)
                
            finally:
                self.is_downloading = False
                
    def _download_workshop_item(self, workshop_id: str) -> bool:
        """Download workshop item"""
        try:
            import subprocess
            
            # Download with SteamCMD (if available)
            steamcmd_paths = [
                "/usr/bin/steamcmd",
                "/usr/local/bin/steamcmd",
                Path.home() / "steamcmd" / "steamcmd.sh"
            ]
            
            steamcmd_path = None
            for path in steamcmd_paths:
                if Path(path).exists():
                    steamcmd_path = str(path)
                    break
                    
            if not steamcmd_path:
                logger.warning("SteamCMD not found, manual download required")
                return False
                
            # SteamCMD command
            cmd = [
                steamcmd_path,
                "+login", "anonymous",
                "+workshop_download_item", "431960", workshop_id,
                "+quit"
            ]
            
            logger.info(f"Downloading with SteamCMD: {workshop_id}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info(f"Workshop item downloaded successfully: {workshop_id}")
                return True
            else:
                logger.error(f"SteamCMD error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Download timeout: {workshop_id}")
            return False
        except Exception as e:
            logger.error(f"Download error: {e}")
            return False


class SteamWebPage(QWebEnginePage):
    """Customized Steam web page"""
    
    workshop_item_detected = Signal(str)  # workshop_id
    
    def __init__(self, profile=None, parent=None):
        if profile:
            super().__init__(profile, parent)
        else:
            super().__init__(parent)
        self.workshop_pattern = re.compile(r'steamcommunity\.com/sharedfiles/filedetails/\?id=(\d+)')
        
    def acceptNavigationRequest(self, url: QUrl, nav_type, is_main_frame: bool) -> bool:
        """Capture navigation requests"""
        url_string = url.toString()
        
        # Capture workshop item link
        match = self.workshop_pattern.search(url_string)
        if match:
            workshop_id = match.group(1)
            logger.info(f"Workshop item detected: {workshop_id}")
            self.workshop_item_detected.emit(workshop_id)
            
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


class SteamBrowserWidget(QFrame):
    """
    Steam Workshop browser widget
    
    Signals:
        wallpaper_downloaded: Emitted when wallpaper is downloaded
    """
    
    wallpaper_downloaded = Signal(str)  # workshop_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.downloader = WorkshopDownloader()
        self.current_downloads: List[str] = []
        
        self.setup_ui()
        self.setup_connections()
        self.setup_styles()
        
        # Start download thread
        self.downloader.start()
        
    def setup_ui(self):
        """Setup UI"""
        self.setFrameStyle(QFrame.StyledPanel)
        self.setObjectName("SteamBrowserWidget")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Header
        header = self.create_header()
        layout.addWidget(header)
        
        # External browser sync panel
        sync_panel = self.create_browser_sync_panel()
        layout.addWidget(sync_panel)
        
        # Splitter - Browser and Download Panel
        splitter = QSplitter(Qt.Vertical)
        
        # Web browser
        self.browser = self.create_browser()
        splitter.addWidget(self.browser)
        
        # Download panel
        download_panel = self.create_download_panel()
        splitter.addWidget(download_panel)
        
        splitter.setSizes([400, 150])
        layout.addWidget(splitter)
        
    def create_header(self) -> QWidget:
        """Create header"""
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("🌐 Steam Workshop Browser")
        title.setObjectName("BrowserTitle")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # URL input
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Workshop URL or search...")
        self.url_input.setMinimumWidth(300)
        self.url_input.clear()  # Keep URL input clean
        layout.addWidget(self.url_input)
        
        # Go button
        self.go_btn = QPushButton("🔍 Go")
        self.go_btn.setObjectName("GoButton")
        layout.addWidget(self.go_btn)
        
        # Home button
        self.home_btn = QPushButton("🏠 Home")
        self.home_btn.setObjectName("HomeButton")
        layout.addWidget(self.home_btn)
        
        return header
        
    def create_browser(self) -> QWebEngineView:
        """Create web browser - Advanced login persistence"""
        browser = QWebEngineView()
        
        # DETAILED PERSIST PATH SETUP
        from pathlib import Path
        persist_path = Path.home() / ".config" / "wallpaper_engine" / "steam_cookies"
        persist_path.mkdir(parents=True, exist_ok=True)
        
        # CUSTOM PROFILE - for full control
        profile = QWebEngineProfile("SteamPersist", browser)
        
        # EXPLICIT STORAGE PATHS
        profile.setPersistentStoragePath(str(persist_path))
        profile.setCachePath(str(persist_path / "cache"))
        profile.setDownloadPath(str(persist_path / "downloads"))
        
        # COOKIE POLICY - force persistent
        profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
        profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
        profile.setHttpCacheMaximumSize(100 * 1024 * 1024)  # 100MB cache
        
        # STEAM-FRIENDLY USER AGENT
        steam_ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 SteamClient/1701890080"
        profile.setHttpUserAgent(steam_ua)
        
        # HTTP HEADERS
        profile.setHttpAcceptLanguage("en-US,en;q=0.9")
        
        # WEB SETTINGS - full browser behavior
        settings = profile.settings()
        settings.setAttribute(settings.WebAttribute.AutoLoadImages, True)
        settings.setAttribute(settings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(settings.WebAttribute.JavascriptCanOpenWindows, True)
        settings.setAttribute(settings.WebAttribute.JavascriptCanAccessClipboard, True)
        settings.setAttribute(settings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(settings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(settings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(settings.WebAttribute.AllowRunningInsecureContent, True)
        settings.setAttribute(settings.WebAttribute.PluginsEnabled, True)
        
        # CUSTOM PAGE
        page = SteamWebPage(profile)
        browser.setPage(page)
        
        # DELAY INITIAL REQUEST
        QTimer.singleShot(3000, self._delayed_load_workshop)  # Wait 3 seconds (longer)
        
        logger.info(f"Steam browser advanced persist profile: {persist_path}")
        return browser
        
    def create_download_panel(self) -> QWidget:
        """Create download panel"""
        panel = QFrame()
        panel.setObjectName("DownloadPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Panel title
        title = QLabel("📥 Download Status")
        title.setObjectName("DownloadTitle")
        layout.addWidget(title)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Download log
        self.download_log = QTextEdit()
        self.download_log.setMaximumHeight(80)
        self.download_log.setReadOnly(True)
        self.download_log.setPlaceholderText("Download logs will appear here...")
        layout.addWidget(self.download_log)
        
        return panel
        
    def setup_connections(self):
        """Setup signal connections"""
        # Header buttons
        self.go_btn.clicked.connect(self._on_go_clicked)
        self.home_btn.clicked.connect(self._on_home_clicked)
        self.url_input.returnPressed.connect(self._on_go_clicked)
        
        # Browser page signals
        if hasattr(self.browser.page(), 'workshop_item_detected'):
            self.browser.page().workshop_item_detected.connect(self._on_workshop_item_detected)
            
        # Downloader signals
        self.downloader.download_started.connect(self._on_download_started)
        self.downloader.download_progress.connect(self._on_download_progress)
        self.downloader.download_finished.connect(self._on_download_finished)
        
    def _delayed_load_workshop(self):
        """Delayed Steam Workshop loading after browser is ready"""
        workshop_url = "https://steamcommunity.com/workshop/browse/?appid=431960&browsesort=trend&section=readytouseitems"
        self.browser.load(QUrl(workshop_url))
        logger.info("Steam Workshop delayed loading started")
        
    def create_browser_sync_panel(self) -> QWidget:
        """Create external browser sync panel"""
        panel = QFrame()
        panel.setObjectName("SyncPanel")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        # Info icon
        info_label = QLabel("🔗")
        info_label.setStyleSheet("font-size: 16px; color: #00d4ff;")
        layout.addWidget(info_label)
        
        # Info text
        text_label = QLabel("If login is not persistent:")
        text_label.setStyleSheet("color: #ccc; font-size: 12px;")
        layout.addWidget(text_label)
        
        # External login button
        external_btn = QPushButton("🌐 Login in System Browser")
        external_btn.setObjectName("ExternalLoginBtn")
        external_btn.setStyleSheet("""
            QPushButton#ExternalLoginBtn {
                background: rgba(0, 212, 255, 0.15);
                color: #00d4ff;
                border: 1px solid rgba(0, 212, 255, 0.3);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton#ExternalLoginBtn:hover {
                background: rgba(0, 212, 255, 0.25);
                border-color: #00d4ff;
            }
        """)
        external_btn.clicked.connect(self._open_external_login)
        layout.addWidget(external_btn)
        
        # Sync button
        sync_btn = QPushButton("🔄 Synchronize Cookies")
        sync_btn.setObjectName("SyncBtn")
        sync_btn.setStyleSheet("""
            QPushButton#SyncBtn {
                background: rgba(0, 255, 136, 0.15);
                color: #00ff88;
                border: 1px solid rgba(0, 255, 136, 0.3);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton#SyncBtn:hover {
                background: rgba(0, 255, 136, 0.25);
                border-color: #00ff88;
            }
        """)
        sync_btn.clicked.connect(self._sync_cookies_from_system)
        layout.addWidget(sync_btn)
        
        layout.addStretch()
        return panel
        
    def _open_external_login(self):
        """Open Steam login page in system browser"""
        import subprocess
        login_url = "https://steamcommunity.com/login/home/?goto=%2Fworkshop%2Fbrowse%2F%3Fappid%3D431960%26browsesort%3Dtrend%26section%3Dreadytouseitems"
        try:
            subprocess.run(["xdg-open", login_url], check=True)
            logger.info("Steam login opened in system browser")
            self._log("🌐 Login to Steam in system browser, then press Cookie Sync")
        except subprocess.CalledProcessError:
            logger.error("Could not open browser")
            self._log("❌ Could not open browser")
            
    def _sync_cookies_from_system(self):
        """Synchronize cookies from system browser - async"""
        self._log("🔄 Starting cookie synchronization...")
        
        # Use timer for async to avoid blocking main thread
        QTimer.singleShot(100, self._perform_cookie_sync)
        
    def _perform_cookie_sync(self):
        """Actual cookie sync operation (async)"""
        try:
            # Read Chrome cookies
            chrome_success = self._import_chrome_cookies()
            firefox_success = self._import_firefox_cookies()
            
            if chrome_success or firefox_success:
                self._log("✅ Cookies synchronized successfully!")
                # Reload page
                self.browser.reload()
            else:
                self._log("❌ Cookie synchronization failed - manual login required")
                
        except Exception as e:
            logger.error(f"Cookie sync error: {e}")
            self._log(f"❌ Sync error: {e}")
            
    def _import_chrome_cookies(self) -> bool:
        """Import Steam cookies from Chrome"""
        try:
            import sqlite3
            from pathlib import Path
            
            # Try different Chrome paths
            possible_paths = [
                Path.home() / ".config" / "google-chrome" / "Default" / "Cookies",
                Path.home() / ".config" / "chromium" / "Default" / "Cookies",
                Path.home() / ".local" / "share" / "google-chrome" / "Default" / "Cookies"
            ]
            
            chrome_cookies_path = None
            for path in possible_paths:
                if path.exists():
                    chrome_cookies_path = path
                    self._log(f"🔍 Chrome cookies found: {path}")
                    break
            
            if not chrome_cookies_path:
                self._log("❌ Chrome cookies database not found")
                self._log(f"🔍 Searched paths: {[str(p) for p in possible_paths]}")
                return False
                
            # Connect to database
            self._log(f"📂 Opening database: {chrome_cookies_path}")
            conn = sqlite3.connect(str(chrome_cookies_path))
            cursor = conn.cursor()
            
            # Get Steam domain cookies
            self._log("🔍 Searching for Steam cookies...")
            cursor.execute("""
                SELECT name, value, domain, path, expires_utc, is_secure, is_httponly
                FROM cookies
                WHERE domain LIKE '%steam%' OR domain LIKE '%valve%'
            """)
            
            cookies = cursor.fetchall()
            conn.close()
            
            self._log(f"📊 {len(cookies)} Steam cookies found")
            
            if cookies:
                for cookie in cookies[:3]:  # İlk 3'ünü logla
                    self._log(f"🍪 {cookie[0]} @ {cookie[2]}")
                
                # TODO: Add cookies to Qt browser (for now just log)
                self._log("⚠️ Cookie transfer not yet implemented - manual login required")
                return False  # Not yet implemented
                
            else:
                self._log("❌ Steam cookies not found - login in system browser first")
                return False
            
        except PermissionError:
            self._log("❌ Chrome database permission error - close Chrome")
            return False
        except Exception as e:
            self._log(f"❌ Chrome cookie error: {e}")
            logger.error(f"Chrome cookie import error: {e}")
            return False
            
    def _import_firefox_cookies(self) -> bool:
        """Import Steam cookies from Firefox"""
        try:
            import sqlite3
            from pathlib import Path
            import glob
            
            # Find Firefox profile folder
            firefox_root = Path.home() / ".mozilla" / "firefox"
            if not firefox_root.exists():
                self._log("❌ Firefox profile folder not found")
                return False
                
            # Search for profile folders (random named)
            profile_pattern = str(firefox_root / "*.default*")
            profile_dirs = glob.glob(profile_pattern)
            
            if not profile_dirs:
                self._log("❌ Firefox profile not found")
                return False
                
            # Use first profile
            profile_path = Path(profile_dirs[0])
            cookies_db = profile_path / "cookies.sqlite"
            
            if not cookies_db.exists():
                self._log(f"❌ Firefox cookies.sqlite not found: {cookies_db}")
                return False
                
            self._log(f"🔍 Firefox cookies found: {cookies_db}")
            
            # Connect to Firefox database
            conn = sqlite3.connect(str(cookies_db))
            cursor = conn.cursor()
            
            # Firefox cookie table is different
            self._log("🔍 Searching for Firefox Steam cookies...")
            cursor.execute("""
                SELECT name, value, host, path, expiry, isSecure, isHttpOnly
                FROM moz_cookies
                WHERE host LIKE '%steam%' OR host LIKE '%valve%'
            """)
            
            cookies = cursor.fetchall()
            conn.close()
            
            self._log(f"📊 {len(cookies)} Steam cookies found in Firefox")
            
            if cookies:
                for cookie in cookies[:3]:  # Log first 3
                    self._log(f"🍪 {cookie[0]} @ {cookie[2]}")
                
                # TODO: Add cookies to Qt browser
                self._log("⚠️ Firefox cookie transfer not yet implemented")
                return False
                
            else:
                self._log("❌ Steam cookies not found in Firefox")
                return False
                
        except PermissionError:
            self._log("❌ Firefox database permission error")
            return False
        except Exception as e:
            self._log(f"❌ Firefox cookie error: {e}")
            logger.error(f"Firefox cookie import error: {e}")
            return False
        
    def setup_styles(self):
        """Setup styles"""
        self.setStyleSheet("""
            QFrame#SteamBrowserWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.08), stop:1 rgba(255, 255, 255, 0.03));
                border: 2px solid #444;
                border-radius: 10px;
                margin: 5px;
            }
            
            QLabel#BrowserTitle {
                font-size: 16px;
                font-weight: bold;
                color: #00d4ff;
                padding: 5px;
            }
            
            QLabel#DownloadTitle {
                font-size: 14px;
                font-weight: bold;
                color: #00ff88;
                padding: 3px;
            }
            
            QPushButton#GoButton, QPushButton#HomeButton {
                background: rgba(0, 212, 255, 0.2);
                color: #00d4ff;
                border: 1px solid rgba(0, 212, 255, 0.4);
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }
            
            QPushButton#GoButton:hover, QPushButton#HomeButton:hover {
                background: rgba(0, 212, 255, 0.4);
                border-color: #00d4ff;
            }
            
            QFrame#DownloadPanel {
                background: rgba(0, 255, 136, 0.05);
                border: 1px solid rgba(0, 255, 136, 0.2);
                border-radius: 6px;
            }
            
            QLineEdit {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(0, 212, 255, 0.3);
                border-radius: 4px;
                padding: 6px;
                color: white;
            }
            
            QTextEdit {
                background: rgba(0, 0, 0, 0.3);
                border: 1px solid #333;
                border-radius: 4px;
                color: #ccc;
                font-family: monospace;
                font-size: 11px;
            }
        """)
        
    def _on_go_clicked(self):
        """When Go button is clicked"""
        url_text = self.url_input.text().strip()
        if not url_text:
            return
            
        # Check URL format
        if not url_text.startswith(('http://', 'https://')):
            # Accept as search query
            search_url = f"https://steamcommunity.com/workshop/browse/?appid=431960&searchtext={url_text}&browsesort=trend"
            url_text = search_url
            
        self.browser.load(QUrl(url_text))
        self._log(f"Loading: {url_text}")
        
    def _on_home_clicked(self):
        """When Home button is clicked"""
        workshop_url = "https://steamcommunity.com/workshop/browse/?appid=431960&browsesort=trend&section=readytouseitems"
        self.browser.load(QUrl(workshop_url))
        self.url_input.clear()
        self._log("Steam Workshop home page loaded")
        
    def _on_workshop_item_detected(self, workshop_id: str):
        """When workshop item is detected"""
        reply = QMessageBox.question(
            self,
            "Workshop Item Detected",
            f"Workshop ID: {workshop_id}\n\nDo you want to download this wallpaper?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.downloader.add_to_queue(workshop_id)
            self._log(f"Added to download queue: {workshop_id}")
            
    def _on_download_started(self, workshop_id: str):
        """When download starts"""
        self.current_downloads.append(workshop_id)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self._log(f"Download started: {workshop_id}")
        
    def _on_download_progress(self, workshop_id: str, progress: int):
        """Download progress"""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(progress)
        self._log(f"Download progress {workshop_id}: {progress}%")
        
    def _on_download_finished(self, workshop_id: str, success: bool):
        """When download is completed"""
        if workshop_id in self.current_downloads:
            self.current_downloads.remove(workshop_id)
            
        if not self.current_downloads:
            self.progress_bar.setVisible(False)
            
        if success:
            self._log(f"✅ Download completed: {workshop_id}")
            self.wallpaper_downloaded.emit(workshop_id)
        else:
            self._log(f"❌ Download failed: {workshop_id}")
            
    def _log(self, message: str):
        """Add log message"""
        self.download_log.append(f"[{self._get_timestamp()}] {message}")
        
    def _get_timestamp(self) -> str:
        """Get timestamp"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")
        
    def navigate_to_workshop(self):
        """Navigate to workshop home page"""
        self._on_home_clicked()
        
    def search_workshop(self, query: str):
        """Search in workshop"""
        self.url_input.setText(query)
        self._on_go_clicked()