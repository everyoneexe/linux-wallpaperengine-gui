#!/usr/bin/env python3
"""
Wallpaper Search Widget
Metadata-based search interface
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                               QPushButton, QComboBox, QLabel, QScrollArea,
                               QFrame, QGridLayout, QCheckBox, QSpinBox)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QPixmap, QPainter, QFont
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

from utils.metadata_manager import metadata_manager, WallpaperMetadata

class SearchWorker(QThread):
    """Worker that performs search in background"""
    
    results_ready = Signal(list)
    
    def __init__(self, query: str, filters: Dict[str, Any]):
        super().__init__()
        self.query = query
        self.filters = filters
    
    def run(self):
        """Run search operation"""
        try:
            results = metadata_manager.search(self.query, self.filters)
            self.results_ready.emit(results)
        except Exception as e:
            print(f"Search error: {e}")
            self.results_ready.emit([])

class WallpaperSearchResult(QFrame):
    """Search result widget"""
    
    wallpaper_selected = Signal(str)  # workshop_id
    
    def __init__(self, metadata: WallpaperMetadata):
        super().__init__()
        self.metadata = metadata
        self.setup_ui()
        
    def setup_ui(self):
        """Setup UI"""
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet("""
            WallpaperSearchResult {
                border: 1px solid #444;
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.05);
                margin: 2px;
            }
            WallpaperSearchResult:hover {
                background: rgba(255, 255, 255, 0.1);
                border-color: #666;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        
        # Preview image placeholder
        preview_label = QLabel()
        preview_label.setFixedSize(80, 60)
        preview_label.setStyleSheet("""
            QLabel {
                border: 1px solid #555;
                border-radius: 4px;
                background: #333;
                color: #888;
            }
        """)
        preview_label.setAlignment(Qt.AlignCenter)
        preview_label.setText("🖼️")
        layout.addWidget(preview_label)
        
        # Info layout
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # Title
        title_label = QLabel(self.metadata.title)
        title_label.setStyleSheet("font-weight: bold; color: white; font-size: 14px;")
        title_label.setWordWrap(True)
        info_layout.addWidget(title_label)
        
        # Details
        details = []
        if self.metadata.tags:
            details.append(f"🏷️ {', '.join(self.metadata.tags[:3])}")
        details.append(f"📁 {self.metadata.type}")
        details.append(f"🆔 {self.metadata.workshop_id}")
        
        details_label = QLabel(" • ".join(details))
        details_label.setStyleSheet("color: #aaa; font-size: 11px;")
        details_label.setWordWrap(True)
        info_layout.addWidget(details_label)
        
        # Description (if available)
        if self.metadata.description:
            desc_text = self.metadata.description[:100] + "..." if len(self.metadata.description) > 100 else self.metadata.description
            desc_label = QLabel(desc_text)
            desc_label.setStyleSheet("color: #ccc; font-size: 10px; font-style: italic;")
            desc_label.setWordWrap(True)
            info_layout.addWidget(desc_label)
        
        layout.addLayout(info_layout, 1)
        
        # Select button
        select_btn = QPushButton("Select")
        select_btn.setFixedSize(60, 30)
        select_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #45a049;
            }
            QPushButton:pressed {
                background: #3d8b40;
            }
        """)
        select_btn.clicked.connect(lambda: self.wallpaper_selected.emit(self.metadata.workshop_id))
        layout.addWidget(select_btn)
        
        self.setMaximumHeight(80)

class SearchWidget(QWidget):
    """Search widget"""
    
    wallpaper_selected = Signal(str)  # workshop_id
    
    def __init__(self):
        super().__init__()
        self.search_worker = None
        self.setup_ui()
        self.setup_connections()
        
        # Load metadata
        QTimer.singleShot(1000, self.load_metadata)
        
    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Search header
        header_layout = QHBoxLayout()
        
        search_label = QLabel("🔍 Wallpaper Arama")
        search_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        header_layout.addWidget(search_label)
        
        header_layout.addStretch()
        
        # Metadata yenile butonu
        refresh_btn = QPushButton("🔄 Yenile")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover { background: #1976D2; }
        """)
        refresh_btn.clicked.connect(self.load_metadata)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Search input
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search wallpaper name, tag or ID...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 2px solid #444;
                border-radius: 6px;
                background: rgba(255, 255, 255, 0.1);
                color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #4CAF50;
            }
        """)
        search_layout.addWidget(self.search_input)
        
        search_btn = QPushButton("Ara")
        search_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background: #45a049; }
        """)
        search_btn.clicked.connect(self.perform_search)
        search_layout.addWidget(search_btn)
        
        layout.addLayout(search_layout)
        
        # Filters
        filters_frame = QFrame()
        filters_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #444;
                border-radius: 6px;
                background: rgba(255, 255, 255, 0.05);
                padding: 5px;
            }
        """)
        filters_layout = QHBoxLayout(filters_frame)
        
        # Type filter
        type_label = QLabel("Tip:")
        type_label.setStyleSheet("color: #ccc;")
        filters_layout.addWidget(type_label)
        
        self.type_combo = QComboBox()
        self.type_combo.setStyleSheet("""
            QComboBox {
                background: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
                min-width: 80px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ccc;
            }
        """)
        filters_layout.addWidget(self.type_combo)
        
        # Tag filter
        tag_label = QLabel("Etiket:")
        tag_label.setStyleSheet("color: #ccc;")
        filters_layout.addWidget(tag_label)
        
        self.tag_combo = QComboBox()
        self.tag_combo.setStyleSheet(self.type_combo.styleSheet())
        filters_layout.addWidget(self.tag_combo)
        
        filters_layout.addStretch()
        
        # Clear filters
        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet("""
            QPushButton {
                background: #ff9800;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton:hover { background: #f57c00; }
        """)
        clear_btn.clicked.connect(self.clear_filters)
        filters_layout.addWidget(clear_btn)
        
        layout.addWidget(filters_frame)
        
        # Results info
        self.results_info = QLabel("Loading metadata...")
        self.results_info.setStyleSheet("color: #aaa; font-size: 12px;")
        layout.addWidget(self.results_info)
        
        # Results scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #444;
                border-radius: 6px;
                background: rgba(0, 0, 0, 0.3);
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.1);
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.3);
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.5);
            }
        """)
        
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_layout.setSpacing(2)
        self.results_layout.addStretch()
        
        self.scroll_area.setWidget(self.results_widget)
        layout.addWidget(self.scroll_area)
        
    def setup_connections(self):
        """Setup connections"""
        # Real-time search (with 500ms delay)
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        
        self.search_input.textChanged.connect(lambda: self.search_timer.start(500))
        self.type_combo.currentTextChanged.connect(self.perform_search)
        self.tag_combo.currentTextChanged.connect(self.perform_search)
        
    def load_metadata(self):
        """Load metadata"""
        self.results_info.setText("Scanning metadata...")

        # Load metadata in background
        def load_in_background():
            count = metadata_manager.scan_wallpapers()
            
            # Update UI
            QTimer.singleShot(0, lambda: self.metadata_loaded(count))
        
        QTimer.singleShot(100, load_in_background)
        
    def metadata_loaded(self, count: int):
        """Called when metadata is loaded"""
        self.results_info.setText(f"Total {count} wallpapers found")

        # Update filters
        self.update_filters()

        # Perform initial search
        self.perform_search()
        
    def update_filters(self):
        """Update filter options"""
        # Type combo
        self.type_combo.clear()
        self.type_combo.addItem("All", "")
        for type_name in metadata_manager.get_all_types():
            self.type_combo.addItem(type_name.title(), type_name)
        
        # Tag combo
        self.tag_combo.clear()
        self.tag_combo.addItem("All", "")
        for tag in metadata_manager.get_all_tags()[:50]:  # First 50 tags
            self.tag_combo.addItem(tag, tag)
    
    def clear_filters(self):
        """Clear filters"""
        self.search_input.clear()
        self.type_combo.setCurrentIndex(0)
        self.tag_combo.setCurrentIndex(0)
        
    def perform_search(self):
        """Arama yap"""
        if self.search_worker and self.search_worker.isRunning():
            return
            
        query = self.search_input.text().strip()
        filters = {}
        
        # Filtreleri topla
        if self.type_combo.currentData():
            filters['type'] = self.type_combo.currentData()
        if self.tag_combo.currentData():
            filters['tag'] = self.tag_combo.currentData()
        
        # Start search worker
        self.search_worker = SearchWorker(query, filters)
        self.search_worker.results_ready.connect(self.display_results)
        self.search_worker.start()
        
        self.results_info.setText("Searching...")
        
    def display_results(self, results: List[WallpaperMetadata]):
        """Display results"""
        # Clear previous results
        for i in reversed(range(self.results_layout.count() - 1)):
            child = self.results_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Add new results
        for metadata in results[:50]:  # First 50 results
            result_widget = WallpaperSearchResult(metadata)
            result_widget.wallpaper_selected.connect(self.wallpaper_selected.emit)
            self.results_layout.insertWidget(self.results_layout.count() - 1, result_widget)
        
        # Update result info
        total_count = metadata_manager.get_wallpaper_count()
        if results:
            self.results_info.setText(f"{len(results)} results found (total {total_count} wallpapers)")
        else:
            query = self.search_input.text().strip()
            if query:
                self.results_info.setText(f"No results found for '{query}' (total {total_count} wallpapers)")
            else:
                self.results_info.setText(f"Toplam {total_count} wallpaper")