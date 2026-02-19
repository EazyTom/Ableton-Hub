"""Worker for scanning a location for audio files in background thread."""

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from ...services.export_tracker import AUDIO_EXTENSIONS


class AudioScanWorker(QThread):
    """Background worker for recursively scanning a location for audio files."""

    file_found = pyqtSignal(str, int, float)  # path, size, mtime
    scan_complete = pyqtSignal(int)  # total count

    def __init__(self, location_path: Path):
        """Initialize the audio scan worker.

        Args:
            location_path: Root path to scan recursively for audio files.
        """
        super().__init__()
        self._location_path = Path(location_path)
        self._stop_requested = False
        self._found_count = 0

    def run(self) -> None:
        """Execute the scan."""
        self._stop_requested = False
        self._found_count = 0

        if not self._location_path.exists() or not self._location_path.is_dir():
            self.scan_complete.emit(0)
            return

        self._scan_folder(self._location_path)
        self.scan_complete.emit(self._found_count)

    def _is_excluded(self, path: Path) -> bool:
        """Check if a path should be excluded from scanning.

        Skips Backup folders, .git, Ableton Project Info, etc.
        """
        path_str = str(path).replace("\\", "/")
        name = path.name

        if name.startswith("."):
            return True

        exclude_patterns = [
            "/Backup/",
            "\\Backup\\",
            "/Samples/",
            "\\Samples\\",
            "/.git/",
            "\\.git\\",
            "/Ableton Project Info/",
            "\\Ableton Project Info\\",
            "/__pycache__/",
            "\\__pycache__\\",
            "/node_modules/",
            "\\node_modules\\",
        ]

        for pattern in exclude_patterns:
            if pattern in path_str:
                return True

        return False

    def _scan_folder(self, folder: Path) -> None:
        """Recursively scan a folder for audio files."""
        if not folder.exists():
            return

        try:
            for item in folder.iterdir():
                if self._stop_requested:
                    break

                if item.is_file():
                    if item.suffix.lower() in AUDIO_EXTENSIONS:
                        self._found_count += 1
                        stat = item.stat()
                        self.file_found.emit(str(item), stat.st_size, stat.st_mtime)
                elif item.is_dir():
                    if not self._is_excluded(item):
                        self._scan_folder(item)

        except PermissionError:
            pass

    def stop(self) -> None:
        """Request stop."""
        self._stop_requested = True
