"""Cross-platform path utilities for Ableton Hub."""

import os
import sys
from pathlib import Path
from typing import List


def get_app_data_dir() -> Path:
    """Get the application data directory for storing config and database.
    
    Returns:
        Path to the app data directory (created if it doesn't exist).
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    
    app_dir = base / "AbletonHub"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_database_path() -> Path:
    """Get the path to the SQLite database file.
    
    Returns:
        Path to the database file.
    """
    return get_app_data_dir() / "ableton_hub.db"


def get_config_path() -> Path:
    """Get the path to the configuration JSON file.
    
    Returns:
        Path to the config file.
    """
    return get_app_data_dir() / "config.json"


def get_thumbnail_cache_dir() -> Path:
    """Get the path to the thumbnail cache directory.
    
    Returns:
        Path to the thumbnail cache directory (created if it doesn't exist).
    """
    cache_dir = get_app_data_dir() / "thumbnails"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_default_locations() -> List[Path]:
    """Get default Ableton project folder locations based on the OS.
    
    Returns:
        List of default paths that may contain Ableton projects.
    """
    locations = []
    
    if sys.platform == "win32":
        # Windows default locations
        user_profile = Path(os.environ.get("USERPROFILE", Path.home()))
        appdata = Path(os.environ.get("APPDATA", user_profile / "AppData" / "Roaming"))
        
        locations.extend([
            user_profile / "Documents" / "Ableton",
            user_profile / "Music" / "Ableton",
            appdata / "Ableton",
            user_profile / "Documents" / "Ableton" / "User Library",
        ])
    elif sys.platform == "darwin":
        # macOS default locations
        home = Path.home()
        locations.extend([
            home / "Music" / "Ableton",
            home / "Documents" / "Ableton",
            home / "Library" / "Application Support" / "Ableton",
            home / "Music" / "Ableton" / "User Library",
        ])
    else:
        # Linux (if Ableton runs via Wine or similar)
        home = Path.home()
        locations.extend([
            home / "Music" / "Ableton",
            home / "Documents" / "Ableton",
        ])
    
    # Filter to only existing directories
    return [loc for loc in locations if loc.exists()]


def normalize_path(path: Path | str) -> str:
    """Normalize a path for storage in the database.
    
    Converts to forward slashes for cross-platform compatibility.
    
    Args:
        path: The path to normalize.
        
    Returns:
        Normalized path string with forward slashes.
    """
    if isinstance(path, str):
        path = Path(path)
    return path.as_posix()


def denormalize_path(path_str: str) -> Path:
    """Convert a normalized path string back to a Path object.
    
    Args:
        path_str: The normalized path string from the database.
        
    Returns:
        Path object suitable for the current OS.
    """
    return Path(path_str)


def get_relative_path(path: Path, base: Path) -> str | None:
    """Get the relative path from a base directory.
    
    Args:
        path: The full path.
        base: The base directory.
        
    Returns:
        Relative path string or None if path is not under base.
    """
    try:
        return normalize_path(path.relative_to(base))
    except ValueError:
        return None


def is_ableton_project(path: Path) -> bool:
    """Check if a file is an Ableton Live project.
    
    Args:
        path: Path to check.
        
    Returns:
        True if the file is an Ableton project (.als file).
    """
    return path.is_file() and path.suffix.lower() == ".als"


def get_resources_path() -> Path:
    """Get the path to the resources directory.
    
    Works both in development and when installed via pip.
    
    Returns:
        Path to the resources directory.
    """
    # Resources are now inside the src package: src/resources/
    # This works both in development and when installed via pip
    current_file = Path(__file__)
    # Go up from src/utils/paths.py to src, then into resources
    resources_path = current_file.parent.parent / "resources"
    
    if resources_path.exists():
        return resources_path
    
    # Fallback: try the old location (ableton_hub/resources/) for development
    old_resources_path = current_file.parent.parent.parent / "resources"
    if old_resources_path.exists():
        return old_resources_path
    
    # Last resort: return the expected path even if it doesn't exist
    return resources_path


def get_project_folder(project_path: Path) -> Path:
    """Get the parent folder of a project file.
    
    This is typically the folder containing the .als file and 
    associated Samples, Backup folders, etc.
    
    Args:
        project_path: Path to the .als file.
        
    Returns:
        Path to the project folder.
    """
    return project_path.parent


def find_backup_files(project_path: Path) -> List[Path]:
    """Find all backup .als files for a project.
    
    Searches for backup files in:
    - Backup folder within the project folder
    - Any .als files with 'backup' in the name or timestamp patterns
    
    Args:
        project_path: Path to the main .als project file.
        
    Returns:
        List of backup .als file paths, sorted by modification time (newest first).
    """
    backups = []
    project_folder = get_project_folder(project_path)
    
    # Look in Backup folder
    backup_dir = project_folder / 'Backup'
    if backup_dir.exists() and backup_dir.is_dir():
        for backup_file in backup_dir.glob('*.als'):
            if backup_file.is_file():
                backups.append(backup_file)
    
    # Also check for .als files with backup indicators in the project folder
    # (but not in subdirectories to avoid duplicates)
    for als_file in project_folder.glob('*.als'):
        if als_file == project_path:
            continue  # Skip the main project file
        # Check if filename suggests it's a backup
        name_lower = als_file.name.lower()
        if 'backup' in name_lower or '[' in als_file.name:
            if als_file not in backups:
                backups.append(als_file)
    
    # Sort by modification time (newest first)
    return sorted(backups, key=lambda p: p.stat().st_mtime, reverse=True)


def find_export_folders(project_path: Path, location_path: Path = None) -> List[Path]:
    """Find common export folder locations relative to a project.
    
    Searches for audio exports in:
    - The same folder as the .als file (for exports with matching names)
    - Standard export subfolders (Exports, Renders, Bounces, Audio)
    - Parent directory export folders
    - Location root folder (if provided)
    
    Args:
        project_path: Path to the .als file.
        location_path: Optional root location path to also search.
        
    Returns:
        List of existing export folder paths (may include the project folder itself).
    """
    project_folder = get_project_folder(project_path)
    possible_exports = [
        # Same folder as the .als file (for "MySong.als" + "MySong.wav")
        project_folder,
        # Standard export subfolders
        project_folder / "Exports",
        project_folder / "Renders", 
        project_folder / "Bounces",
        project_folder / "Audio",
        project_folder / "Mixdowns",
        # Parent directory
        project_folder.parent / "Exports",
        project_folder.parent / "Renders",
        project_folder.parent / "Bounces",
    ]
    
    # Include location root if provided
    if location_path:
        loc_path = Path(location_path) if isinstance(location_path, str) else location_path
        if loc_path.exists():
            possible_exports.extend([
                loc_path,  # Location root itself
                loc_path / "Exports",
                loc_path / "Renders",
                loc_path / "Bounces",
            ])
    
    # Also check user's common export locations
    home = Path.home()
    possible_exports.extend([
        home / "Music" / "Exports",
        home / "Music" / "Renders",
        home / "Documents" / "Exports",
    ])
    
    # Remove duplicates while preserving order, filter to existing
    seen = set()
    result = []
    for folder in possible_exports:
        if folder.exists() and folder not in seen:
            seen.add(folder)
            result.append(folder)
    
    return result
