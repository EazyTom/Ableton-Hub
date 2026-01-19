"""Controller for managing project scanning operations."""

import logging
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from ...database import get_session, Location
from ...services.scanner import ProjectScanner
from ...utils.logging import get_logger


class ScanController(QObject):
    """Manages project scanning operations and state."""
    
    # Signals
    scan_started = pyqtSignal()
    scan_progress = pyqtSignal(int, int, str)  # current, total, message
    scan_complete = pyqtSignal(int)  # found_count
    scan_error = pyqtSignal(str)  # error_message
    project_found = pyqtSignal(str)  # path
    
    def __init__(self, parent: Optional[QObject] = None):
        """Initialize the scan controller.
        
        Args:
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self._scanner: Optional[ProjectScanner] = None
    
    def is_running(self) -> bool:
        """Check if a scan is currently running.
        
        Returns:
            True if scan is in progress.
        """
        return self._scanner is not None and self._scanner.is_running
    
    def start_scan(self, location_id: Optional[int] = None) -> None:
        """Start scanning for projects.
        
        Args:
            location_id: Optional location ID to scan, or None for all locations.
        """
        if self.is_running():
            self.logger.warning("Scan already in progress, ignoring request")
            return
        
        self.logger.info(f"Starting scan {'for location ' + str(location_id) if location_id else 'of all locations'}")
        
        self._scanner = ProjectScanner()
        self._scanner.progress_updated.connect(self._on_progress)
        self._scanner.scan_complete.connect(self._on_complete)
        self._scanner.project_found.connect(self._on_project_found)
        self._scanner.error_occurred.connect(self._on_error)
        
        self.scan_started.emit()
        
        if location_id:
            self._scanner.scan_location(location_id)
        else:
            self._scanner.scan_all()
    
    def stop_scan(self) -> None:
        """Stop the current scan operation."""
        if self._scanner:
            self._scanner.stop()
            self._scanner = None
    
    def _on_progress(self, current: int, total: int, message: str) -> None:
        """Handle scan progress updates.
        
        Args:
            current: Current progress value.
            total: Total items to process.
            message: Progress message.
        """
        self.scan_progress.emit(current, total, message)
    
    def _on_complete(self, found_count: int) -> None:
        """Handle scan completion.
        
        Args:
            found_count: Number of projects found.
        """
        self.logger.info(f"Scan complete: Found {found_count} new project(s)")
        self.scan_complete.emit(found_count)
        self._scanner = None
    
    def _on_error(self, error_msg: str) -> None:
        """Handle scan errors.
        
        Args:
            error_msg: Error message.
        """
        self.logger.error(f"Scan error: {error_msg}")
        self.scan_error.emit(error_msg)
        self._scanner = None
    
    def _on_project_found(self, path: str) -> None:
        """Handle a project being found.
        
        Args:
            path: Path to the found project.
        """
        self.project_found.emit(path)
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop_scan()
