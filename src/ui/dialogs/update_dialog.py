"""Update dialog - shown when a newer version is available."""

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ... import __version__
from ...config import get_config_manager, save_config
from ..theme import AbletonTheme


class UpdateDialog(QDialog):
    """Dialog shown when a newer version is available."""

    def __init__(
        self,
        latest_version: str,
        release_url: str,
        download_url: str | None,
        parent=None,
    ):
        """Initialize the update dialog.

        Args:
            latest_version: The latest version string (e.g. "1.0.8").
            release_url: URL to the release page.
            download_url: Optional direct download URL (.msi/.dmg); falls back to release_url.
            parent: Parent widget.
        """
        super().__init__(parent)

        self._config = get_config_manager().config
        self._release_url = release_url
        self._download_url = download_url or release_url

        self.setWindowTitle("Update Available")
        self.setMinimumSize(400, 180)

        self._setup_ui(latest_version)

    def _setup_ui(self, latest_version: str) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header with plant emojis
        header = QLabel("🌱 🌿 Update Available 🌿 🌱")
        header.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {AbletonTheme.COLORS['text_primary']};
            """)
        layout.addWidget(header)

        # Message
        message = QLabel(
            f"Ableton Hub v{latest_version} is available. You're running v{__version__}."
        )
        message.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 13px;")
        message.setWordWrap(True)
        layout.addWidget(message)

        # Don't check for updates checkbox
        self.dont_check_checkbox = QCheckBox("Don't check for updates at startup")
        self.dont_check_checkbox.setStyleSheet(f"color: {AbletonTheme.COLORS['text_primary']};")
        layout.addWidget(self.dont_check_checkbox)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        later_btn = QPushButton("Later")
        later_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {AbletonTheme.COLORS['surface_light']};
                color: {AbletonTheme.COLORS['text_primary']};
                border: 1px solid {AbletonTheme.COLORS['border']};
                border-radius: 4px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {AbletonTheme.COLORS['surface_hover']};
            }}
            """)
        later_btn.clicked.connect(self._on_later)

        download_btn = QPushButton("Download")
        download_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {AbletonTheme.COLORS['accent']};
                color: {AbletonTheme.COLORS['text_on_accent']};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {AbletonTheme.COLORS['accent_hover']};
            }}
            """)
        download_btn.clicked.connect(self._on_download)

        button_layout.addWidget(later_btn)
        button_layout.addWidget(download_btn)
        layout.addLayout(button_layout)

    def _save_dont_check_if_checked(self) -> None:
        """Save config to disable startup check if user checked the box."""
        if self.dont_check_checkbox.isChecked():
            self._config.ui.check_for_updates_at_startup = False
            save_config()

    def _on_later(self) -> None:
        """Close without downloading; save 'don't check' if checkbox is checked."""
        self._save_dont_check_if_checked()
        self.reject()

    def _on_download(self) -> None:
        """Open download URL and close dialog."""
        self._save_dont_check_if_checked()
        QDesktopServices.openUrl(QUrl(self._download_url))
        self.accept()
