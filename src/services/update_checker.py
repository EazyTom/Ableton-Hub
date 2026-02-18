"""Update checker service - fetches latest release from GitHub and compares versions."""

import json
import sys

from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest

from .. import __version__
from ..utils.logging import get_logger

GITHUB_RELEASES_URL = "https://api.github.com/repos/EazyTom/ableton-hub/releases/latest"


def _parse_version(s: str) -> tuple[int, ...]:
    """Parse version string to tuple for comparison. Strips 'v' prefix."""
    cleaned = s.strip().lstrip("v")
    parts = []
    for x in cleaned.split("."):
        try:
            # Handle suffixes like "1.0.7b1" - take numeric part only
            num_str = "".join(c for c in x if c.isdigit() or c == "-")
            if num_str:
                parts.append(int(num_str.split("-")[0]))
            else:
                parts.append(0)
        except ValueError:
            parts.append(0)
    return tuple(parts) if parts else (0,)


def _is_newer(latest: str, current: str) -> bool:
    """Return True if latest version is newer than current."""
    try:
        return _parse_version(latest) > _parse_version(current)
    except Exception:
        return False


class UpdateChecker(QObject):
    """Checks GitHub for the latest release and emits signals with update info."""

    update_available = pyqtSignal(str, str, str)  # latest_version, release_url, download_url (or release_url if no asset)
    check_failed = pyqtSignal(str)
    no_update_available = pyqtSignal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._logger = get_logger(__name__)
        self._nam = QNetworkAccessManager(self)
        self._nam.finished.connect(self._on_finished)
        self._current_version = __version__

    def check(self) -> None:
        """Start the update check. Emits update_available, no_update_available, or check_failed."""
        request = QNetworkRequest(QUrl(GITHUB_RELEASES_URL))
        request.setRawHeader(b"User-Agent", f"AbletonHub/{self._current_version}".encode())
        self._nam.get(request)
        self._logger.debug("Update check started")

    def _on_finished(self, reply) -> None:
        """Handle network reply."""
        try:
            if reply.error() != reply.NetworkError.NoError:
                err_msg = reply.errorString() or "Unknown network error"
                self._logger.warning(f"Update check failed: {err_msg}")
                self.check_failed.emit(err_msg)
                reply.deleteLater()
                return

            data = reply.readAll().data().decode("utf-8")
            reply.deleteLater()

            release = json.loads(data)
            tag_name = release.get("tag_name", "")
            latest_version = tag_name.lstrip("v")
            release_url = release.get("html_url", "https://github.com/EazyTom/ableton-hub/releases")

            if not _is_newer(latest_version, self._current_version):
                self._logger.debug(f"Already up to date: {self._current_version}")
                self.no_update_available.emit()
                return

            download_url = self._get_platform_download_url(release) or release_url
            self._logger.info(f"Update available: {latest_version} (current: {self._current_version})")
            self.update_available.emit(latest_version, release_url, download_url)

        except json.JSONDecodeError as e:
            self._logger.warning(f"Update check: invalid JSON: {e}")
            self.check_failed.emit("Invalid response from server")
        except Exception as e:
            self._logger.warning(f"Update check failed: {e}", exc_info=True)
            self.check_failed.emit(str(e))

    def _get_platform_download_url(self, release: dict) -> str | None:
        """Pick platform-specific asset URL from release. Returns None if no match."""
        assets = release.get("assets", [])
        if sys.platform == "win32":
            suffix = ".msi"
        elif sys.platform == "darwin":
            suffix = ".dmg"
        else:
            return None

        for asset in assets:
            name = asset.get("name", "")
            if name.lower().endswith(suffix):
                return asset.get("browser_download_url")
        return None
