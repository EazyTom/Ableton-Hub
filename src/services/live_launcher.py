"""Service for launching Ableton Live with project files."""

import subprocess
import sys
from pathlib import Path

from ..utils.logging import get_logger
from .live_detector import LiveDetector, LiveVersion


class LiveLauncher:
    """Launches Ableton Live with project files."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self._detector = LiveDetector.from_config()

    def get_available_versions(self) -> list[LiveVersion]:
        """Get all available Live versions."""
        return self._detector.get_versions()

    def launch_project(self, project_path: Path, live_version: LiveVersion | None = None) -> bool:
        """Launch Live with a project file.

        Args:
            project_path: Path to the .als project file.
            live_version: Live version to use. If None, uses the newest version.

        Returns:
            True if launch was successful, False otherwise.
        """
        if not project_path.exists():
            self.logger.error(f"Project file not found: {project_path}")
            return False

        if live_version is None:
            versions = self._detector.get_versions()
            if not versions:
                self.logger.error("No Ableton Live versions found")
                return False
            live_version = versions[0]  # Use newest version

        try:
            if sys.platform == "win32":
                return self._launch_windows(project_path, live_version)
            elif sys.platform == "darwin":
                return self._launch_macos(project_path, live_version)
            else:
                return self._launch_linux(project_path, live_version)
        except Exception as e:
            self.logger.error(f"Failed to launch Live: {e}", exc_info=True)
            return False

    def _launch_windows(self, project_path: Path, live_version: LiveVersion) -> bool:
        """Launch Live on Windows."""
        # On Windows, we can use subprocess to launch the .als file directly
        # Windows will use the default handler, or we can specify the executable
        try:
            # Method 1: Use start command (opens with default handler)
            # subprocess.Popen(['start', str(project_path)], shell=True)

            # Method 2: Launch Live.exe with project as argument
            subprocess.Popen(
                [str(live_version.path), str(project_path)], cwd=live_version.path.parent
            )
            self.logger.info(f"Launched {live_version} with project: {project_path.name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to launch on Windows: {e}", exc_info=True)
            return False

    def _launch_macos(self, project_path: Path, live_version: LiveVersion) -> bool:
        """Launch Live on macOS."""
        try:
            # On macOS, we need to use 'open' command with the .app bundle
            # The executable path is inside the .app bundle, but we need the .app path
            app_path = live_version.path.parent.parent.parent  # Go up from MacOS/Live to .app

            # Use 'open' command to launch the app with the project file
            subprocess.Popen(["open", "-a", str(app_path), str(project_path)])
            self.logger.info(f"Launched {live_version} with project: {project_path.name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to launch on macOS: {e}", exc_info=True)
            return False

    def _launch_linux(self, project_path: Path, live_version: LiveVersion) -> bool:
        """Launch Live on Linux."""
        try:
            # On Linux, launch the executable directly with project as argument
            subprocess.Popen(
                [str(live_version.path), str(project_path)], cwd=live_version.path.parent
            )
            self.logger.info(f"Launched {live_version} with project: {project_path.name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to launch on Linux: {e}", exc_info=True)
            return False

    def refresh_versions(self) -> None:
        """Refresh the list of available Live versions."""
        self._detector.refresh()
