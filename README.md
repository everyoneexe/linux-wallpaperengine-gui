# Linux Wallpaper Engine

GUI for the [Almamu/linux-wallpaperengine](https://github.com/Almamu/linux-wallpaperengine).

A powerful wallpaper management application for Linux with Steam Workshop support, video wallpapers, and advanced features.

## Features

- 🎨 **Steam Workshop Integration** - Browse and apply Steam Workshop wallpapers
- 🎬 **Video/GIF Support** - MP4, WebM, GIF with FFmpeg processing
- 📋 **Playlist Management** - Create playlists with auto-switching
- 🖥️ **Multi-Monitor Support** - Individual settings per monitor
- 🎵 **Audio Control** - Volume and mute controls
- ⚡ **Performance Control** - FPS settings and optimization

## Quick Start

### Install Dependencies
```bash
# Ubuntu/Debian
sudo apt install python3 python3-pip ffmpeg swww
pip3 install PySide6 psutil

# Arch Linux
sudo pacman -S python python-pip ffmpeg swww
pip3 install PySide6 psutil
```

### Run Application
```bash
git clone https://github.com/yourusername/linux-wallpaper-engine.git
cd linux-wallpaper-engine
python3 main.py
```


## Usage

1. **Apply Wallpaper**: Click any thumbnail to set as wallpaper
2. **Create Playlist**: Right-click wallpapers to add to playlist
3. **Control Playback**: Use playlist controls for auto-switching
4. **Adjust Settings**: Use volume/FPS sliders for optimization

## Configuration

### Steam Workshop Path
Auto-detected from:
- `~/.steam/steam/steamapps/workshop/content/431960/`
- `~/.local/share/Steam/steamapps/workshop/content/431960/`

### Settings Location
- `~/.config/wallpaper_engine/`

### Desktop Entry Customization
You can customize the `.desktop` file according to your preferences for better desktop integration.

## Troubleshooting

**Wallpaper not applying**: Check if `swww` daemon is running with `swww query`

**Performance issues**: Lower FPS settings or use optimization features

**Audio problems**: Check volume slider and verify audio track exists

## License

GNU General Public License v3.0 - see [LICENSE](LICENSE) file.

## Requirements

- Linux (X11/Wayland)
- Python 3.8+
- FFmpeg, swww
- 2GB RAM minimum