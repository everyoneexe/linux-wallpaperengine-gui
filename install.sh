#!/bin/bash

# Wallpaper Engine Linux Installer (User-Level)
# Universal installer for all Linux distributions

set -e

echo "🎨 Wallpaper Engine Linux Installer"
echo "=================================="

# Detect distribution
detect_distro() {
    if command -v pacman >/dev/null; then
        echo "arch"
    elif command -v apt >/dev/null; then
        echo "debian"
    elif command -v dnf >/dev/null; then
        echo "fedora"
    elif command -v zypper >/dev/null; then
        echo "opensuse"
    else
        echo "unknown"
    fi
}

DISTRO=$(detect_distro)
echo "📋 Detected distribution: $DISTRO"

# Check dependencies
check_dependencies() {
    echo "🔍 Checking dependencies..."
    
    MISSING=""
    
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
        MISSING="$MISSING python3"
    fi
    
    if ! python3 -c "import PySide6" 2>/dev/null; then
        MISSING="$MISSING PySide6"
    fi
    
    if ! python3 -c "import PIL" 2>/dev/null; then
        MISSING="$MISSING Pillow"
    fi
    
    if ! python3 -c "import requests" 2>/dev/null; then
        MISSING="$MISSING requests"
    fi
    
    if ! command -v ffmpeg >/dev/null; then
        MISSING="$MISSING ffmpeg"
    fi
    
    if [ -n "$MISSING" ]; then
        echo "❌ Missing dependencies:$MISSING"
        echo ""
        echo "📦 Please install them manually:"
        case $DISTRO in
            "arch")
                echo "   sudo pacman -S python pyside6 python-pillow python-requests ffmpeg"
                ;;
            "debian")
                echo "   sudo apt install python3 python3-pyside6.qtwidgets python3-pil python3-requests ffmpeg"
                ;;
            "fedora")
                echo "   sudo dnf install python3 python3-pyside6 python3-pillow python3-requests ffmpeg"
                ;;
            "opensuse")
                echo "   sudo zypper install python3 python3-pyside6 python3-Pillow python3-requests ffmpeg"
                ;;
            *)
                echo "   Or try: pip3 install --user PySide6 Pillow requests"
                echo "   And install ffmpeg from your package manager"
                ;;
        esac
        echo ""
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo "✅ All dependencies found!"
    fi
}

# Install Python dependencies via pip
install_pip_dependencies() {
    echo "📦 Installing missing Python packages via pip..."
    
    if ! python3 -c "import PySide6" 2>/dev/null; then
        pip3 install --user PySide6
    fi
    
    if ! python3 -c "import PIL" 2>/dev/null; then
        pip3 install --user Pillow
    fi
    
    if ! python3 -c "import requests" 2>/dev/null; then
        pip3 install --user requests
    fi
}

# Create user directories
create_directories() {
    echo "📁 Creating directories..."
    mkdir -p ~/.local/bin
    mkdir -p ~/.local/share/applications
    mkdir -p ~/.local/share/wallpaper-engine
}

# Copy files
copy_files() {
    echo "📋 Copying files..."
    cp -r . ~/.local/share/wallpaper-engine/
    chmod +x ~/.local/share/wallpaper-engine/main.py
}

# Create terminal command
create_command() {
    echo "💻 Creating terminal command..."
    cat > ~/.local/bin/wallpaper-engine << 'EOF'
#!/bin/bash
cd ~/.local/share/wallpaper-engine
python3 main.py "$@"
EOF
    chmod +x ~/.local/bin/wallpaper-engine
    
    # Add to PATH if not already there
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo "📝 Adding ~/.local/bin to PATH..."
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc 2>/dev/null || true
        export PATH="$HOME/.local/bin:$PATH"
    fi
}

# Create desktop entry
create_desktop_entry() {
    echo "🖥️  Creating desktop entry..."
    
    # Remove old entries
    rm -f ~/.local/share/applications/*wallpaper* 2>/dev/null || true
    
    # Create desktop entry
    cat > ~/.local/share/applications/wallpaper-engine.desktop << EOF
[Desktop Entry]
Name=Wallpaper Engine
Comment=Steam Workshop wallpapers for Linux
Exec=$HOME/.local/bin/wallpaper-engine
Icon=$HOME/.local/share/wallpaper-engine/wallpaper-engine.png
Terminal=false
Type=Application
Categories=Graphics;Utility;
StartupNotify=true
EOF

    # Update desktop database
    if command -v update-desktop-database >/dev/null; then
        update-desktop-database ~/.local/share/applications/ 2>/dev/null || true
    fi
    
    echo "✅ Desktop entry created"
}

# Main installation
main() {
    echo "🚀 Starting user-level installation..."
    echo "ℹ️  This installer need sudo privileges"
    echo ""
    
    check_dependencies
    
    # Try to install missing Python deps
    if ! python3 -c "import PySide6, PIL, requests" 2>/dev/null; then
        echo "🔧 Attempting to install Python dependencies..."
        install_pip_dependencies || echo "⚠️  Some pip installations may have failed"
    fi
    
    create_directories
    copy_files
    create_command
    create_desktop_entry
    
    echo ""
    echo "🎉 Installation completed successfully!"
    echo ""
    echo "📱 Launch from application menu: 'Wallpaper Engine'"
    echo "💻 Launch from terminal: wallpaper-engine"
    echo "📁 Installed to: ~/.local/share/wallpaper-engine"
    echo ""
    echo "🔄 You may need to restart your terminal or run:"
    echo "   source ~/.bashrc"
    echo ""
    echo "🔧 If you encounter issues:"
    echo "   - Make sure all dependencies are installed"
    echo "   - Check that ~/.local/bin is in your PATH"
    echo "   - Verify internet connection for Steam Workshop"
}

# Run main function
main