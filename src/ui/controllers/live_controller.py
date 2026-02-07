"""Controller for managing Ableton Live installations."""

import os

from PyQt6.QtCore import QObject, pyqtSignal

from ...database import LiveInstallation, get_session
from ...services.live_detector import LiveDetector
from ...utils.logging import get_logger


class LiveController(QObject):
    """Manages Ableton Live installation operations."""

    # Signals
    installations_changed = pyqtSignal()
    installation_added = pyqtSignal(int)  # install_id
    installation_removed = pyqtSignal(int)  # install_id

    def __init__(self, parent: QObject | None = None):
        """Initialize the Live controller.

        Args:
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self._detector = LiveDetector()

    def auto_detect_installations(self) -> list:
        """Auto-detect Ableton Live installations.

        Returns:
            List of detected LiveVersion objects.
        """
        self.logger.info("Starting auto-detection...")
        self.logger.debug(f"ProgramFiles: {os.environ.get('ProgramFiles', 'N/A')}")
        self.logger.debug(f"ProgramFiles(x86): {os.environ.get('ProgramFiles(x86)', 'N/A')}")
        self.logger.debug(f"ProgramData: {os.environ.get('ProgramData', 'N/A')}")
        self.logger.debug(f"LOCALAPPDATA: {os.environ.get('LOCALAPPDATA', 'N/A')}")
        self.logger.debug(f"APPDATA: {os.environ.get('APPDATA', 'N/A')}")

        detected_versions = self._detector.detect_all()

        self.logger.info(f"Found {len(detected_versions)} version(s)")
        for v in detected_versions:
            self.logger.debug(f"  - {v} at {v.path}")

        return detected_versions

    def get_all_installations(self) -> list[LiveInstallation]:
        """Get all Live installations from database.

        Returns:
            List of LiveInstallation objects.
        """
        with get_session() as session:
            return session.query(LiveInstallation).order_by(LiveInstallation.version.desc()).all()

    def get_favorite_installation(self) -> LiveInstallation | None:
        """Get the favorite Live installation.

        Returns:
            LiveInstallation object or None.
        """
        with get_session() as session:
            return (
                session.query(LiveInstallation).filter(LiveInstallation.is_favorite == True).first()
            )

    def set_favorite(self, install_id: int) -> bool:
        """Set a Live installation as favorite.

        Args:
            install_id: Installation ID.

        Returns:
            True if successful.
        """
        with get_session() as session:
            # Clear all favorites first
            session.query(LiveInstallation).update({"is_favorite": False})

            # Set new favorite
            install = (
                session.query(LiveInstallation).filter(LiveInstallation.id == install_id).first()
            )
            if install:
                install.is_favorite = True
                session.commit()
                self.installations_changed.emit()
                return True
            return False

    def remove_installation(self, install_id: int) -> bool:
        """Remove a Live installation.

        Args:
            install_id: Installation ID to remove.

        Returns:
            True if removed successfully.
        """
        with get_session() as session:
            install = (
                session.query(LiveInstallation).filter(LiveInstallation.id == install_id).first()
            )
            if install:
                session.delete(install)
                session.commit()
                self.logger.info(f"Removed Live installation: {install.name} (ID: {install_id})")
                self.installation_removed.emit(install_id)
                self.installations_changed.emit()
                # Auto-set default if only one installation remains
                self._auto_set_default_if_needed(session)
                return True
            return False

    def find_matching_installation(self, major_version: int | None) -> LiveInstallation | None:
        """Find a Live installation matching the given major version.

        Args:
            major_version: Major version number (9, 10, 11, 12) or None.

        Returns:
            Matching LiveInstallation or None if not found.
        """
        if major_version is None:
            return None

        with get_session() as session:
            installations = session.query(LiveInstallation).all()
            for install in installations:
                if install.get_major_version() == major_version:
                    return install
        return None

    def get_default_installation(self) -> LiveInstallation | None:
        """Get the default Live installation (favorite, or first if only one exists).

        Returns:
            LiveInstallation object or None.
        """
        with get_session() as session:
            # Check for favorite first
            favorite = (
                session.query(LiveInstallation).filter(LiveInstallation.is_favorite == True).first()
            )
            if favorite:
                return favorite

            # If no favorite, check if only one installation exists
            all_installations = session.query(LiveInstallation).all()
            if len(all_installations) == 1:
                # Auto-set as favorite
                install = all_installations[0]
                install.is_favorite = True
                session.commit()
                self.installations_changed.emit()
                return install

            # Return first installation if multiple exist
            return all_installations[0] if all_installations else None

    def _auto_set_default_if_needed(self, session) -> None:
        """Auto-set default installation if only one exists.

        Args:
            session: Database session (must be active).
        """
        installations = session.query(LiveInstallation).all()
        if len(installations) == 1:
            install = installations[0]
            if not install.is_favorite:
                # Clear any existing favorites (shouldn't be any, but be safe)
                session.query(LiveInstallation).update({"is_favorite": False})
                install.is_favorite = True
                session.commit()
                self.logger.info(f"Auto-set default installation: {install.name}")
                self.installations_changed.emit()

    def get_installation_for_project_path(self, project_path) -> LiveInstallation | None:
        """Get the best Live installation for a project file path.

        Tries to match by major version, falls back to default installation.
        First checks if the path matches an existing project in the database
        to use stored version data, otherwise parses the file.

        Args:
            project_path: Path to the .als project file.

        Returns:
            LiveInstallation object or None.
        """
        from pathlib import Path

        project_major_version = None

        # First, try to find if this path matches an existing project in the database
        # to use stored version data (more efficient than parsing)
        with get_session() as session:
            from ...database import Project

            existing_project = (
                session.query(Project)
                .filter(Project.file_path == str(Path(project_path).resolve()))
                .first()
            )

            if existing_project and existing_project.ableton_version:
                # Use stored version from database
                project_major_version = existing_project.get_live_version_major()
                self.logger.debug(
                    f"Using stored version for {project_path}: {existing_project.ableton_version}"
                )

        # If no stored version found, parse the file as fallback
        if project_major_version is None:
            try:
                from ..services.als_parser import ALSParser

                parser = ALSParser()
                metadata = parser.parse(Path(project_path))
                if metadata and metadata.ableton_version:
                    # Extract major version from version string like "Ableton Live 11.3.10"
                    import re

                    match = re.search(r"Live\s+(\d+)", metadata.ableton_version)
                    if match:
                        try:
                            project_major_version = int(match.group(1))
                            self.logger.debug(f"Parsed version from file: {project_major_version}")
                        except (ValueError, TypeError):
                            pass
            except Exception as e:
                self.logger.debug(f"Could not parse project version: {e}")

        # Try to find matching installation
        if project_major_version:
            matching_install = self.find_matching_installation(project_major_version)
            if matching_install:
                return matching_install

        # Fall back to default installation
        return self.get_default_installation()
