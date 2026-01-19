"""File system scanner for discovering Ableton projects."""

import logging
from typing import Optional, List, Set
from pathlib import Path
from datetime import datetime
import os
import hashlib
import json

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from ..database import get_session, Location, Project, ProjectStatus, Export
from ..utils.paths import is_ableton_project, normalize_path, find_export_folders
from ..utils.logging import get_logger
from ..utils.fuzzy_match import match_export_to_project, normalize_for_comparison
from .als_parser import ALSParser

# Audio file extensions for export detection
AUDIO_EXTENSIONS = {'.wav', '.mp3', '.flac', '.aiff', '.aif', '.ogg', '.m4a'}


class ScanWorker(QThread):
    """Background worker for scanning file systems."""
    
    progress = pyqtSignal(int, int, str)  # current, total, message
    project_found = pyqtSignal(str)        # path
    scan_complete = pyqtSignal(int)        # total found
    error = pyqtSignal(str)                # error message
    
    def __init__(self, location_ids: Optional[List[int]] = None,
                 exclude_patterns: Optional[List[str]] = None,
                 parse_metadata: bool = True):
        super().__init__()
        self.logger = get_logger(__name__)
        
        self.location_ids = location_ids
        self.exclude_patterns = exclude_patterns or []
        self._stop_requested = False
        self._found_count = 0
        self._parse_metadata = parse_metadata
        self._parser = ALSParser() if parse_metadata else None
    
    def run(self) -> None:
        """Execute the scan."""
        try:
            self._found_count = 0
            
            session = get_session()
            try:
                # Get locations to scan
                if self.location_ids:
                    locations = session.query(Location).filter(
                        Location.id.in_(self.location_ids),
                        Location.is_active == True
                    ).all()
                else:
                    locations = session.query(Location).filter(
                        Location.is_active == True
                    ).all()
                
                if not locations:
                    self.logger.warning("No active locations to scan")
                    self.scan_complete.emit(0)
                    return
                
                self.logger.info(f"Starting scan of {len(locations)} location(s)")
                
                # Scan each location
                total_locations = len(locations)
                for idx, location in enumerate(locations):
                    if self._stop_requested:
                        self.logger.info("Scan stopped by user")
                        break
                    
                    self.progress.emit(idx, total_locations, f"Scanning {location.name}...")
                    self.logger.info(f"Scanning location: {location.name} ({location.path})")
                    try:
                        self._scan_location(location, session)
                        self.logger.info(f"Completed location: {location.name} - Found {self._found_count} new project(s) so far")
                    except Exception as e:
                        self.logger.error(f"Error scanning location {location.name}: {e}", exc_info=True)
                        self.error.emit(f"Error scanning {location.name}: {e}")
                    
                    # Update last scan time
                    location.last_scan_time = datetime.utcnow()
                    session.commit()
                
                self.logger.info(f"Scan complete - Total new projects found: {self._found_count}")
                self.scan_complete.emit(self._found_count)
            finally:
                session.close()
                
        except Exception as e:
            error_msg = f"Scan failed: {e}"
            self.logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
    
    def _scan_location(self, location: Location, session) -> None:
        """Scan a single location for projects.
        
        Args:
            location: Location to scan.
            session: Database session.
        """
        path = Path(location.path)
        
        if not path.exists():
            self.progress.emit(0, 0, f"Location not found: {location.path}")
            return
        
        # Get existing projects for this location
        existing_paths: Set[str] = set()
        for project in session.query(Project).filter(
            Project.location_id == location.id
        ).all():
            existing_paths.add(project.file_path)
        
        # Walk the directory tree
        found_paths: Set[str] = set()
        
        for root, dirs, files in os.walk(path):
            if self._stop_requested:
                break
            
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not self._is_excluded(Path(root) / d)]
            
            for filename in files:
                if self._stop_requested:
                    break
                
                file_path = Path(root) / filename
                
                if is_ableton_project(file_path):
                    normalized_path = normalize_path(file_path)
                    found_paths.add(str(file_path))
                    
                    if str(file_path) not in existing_paths:
                        # New project found
                        self._add_project(file_path, location.id, session)
                        self._found_count += 1
                        self.project_found.emit(str(file_path))
                    else:
                        # Update existing project
                        self._update_project(file_path, session)
        
        # Mark missing projects
        missing = existing_paths - found_paths
        for path_str in missing:
            project = session.query(Project).filter(
                Project.file_path == path_str
            ).first()
            if project:
                project.status = ProjectStatus.MISSING
        
        session.commit()
        
        # Auto-scan for exports in this location
        self._scan_exports_for_location(location, session)
    
    def _calculate_file_hash(self, path: Path) -> Optional[str]:
        """Calculate MD5 hash of file for duplicate detection."""
        try:
            hash_md5 = hashlib.md5()
            with open(path, "rb") as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return None
    
    def _add_project(self, path: Path, location_id: int, session) -> None:
        """Add a new project to the database.
        
        Args:
            path: Path to the project file.
            location_id: ID of the containing location.
            session: Database session.
        """
        try:
            stat = path.stat()
            
            # Calculate file hash for duplicate detection
            file_hash = self._calculate_file_hash(path)
            
            project = Project(
                name=path.stem,
                file_path=str(path),
                location_id=location_id,
                file_size=stat.st_size,
                file_hash=file_hash,
                created_date=datetime.fromtimestamp(stat.st_ctime),
                modified_date=datetime.fromtimestamp(stat.st_mtime),
                last_scanned=datetime.utcnow(),
                status=ProjectStatus.LOCAL
            )
            
            # Parse .als metadata if enabled
            if self._parse_metadata and self._parser:
                try:
                    metadata = self._parser.parse(path)
                    if metadata:
                        self._apply_metadata_to_project(project, metadata)
                except Exception as e:
                    # Don't fail project creation if parsing fails
                    print(f"Warning: Failed to parse metadata for {path}: {e}")
            
            session.add(project)
            session.commit()
            
        except Exception as e:
            print(f"Error adding project {path}: {e}")
    
    def _update_project(self, path: Path, session) -> None:
        """Update an existing project's metadata.
        
        Args:
            path: Path to the project file.
            session: Database session.
        """
        try:
            project = session.query(Project).filter(
                Project.file_path == str(path)
            ).first()
            
            if project:
                stat = path.stat()
                project.file_size = stat.st_size
                project.modified_date = datetime.fromtimestamp(stat.st_mtime)
                project.last_scanned = datetime.utcnow()
                project.status = ProjectStatus.LOCAL
                
                # Re-parse metadata if file changed or never parsed
                if self._parse_metadata and self._parser:
                    # Check if file was modified since last parse
                    file_changed = (not project.last_parsed or 
                                  datetime.fromtimestamp(stat.st_mtime) > project.last_parsed)
                    if file_changed:
                        try:
                            metadata = self._parser.parse(path)
                            if metadata:
                                self._apply_metadata_to_project(project, metadata)
                        except Exception as e:
                            # Don't fail update if parsing fails
                            print(f"Warning: Failed to parse metadata for {path}: {e}")
                
        except Exception as e:
            print(f"Error updating project {path}: {e}")
    
    def _apply_metadata_to_project(self, project: Project, metadata) -> None:
        """Apply parsed metadata to a project object.
        
        Args:
            project: Project database object.
            metadata: ProjectMetadata object from parser.
        """
        project.plugins = json.dumps(metadata.plugins) if metadata.plugins else '[]'
        project.devices = json.dumps(metadata.devices) if metadata.devices else '[]'
        project.tempo = metadata.tempo
        project.time_signature = metadata.time_signature
        project.track_count = metadata.track_count
        project.audio_tracks = metadata.audio_tracks
        project.midi_tracks = metadata.midi_tracks
        project.return_tracks = metadata.return_tracks
        project.has_master_track = metadata.master_track
        project.arrangement_length = metadata.arrangement_length
        # Calculate duration in seconds: bars * 4 beats/bar / tempo BPM * 60 sec/min
        if metadata.arrangement_length and metadata.tempo and metadata.tempo > 0:
            # bars * 4 beats/bar / tempo beats/min * 60 sec/min = seconds
            project.arrangement_duration_seconds = (metadata.arrangement_length * 4.0 / metadata.tempo) * 60.0
        else:
            project.arrangement_duration_seconds = None
        project.ableton_version = metadata.ableton_version
        project.sample_references = json.dumps(metadata.sample_references) if metadata.sample_references else '[]'
        project.has_automation = metadata.has_automation
        project.last_parsed = datetime.utcnow()
        
        # Auto-populate export_song_name if not already set
        # Priority: annotation > export filenames > master track name
        if not project.export_song_name:
            # Try annotation first (if it looks like a song name)
            if metadata.annotation:
                anno = metadata.annotation.strip()
                # Only use if short and looks like a title (not a long note)
                if len(anno) < 100 and '\n' not in anno:
                    project.export_song_name = anno
            
            # Try export filenames found in project
            if not project.export_song_name and metadata.export_filenames:
                # Use the first export filename (most recent in Live)
                project.export_song_name = metadata.export_filenames[0]
            
            # Try master track name if it's customized
            if not project.export_song_name and metadata.master_track_name:
                project.export_song_name = metadata.master_track_name
    
    def _scan_exports_for_location(self, location: Location, session) -> None:
        """Scan for audio exports in a location and link to projects.
        
        Args:
            location: Location being scanned.
            session: Database session.
        """
        self.logger.info(f"Scanning for exports in location: {location.name}")
        
        # Get all projects in this location with their names
        projects = session.query(Project).filter(
            Project.location_id == location.id
        ).all()
        
        if not projects:
            return
        
        project_names = [(p.id, p.name) for p in projects]
        
        # Build lookup dicts - both raw and normalized versions
        project_name_to_id = {}
        normalized_name_to_id = {}
        
        for p in projects:
            # Raw name (lowercased)
            project_name_to_id[p.name.lower()] = p.id
            # Normalized name (strips "project", version numbers, etc.)
            normalized = normalize_for_comparison(p.name)
            if normalized:
                normalized_name_to_id[normalized] = p.id
            
            # Also map by export_song_name if set
            if p.export_song_name:
                project_name_to_id[p.export_song_name.lower()] = p.id
                normalized_export = normalize_for_comparison(p.export_song_name)
                if normalized_export:
                    normalized_name_to_id[normalized_export] = p.id
        
        # Get existing export paths to avoid duplicates
        existing_exports = set()
        for export in session.query(Export.export_path).all():
            existing_exports.add(export.export_path)
        
        # Collect all folders to scan for exports
        folders_to_scan: Set[Path] = set()
        location_path = Path(location.path)
        
        # Add location root
        folders_to_scan.add(location_path)
        
        # Add standard export folders at location level
        for subdir in ['Exports', 'Renders', 'Bounces', 'Mixdowns']:
            export_dir = location_path / subdir
            if export_dir.exists():
                folders_to_scan.add(export_dir)
        
        # Add export folders for each project
        for project in projects:
            project_folder = Path(project.file_path).parent
            folders_to_scan.add(project_folder)  # Same folder as .als
            
            # Add nested export folders
            for subdir in ['Exports', 'Renders', 'Bounces', 'Audio', 'Mixdowns']:
                export_dir = project_folder / subdir
                if export_dir.exists():
                    folders_to_scan.add(export_dir)
        
        # Scan each folder for audio files
        exports_found = 0
        exports_linked = 0
        
        for folder in folders_to_scan:
            if self._stop_requested:
                break
            
            if not folder.exists():
                continue
            
            try:
                for item in folder.iterdir():
                    if self._stop_requested:
                        break
                    
                    if item.is_file() and item.suffix.lower() in AUDIO_EXTENSIONS:
                        export_path_str = str(item)
                        
                        # Skip if already in database
                        if export_path_str in existing_exports:
                            continue
                        
                        exports_found += 1
                        
                        # Try to match to a project
                        export_stem = item.stem
                        matched_project_id = None
                        
                        # Try exact match first (case-insensitive)
                        if export_stem.lower() in project_name_to_id:
                            matched_project_id = project_name_to_id[export_stem.lower()]
                        else:
                            # Try normalized exact match (strips "project", version numbers, etc.)
                            normalized_export = normalize_for_comparison(export_stem)
                            if normalized_export in normalized_name_to_id:
                                matched_project_id = normalized_name_to_id[normalized_export]
                                self.logger.debug(f"Normalized match: '{export_stem}' -> '{normalized_export}'")
                            else:
                                # Try fuzzy matching as last resort
                                names_list = [name for _, name in project_names]
                                matches = match_export_to_project(export_stem, names_list, threshold=65.0)
                                if matches:
                                    best_match_name, best_score = matches[0]
                                    # Find the project ID for this name
                                    for pid, pname in project_names:
                                        if pname == best_match_name:
                                            matched_project_id = pid
                                            self.logger.debug(f"Fuzzy matched '{export_stem}' to '{pname}' (score: {best_score:.1f})")
                                            break
                        
                        # Create export record
                        try:
                            stat = item.stat()
                            export = Export(
                                project_id=matched_project_id,
                                export_path=export_path_str,
                                export_name=export_stem,
                                export_date=datetime.fromtimestamp(stat.st_mtime),
                                format=item.suffix.lower().lstrip('.'),
                                file_size=stat.st_size,
                                created_date=datetime.utcnow()
                            )
                            session.add(export)
                            existing_exports.add(export_path_str)
                            
                            if matched_project_id:
                                exports_linked += 1
                        except Exception as e:
                            self.logger.warning(f"Failed to add export {item}: {e}")
                            
            except PermissionError:
                pass
            except Exception as e:
                self.logger.warning(f"Error scanning folder {folder}: {e}")
        
        if exports_found > 0:
            session.commit()
            self.logger.info(f"Found {exports_found} export(s), linked {exports_linked} to projects")
    
    def _is_excluded(self, path: Path) -> bool:
        """Check if a path should be excluded from scanning.
        
        Args:
            path: Path to check.
            
        Returns:
            True if the path should be excluded.
        """
        path_str = str(path)
        name = path.name
        
        # Always exclude hidden directories
        if name.startswith('.'):
            return True
        
        # Check against exclude patterns
        for pattern in self.exclude_patterns:
            # Simple glob matching
            if '**' in pattern:
                pattern_part = pattern.replace('**/', '').replace('**', '')
                if pattern_part.strip('/') in path_str:
                    return True
            elif pattern.startswith('**/'):
                if name == pattern[3:]:
                    return True
            elif name == pattern:
                return True
        
        return False
    
    def stop(self) -> None:
        """Request the scan to stop."""
        self._stop_requested = True


class ProjectScanner(QObject):
    """Main scanner interface for UI integration."""
    
    # Signals (forwarded from worker)
    progress_updated = pyqtSignal(int, int, str)
    project_found = pyqtSignal(str)
    scan_complete = pyqtSignal(int)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent: Optional[QObject] = None, parse_metadata: bool = True):
        super().__init__(parent)
        
        self._worker: Optional[ScanWorker] = None
        self._parse_metadata = parse_metadata
        self._exclude_patterns = [
            "**/Backup/**",
            "**/Ableton Project Info/**",
            "**/.git/**",
            "**/node_modules/**",
            "**/__pycache__/**",
        ]
    
    @property
    def is_running(self) -> bool:
        """Check if a scan is currently running."""
        return self._worker is not None and self._worker.isRunning()
    
    def scan_all(self) -> None:
        """Scan all active locations."""
        self._start_scan(None)
    
    def scan_location(self, location_id: int) -> None:
        """Scan a specific location.
        
        Args:
            location_id: ID of the location to scan.
        """
        self._start_scan([location_id])
    
    def scan_locations(self, location_ids: List[int]) -> None:
        """Scan specific locations.
        
        Args:
            location_ids: List of location IDs to scan.
        """
        self._start_scan(location_ids)
    
    def _start_scan(self, location_ids: Optional[List[int]]) -> None:
        """Start a scan operation.
        
        Args:
            location_ids: List of location IDs, or None for all.
        """
        if self.is_running:
            return
        
        self._worker = ScanWorker(location_ids, self._exclude_patterns, self._parse_metadata)
        self._worker.progress.connect(self.progress_updated.emit)
        self._worker.project_found.connect(self.project_found.emit)
        self._worker.scan_complete.connect(self._on_complete)
        self._worker.error.connect(self.error_occurred.emit)
        self._worker.start()
    
    def _on_complete(self, count: int) -> None:
        """Handle scan completion."""
        self._worker = None
        self.scan_complete.emit(count)
    
    def stop(self) -> None:
        """Stop the current scan."""
        if self._worker:
            self._worker.stop()
            if self._worker.isRunning():
                # Wait for thread to finish
                if not self._worker.wait(5000):  # Wait up to 5 seconds
                    # If still running, try to terminate
                    self._worker.terminate()
                    self._worker.wait(2000)  # Wait a bit more
            # Clean up worker
            self._worker.deleteLater()
            self._worker = None
    
    def set_exclude_patterns(self, patterns: List[str]) -> None:
        """Set the exclude patterns for scanning.
        
        Args:
            patterns: List of glob patterns to exclude.
        """
        self._exclude_patterns = patterns


class GlobalScanner(QObject):
    """Scanner for searching entire file system for projects."""
    
    progress_updated = pyqtSignal(str)  # Current directory
    project_found = pyqtSignal(str)     # Project path
    scan_complete = pyqtSignal(list)    # List of found paths
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self._worker: Optional[GlobalScanWorker] = None
    
    def search(self, drives: Optional[List[str]] = None) -> None:
        """Start a global search for projects.
        
        Args:
            drives: List of drive roots to search, or None for all.
        """
        if self._worker and self._worker.isRunning():
            return
        
        self._worker = GlobalScanWorker(drives)
        self._worker.progress.connect(self.progress_updated.emit)
        self._worker.project_found.connect(self.project_found.emit)
        self._worker.scan_complete.connect(self.scan_complete.emit)
        self._worker.start()
    
    def stop(self) -> None:
        """Stop the current search."""
        if self._worker:
            self._worker.stop()
            self._worker.wait(5000)
            self._worker = None


class GlobalScanWorker(QThread):
    """Worker thread for global file system search."""
    
    progress = pyqtSignal(str)        # Current directory
    project_found = pyqtSignal(str)   # Project path
    scan_complete = pyqtSignal(list)  # List of found paths
    
    def __init__(self, drives: Optional[List[str]] = None):
        super().__init__()
        
        self.drives = drives
        self._stop_requested = False
        self._found_projects: List[str] = []
    
    def run(self) -> None:
        """Execute the global search."""
        import sys
        
        # Determine drives to search
        if self.drives:
            roots = [Path(d) for d in self.drives]
        else:
            if sys.platform == "win32":
                # Search common Windows drives
                roots = []
                for letter in "CDEFGHIJ":
                    drive = Path(f"{letter}:/")
                    if drive.exists():
                        roots.append(drive)
            else:
                # Search common Unix locations
                roots = [Path.home(), Path("/Volumes")]
        
        # Exclude system directories
        system_excludes = {
            "Windows", "System", "Program Files", "Program Files (x86)",
            "Library", "System Volume Information", "$Recycle.Bin",
            "node_modules", ".git", "__pycache__", "venv", ".venv"
        }
        
        for root in roots:
            if self._stop_requested:
                break
            
            self._search_directory(root, system_excludes)
        
        self.scan_complete.emit(self._found_projects)
    
    def _search_directory(self, path: Path, excludes: Set[str]) -> None:
        """Recursively search a directory."""
        if self._stop_requested:
            return
        
        try:
            self.progress.emit(str(path))
            
            for item in path.iterdir():
                if self._stop_requested:
                    break
                
                if item.is_file() and is_ableton_project(item):
                    self._found_projects.append(str(item))
                    self.project_found.emit(str(item))
                    
                elif item.is_dir() and item.name not in excludes:
                    # Skip hidden directories
                    if not item.name.startswith('.'):
                        self._search_directory(item, excludes)
                        
        except PermissionError:
            pass  # Skip directories we can't access
        except Exception as e:
            pass  # Skip on any other error
    
    def stop(self) -> None:
        """Request the search to stop."""
        self._stop_requested = True
