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
    """Workshop item indirme thread'i"""
    
    download_started = Signal(str)  # workshop_id
    download_progress = Signal(str, int)  # workshop_id, progress
    download_finished = Signal(str, bool)  # workshop_id, success
    
    def __init__(self):
        super().__init__()
        self.download_queue: List[str] = []
        self.is_downloading = False
        
    def add_to_queue(self, workshop_id: str):
        """İndirme kuyruğuna ekle"""
        if workshop_id not in self.download_queue:
            self.download_queue.append(workshop_id)
            logger.info(f"Workshop item kuyruğa eklendi: {workshop_id}")
            
    def run(self):
        """İndirme işlemini başlat"""
        while self.download_queue:
            workshop_id = self.download_queue.pop(0)
            self.is_downloading = True
            
            try:
                self.download_started.emit(workshop_id)
                success = self._download_workshop_item(workshop_id)
                self.download_finished.emit(workshop_id, success)
                
            except Exception as e:
                logger.error(f"İndirme hatası {workshop_id}: {e}")
                self.download_finished.emit(workshop_id, False)
                
            finally:
                self.is_downloading = False
                
    def _download_workshop_item(self, workshop_id: str) -> bool:
        """Workshop item'ını indir"""
        try:
            import subprocess
            
            # SteamCMD ile indirme (eğer varsa)
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
                logger.warning("SteamCMD bulunamadı, manuel indirme gerekli")
                return False
                
            # SteamCMD komutu
            cmd = [
                steamcmd_path,
                "+login", "anonymous",
                "+workshop_download_item", "431960", workshop_id,
                "+quit"
            ]
            
            logger.info(f"SteamCMD ile indiriliyor: {workshop_id}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info(f"Workshop item başarıyla indirildi: {workshop_id}")
                return True
            else:
                logger.error(f"SteamCMD hatası: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"İndirme zaman aşımı: {workshop_id}")
            return False
        except Exception as e:
            logger.error(f"İndirme hatası: {e}")
            return False


class SteamWebPage(QWebEnginePage):
    """Özelleştirilmiş Steam web sayfası"""
    
    workshop_item_detected = Signal(str)  # workshop_id
    
    def __init__(self, profile=None, parent=None):
        if profile:
            super().__init__(profile, parent)
        else:
            super().__init__(parent)
        self.workshop_pattern = re.compile(r'steamcommunity\.com/sharedfiles/filedetails/\?id=(\d+)')
        
    def acceptNavigationRequest(self, url: QUrl, nav_type, is_main_frame: bool) -> bool:
        """Navigasyon isteklerini yakala"""
        url_string = url.toString()
        
        # Workshop item linkini yakala
        match = self.workshop_pattern.search(url_string)
        if match:
            workshop_id = match.group(1)
            logger.info(f"Workshop item tespit edildi: {workshop_id}")
            self.workshop_item_detected.emit(workshop_id)
            
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


class SteamBrowserWidget(QFrame):
    """
    Steam Workshop browser widget'ı
    
    Signals:
        wallpaper_downloaded: Wallpaper indirildiğinde emit edilir
    """
    
    wallpaper_downloaded = Signal(str)  # workshop_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.downloader = WorkshopDownloader()
        self.current_downloads: List[str] = []
        
        self.setup_ui()
        self.setup_connections()
        self.setup_styles()
        
        # İndirme thread'ini başlat
        self.downloader.start()
        
    def setup_ui(self):
        """UI'ı kur"""
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
        
        # Splitter - Browser ve Download Panel
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
        """Header oluştur"""
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
        self.url_input.setPlaceholderText("Workshop URL veya arama...")
        self.url_input.setMinimumWidth(300)
        self.url_input.clear()  # URL input'u temiz tut
        layout.addWidget(self.url_input)
        
        # Go button
        self.go_btn = QPushButton("🔍 Git")
        self.go_btn.setObjectName("GoButton")
        layout.addWidget(self.go_btn)
        
        # Home button
        self.home_btn = QPushButton("🏠 Ana Sayfa")
        self.home_btn.setObjectName("HomeButton")
        layout.addWidget(self.home_btn)
        
        return header
        
    def create_browser(self) -> QWebEngineView:
        """Web browser oluştur - Gelişmiş login kalıcılığı"""
        browser = QWebEngineView()
        
        # DETAYLI PERSİST PATH AYARI
        from pathlib import Path
        persist_path = Path.home() / ".config" / "wallpaper_engine" / "steam_cookies"
        persist_path.mkdir(parents=True, exist_ok=True)
        
        # CUSTOM PROFİLE - tam kontrol için
        profile = QWebEngineProfile("SteamPersist", browser)
        
        # EXPLICIT STORAGE PATHS
        profile.setPersistentStoragePath(str(persist_path))
        profile.setCachePath(str(persist_path / "cache"))
        profile.setDownloadPath(str(persist_path / "downloads"))
        
        # COOKIE POLİCY - zorla kalıcı
        profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
        profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
        profile.setHttpCacheMaximumSize(100 * 1024 * 1024)  # 100MB cache
        
        # STEAM-FRIENDLY USER AGENT
        steam_ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 SteamClient/1701890080"
        profile.setHttpUserAgent(steam_ua)
        
        # HTTP HEADERS
        profile.setHttpAcceptLanguage("en-US,en;q=0.9")
        
        # WEB SETTINGS - tam browser davranışı
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
        
        # CUSTOM SAYFA
        page = SteamWebPage(profile)
        browser.setPage(page)
        
        # İLK REQUEST'İ GECİKTİR
        QTimer.singleShot(3000, self._delayed_load_workshop)  # 3 saniye bekle (daha uzun)
        
        logger.info(f"Steam browser gelişmiş persist profile: {persist_path}")
        return browser
        
    def create_download_panel(self) -> QWidget:
        """İndirme paneli oluştur"""
        panel = QFrame()
        panel.setObjectName("DownloadPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Panel title
        title = QLabel("📥 İndirme Durumu")
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
        self.download_log.setPlaceholderText("İndirme logları burada görünecek...")
        layout.addWidget(self.download_log)
        
        return panel
        
    def setup_connections(self):
        """Sinyal bağlantılarını kur"""
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
        """Browser hazır olduktan sonra gecikmiş Steam Workshop yükleme"""
        workshop_url = "https://steamcommunity.com/workshop/browse/?appid=431960&browsesort=trend&section=readytouseitems"
        self.browser.load(QUrl(workshop_url))
        logger.info("Steam Workshop gecikmiş yükleme başlatıldı")
        
    def create_browser_sync_panel(self) -> QWidget:
        """Dış tarayıcı sync paneli oluştur"""
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
        text_label = QLabel("Login kalıcı değilse:")
        text_label.setStyleSheet("color: #ccc; font-size: 12px;")
        layout.addWidget(text_label)
        
        # External login button
        external_btn = QPushButton("🌐 Sistem Tarayıcısında Giriş Yap")
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
        sync_btn = QPushButton("🔄 Cookie'leri Senkronize Et")
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
        """Sistem tarayıcısında Steam login sayfasını aç"""
        import subprocess
        login_url = "https://steamcommunity.com/login/home/?goto=%2Fworkshop%2Fbrowse%2F%3Fappid%3D431960%26browsesort%3Dtrend%26section%3Dreadytouseitems"
        try:
            subprocess.run(["xdg-open", login_url], check=True)
            logger.info("Steam login sistem tarayıcısında açıldı")
            self._log("🌐 Sistem tarayıcısında Steam'e giriş yapın, sonra Cookie Sync'e basın")
        except subprocess.CalledProcessError:
            logger.error("Tarayıcı açılamadı")
            self._log("❌ Tarayıcı açılamadı")
            
    def _sync_cookies_from_system(self):
        """Sistem tarayıcısından cookie'leri senkronize et - async"""
        self._log("🔄 Cookie senkronizasyonu başlatılıyor...")
        
        # Main thread'i bloklamaz için timer ile async yap
        QTimer.singleShot(100, self._perform_cookie_sync)
        
    def _perform_cookie_sync(self):
        """Gerçek cookie sync işlemi (async)"""
        try:
            # Chrome cookie'lerini oku
            chrome_success = self._import_chrome_cookies()
            firefox_success = self._import_firefox_cookies()
            
            if chrome_success or firefox_success:
                self._log("✅ Cookie'ler başarıyla senkronize edildi!")
                # Sayfayı yenile
                self.browser.reload()
            else:
                self._log("❌ Cookie senkronizasyonu başarısız - manuel giriş gerekli")
                
        except Exception as e:
            logger.error(f"Cookie sync hatası: {e}")
            self._log(f"❌ Sync hatası: {e}")
            
    def _import_chrome_cookies(self) -> bool:
        """Chrome'dan Steam cookie'lerini import et"""
        try:
            import sqlite3
            from pathlib import Path
            
            # Farklı Chrome paths dene
            possible_paths = [
                Path.home() / ".config" / "google-chrome" / "Default" / "Cookies",
                Path.home() / ".config" / "chromium" / "Default" / "Cookies",
                Path.home() / ".local" / "share" / "google-chrome" / "Default" / "Cookies"
            ]
            
            chrome_cookies_path = None
            for path in possible_paths:
                if path.exists():
                    chrome_cookies_path = path
                    self._log(f"🔍 Chrome cookies bulundu: {path}")
                    break
            
            if not chrome_cookies_path:
                self._log("❌ Chrome cookies database bulunamadı")
                self._log(f"🔍 Aranan yollar: {[str(p) for p in possible_paths]}")
                return False
                
            # Database'e bağlan
            self._log(f"📂 Database açılıyor: {chrome_cookies_path}")
            conn = sqlite3.connect(str(chrome_cookies_path))
            cursor = conn.cursor()
            
            # Steam domain cookie'lerini al
            self._log("🔍 Steam cookie'leri aranıyor...")
            cursor.execute("""
                SELECT name, value, domain, path, expires_utc, is_secure, is_httponly
                FROM cookies
                WHERE domain LIKE '%steam%' OR domain LIKE '%valve%'
            """)
            
            cookies = cursor.fetchall()
            conn.close()
            
            self._log(f"📊 {len(cookies)} Steam cookie'si bulundu")
            
            if cookies:
                for cookie in cookies[:3]:  # İlk 3'ünü logla
                    self._log(f"🍪 {cookie[0]} @ {cookie[2]}")
                
                # TODO: Qt browser'a cookie'leri ekle (şimdilik sadece log)
                self._log("⚠️ Cookie aktarımı henüz implement edilmedi - manuel giriş gerekli")
                return False  # Henüz implement edilmedi
                
            else:
                self._log("❌ Steam cookie'si bulunamadı - önce sistem tarayıcısında giriş yapın")
                return False
            
        except PermissionError:
            self._log("❌ Chrome database permission hatası - Chrome'u kapatın")
            return False
        except Exception as e:
            self._log(f"❌ Chrome cookie hatası: {e}")
            logger.error(f"Chrome cookie import hatası: {e}")
            return False
            
    def _import_firefox_cookies(self) -> bool:
        """Firefox'tan Steam cookie'lerini import et"""
        try:
            import sqlite3
            from pathlib import Path
            import glob
            
            # Firefox profile klasörünü bul
            firefox_root = Path.home() / ".mozilla" / "firefox"
            if not firefox_root.exists():
                self._log("❌ Firefox profil klasörü bulunamadı")
                return False
                
            # Profile klasörlerini ara (random isimli)
            profile_pattern = str(firefox_root / "*.default*")
            profile_dirs = glob.glob(profile_pattern)
            
            if not profile_dirs:
                self._log("❌ Firefox profile bulunamadı")
                return False
                
            # İlk profili kullan
            profile_path = Path(profile_dirs[0])
            cookies_db = profile_path / "cookies.sqlite"
            
            if not cookies_db.exists():
                self._log(f"❌ Firefox cookies.sqlite bulunamadı: {cookies_db}")
                return False
                
            self._log(f"🔍 Firefox cookies bulundu: {cookies_db}")
            
            # Firefox database'e bağlan
            conn = sqlite3.connect(str(cookies_db))
            cursor = conn.cursor()
            
            # Firefox cookie tablosu farklı
            self._log("🔍 Firefox Steam cookie'leri aranıyor...")
            cursor.execute("""
                SELECT name, value, host, path, expiry, isSecure, isHttpOnly
                FROM moz_cookies
                WHERE host LIKE '%steam%' OR host LIKE '%valve%'
            """)
            
            cookies = cursor.fetchall()
            conn.close()
            
            self._log(f"📊 Firefox'ta {len(cookies)} Steam cookie'si bulundu")
            
            if cookies:
                for cookie in cookies[:3]:  # İlk 3'ünü logla
                    self._log(f"🍪 {cookie[0]} @ {cookie[2]}")
                
                # TODO: Qt browser'a cookie'leri ekle
                self._log("⚠️ Firefox cookie aktarımı henüz implement edilmedi")
                return False
                
            else:
                self._log("❌ Firefox'ta Steam cookie'si bulunamadı")
                return False
                
        except PermissionError:
            self._log("❌ Firefox database permission hatası")
            return False
        except Exception as e:
            self._log(f"❌ Firefox cookie hatası: {e}")
            logger.error(f"Firefox cookie import hatası: {e}")
            return False
        
    def setup_styles(self):
        """Stilleri ayarla"""
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
        """Git butonuna tıklandığında"""
        url_text = self.url_input.text().strip()
        if not url_text:
            return
            
        # URL formatını kontrol et
        if not url_text.startswith(('http://', 'https://')):
            # Arama sorgusu olarak kabul et
            search_url = f"https://steamcommunity.com/workshop/browse/?appid=431960&searchtext={url_text}&browsesort=trend"
            url_text = search_url
            
        self.browser.load(QUrl(url_text))
        self._log(f"Yükleniyor: {url_text}")
        
    def _on_home_clicked(self):
        """Ana sayfa butonuna tıklandığında"""
        workshop_url = "https://steamcommunity.com/workshop/browse/?appid=431960&browsesort=trend&section=readytouseitems"
        self.browser.load(QUrl(workshop_url))
        self.url_input.clear()
        self._log("Steam Workshop ana sayfası yüklendi")
        
    def _on_workshop_item_detected(self, workshop_id: str):
        """Workshop item tespit edildiğinde"""
        reply = QMessageBox.question(
            self,
            "Workshop Item Tespit Edildi",
            f"Workshop ID: {workshop_id}\n\nBu wallpaper'ı indirmek istiyor musunuz?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.downloader.add_to_queue(workshop_id)
            self._log(f"İndirme kuyruğuna eklendi: {workshop_id}")
            
    def _on_download_started(self, workshop_id: str):
        """İndirme başladığında"""
        self.current_downloads.append(workshop_id)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self._log(f"İndirme başladı: {workshop_id}")
        
    def _on_download_progress(self, workshop_id: str, progress: int):
        """İndirme ilerlemesi"""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(progress)
        self._log(f"İndirme ilerlemesi {workshop_id}: %{progress}")
        
    def _on_download_finished(self, workshop_id: str, success: bool):
        """İndirme tamamlandığında"""
        if workshop_id in self.current_downloads:
            self.current_downloads.remove(workshop_id)
            
        if not self.current_downloads:
            self.progress_bar.setVisible(False)
            
        if success:
            self._log(f"✅ İndirme tamamlandı: {workshop_id}")
            self.wallpaper_downloaded.emit(workshop_id)
        else:
            self._log(f"❌ İndirme başarısız: {workshop_id}")
            
    def _log(self, message: str):
        """Log mesajı ekle"""
        self.download_log.append(f"[{self._get_timestamp()}] {message}")
        
    def _get_timestamp(self) -> str:
        """Zaman damgası al"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")
        
    def navigate_to_workshop(self):
        """Workshop ana sayfasına git"""
        self._on_home_clicked()
        
    def search_workshop(self, query: str):
        """Workshop'ta ara"""
        self.url_input.setText(query)
        self._on_go_clicked()