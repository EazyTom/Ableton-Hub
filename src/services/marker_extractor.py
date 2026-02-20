"""Service for extracting timeline markers from Ableton Live project files using dawtool.

Timeline markers (locators) are text annotations placed on the DAW timeline.
This service wraps dawtool to extract markers with comprehensive error handling.
"""

from pathlib import Path
from typing import Any

from ..utils.logging import get_logger

# Try to import dawtool - make it optional
try:
    import dawtool

    DAWTOOL_AVAILABLE = True
except ImportError:
    DAWTOOL_AVAILABLE = False
    dawtool = None


class MarkerExtractor:
    """Extracts timeline markers from Ableton Live .als files using dawtool.

    Provides graceful fallback if dawtool is not available.
    """

    def __init__(self):
        """Initialize the marker extractor."""
        self.logger = get_logger(__name__)
        self._available: bool = DAWTOOL_AVAILABLE

        if not self._available:
            self.logger.warning(
                "dawtool not available - timeline marker extraction will be disabled. "
                "Install with: pip install 'dawtool @ git+https://github.com/EazyTom/dawtool'"
            )

    @property
    def is_available(self) -> bool:
        """Check if dawtool is available."""
        return self._available

    def extract_markers(self, als_path: Path) -> list[dict[str, Any]]:
        """Extract timeline markers from an .als file.

        Args:
            als_path: Path to the .als file.

        Returns:
            List of marker dictionaries with 'time' (float) and 'text' (str) keys.
            Returns empty list if extraction fails or dawtool is unavailable.
        """
        if not self._available:
            return []

        if not als_path.exists():
            self.logger.warning(f"ALS file not found: {als_path}")
            return []

        try:
            # Use dawtool's simple API to extract markers
            with open(als_path, "rb") as f:
                markers = dawtool.extract_markers(str(als_path), f)

            # Convert dawtool Marker objects to dict format
            result = []
            for marker in markers:
                result.append({"time": float(marker.time), "text": str(marker.text)})

            if result:
                self.logger.debug(f"Extracted {len(result)} timeline markers from {als_path.name}")
            return result

        except ValueError as e:
            # dawtool raises ValueError for known parse issues (e.g. "Cannot parse tempo")
            # Log at warning level without traceback since these are expected for some projects
            self.logger.warning(f"Could not extract markers from {als_path.name}: {e}")
            return []
        except Exception as e:
            self.logger.error(
                f"Error extracting timeline markers from {als_path}: {e}", exc_info=True
            )
            return []

    def extract_markers_advanced(self, als_path: Path) -> dict[str, Any] | None:
        """Extract markers using dawtool's advanced API (includes tempo automation data).

        Args:
            als_path: Path to the .als file.

        Returns:
            Dictionary with 'markers' list and optionally 'tempo_automation' data,
            or None if extraction fails.
        """
        if not self._available:
            return None

        if not als_path.exists():
            return None

        try:
            with open(als_path, "rb") as f:
                # Load project using advanced API
                proj = dawtool.load_project(str(als_path), f)
                proj.parse()

            # Extract markers
            markers = []
            for marker in proj.markers:
                markers.append({"time": float(marker.time), "text": str(marker.text)})

            result = {"markers": markers}

            # Note: Tempo automation data is available via internal APIs
            # but not officially supported, so we don't include it here

            return result

        except Exception as e:
            self.logger.error(
                f"Error extracting markers (advanced) from {als_path}: {e}", exc_info=True
            )
            return None
