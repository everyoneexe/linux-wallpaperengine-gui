#!/bin/bash

# ============================================================================
# Wallpaper Engine Linux - Professional Universal Installer
# ============================================================================
# Version: 2.0.0
# Author: Advanced Linux Installer System
# Description: Comprehensive, bulletproof installer for all Linux distributions
# Features: Auto-detection, dependency management, error handling, logging
# ============================================================================

set -euo pipefail  # Strict error handling
IFS=$'\n\t'       # Secure Internal Field Separator

# ============================================================================
# GLOBAL CONFIGURATION & CONSTANTS
# ============================================================================

readonly SCRIPT_VERSION="2.0.0"
readonly APP_NAME="Wallpaper Engine Linux"
readonly APP_VERSION="1.0.0"
readonly INSTALL_DIR="/opt/wallpaper-engine"
readonly BIN_DIR="/usr/local/bin"
readonly DESKTOP_DIR="/usr/share/applications"
readonly CONFIG_DIR="/etc/wallpaper_engine"
readonly LOG_FILE="/var/log/wallpaper-engine-install.log"
readonly BACKUP_DIR="/opt/wallpaper-engine-backup-$(date +%Y%m%d_%H%M%S)"
# These will be set after we determine the real user
USER_CONFIG_DIR=""
USER_DATA_DIR=""

# Color codes for beautiful output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly BOLD='\033[1m'
readonly NC='\033[0m' # No Color

# Unicode symbols for modern appearance
readonly CHECK_MARK="✅"
readonly CROSS_MARK="❌"
readonly WARNING="⚠️"
readonly INFO="ℹ️"
readonly ROCKET="🚀"
readonly GEAR="⚙️"
readonly PACKAGE="📦"
readonly FOLDER="📁"
readonly COMPUTER="💻"
readonly DESKTOP="🖥️"
readonly FIRE="🔥"
readonly STAR="⭐"
readonly LIGHTNING="⚡"
readonly SHIELD="🛡️"

# ============================================================================
# LOGGING & OUTPUT FUNCTIONS
# ============================================================================

# Initialize logging
init_logging() {
    # Only initialize logging for actual installation, not for help/version
    if [[ "${1:-}" != "--help" && "${1:-}" != "-h" && "${1:-}" != "--version" && "${1:-}" != "-v" ]]; then
        mkdir -p "$(dirname "$LOG_FILE")"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Installation started" > "$LOG_FILE"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Script version: $SCRIPT_VERSION" >> "$LOG_FILE"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - System: $(uname -a)" >> "$LOG_FILE"
    fi
}

# Logging function
log() {
    # Only log if LOG_FILE exists (installation mode)
    if [[ -f "$LOG_FILE" ]]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
    fi
}

# Enhanced output functions
print_header() {
    echo -e "${BOLD}${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                              ║"
    echo "║                    ${FIRE} WALLPAPER ENGINE LINUX INSTALLER ${FIRE}                    ║"
    echo "║                                                                              ║"
    echo "║                           ${STAR} Professional Edition ${STAR}                           ║"
    echo "║                                                                              ║"
    echo "║                              Version: $SCRIPT_VERSION                               ║"
    echo "║                                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo
}

print_section() {
    echo -e "${BOLD}${BLUE}┌─────────────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${BOLD}${BLUE}│ $1${NC}"
    echo -e "${BOLD}${BLUE}└─────────────────────────────────────────────────────────────────────────────┘${NC}"
    echo
}

print_success() {
    echo -e "${GREEN}${CHECK_MARK} $1${NC}"
    log "SUCCESS: $1"
}

print_error() {
    echo -e "${RED}${CROSS_MARK} $1${NC}" >&2
    log "ERROR: $1"
}

print_warning() {
    echo -e "${YELLOW}${WARNING} $1${NC}"
    log "WARNING: $1"
}

print_info() {
    echo -e "${CYAN}${INFO} $1${NC}"
    log "INFO: $1"
}

print_step() {
    echo -e "${WHITE}${GEAR} $1...${NC}"
    log "STEP: $1"
}

# Progress bar function
show_progress() {
    local duration=$1
    local message=$2
    local progress=0
    local bar_length=50
    
    echo -ne "${CYAN}${message}: ${NC}"
    
    while [ $progress -le 100 ]; do
        local filled=$((progress * bar_length / 100))
        local empty=$((bar_length - filled))
        
        printf "\r${CYAN}${message}: ${NC}["
        printf "%*s" $filled | tr ' ' '█'
        printf "%*s" $empty | tr ' ' '░'
        printf "] %d%%" $progress
        
        sleep $(echo "scale=2; $duration/100" | bc -l 2>/dev/null || echo "0.01")
        progress=$((progress + 2))
    done
    echo
}

# ============================================================================
# SYSTEM DETECTION & ANALYSIS
# ============================================================================

# Comprehensive distribution detection
detect_distribution() {
    local distro="unknown"
    local version=""
    local codename=""
    
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        distro=$(echo "${ID:-unknown}" | tr '[:upper:]' '[:lower:]')
        version="${VERSION_ID:-unknown}"
        codename="${VERSION_CODENAME:-unknown}"
    elif [[ -f /etc/lsb-release ]]; then
        source /etc/lsb-release
        distro=$(echo "${DISTRIB_ID:-unknown}" | tr '[:upper:]' '[:lower:]')
        version="${DISTRIB_RELEASE:-unknown}"
        codename="${DISTRIB_CODENAME:-unknown}"
    elif command -v lsb_release >/dev/null 2>&1; then
        distro=$(lsb_release -si | tr '[:upper:]' '[:lower:]')
        version=$(lsb_release -sr)
        codename=$(lsb_release -sc)
    fi
    
    # Normalize distribution names
    case "$distro" in
        "ubuntu"|"debian"|"linuxmint"|"elementary"|"zorin"|"pop") distro="debian" ;;
        "fedora"|"centos"|"rhel"|"rocky"|"alma") distro="fedora" ;;
        "arch"|"manjaro"|"endeavouros"|"garuda"|"artix") distro="arch" ;;
        "opensuse"|"opensuse-leap"|"opensuse-tumbleweed"|"sles") distro="opensuse" ;;
        "gentoo"|"funtoo") distro="gentoo" ;;
        "void") distro="void" ;;
        "alpine") distro="alpine" ;;
        "nixos") distro="nixos" ;;
    esac
    
    echo "$distro:$version:$codename"
}

# System information gathering
gather_system_info() {
    local info_file="$HOME/.cache/wallpaper-engine-sysinfo.txt"
    
    {
        echo "=== SYSTEM INFORMATION ==="
        echo "Date: $(date)"
        echo "Hostname: $(hostname 2>/dev/null || echo 'unknown')"
        echo "Kernel: $(uname -r)"
        echo "Architecture: $(uname -m)"
        echo "Distribution: $(detect_distribution)"
        echo "Shell: $SHELL"
        echo "Desktop Environment: ${XDG_CURRENT_DESKTOP:-Unknown}"
        echo "Session Type: ${XDG_SESSION_TYPE:-Unknown}"
        echo "Python Version: $(python3 --version 2>/dev/null || echo 'Not found')"
        echo "Pip Version: $(pip3 --version 2>/dev/null || echo 'Not found')"
        echo "Available Memory: $(free -h | grep '^Mem:' | awk '{print $2}' 2>/dev/null || echo 'Unknown')"
        echo "Available Disk Space: $(df -h . | tail -1 | awk '{print $4}' 2>/dev/null || echo 'Unknown')"
        echo "CPU Info: $(grep 'model name' /proc/cpuinfo | head -1 | cut -d':' -f2 | xargs 2>/dev/null || echo 'Unknown')"
        echo "GPU Info: $(lspci | grep -i vga | head -1 2>/dev/null || echo 'Unknown')"
        echo "=== END SYSTEM INFORMATION ==="
    } > "$info_file"
    
    log "System information gathered: $info_file"
}

# ============================================================================
# DEPENDENCY MANAGEMENT
# ============================================================================

# Comprehensive dependency checker
check_system_dependencies() {
    print_step "Analyzing system dependencies"
    
    local missing_deps=()
    local python_deps=()
    local system_deps=()
    
    # Check Python version
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
        missing_deps+=("python3>=3.8")
        system_deps+=("python3")
    fi
    
    # Check pip
    if ! command -v pip3 >/dev/null 2>&1; then
        missing_deps+=("pip3")
        system_deps+=("python3-pip")
    fi
    
    # Check system tools
    local tools=("git" "curl" "wget" "unzip" "ffmpeg")
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing_deps+=("$tool")
            system_deps+=("$tool")
        fi
    done
    
    # Check Python modules
    local python_modules=("PySide6" "PIL" "requests")
    for module in "${python_modules[@]}"; do
        if ! python3 -c "import $module" 2>/dev/null; then
            missing_deps+=("python3-$module")
            python_deps+=("$module")
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        print_warning "Missing dependencies detected: ${missing_deps[*]}"
        return 1
    else
        print_success "All system dependencies are satisfied"
        return 0
    fi
}

# Smart package manager detection and installation
install_system_dependencies() {
    local distro_info
    distro_info=$(detect_distribution)
    local distro=$(echo "$distro_info" | cut -d':' -f1)
    
    print_step "Installing system dependencies for $distro"
    
    case "$distro" in
        "debian")
            print_info "Using APT package manager"
            if command -v apt >/dev/null 2>&1; then
                sudo apt update
                sudo apt install -y python3 python3-pip python3-pyside6.qtwidgets python3-pil python3-requests ffmpeg git curl wget unzip
            else
                print_error "APT not found on Debian-based system"
                return 1
            fi
            ;;
        "fedora")
            print_info "Using DNF package manager"
            if command -v dnf >/dev/null 2>&1; then
                sudo dnf install -y python3 python3-pip python3-pyside6 python3-pillow python3-requests ffmpeg git curl wget unzip
            elif command -v yum >/dev/null 2>&1; then
                sudo yum install -y python3 python3-pip python3-pyside6 python3-pillow python3-requests ffmpeg git curl wget unzip
            else
                print_error "Neither DNF nor YUM found on Fedora-based system"
                return 1
            fi
            ;;
        "arch")
            print_info "Using Pacman package manager"
            if command -v pacman >/dev/null 2>&1; then
                sudo pacman -Sy --noconfirm python pyside6 python-pillow python-requests ffmpeg git curl wget unzip
            else
                print_error "Pacman not found on Arch-based system"
                return 1
            fi
            ;;
        "opensuse")
            print_info "Using Zypper package manager"
            if command -v zypper >/dev/null 2>&1; then
                sudo zypper install -y python3 python3-pip python3-pyside6 python3-Pillow python3-requests ffmpeg git curl wget unzip
            else
                print_error "Zypper not found on openSUSE system"
                return 1
            fi
            ;;
        "gentoo")
            print_info "Using Portage package manager"
            print_warning "Gentoo detected - manual compilation may be required"
            sudo emerge -av dev-lang/python dev-python/pip dev-python/pyside6 dev-python/pillow dev-python/requests media-video/ffmpeg
            ;;
        "void")
            print_info "Using XBPS package manager"
            sudo xbps-install -Sy python3 python3-pip python3-pyside6 python3-Pillow python3-requests ffmpeg git curl wget unzip
            ;;
        "alpine")
            print_info "Using APK package manager"
            sudo apk add python3 py3-pip py3-pyside6 py3-pillow py3-requests ffmpeg git curl wget unzip
            ;;
        *)
            print_warning "Unknown distribution: $distro"
            print_info "Attempting universal pip installation"
            install_python_dependencies_pip
            return $?
            ;;
    esac
    
    print_success "System dependencies installed successfully"
}

# Fallback pip installation
install_python_dependencies_pip() {
    print_step "Installing Python dependencies via pip"
    
    local pip_packages=("PySide6" "Pillow" "requests")
    
    for package in "${pip_packages[@]}"; do
        if ! python3 -c "import ${package/Pillow/PIL}" 2>/dev/null; then
            print_info "Installing $package..."
            if pip3 install --user "$package"; then
                print_success "$package installed successfully"
            else
                print_error "Failed to install $package"
                return 1
            fi
        else
            print_success "$package already installed"
        fi
    done
}

# ============================================================================
# INSTALLATION FUNCTIONS
# ============================================================================

# Backup existing installation
backup_existing_installation() {
    if [[ -d "$INSTALL_DIR" ]]; then
        print_step "Backing up existing installation"
        
        if cp -r "$INSTALL_DIR" "$BACKUP_DIR"; then
            print_success "Backup created: $BACKUP_DIR"
            log "Backup created: $BACKUP_DIR"
        else
            print_error "Failed to create backup"
            return 1
        fi
    fi
}

# Create directory structure
create_directory_structure() {
    print_step "Creating directory structure"
    
    # System directories (as root)
    local system_directories=(
        "$INSTALL_DIR"
        "$CONFIG_DIR"
        "$CONFIG_DIR/themes"
        "$CONFIG_DIR/playlists"
        "$CONFIG_DIR/cache"
        "$CONFIG_DIR/logs"
    )
    
    # User directories (as real user)
    local user_directories=(
        "$USER_CONFIG_DIR"
        "$USER_DATA_DIR"
        "$USER_CONFIG_DIR/themes"
        "$USER_CONFIG_DIR/playlists"
        "$USER_CONFIG_DIR/cache"
        "$USER_CONFIG_DIR/logs"
    )
    
    # Create system directories
    for dir in "${system_directories[@]}"; do
        if mkdir -p "$dir"; then
            print_success "Created system directory: $dir"
        else
            print_error "Failed to create system directory: $dir"
            return 1
        fi
    done
    
    # Create user directories as real user
    for dir in "${user_directories[@]}"; do
        if sudo -u "$REAL_USER" mkdir -p "$dir"; then
            print_success "Created user directory: $dir"
        else
            print_error "Failed to create user directory: $dir"
            return 1
        fi
    done
    
    # Set proper permissions
    chown -R "$REAL_USER:$REAL_USER" "$USER_CONFIG_DIR" "$USER_DATA_DIR" 2>/dev/null || true
}

# Copy application files with verification
copy_application_files() {
    print_step "Copying application files"
    
    # Verify source files exist
    local required_files=("main.py" "requirements.txt" "wallpaper-engine.png")
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            print_error "Required file not found: $file"
            return 1
        fi
    done
    
    # Copy files excluding .git directory and other unnecessary files
    print_info "Copying application files (excluding .git and cache files)..."
    
    # Use rsync if available, otherwise use find+cp
    if command -v rsync >/dev/null 2>&1; then
        rsync -av --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store' . "$INSTALL_DIR/"
    else
        # Fallback to find+cp if rsync is not available
        print_warning "rsync not available, using find+cp with exclusions..."
        
        # Create target directory structure first
        find . -type d -not -path './.git*' -not -path './__pycache__*' | while read -r dir; do
            mkdir -p "$INSTALL_DIR/$dir"
        done
        
        # Copy files excluding problematic directories
        find . -type f -not -path './.git*' -not -path './__pycache__*' -not -name '*.pyc' -not -name '.DS_Store' | while read -r file; do
            cp "$file" "$INSTALL_DIR/$file"
        done
    fi
    
    # Set executable permissions
    chmod +x "$INSTALL_DIR/main.py"
    
    # Verify installation
    if [[ -f "$INSTALL_DIR/main.py" ]]; then
        print_success "Application files copied successfully"
    else
        print_error "Installation verification failed"
        return 1
    fi
}

# Create launcher script with advanced features
create_launcher_script() {
    print_step "Creating launcher script"
    
    cat > "$BIN_DIR/wallpaper-engine" << EOF
#!/bin/bash

# Wallpaper Engine Linux Launcher
# Advanced launcher with error handling and logging

set -euo pipefail

readonly INSTALL_DIR="$INSTALL_DIR"
readonly LOG_DIR="\$HOME/.config/wallpaper_engine/logs"
readonly LOG_FILE="\$LOG_DIR/wallpaper-engine-\$(date +%Y%m%d).log"

# Ensure log directory exists
mkdir -p "\$LOG_DIR"

# Logging function
log() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" >> "\$LOG_FILE"
}

# Error handler
error_handler() {
    local exit_code=\$?
    log "ERROR: Wallpaper Engine exited with code \$exit_code"
    echo "❌ Wallpaper Engine encountered an error. Check log: \$LOG_FILE"
    exit \$exit_code
}

# Set error trap
trap error_handler ERR

# Check installation
if [[ ! -d "\$INSTALL_DIR" ]]; then
    echo "❌ Wallpaper Engine not found. Please reinstall."
    exit 1
fi

if [[ ! -f "\$INSTALL_DIR/main.py" ]]; then
    echo "❌ Main application file not found. Please reinstall."
    exit 1
fi

# Change to installation directory
cd "\$INSTALL_DIR"

# Log startup
log "Starting Wallpaper Engine with arguments: \$*"

# Check dependencies
if ! python3 -c "import PySide6, PIL, requests" 2>/dev/null; then
    echo "❌ Python dependencies missing. Please reinstall."
    log "ERROR: Python dependencies missing"
    exit 1
fi

# Launch application
log "Launching main application"
python3 main.py "\$@"

# Log successful exit
log "Wallpaper Engine exited normally"
EOF

    chmod +x "$BIN_DIR/wallpaper-engine"
    print_success "System-wide launcher script created"
}

# Create desktop entry with advanced features
create_desktop_entry() {
    print_step "Creating desktop entry"
    
    # Remove old entries from both system and user directories
    find "$DESKTOP_DIR" -name "*wallpaper*" -type f -delete 2>/dev/null || true
    sudo -u "$REAL_USER" find "$REAL_HOME/.local/share/applications" -name "*wallpaper*" -type f -delete 2>/dev/null || true
    
    # Create system-wide desktop entry
    cat > "$DESKTOP_DIR/wallpaper-engine.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Wallpaper Engine
GenericName=Wallpaper Manager
Comment=Steam Workshop wallpapers for Linux with advanced features
Keywords=wallpaper;steam;workshop;background;desktop;
Exec=$BIN_DIR/wallpaper-engine
Icon=$INSTALL_DIR/wallpaper-engine.png
Terminal=false
Categories=Graphics;Utility;DesktopSettings;
StartupNotify=true
MimeType=image/jpeg;image/png;image/gif;video/mp4;video/webm;
Actions=Settings;Playlist;Workshop;

[Desktop Action Settings]
Name=Settings
Exec=$BIN_DIR/wallpaper-engine --settings
Icon=preferences-system

[Desktop Action Playlist]
Name=Playlist Manager
Exec=$BIN_DIR/wallpaper-engine --playlist
Icon=media-playlist-repeat

[Desktop Action Workshop]
Name=Steam Workshop
Exec=$BIN_DIR/wallpaper-engine --workshop
Icon=applications-internet
EOF

    # Set proper permissions
    chmod 644 "$DESKTOP_DIR/wallpaper-engine.desktop"
    
    # Update desktop database
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    fi
    
    print_success "System-wide desktop entry created with advanced actions"
}

# PATH management
setup_path_environment() {
    print_step "Setting up PATH environment"
    
    # Since we're installing to /usr/local/bin, PATH setup is not needed
    # /usr/local/bin is already in the system PATH
    
    print_info "Using system-wide installation path: $BIN_DIR"
    print_info "No PATH configuration needed - $BIN_DIR is already in system PATH"
    
    # Verify PATH
    if echo "$PATH" | grep -q "/usr/local/bin"; then
        print_success "System PATH already includes /usr/local/bin"
    else
        print_warning "System PATH may not include /usr/local/bin"
    fi
}

# ============================================================================
# VERIFICATION & TESTING
# ============================================================================

# Comprehensive installation verification
verify_installation() {
    print_step "Verifying installation"
    
    local verification_failed=false
    
    # Check directories
    local required_dirs=("$INSTALL_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$CONFIG_DIR")
    for dir in "${required_dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            print_success "Directory exists: $dir"
        else
            print_error "Directory missing: $dir"
            verification_failed=true
        fi
    done
    
    # Check files
    local required_files=(
        "$INSTALL_DIR/main.py"
        "$BIN_DIR/wallpaper-engine"
        "$DESKTOP_DIR/wallpaper-engine.desktop"
    )
    
    for file in "${required_files[@]}"; do
        if [[ -f "$file" ]]; then
            print_success "File exists: $file"
        else
            print_error "File missing: $file"
            verification_failed=true
        fi
    done
    
    # Check executable permissions
    if [[ -x "$BIN_DIR/wallpaper-engine" ]]; then
        print_success "Launcher is executable"
    else
        print_error "Launcher is not executable"
        verification_failed=true
    fi
    
    # Test Python imports
    if python3 -c "import sys; sys.path.insert(0, '$INSTALL_DIR'); import main" 2>/dev/null; then
        print_success "Python application can be imported"
    else
        print_warning "Python application import test failed (may be normal)"
    fi
    
    if $verification_failed; then
        print_error "Installation verification failed"
        return 1
    else
        print_success "Installation verification passed"
        return 0
    fi
}

# Performance test
run_performance_test() {
    print_step "Running performance test"
    
    local start_time=$(date +%s.%N)
    
    # Test launcher script
    if timeout 10s "$BIN_DIR/wallpaper-engine" --version 2>/dev/null; then
        print_success "Launcher performance test passed"
    else
        print_warning "Launcher performance test failed (may be normal)"
    fi
    
    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "unknown")
    
    print_info "Performance test completed in ${duration}s"
}

# ============================================================================
# CLEANUP & FINALIZATION
# ============================================================================

# Cleanup temporary files
cleanup_temporary_files() {
    print_step "Cleaning up temporary files"
    
    local temp_files=(
        "/tmp/wallpaper-engine-*.log"
        "/tmp/wallpaper-engine-*.txt"
        "/tmp/wallpaper-engine-*.tmp"
    )
    
    for pattern in "${temp_files[@]}"; do
        rm -f $pattern 2>/dev/null || true
    done
    
    print_success "Temporary files cleaned up"
}

# Generate installation report
generate_installation_report() {
    local report_file="$CONFIG_DIR/installation-report.txt"
    
    {
        echo "=== WALLPAPER ENGINE INSTALLATION REPORT ==="
        echo "Date: $(date)"
        echo "Installer Version: $SCRIPT_VERSION"
        echo "Installation Directory: $INSTALL_DIR"
        echo "System Information:"
        cat /tmp/wallpaper-engine-sysinfo.txt 2>/dev/null || echo "System info not available"
        echo ""
        echo "Installation Log:"
        cat "$LOG_FILE" 2>/dev/null || echo "Log not available"
        echo "=== END REPORT ==="
    } > "$report_file"
    
    print_success "Installation report generated: $report_file"
}

# ============================================================================
# INTERACTIVE FEATURES
# ============================================================================

# Interactive dependency installation
interactive_dependency_install() {
    if ! check_system_dependencies; then
        echo
        print_warning "Some dependencies are missing."
        echo -e "${YELLOW}Would you like to install them automatically? ${NC}"
        echo -e "${CYAN}1) Yes, install automatically (recommended)${NC}"
        echo -e "${CYAN}2) No, I'll install them manually${NC}"
        echo -e "${CYAN}3) Show installation commands and exit${NC}"
        echo
        
        read -p "Choose an option [1-3]: " -n 1 -r choice
        echo
        
        case $choice in
            1)
                print_info "Installing dependencies automatically..."
                if install_system_dependencies; then
                    print_success "Dependencies installed successfully"
                else
                    print_error "Automatic installation failed"
                    return 1
                fi
                ;;
            2)
                print_info "Continuing without automatic installation..."
                install_python_dependencies_pip
                ;;
            3)
                show_manual_installation_commands
                exit 0
                ;;
            *)
                print_error "Invalid choice"
                return 1
                ;;
        esac
    fi
}

# Show manual installation commands
show_manual_installation_commands() {
    local distro_info
    distro_info=$(detect_distribution)
    local distro=$(echo "$distro_info" | cut -d':' -f1)
    
    print_section "Manual Installation Commands"
    
    case "$distro" in
        "debian")
            echo -e "${CYAN}For Debian/Ubuntu-based systems:${NC}"
            echo "sudo apt update"
            echo "sudo apt install python3 python3-pip python3-pyside6.qtwidgets python3-pil python3-requests ffmpeg git curl wget unzip"
            ;;
        "fedora")
            echo -e "${CYAN}For Fedora/RHEL-based systems:${NC}"
            echo "sudo dnf install python3 python3-pip python3-pyside6 python3-pillow python3-requests ffmpeg git curl wget unzip"
            ;;
        "arch")
            echo -e "${CYAN}For Arch-based systems:${NC}"
            echo "sudo pacman -S python pyside6 python-pillow python-requests ffmpeg git curl wget unzip"
            ;;
        "opensuse")
            echo -e "${CYAN}For openSUSE systems:${NC}"
            echo "sudo zypper install python3 python3-pip python3-pyside6 python3-Pillow python3-requests ffmpeg git curl wget unzip"
            ;;
        *)
            echo -e "${CYAN}For other distributions:${NC}"
            echo "Install Python 3.8+, pip3, and ffmpeg using your package manager"
            echo "Then run: pip3 install --user PySide6 Pillow requests"
            ;;
    esac
    
    echo
    echo -e "${YELLOW}After installing dependencies, run this installer again.${NC}"
}

# ============================================================================
# MAIN INSTALLATION FLOW
# ============================================================================

# Pre-installation checks
pre_installation_checks() {
    print_section "${SHIELD} Pre-Installation Checks"
    
    # Check if running as root (now required)
    if [[ $EUID -ne 0 ]]; then
        print_error "This installer must be run with sudo privileges!"
        print_info "Please run: sudo $0"
        exit 1
    fi
    
    # Get the real user (not root)
    if [[ -n "${SUDO_USER:-}" ]]; then
        readonly REAL_USER="$SUDO_USER"
        readonly REAL_HOME=$(eval echo ~$SUDO_USER)
    else
        print_error "Could not determine the real user. Please run with sudo."
        exit 1
    fi
    
    # Set user directories based on real user
    readonly USER_CONFIG_DIR="$REAL_HOME/.config/wallpaper_engine"
    readonly USER_DATA_DIR="$REAL_HOME/.local/share/wallpaper-engine"
    
    print_info "Installing as root for user: $REAL_USER"
    print_info "Real user home: $REAL_HOME"
    print_info "User config directory: $USER_CONFIG_DIR"
    print_info "User data directory: $USER_DATA_DIR"
    
    # Check available disk space (minimum 100MB)
    local available_space
    available_space=$(df /opt 2>/dev/null | tail -1 | awk '{print $4}' || df / | tail -1 | awk '{print $4}')
    if [[ $available_space -lt 102400 ]]; then  # 100MB in KB
        print_error "Insufficient disk space. At least 100MB required."
        exit 1
    fi
    
    # Check internet connectivity
    if ! ping -c 1 google.com >/dev/null 2>&1; then
        print_warning "No internet connection detected. Some features may not work."
    fi
    
    print_success "Pre-installation checks passed"
}

# Main installation function
main_installation() {
    print_section "${ROCKET} Main Installation"
    
    # Backup existing installation
    backup_existing_installation
    
    # Create directory structure
    create_directory_structure
    
    # Copy application files
    copy_application_files
    
    # Create launcher script
    create_launcher_script
    
    # Create desktop entry
    create_desktop_entry
    
    # Setup PATH environment
    setup_path_environment
    
    print_success "Main installation completed"
}

# Post-installation tasks
post_installation_tasks() {
    print_section "${LIGHTNING} Post-Installation Tasks"
    
    # Verify installation
    verify_installation
    
    # Run performance test
    run_performance_test
    
    # Generate installation report
    generate_installation_report
    
    # Cleanup temporary files
    cleanup_temporary_files
    
    print_success "Post-installation tasks completed"
}

# Installation summary
show_installation_summary() {
    print_section "${STAR} Installation Summary"
    
    echo -e "${GREEN}${CHECK_MARK} System-wide installation completed successfully!${NC}"
    echo
    echo -e "${BOLD}${WHITE}Application Details:${NC}"
    echo -e "  ${CYAN}Name:${NC} $APP_NAME"
    echo -e "  ${CYAN}Version:${NC} $APP_VERSION"
    echo -e "  ${CYAN}Installation Directory:${NC} $INSTALL_DIR"
    echo -e "  ${CYAN}System Configuration:${NC} $CONFIG_DIR"
    echo -e "  ${CYAN}User Configuration:${NC} $USER_CONFIG_DIR"
    echo -e "  ${CYAN}Installed for User:${NC} $REAL_USER"
    echo
    echo -e "${BOLD}${WHITE}How to Launch:${NC}"
    echo -e "  ${CYAN}${DESKTOP} From Application Menu:${NC} Search for 'Wallpaper Engine'"
    echo -e "  ${CYAN}${COMPUTER} From Terminal:${NC} wallpaper-engine"
    echo -e "  ${CYAN}${GEAR} With Options:${NC} wallpaper-engine --help"
    echo
    echo -e "${BOLD}${WHITE}Quick Start:${NC}"
    echo -e "  ${CYAN}1.${NC} Launch the application (no sudo needed for usage)"
    echo -e "  ${CYAN}2.${NC} Browse Steam Workshop wallpapers"
    echo -e "  ${CYAN}3.${NC} Select and apply wallpapers"
    echo -e "  ${CYAN}4.${NC} Create playlists for automatic rotation"
    echo
    echo -e "${BOLD}${WHITE}System Information:${NC}"
    echo -e "  ${CYAN}${INFO} Installation Type:${NC} System-wide (requires sudo)"
    echo -e "  ${CYAN}${INFO} Executable Location:${NC} $BIN_DIR/wallpaper-engine"
    echo -e "  ${CYAN}${INFO} Desktop Entry:${NC} $DESKTOP_DIR/wallpaper-engine.desktop"
    echo
    echo -e "${BOLD}${WHITE}Troubleshooting:${NC}"
    echo -e "  ${CYAN}${INFO} System Logs:${NC} $LOG_FILE"
    echo -e "  ${CYAN}${INFO} User Logs:${NC} $USER_CONFIG_DIR/logs/"
    echo -e "  ${CYAN}${INFO} Installation Report:${NC} $CONFIG_DIR/installation-report.txt"
    echo -e "  ${CYAN}${INFO} Backup Location:${NC} $BACKUP_DIR"
    echo
    echo -e "${GREEN}${FIRE} System-wide installation complete! All users can now access Wallpaper Engine! ${FIRE}${NC}"
}

# ============================================================================
# ERROR HANDLING & RECOVERY
# ============================================================================

# Global error handler
global_error_handler() {
    local exit_code=$?
    local line_number=$1
    
    print_error "Installation failed at line $line_number with exit code $exit_code"
    log "FATAL ERROR: Installation failed at line $line_number with exit code $exit_code"
    
    echo
    print_section "${CROSS_MARK} Installation Failed"
    echo -e "${RED}The installation encountered an error and could not complete.${NC}"
    echo
    echo -e "${YELLOW}Troubleshooting steps:${NC}"
    echo -e "  ${CYAN}1.${NC} Check the log file: $LOG_FILE"
    echo -e "  ${CYAN}2.${NC} Ensure all dependencies are installed"
    echo -e "  ${CYAN}3.${NC} Verify you have sufficient permissions"
    echo -e "  ${CYAN}4.${NC} Check available disk space"
    echo -e "  ${CYAN}5.${NC} Try running the installer again"
    echo
    echo -e "${CYAN}If the problem persists, please report it with the log file.${NC}"
    
    exit $exit_code
}

# Set global error trap
trap 'global_error_handler $LINENO' ERR

# ============================================================================
# MAIN EXECUTION
# ============================================================================

# Show help
show_help() {
    echo "Wallpaper Engine Linux Installer v$SCRIPT_VERSION"
    echo
    echo "Usage: sudo $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --help, -h        Show this help message"
    echo "  --uninstall, -u   Uninstall Wallpaper Engine"
    echo "  --version, -v     Show version information"
    echo
    echo "Examples:"
    echo "  sudo $0           Install Wallpaper Engine"
    echo "  sudo $0 --uninstall  Remove Wallpaper Engine"
    echo
}

# Show version
show_version() {
    echo "Wallpaper Engine Linux Installer"
    echo "Version: $SCRIPT_VERSION"
    echo "Author: Advanced Linux Installer System"
    echo
}

# Uninstall function
uninstall_wallpaper_engine() {
    print_header
    echo -e "${RED}${CROSS_MARK} UNINSTALL MODE${NC}"
    echo
    
    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        print_error "Uninstaller must be run with sudo privileges!"
        print_info "Please run: sudo $0 --uninstall"
        exit 1
    fi
    
    # Get the real user
    if [[ -n "${SUDO_USER:-}" ]]; then
        readonly REAL_USER="$SUDO_USER"
        readonly REAL_HOME=$(eval echo ~$SUDO_USER)
    else
        print_error "Could not determine the real user. Please run with sudo."
        exit 1
    fi
    
    readonly USER_CONFIG_DIR="$REAL_HOME/.config/wallpaper_engine"
    readonly USER_DATA_DIR="$REAL_HOME/.local/share/wallpaper-engine"
    
    print_info "Uninstalling for user: $REAL_USER"
    
    # Confirmation
    echo -e "${YELLOW}${WARNING} This will completely remove Wallpaper Engine from your system.${NC}"
    echo -e "${YELLOW}Are you sure you want to continue? [y/N]${NC}"
    read -r response
    
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        print_info "Uninstall cancelled"
        exit 0
    fi
    
    print_step "Stopping wallpaper processes"
    
    # Kill wallpaper processes
    killall linux-wallpaperengine 2>/dev/null || true
    pkill -f mpvpaper 2>/dev/null || true
    pkill -f "mpv.*wallpaper" 2>/dev/null || true
    
    print_step "Removing system files"
    
    # Remove system directories and files
    rm -rf "$INSTALL_DIR" 2>/dev/null || true
    rm -f "$BIN_DIR/wallpaper-engine" 2>/dev/null || true
    rm -f "$DESKTOP_DIR/wallpaper-engine.desktop" 2>/dev/null || true
    rm -rf "$CONFIG_DIR" 2>/dev/null || true
    rm -f "$LOG_FILE" 2>/dev/null || true
    
    print_step "Removing user files"
    
    # Remove user directories
    sudo -u "$REAL_USER" rm -rf "$USER_CONFIG_DIR" 2>/dev/null || true
    sudo -u "$REAL_USER" rm -rf "$USER_DATA_DIR" 2>/dev/null || true
    
    # Remove from user applications
    sudo -u "$REAL_USER" rm -f "$REAL_HOME/.local/share/applications/wallpaper-engine.desktop" 2>/dev/null || true
    
    # Update desktop database
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
        sudo -u "$REAL_USER" update-desktop-database "$REAL_HOME/.local/share/applications" 2>/dev/null || true
    fi
    
    print_success "Wallpaper Engine uninstalled successfully!"
    print_info "All files and configurations have been removed"
    
    echo
    echo -e "${GREEN}${CHECK_MARK} Uninstall completed successfully!${NC}"
    echo
}

main() {
    # Parse command line arguments
    case "${1:-}" in
        --help|-h)
            show_help
            exit 0
            ;;
        --version|-v)
            show_version
            exit 0
            ;;
        --uninstall|-u)
            uninstall_wallpaper_engine
            exit 0
            ;;
        "")
            # No arguments, proceed with installation
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
    
    # Initialize (pass first argument to check if it's help/version)
    init_logging "${1:-}"
    print_header
    gather_system_info
    
    # Pre-installation
    pre_installation_checks
    
    # Dependency management
    interactive_dependency_install
    
    # Main installation
    main_installation
    
    # Post-installation
    post_installation_tasks
    
    # Show summary
    show_installation_summary
    
    log "Installation completed successfully"
}

# Execute main function
main "$@"
