#!/usr/bin/env python3
"""
Wallpaper Engine Launcher Script

Bu script, wallpaper engine uygulamasını başlatmak için kullanılır.
"""

import sys
from pathlib import Path

# Proje dizinini Python path'ine ekle
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Ana uygulamayı import et ve çalıştır
if __name__ == "__main__":
    from main import main
    main()