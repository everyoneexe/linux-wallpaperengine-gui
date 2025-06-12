#!/usr/bin/env python3
"""
Wallpaper Metadata Manager
Reads metadata from project.json files and provides search functionality
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import re

class WallpaperMetadata:
    """Wallpaper metadata class"""
    
    def __init__(self, workshop_id: str, data: Dict[str, Any]):
        self.workshop_id = workshop_id
        self.title = data.get('title', f'Wallpaper {workshop_id}')
        self.description = data.get('description', '')
        self.tags = data.get('tags', [])
        self.type = data.get('type', 'unknown')
        self.file = data.get('file', '')
        self.preview = data.get('preview', '')
        self.contentrating = data.get('contentrating', 'Everyone')
        self.workshopurl = data.get('workshopurl', '')
        self.version = data.get('version', 0)
        
        # Renk bilgisi
        self.scheme_color = self._extract_scheme_color(data)
        
    def _extract_scheme_color(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract color scheme"""
        try:
            general = data.get('general', {})
            properties = general.get('properties', {})
            schemecolor = properties.get('schemecolor', {})
            return schemecolor.get('value', None)
        except:
            return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'workshop_id': self.workshop_id,
            'title': self.title,
            'description': self.description,
            'tags': self.tags,
            'type': self.type,
            'file': self.file,
            'preview': self.preview,
            'contentrating': self.contentrating,
            'workshopurl': self.workshopurl,
            'version': self.version,
            'scheme_color': self.scheme_color
        }
    
    def matches_search(self, query: str) -> bool:
        """Check if it matches the search query"""
        query = query.lower().strip()
        if not query:
            return True
            
        # Search in title, description, tags and filename
        search_text = ' '.join([
            self.title.lower(),
            self.description.lower(),
            ' '.join(self.tags).lower(),
            self.file.lower(),
            self.workshop_id
        ])
        
        # If multiple words, all must be found
        words = query.split()
        return all(word in search_text for word in words)

class MetadataManager:
    """Metadata manager"""
    
    def __init__(self):
        self.wallpapers: Dict[str, WallpaperMetadata] = {}
        self.workshop_paths = [
            Path.home() / ".steam/steam/steamapps/workshop/content/431960",
            Path.home() / ".local/share/Steam/steamapps/workshop/content/431960",
            Path("/home/everyone/.steam/steam/steamapps/workshop/content/431960")
        ]
        
    def scan_wallpapers(self) -> int:
        """Scan wallpapers and load metadata"""
        count = 0
        
        for workshop_path in self.workshop_paths:
            if workshop_path.exists():
                print(f"Scanning: {workshop_path}")
                count += self._scan_directory(workshop_path)
                break
        
        print(f"Total {count} wallpaper metadata loaded")
        return count
    
    def _scan_directory(self, directory: Path) -> int:
        """Belirtilen dizini tara"""
        count = 0
        
        for item in directory.iterdir():
            if item.is_dir() and item.name.isdigit():
                workshop_id = item.name
                project_file = item / "project.json"
                
                if project_file.exists():
                    try:
                        with open(project_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            
                        metadata = WallpaperMetadata(workshop_id, data)
                        self.wallpapers[workshop_id] = metadata
                        count += 1
                        
                    except Exception as e:
                        print(f"Hata {workshop_id}: {e}")
        
        return count
    
    def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[WallpaperMetadata]:
        """Wallpaper'larda ara"""
        results = []
        
        for metadata in self.wallpapers.values():
            # Arama sorgusunu kontrol et
            if not metadata.matches_search(query):
                continue
                
            # Filtreleri uygula
            if filters:
                if not self._apply_filters(metadata, filters):
                    continue
            
            results.append(metadata)
        
        # Sort results (exact match in title first)
        query_lower = query.lower()
        results.sort(key=lambda x: (
            0 if query_lower in x.title.lower() else 1,
            x.title.lower()
        ))
        
        return results
    
    def _apply_filters(self, metadata: WallpaperMetadata, filters: Dict[str, Any]) -> bool:
        """Filtreleri uygula"""
        # Tip filtresi
        if 'type' in filters and filters['type']:
            if metadata.type != filters['type']:
                return False
        
        # Etiket filtresi
        if 'tag' in filters and filters['tag']:
            if filters['tag'] not in metadata.tags:
                return False
        
        # Content rating filter
        if 'contentrating' in filters and filters['contentrating']:
            if metadata.contentrating != filters['contentrating']:
                return False
        
        return True
    
    def get_all_tags(self) -> List[str]:
        """Get all tags"""
        tags = set()
        for metadata in self.wallpapers.values():
            tags.update(metadata.tags)
        return sorted(list(tags))
    
    def get_all_types(self) -> List[str]:
        """Get all types"""
        types = set()
        for metadata in self.wallpapers.values():
            types.add(metadata.type)
        return sorted(list(types))
    
    def get_metadata(self, workshop_id: str) -> Optional[WallpaperMetadata]:
        """Get metadata of a specific wallpaper"""
        return self.wallpapers.get(workshop_id)
    
    def get_wallpaper_count(self) -> int:
        """Get total wallpaper count"""
        return len(self.wallpapers)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics"""
        types = {}
        tags = {}
        ratings = {}
        
        for metadata in self.wallpapers.values():
            # Tip istatistikleri
            types[metadata.type] = types.get(metadata.type, 0) + 1
            
            # Etiket istatistikleri
            for tag in metadata.tags:
                tags[tag] = tags.get(tag, 0) + 1
            
            # Derecelendirme istatistikleri
            ratings[metadata.contentrating] = ratings.get(metadata.contentrating, 0) + 1
        
        return {
            'total_wallpapers': len(self.wallpapers),
            'types': dict(sorted(types.items(), key=lambda x: x[1], reverse=True)),
            'top_tags': dict(sorted(tags.items(), key=lambda x: x[1], reverse=True)[:20]),
            'content_ratings': dict(sorted(ratings.items(), key=lambda x: x[1], reverse=True))
        }

# Global metadata manager instance
metadata_manager = MetadataManager()