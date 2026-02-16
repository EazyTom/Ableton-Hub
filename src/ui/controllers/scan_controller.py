"""Controller for managing project scanning operations."""

from pathlib import Path

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from ...database import Project, get_session
from ...services.scanner import ProjectScanner
from ...utils.logging import get_logger
from ...utils.paths import is_ableton_project


class ScanController(QObject):
    """Manages project scanning operations and state."""

    # Signals
    scan_started = pyqtSignal()
    scan_progress = pyqtSignal(int, int, str)  # current, total, message
    scan_complete = pyqtSignal(int)  # found_count
    scan_error = pyqtSignal(str)  # error_message
    project_found = pyqtSignal(str)  # path
    project_rescanned = pyqtSignal(int)  # project_id

    def __init__(self, parent: QObject | None = None):
        """Initialize the scan controller.

        Args:
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self._scanner: ProjectScanner | None = None

    def is_running(self) -> bool:
        """Check if a scan is currently running.

        Returns:
            True if scan is in progress.
        """
        return self._scanner is not None and self._scanner.is_running

    def start_scan(self, location_id: int | None = None) -> None:
        """Start scanning for projects.

        Args:
            location_id: Optional location ID to scan, or None for all locations.
        """
        if self.is_running():
            self.logger.warning("Scan already in progress, ignoring request")
            return

        self.logger.info(
            f"Starting scan {'for location ' + str(location_id) if location_id else 'of all locations'}"
        )

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

        # Wait for scanner thread to fully complete before clearing reference
        # This prevents race conditions where the thread is still running
        # when we set scanner to None
        if self._scanner:
            # Check if worker thread is still running
            if self._scanner.is_running:
                self.logger.debug("Waiting for scanner thread to finish...")
                # Give it a moment - the scanner's _on_complete should handle cleanup
                # but we wait here to ensure thread is fully done
                import time

                timeout = 3.0  # 3 seconds max wait
                start_time = time.time()
                while self._scanner.is_running and (time.time() - start_time) < timeout:
                    time.sleep(0.1)
                if self._scanner.is_running:
                    self.logger.warning("Scanner thread still running after timeout, forcing stop")
                    self._scanner.stop()

        self.scan_complete.emit(found_count)
        self._scanner = None

    def _on_error(self, error_msg: str) -> None:
        """Handle scan errors.

        Args:
            error_msg: Error message.
        """
        # Add context about scan state
        context_msg = f"Scan error: {error_msg}"
        if self._scanner:
            # Add scanner state info
            context_msg += f" (Scanner running: {self._scanner.is_running})"
            # Ensure scanner is stopped on error
            if self._scanner.is_running:
                self.logger.debug("Stopping scanner due to error")
                self._scanner.stop()

        self.logger.error(context_msg)
        self.scan_error.emit(error_msg)
        self._scanner = None

    def _on_project_found(self, path: str) -> None:
        """Handle a project being found.

        Args:
            path: Path to the found project.
        """
        self.project_found.emit(path)

    def rescan_project(self, project_id: int) -> None:
        """Rescan a single project to update its metadata.

        Args:
            project_id: ID of the project to rescan.
        """
        if self.is_running():
            self.logger.warning("Scan already in progress, cannot rescan individual project")
            return

        self.logger.info(f"Rescanning project ID: {project_id}")

        # Create a worker thread for the rescan operation
        worker = ProjectRescanWorker(project_id, self)

        def on_finished():
            # Disconnect signals before cleanup
            try:
                worker.finished.disconnect()
                worker.error.disconnect()
            except (TypeError, RuntimeError):
                pass

            # Wait for thread to finish
            if worker.isRunning():
                worker.quit()
                if not worker.wait(2000):
                    worker.terminate()
                    worker.wait(1000)

            self.project_rescanned.emit(project_id)
            worker.deleteLater()

        def on_error(error_msg: str):
            # Disconnect signals before cleanup
            try:
                worker.finished.disconnect()
                worker.error.disconnect()
            except (TypeError, RuntimeError):
                pass

            # Wait for thread to finish
            if worker.isRunning():
                worker.quit()
                if not worker.wait(2000):
                    worker.terminate()
                    worker.wait(1000)

            self._on_error(error_msg)
            worker.deleteLater()

        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        worker.start()

    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop_scan()


class ProjectRescanWorker(QThread):
    """Worker thread for rescanning a single project."""

    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, project_id: int, parent: QObject | None = None):
        """Initialize the rescan worker.

        Args:
            project_id: ID of the project to rescan.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.project_id = project_id
        self.logger = get_logger(__name__)

    def run(self) -> None:
        """Execute the rescan."""
        try:
            session = get_session()
            try:
                project = session.query(Project).get(self.project_id)
                if not project:
                    self.error.emit(f"Project {self.project_id} not found")
                    return

                project_path = Path(project.file_path)
                if not project_path.exists():
                    self.error.emit(f"Project file not found: {project_path}")
                    return

                if not is_ableton_project(project_path):
                    self.error.emit(f"Not a valid Ableton project: {project_path}")
                    return

                # Update project metadata
                from datetime import datetime

                stat = project_path.stat()
                project.file_size = stat.st_size
                project.modified_date = datetime.fromtimestamp(stat.st_mtime)
                project.last_scanned = datetime.utcnow()

                # Re-parse metadata
                from ...services.als_parser import ALSParser

                parser = ALSParser()
                try:
                    metadata = parser.parse(project_path)
                    if metadata:
                        self._apply_metadata_to_project(project, metadata)
                except Exception as e:
                    self.logger.warning(f"Failed to parse metadata for {project_path}: {e}")

                session.commit()
                self.logger.info(f"Successfully rescanned project: {project.name}")
                self.finished.emit()

            finally:
                session.close()

        except Exception as e:
            error_msg = f"Rescan failed: {e}"
            self.logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)

    def _apply_metadata_to_project(self, project: Project, metadata) -> None:
        """Apply parsed metadata to a project object.

        Args:
            project: Project database object.
            metadata: ProjectMetadata object from parser.
        """
        from datetime import datetime

        # Assign lists directly — SQLAlchemy's JSON column handles serialization.
        # Do NOT use json.dumps() here, as that would double-encode the data.
        project.plugins = metadata.plugins or []
        project.devices = metadata.devices or []
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
            project.arrangement_duration_seconds = (
                metadata.arrangement_length * 4.0 / metadata.tempo
            ) * 60.0
        else:
            project.arrangement_duration_seconds = None
        # Store longest session clip (sample) length separately
        project.furthest_sample_end = metadata.furthest_sample_end
        if metadata.furthest_sample_end and metadata.tempo and metadata.tempo > 0:
            project.sample_duration_seconds = (
                metadata.furthest_sample_end * 4.0 / metadata.tempo
            ) * 60.0
        else:
            project.sample_duration_seconds = None
        project.ableton_version = metadata.ableton_version
        project.sample_references = metadata.sample_references or []
        project.has_automation = metadata.has_automation
        project.last_parsed = datetime.utcnow()

        # Musical key/scale information
        project.musical_key = metadata.musical_key
        project.scale_type = metadata.scale_type
        project.is_in_key = metadata.is_in_key

        # Timeline markers (extracted using dawtool)
        project.timeline_markers = metadata.timeline_markers or []

        # ALS project metadata (stored so views don't need to re-parse)
        project.export_filenames = metadata.export_filenames or None
        project.annotation = metadata.annotation
        project.master_track_name = metadata.master_track_name
