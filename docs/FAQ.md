# Frequently Asked Questions (FAQ)

Common questions and answers about Ableton Hub.

## Installation

### Do I need to know Python to use Ableton Hub?

No! While Ableton Hub is built with Python (programming language), you don't need to know Python to use it. You just need Python installed on your computer, which most Macs already have. See the [Installation Guides](INSTALLATION_MAC.md) for help.

### Which installation method should I use?

**Method 1 (pip install from GitHub)** is recommended for most users - it's the easiest and automatically handles everything. **Method 2 (download source)** is good if you want more control or prefer to see the source code.

### Do I need to install Python separately?

- **macOS**: Most Macs come with Python already installed. Check with `python3 --version` in Terminal.
- **Windows**: You'll likely need to install Python from [python.org](https://www.python.org/downloads/). Make sure to check "Add Python to PATH" during installation.

### What's a virtual environment and do I need it?

A virtual environment (venv) is an isolated Python environment that keeps your project's dependencies separate from other Python projects. It's recommended for Method 2 (source installation) but not required for Method 1 (pip install). Think of it as a separate container for your project's Python packages.

## Using the Application

### Why don't I see any projects?

You need to:
1. Add at least one location (folder containing `.als` files)
2. Click "Scan" to search for projects
3. Wait for the scan to complete

Projects won't appear until you've scanned at least one location.

### How do I add multiple project folders?

Click "Add Location" multiple times and select different folders. Each folder becomes a separate location that you can scan independently or all together.

### Can I scan network drives or cloud storage?

Yes! When adding a location, choose "Network" or "Cloud" as the location type. Note that scanning network drives may be slower than local drives.

### What happens if I move or delete a project file?

On the next scan, Ableton Hub will mark the project as "MISSING". You can:
- View missing projects: View → Show Missing Projects
- Clean them up: Tools → Clean Up Missing Projects
- The project file itself isn't deleted - only the database record

### How do I change which Ableton Live version opens projects?

Right-click a Live installation in the sidebar → "Set as Favorite". Projects will open with your favorite version by default. You can also right-click any project → "Open With" → select a specific version.

### What are backup projects?

Backup projects are `.als` files in Backup folders or with "backup" in the filename. These are automatically excluded from the main project grid to keep things clean. You can view and launch them from the Project Properties dialog.

## Collections and Organization

### What's the difference between a Collection and a Smart Collection?

- **Collection**: You manually add projects to it. Like a playlist.
- **Smart Collection**: Automatically includes projects based on rules (tags, tempo, date, etc.). Updates automatically as your projects change.

### Can I have a project in multiple collections?

Yes! Projects can belong to multiple collections at the same time.

### How do tags work?

Tags are labels you can add to projects to categorize them. You can:
- Create tags with colors for visual organization
- Filter projects by tags
- Use tags in Smart Collection rules
- Right-click a project → "Edit Tags" to add/remove tags

### What are favorites?

Favorites are projects you've marked as important (💎 icon). They're just a way to mark special projects - you can filter by favorites or use them in Smart Collections.

## Scanning and Performance

### How long does scanning take?

It depends on:
- Number of projects (more projects = longer scan)
- Number of subfolders (deeper folder structure = longer scan)
- Location type (network drives are slower than local drives)
- First scan is usually slower than subsequent scans

A typical scan might take 1-5 minutes for 100-500 projects on a local drive.

### Can I use the app while scanning?

Yes, but it's best to wait until scanning completes to ensure all projects are indexed properly.

### Why is scanning slow?

- Large number of projects
- Deep folder structures
- Network drives (slower than local)
- First scan (needs to read all project files)

Try scanning locations one at a time instead of all at once.

### Does scanning modify my project files?

No! Scanning is read-only. Ableton Hub only reads `.als` files to extract metadata. It never modifies your project files.

## Exports

### How does export detection work?

Ableton Hub automatically searches for exported audio files (WAV, MP3, etc.) in:
- The same folder as the project
- Common export folders (Exports, Renders, Bounces, Mixdowns)
- Location root folders

It uses fuzzy matching (approximate string matching) to link exports to projects even if filenames don't match exactly.

### Why don't I see exports for some projects?

- Exports might be in a different location
- Export filenames might be too different from project names
- Exports might not exist yet
- Try setting a custom "Export Song Name" in project properties to improve matching

### Can I play exports in Ableton Hub?

Yes! Click a project card with a 🔊 icon to play exports. Click again to cycle through multiple exports. For full controls, view the project details panel.

## Technical Questions

### Where is my data stored?

All data is stored locally on your computer:

**macOS:**
- Config & Database: `~/Library/Application Support/AbletonHub/`
- Thumbnail Cache: `~/Library/Caches/AbletonHub/`

**Windows:**
- Config & Database: `%APPDATA%\AbletonHub\`
- Thumbnail Cache: `%LOCALAPPDATA%\AbletonHub\cache\`

**Linux:**
- Config & Database: `~/.local/share/AbletonHub/`
- Thumbnail Cache: `~/.cache/AbletonHub/`

### Does Ableton Hub send data to the internet?

No! Everything is stored locally. Ableton Hub doesn't connect to any external servers or send any data over the network.

### What's a SQLite database?

SQLite is a file-based database (like a spreadsheet) that stores all your project metadata. It's stored locally on your computer and enables fast searching. You don't need to know anything about it to use Ableton Hub.

### Can I backup my Ableton Hub data?

Yes! The database file is in your application data directory (see above). You can copy it to backup your indexed projects. Settings are stored in a JSON (JavaScript Object Notation) config file in the same location.

## Troubleshooting

### The app won't start

- Check that Python 3.11+ is installed: `python --version` or `python3 --version`
- If using source installation, make sure virtual environment is activated
- Check Terminal/Command Prompt for error messages
- Try reinstalling: `pip install --upgrade git+https://github.com/yourusername/ableton-hub.git`

### Projects aren't appearing after scan

- Make sure `.als` files are actually in the scanned folders
- Check that locations are active (not disabled) in sidebar
- Try rescanning: File → Scan All Locations
- Check View → Show Missing Projects to see if projects were marked as missing
- Look at status bar for error messages

### Can't open projects in Live

- Check that Live installations are detected in sidebar
- Right-click Live version → Set as Favorite
- Or right-click project → Open With → Select version
- Make sure Live is actually installed and accessible

### Search isn't working

- Make sure scan completed successfully
- Try a simple search first (just project name)
- Check status bar for errors
- Try rescanning if search seems incomplete

### Audio playback not working

- Make sure you have exported audio files (WAV, MP3, etc.)
- Check that exports are linked to projects (look for 🔊 icon)
- On Linux, you may need audio codecs: `sudo apt-get install gstreamer1.0-plugins-base gstreamer1.0-plugins-good`
- Try clearing thumbnail cache: Tools → Clear Thumbnail Cache

## Getting Help

### Where can I get more help?

- **[First Time Setup Guide](FIRST_TIME_SETUP.md)** - Detailed walkthrough for new users
- **[Quick Reference](QUICK_REFERENCE.md)** - Common tasks and shortcuts
- **[Installation Guides](INSTALLATION_MAC.md)** - Platform-specific installation help
- **[Main README](../README.md)** - Complete documentation
- **GitHub Issues** - Report bugs or request features

### How do I report a bug?

Open an issue on GitHub with:
- What you were trying to do
- What happened (error messages if any)
- Your operating system and Python version
- Steps to reproduce the problem

### Can I request a feature?

Yes! Open an issue on GitHub with your feature request. We welcome suggestions!

## Still Have Questions?

If your question isn't answered here:
1. Check the [Troubleshooting section](../README.md#-troubleshooting) in the main README
2. Search existing GitHub issues
3. Open a new GitHub issue with your question
