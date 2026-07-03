# SongSorter

## Overview

SongSorter is a powerful music file organization and management tool designed to help users efficiently sort, organize, and manage their music collections. Built with Python and modern desktop technologies, SongSorter provides a comprehensive solution for music library management with advanced categorization, tagging, and organization features.

## Key Features

- **Automatic Organization**: Automatically sort music files into categorized folders based on metadata
- **Smart Tagging**: Extract and apply tags from ID3 headers and file properties
- **Duplicate Detection**: Identify and handle duplicate music files
- **Metadata Management**: Edit and manage music file metadata (artist, album, title, etc.)
- **Preview Support**: Preview music files with built-in audio player
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Batch Processing**: Process multiple files simultaneously
- **Custom Rules**: Define custom organization rules and sorting patterns

## Technology Stack

| Layer | Technology |
|-------|------------|
| Runtime | Python 3.8+, Tkinter (GUI) |
| Audio Processing | pygame, mutagen |
| File System | os, pathlib, shutil |
| Metadata | mutagen, eyeD3 |
| Data Storage | SQLite, JSON |
| Build Tools | PyInstaller, setuptools |

## Project Structure

```
SongSorter/
├── src/
│   ├── core/           # Core application logic
│   ├── gui/            # Graphical user interface
│   ├── utils/          # Utility functions
│   ├── services/       # Background services
│   └── models/         # Data models
├── assets/             # Icons, images, and other assets
├── tests/             # Test files
├── docs/              # Documentation
├── dist/              # Build output (installers)
└── README.md          # This file
```

## Installation

### System Requirements

- Windows 10 or later (64-bit)
- macOS 10.14 or later
- Linux (Ubuntu, Fedora, Arch Linux)
- Minimum RAM: 2 GB
- Minimum Storage: 200 MB free space

### Installation Steps

#### Windows (Recommended)

```bash
# Clone the repository
# Navigate to the project directory

# Install dependencies
pip install -r requirements.txt

# Run in development mode
python -m src.gui.main

# Build for distribution
pip install pyinstaller
pyinstaller src/gui/main.py --onefile
```

#### Linux/macOS

```bash
# Clone the repository
# Navigate to the project directory

# Install dependencies
pip install -r requirements.txt

# Run in development mode
python -m src.gui.main

# Build for distribution
pip install pyinstaller
pyinstaller src/gui/main.py --onefile
```

## Usage

### Basic Usage

1. **Launch the Application**
   - Double-click the installer or run `python -m src.gui.main`
   - Wait for the application to load

2. **Load Music Library**
   - Click "Load Library" button
   - Select the folder containing your music files
   - Choose scan depth (shallow or deep)

3. **View Library**
   - Browse through categorized music files
   - Use search bar to find specific songs
   - Sort by various criteria (artist, album, title, etc.)

4. **Organize Music**
   - Select files to organize
   - Choose destination folder
   - Apply organization rules

### Advanced Features

- **Batch Processing**: Process multiple files simultaneously
- **Custom Rules**: Define custom organization rules
- **Duplicate Handling**: Detect and handle duplicate files
- **Metadata Editing**: Edit artist, album, title, and other metadata
- **File Renaming**: Automatically rename files based on metadata
- **Playlist Creation**: Create and manage playlists
- **Export/Import**: Export library to file or import from another library

## Configuration

### Configuration File

Create a `config.json` file in the project root:

```json
{
  "music_directory": "C:\\Music\\",
  "supported_formats": ["mp3", "wav", "flac", "aac", "ogg", "m4a", "wma"],
  "default_organization": "artist_album",
  "enable_duplicates_detection": true,
  "auto_rename_duplicates": false,
  "backup_before_organization": true,
  "max_file_size": 100,
  "scan_depth": "deep"
}
```

### Configuration Options

SongSorter supports various configuration options:

- **Library Settings**: Default music directory, supported formats
- **Organization Settings**: Default organization pattern, duplicate handling
- **Backup Settings**: Enable/disable backup before organization
- **Performance Settings**: Maximum file size, scan depth
- **Metadata Settings**: Tag extraction preferences, ID3 frame handling

## Build Targets

### Windows

| Build Type | Output | Description |
|------------|--------|-------------|
| Installer | `dist/SongSorter_Setup.exe` | Standard Windows installer |
| Portable | `dist/SongSorter_Portable.exe` | Portable version without installation |

### Linux/macOS

| Build Type | Output | Description |
|------------|--------|-------------|
| AppImage | `dist/SongSorter.AppImage` | Linux AppImage format |
| DMG | `dist/SongSorter.dmg` | macOS disk image |
| Tar.gz | `dist/SongSorter.tar.gz` | Source tarball |

## Development

### Running in Development Mode

```bash
# Install dependencies
pip install -r requirements.txt

# Run the development server
python -m src.gui.main

# Open GUI application
```

### Building for Production

```bash
# Install build tools
pip install pyinstaller

# Build for production
pyinstaller src/gui/main.py --onefile

# Create installer
pyinstaller src/gui/main.py --noconsole
```

### Testing

```bash
# Run unit tests
python -m pytest tests/

# Run integration tests
python -m pytest tests/integration/

# Run e2e tests
python -m pytest tests/e2e/
```

## Deployment

### Production Deployment

SongSorter can be deployed to various platforms:

- **Windows**: Use PyInstaller for Windows executables
- **macOS**: Deploy to Mac App Store or direct download
- **Linux**: Package for distribution platforms
- **Enterprise**: Deploy via SCCM or other deployment tools

### Docker Deployment

```bash
# Build the Docker image
docker build -t songsorter .

# Run the container
docker run -v "$(pwd)/music:/music" songsorter
```

## Contributing

### Contribution Guidelines

1. **Fork the repository**
2. **Create a feature branch**
3. **Make your changes**
4. **Add tests**
5. **Commit your changes**
6. **Push to your branch**
7. **Create a pull request**

### Code Quality

- Follow PEP 8 for Python code style
- Write comprehensive unit and integration tests
- Keep commit messages clear and descriptive
- Update documentation as needed

## Troubleshooting

### Common Issues

#### Application Won't Start

1. **Check dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Check Python version**
   Ensure Python 3.8+ is installed

3. **Check permissions**
   Ensure the application has permission to access music directory

#### Build Errors

1. **Clean pip cache**
   ```bash
   pip cache purge
   pip install -r requirements.txt
   ```

2. **Check dependencies**
   Ensure all required Python packages are installed

#### Performance Issues

1. **Clear cache**
   Delete temporary files and cache

2. **Check for memory leaks**
   Monitor memory usage during long operations

## Support

### Getting Help

- **GitHub Issues**: Report bugs and request features
- **Documentation**: Check the official documentation
- **Community**: Join the community forums

### Reporting Issues

When reporting an issue, please include:

- **Description of the problem**
- **Steps to reproduce**
- **Expected behavior**
- **Actual behavior**
- **Environment details** (OS version, Python version, etc.)

## License

SongSorter is licensed under the MIT License. See the `LICENSE` file for more details.

## Acknowledgements

- **Python**: For providing a powerful programming language
- **Tkinter**: For GUI development
- **pygame**: For audio processing
- **mutagen**: For ID3 tag handling
- **All contributors**: For making this project better

## Contact

- **Website**: https://songsorter.example.com
- **Email**: support@example.com
- **GitHub**: https://github.com/example/songsorter
- **Twitter**: @songsorter_app

---

*SongSorter - Your Ultimate Music Organization Solution*
