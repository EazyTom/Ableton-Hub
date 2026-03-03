# Contributing to Ableton Hub

Thank you for your interest in contributing to Ableton Hub! This guide will help you get started with development.

## Getting Started

### For External Contributors (Fork Workflow)

If you don't have write access to the repository:

1. **Fork the repository** on GitHub (click the "Fork" button at the top of the repository page)
   - This creates your own copy of the repository under your GitHub account

2. **Clone your fork** (not the original repository):
   ```bash
   git clone https://github.com/YOUR-USERNAME/ableton-hub.git
   cd ableton-hub
   ```
   Replace `YOUR-USERNAME` with your GitHub username.

3. **Add the original repository as an upstream remote** (to keep your fork updated):
   ```bash
   git remote add upstream https://github.com/EazyTom/ableton-hub.git
   ```

### For Collaborators with Write Access (Branch Workflow)

If you have write access to the repository:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/EazyTom/ableton-hub.git
   cd ableton-hub
   ```

**Note**: If downloading as ZIP instead of using git clone, extract the ZIP and navigate to the `Ableton-Hub-main` folder.

3. **Create a virtual environment** (isolated Python environment):
   ```bash
   # macOS
   python3 -m venv venv
   source venv/bin/activate
   
   # Windows
   python -m venv venv
   venv\Scripts\activate
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Install development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

6. **Run the application**:
   ```bash
   python -m src.main
   ```

## Development Workflow

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/amazing-feature
   ```

2. **Make your changes**

3. **Add tests if applicable**

4. **Ensure all tests pass**:
   ```bash
   pytest
   ```

5. **Format code**:
   ```bash
   black src tests && ruff check src tests --fix
   ```

6. **Commit your changes**:
   ```bash
   git commit -m 'Add amazing feature'
   ```

7. **Push to your branch**:
   - **If you forked**: `git push origin feature/amazing-feature` (pushes to your fork)
   - **If you have write access**: `git push origin feature/amazing-feature` (pushes to main repo)

8. **Open a Pull Request**:
   - **If you forked**: Go to the original repository on GitHub and click "New Pull Request", then select your fork and branch
   - **If you have write access**: Go to the repository on GitHub and click "New Pull Request", then select your branch

## Code Style

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Write docstrings for all public functions and classes
- Keep functions focused and single-purpose

### Formatting

We use `black` for code formatting and `ruff` for linting:

```bash
# Format code
black src tests

# Lint and auto-fix
ruff check src tests --fix
```

## Testing

### Running Tests

Run the test suite:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=src --cov-report=html
```

### Pre-Release Validation

Before every new version release, run the comprehensive release validation to ensure functionality:

```bash
# Run full release validation (recommended before release)
python tests/test_release.py --verbose

# Windows (using batch file)
scripts\test_release.bat --verbose

# Skip code quality checks (faster)
python tests/test_release.py --skip-code-quality

# Skip ML tests (faster, less comprehensive)
python tests/test_release.py --skip-ml
```

The release validation validates:
- ✅ Code quality (ruff, mypy, black)
- ✅ All unit tests pass
- ✅ Core functionality (imports, database, scanner)
- ✅ Deep extraction (parser, plugins, devices, tempo, key, markers)
- ✅ ML features (feature extraction, similarity, clustering)
- ✅ Live 12 compatibility

The release validation script is located at `tests/test_release.py` and can be run directly.

## Architecture

### Overview

The application follows a layered architecture:

**UI Layer (PyQt6)**
- Main Window orchestrates all UI components
- Sidebar Navigation provides access to locations, collections, and Live installations
- Project Grid/List View displays projects with multiple view modes
- Search & Filter Bar enables full-text search and advanced filtering
- Collection View manages static and smart collections
- Health Dashboard visualizes project health metrics

**Service Layer**
- Project Scanner discovers and indexes `.als` files
- File System Watcher monitors for real-time changes
- ALS Parser extracts metadata from project files
- Live Version Detector finds installed Ableton Live versions
- Live Launcher opens projects with specific Live versions
- Link Network Scanner discovers Ableton Link devices
- Export Tracker identifies and links exported audio files
- Smart Collections creates rule-based dynamic collections
- Duplicate Detector finds duplicate projects using hash comparison
- Health Calculator computes project health metrics
- Similarity Analyzer finds similar projects using Jaccard similarity and multi-metric analysis
- Recommendation Engine provides project recommendations based on similarity
- Audio Player provides in-app playback of exported audio
- Archive Service handles project backup and archiving

**Data Storage**
- SQLite Database with FTS5 stores all project metadata and enables full-text search
- Configuration stores user preferences and settings
- Thumbnail Cache stores generated waveform previews

**External Resources**
- `.als` Project Files are read-only parsed for metadata
- Exported Audio Files are linked to projects and can be played
- Ableton Live Installations are detected and used for launching projects
- Ableton Link Network is monitored for device discovery

**Data Flow**
- UI components interact with services, which read/write to the database
- Scanner and Watcher monitor project files and update the database
- Services like Export Tracker and Archive Service interact with both files and database
- All user preferences and window state are persisted in configuration

### Project Structure

```
ableton_hub/
├── src/
│   ├── main.py                     # Application entry point
│   ├── app.py                      # Main QApplication setup
│   ├── config.py                   # Configuration manager
│   ├── database/                   # SQLAlchemy models and migrations
│   │   ├── models.py               # ORM models
│   │   ├── db.py                   # Database connection and setup
│   │   └── migrations.py           # Schema migrations
│   ├── services/                   # Business logic
│   │   ├── scanner.py              # File system scanner
│   │   ├── watcher.py              # File system watcher
│   │   ├── als_parser.py           # .als file parser
│   │   ├── live_detector.py        # Live version detection
│   │   ├── live_launcher.py        # Live launcher
│   │   ├── link_scanner.py         # Ableton Link discovery
│   │   ├── export_tracker.py       # Export tracking
│   │   ├── smart_collections.py   # Smart collection rules
│   │   ├── duplicate_detector.py  # Duplicate detection
│   │   ├── health_calculator.py    # Health metrics
│   │   ├── audio_preview.py        # Audio preview generation
│   │   ├── audio_player.py         # In-app audio playback
│   │   └── archive_service.py      # Project backup/archive
│   ├── ui/                         # PyQt6 UI components
│   │   ├── main_window.py          # Main application window
│   │   ├── theme.py                # Dark Ableton theme
│   │   ├── widgets/                # Reusable UI widgets
│   │   └── dialogs/                # Modal dialogs
│   └── utils/                      # Utility functions
├── tests/                          # Test suite
├── src/resources/                 # Icons, images, styles, sfx
│   ├── images/                     # Application images
│   ├── icons/                      # Application icons
│   └── styles/                     # Stylesheets
├── docs/                           # Documentation
├── requirements.txt                # Python dependencies
├── pyproject.toml                  # Project configuration
└── README.md                       # Main documentation
```

## Application Data Locations

The application stores data in platform-specific locations:

**Windows:**
- Config & Database: `%APPDATA%\AbletonHub\`
- Thumbnail Cache: `%LOCALAPPDATA%\AbletonHub\cache\`

**macOS:**
- Config & Database: `~/Library/Application Support/AbletonHub/`
- Thumbnail Cache: `~/Library/Caches/AbletonHub/`

**Linux:**
- Config & Database: `~/.local/share/AbletonHub/`
- Thumbnail Cache: `~/.cache/AbletonHub/`

## Database

The application uses SQLite with FTS5 (Full-Text Search) for project metadata. The database file is located in the application data directory (see above) and is automatically created and migrated on first run.

## Configuration

User preferences, window state, and settings are stored in a JSON configuration file in the application data directory. The configuration is automatically loaded and saved.

## Version Management

The application version uses a **single source of truth** pattern:

**To release a new version:**
1. Update `pyproject.toml` → `[project]` → `version`
2. Update `src/__init__.py` → `WHATS_NEW` dictionary with new features

**How it works:**
- `pyproject.toml` defines the package version
- `src/__init__.py` reads from `importlib.metadata` when installed, or uses fallback
- `src/app.py` and `src/ui/main_window.py` import `__version__` from the package
- The About dialog pulls "What's New" content from `src/__init__.py` → `get_whats_new_html()`

> **Note**: The "What's New" section is maintained in `src/__init__.py` and displayed in the in-app About dialog. Feature lists in the README are updated as needed for documentation.

## Technical Details

### .als File Parsing

The application parses Ableton Live Set (`.als`) files to extract metadata. The parser reads:
- **Project Information**: Name, Live version, creation/modification dates
- **Tempo & Time Signature**: Current song tempo and time signature
- **Musical Key & Scale**: Global project key/scale and clip-level key/scale information
- **Track Information**: Audio tracks, MIDI tracks, return tracks, master track
- **Device & Plugin Data**: All devices and plugins used in the project
- **Arrangement Data**: Arrangement length (bars), automation status
- **Sample References**: Linked audio files and samples

The parser handles `.als` files from Live 9.x through Live 12.x. The `.als` format is XML-based, and the parser uses standard XML parsing with error handling for malformed files.

**Key/Scale Detection**: The parser extracts musical key and scale information from both global project settings and clip-level settings. Priority is given to the global key/scale setting, with fallback to clip scales if all clips agree.

### Live Version Compatibility

- **Detected Versions**: Automatically detects Live 9.x, 10.x, 11.x, and 12.x installations
- **Launch Support**: Can launch projects with any detected Live version
- **Version-Specific Features**: Some metadata extraction may vary by Live version

### Ableton Link Integration

The application includes Ableton Link network discovery using the `zeroconf` library. It can:
- Discover devices on the Link network
- Monitor Link network status
- Display device information (name, IP address)

This does not interfere with Live's Link functionality and operates in read-only mode.

### Technical Stack

- **UI Framework**: PyQt6 (Qt 6.6+) for cross-platform GUI
- **Database**: SQLite with FTS5 for full-text search
- **Async Operations**: `qasync` for async/await support with Qt event loop
- **File Watching**: `watchdog` for real-time file system monitoring
- **Audio Playback**: Qt Multimedia (QMediaPlayer) for cross-platform audio preview

### Architecture Pattern

The application follows a clean architecture pattern:
- **UI Layer**: PyQt6 widgets and dialogs (presentation layer)
- **Service Layer**: Business logic and domain services
- **Data Layer**: SQLAlchemy ORM with repository pattern
- **Utils**: Cross-platform utilities and helpers

This separation allows for easy testing and future enhancements without major refactoring.

## Default Project Locations

The application can automatically detect default Ableton project folders (only existing directories are suggested):

**macOS:**
- `~/Music/Ableton/`
- `~/Documents/Ableton/`
- `~/Library/Application Support/Ableton/`
- `~/Music/Ableton/User Library/`

**Windows:**
- `%USERPROFILE%\Documents\Ableton\`
- `%USERPROFILE%\Music\Ableton\`
- `%APPDATA%\Ableton\`
- `%USERPROFILE%\Documents\Ableton\User Library\`

**Linux:**
- `~/Music/Ableton/`
- `~/Documents/Ableton/`

> **Note**: Live installation detection (for launching projects) searches different locations than project folders. The application automatically detects installed Live versions from standard installation paths.

## Data Privacy & Security

- **Local-Only Storage**: All data is stored locally; no cloud sync or external services
- **No Network Communication**: The application does not send any data to external servers
- **Read-Only Access**: The application only reads `.als` files and does not modify them
- **Export Detection**: Uses fuzzy matching to link exported audio files to projects (no modification of export files)

## Roadmap & Planning

Before contributing new features, please review the project roadmap:

- **[Feature Development Status](docs/FEATURE_DEVELOPMENT.md)** - Complete list of implemented features and what's planned
- **[Planned Features Roadmap](docs/PLANNED_FEATURES.plan)** - Detailed implementation plans for future features with priorities, database schemas, and UI layouts

If you'd like to work on a planned feature, please open an issue first to discuss the approach.

## Questions?

If you have questions about contributing, please:
- Open an issue on GitHub
- Check existing issues and discussions
- Review the [README.md](README.md) for user-facing documentation

Thank you for contributing to Ableton Hub! 🎵
