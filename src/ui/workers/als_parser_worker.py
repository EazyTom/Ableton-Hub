"""Worker for parsing ALS files in background thread."""

from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

from .base_worker import BaseWorker


class ALSParserWorker(BaseWorker):
    """Worker for parsing ALS files in background thread."""
    
    finished = pyqtSignal(dict)  # Emits metadata dict
    
    def __init__(self, file_path: str, parent=None):
        """Initialize the ALS parser worker.
        
        Args:
            file_path: Path to the ALS file to parse.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.file_path = file_path
    
    def run(self) -> None:
        """Parse the ALS file and emit results."""
        if self.is_cancelled():
            return
        
        try:
            from ...services.als_parser import ALSParser
            parser = ALSParser()
            metadata = parser.parse(Path(self.file_path))
            
            if self.is_cancelled():
                return
            
            result = {}
            if metadata:
                result['export_filenames'] = metadata.export_filenames or []
                result['annotation'] = metadata.annotation
                result['master_track_name'] = metadata.master_track_name
            
            self.finished.emit(result)
        except Exception as e:
            error_msg = str(e)[:100]
            self.emit_error(error_msg, context={'file_path': self.file_path})
