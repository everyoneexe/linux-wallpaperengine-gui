# 🎨 Python Wallpaper Engine

GUI for the [Almamu/linux-wallpaperengine](https://github.com/Almamu/linux-wallpaperengine).

A powerful wallpaper management application for Linux with Steam Workshop support, video wallpapers, and advanced features.

## ✨ Features

- 🖼️ **Steam Workshop wallpapers** - Full compatibility
- 🎬 **Video/GIF support** - MP4, WebM, GIF wallpapers  
- 📋 **Playlist management** - Organize collections
- 🔧 **System tray** - Minimize to tray
- 📁 **Custom imports** - Add your own wallpapers

## 🎯 Usage

```bash
# Terminal
wallpaper-engine

# Or find "Wallpaper Engine" in your application menu
```

## 📋 Requirements

- Steam account with Wallpaper Engine
- Some wallpapers from Steam Workshop
- Linux (Arch, Ubuntu, Debian, Fedora, openSUSE)

## 🔧 Manual Install (if needed)

**Arch Linux:**
```bash
sudo pacman -S python pyside6 python-pillow python-requests ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt install python3 python3-pyside6.qtwidgets python3-pil python3-requests ffmpeg
```

**Fedora:**
```bash
sudo dnf install python3 python3-pyside6 python3-pillow python3-requests ffmpeg
```

Then run: `python3 main.py`

## 🐛 Troubleshooting

**Steam Workshop not found:** Download wallpapers from Steam Workshop first

**Permission denied:** Don't run as root, use regular user

**Import errors:** Try `pip3 install --user PySide6 Pillow requests`

---

Simple, fast, reliable! 🎉
