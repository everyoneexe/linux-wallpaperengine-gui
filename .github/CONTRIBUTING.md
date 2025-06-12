# Contributing to Linux Wallpaper Engine

Thank you for your interest in contributing to Linux Wallpaper Engine! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/linux-wallpaper-engine.git`
3. Install dependencies: `pip3 install -r requirements.txt`
4. Make sure you have required system packages: `ffmpeg`, `swww`

## Development Setup

```bash
# Install Python dependencies
pip3 install PySide6 psutil

# Install system dependencies (Ubuntu/Debian)
sudo apt install python3 python3-pip ffmpeg swww

# Run the application
python3 main.py
```

## Code Style

- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and concise
- Use English for all code, comments, and documentation

## Submitting Changes

1. Create a new branch for your feature: `git checkout -b feature-name`
2. Make your changes and test thoroughly
3. Commit with clear, descriptive messages
4. Push to your fork: `git push origin feature-name`
5. Create a Pull Request

## Testing

- Test your changes on multiple Linux distributions if possible
- Test with different desktop environments (GNOME, KDE, Hyprland, etc.)
- Ensure existing functionality still works
- Test with various wallpaper formats (images, videos, GIFs)

## Reporting Issues

- Use the issue templates provided
- Include system information (OS, desktop environment, Python version)
- Provide clear reproduction steps
- Add screenshots when relevant

## Areas for Contribution

- **Bug fixes**: Check the issues tab for reported bugs
- **New features**: Desktop environment support, wallpaper formats, UI improvements
- **Documentation**: README improvements, code documentation
- **Testing**: Cross-platform testing, edge case testing
- **Translations**: UI text translations (if internationalization is added)

## Questions?

Feel free to open an issue for questions or join discussions in existing issues.

Thank you for contributing! 🎉