"""Worker for scanning backup files in background thread."""

from pathlib import Path
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal

from .base_worker import BaseWorker
from ...utils.paths import find_backup_files


class BackupScanWorker(BaseWorker):
    """Worker for scanning backup files in background thread."""
    
    finished = pyqtSignal(list)  # Emits list of backup file paths
    
    def __init__(self, project_path: str, parent=None):
        """Initialize the backup scan worker.
        
        Args:
            project_path: Path to the project file.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.project_path = project_path
    
    def run(self) -> None:
        """Scan for backup files and emit results."""
        if self.is_cancelled():
            return
        
        try:
            backup_files = find_backup_files(Path(self.project_path))
            
            if self.is_cancelled():
                return
            
            result = []
            for backup_path in backup_files:
                mod_time = datetime.fromtimestamp(backup_path.stat().st_mtime)
                result.append({
                    'path': str(backup_path),
                    'name': backup_path.name,
                    'date': mod_time.strftime("%Y-%m-%d %H:%M")
                })
            
            self.finished.emit(result)
        except Exception as e:
            error_msg = str(e)[:100]
            self.emit_error(error_msg, context={'project_path': self.project_path})
