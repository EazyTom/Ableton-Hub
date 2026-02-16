"""Dialog for adding a Live installation manually."""

import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ...database import LiveInstallation, get_session
from ...services.live_detector import LiveDetector
from ...utils.logging import get_logger


class AddLiveInstallationDialog(QDialog):
    """Dialog to manually add an Ableton Live installation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.installation_id: int | None = None
        self._setup_ui()
        # Set dialog to be modal and centered on parent
        self.setModal(True)
        self._parent = parent

    def showEvent(self, event):
        """Override showEvent to center dialog on parent window."""
        super().showEvent(event)
        if self._parent:
            # Ensure dialog is properly sized
            self.adjustSize()
            # Center on parent window
            parent_geometry = self._parent.geometry()
            dialog_geometry = self.geometry()
            x = parent_geometry.x() + (parent_geometry.width() - dialog_geometry.width()) // 2
            y = parent_geometry.y() + (parent_geometry.height() - dialog_geometry.height()) // 2
            self.move(x, y)

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Add Live Installation")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Name field
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Live 11 Suite")
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        # Executable path
        path_layout = QVBoxLayout()
        path_layout.addWidget(QLabel("Live Executable:"))
        path_input_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select Live executable...")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_executable)
        path_input_layout.addWidget(self.path_input)
        path_input_layout.addWidget(browse_btn)
        path_layout.addLayout(path_input_layout)
        layout.addLayout(path_layout)

        # Auto-detect button
        detect_btn = QPushButton("Auto-Detect from Path")
        detect_btn.clicked.connect(self._auto_detect)
        layout.addWidget(detect_btn)

        # Version (auto-filled or manual)
        version_layout = QHBoxLayout()
        version_layout.addWidget(QLabel("Version:"))
        self.version_input = QLineEdit()
        self.version_input.setPlaceholderText("e.g., 11.3.13")
        version_layout.addWidget(self.version_input)
        layout.addLayout(version_layout)

        # Suite checkbox
        self.suite_check = QCheckBox("Live Suite")
        layout.addWidget(self.suite_check)

        # Notes
        notes_label = QLabel("Notes (optional):")
        layout.addWidget(notes_label)
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        layout.addWidget(self.notes_input)

        # Buttons
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Add Installation")
        save_btn.clicked.connect(self._on_save)
        save_btn.setDefault(True)
        buttons.addWidget(cancel_btn)
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)

    def _browse_executable(self) -> None:
        """Browse for Live executable."""
        if sys.platform == "win32":
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Ableton Live Executable",
                "",
                "Executable Files (*.exe);;All Files (*.*)",
            )
        elif sys.platform == "darwin":
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Ableton Live.app",
                "/Applications",
                "Application Bundles (*.app);;All Files (*.*)",
            )
            if file_path and file_path.endswith(".app"):
                # Find the actual executable inside the bundle
                exe_path = Path(file_path) / "Contents" / "MacOS" / "Live"
                if exe_path.exists():
                    file_path = str(exe_path)
        else:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Ableton Live Executable", "", "All Files (*.*)"
            )

        if file_path:
            self.path_input.setText(file_path)
            # Try to auto-detect version info
            self._auto_detect()

    def _auto_detect(self) -> None:
        """Auto-detect version information from the executable path."""
        path_str = self.path_input.text().strip()
        if not path_str:
            return

        path = Path(path_str)
        if not path.exists():
            QMessageBox.warning(self, "Path Not Found", f"The path does not exist:\n{path_str}")
            return

        try:
            detector = LiveDetector()
            # Try to get version from path
            version = detector.get_version_by_path(path)
            if version:
                if not self.name_input.text():
                    self.name_input.setText(str(version))
                self.version_input.setText(version.version)
                self.suite_check.setChecked(version.is_suite)
            else:
                # Try to extract version from path manually
                import re

                name = path.name
                # Try to find version pattern like "11.3" or "11.3.13"
                match = re.search(r"(\d+\.\d+(?:\.\d+)?)", name)
                if match:
                    version_str = match.group(1)
                    self.version_input.setText(version_str)
                    if not self.name_input.text():
                        self.name_input.setText(f"Live {version_str}")
        except Exception as e:
            self.logger.error(f"Error auto-detecting: {e}", exc_info=True)

    def _on_save(self) -> None:
        """Save the installation."""
        name = self.name_input.text().strip()
        path_str = self.path_input.text().strip()
        version = self.version_input.text().strip()

        if not name:
            QMessageBox.warning(self, "Invalid Input", "Please enter a name for the installation.")
            return

        if not path_str:
            QMessageBox.warning(self, "Invalid Input", "Please select the Live executable path.")
            return

        path = Path(path_str)
        if not path.exists():
            QMessageBox.warning(
                self,
                "Path Not Found",
                f"The executable path does not exist:\n{path_str}\n\nPlease verify the path is correct.",
            )
            return

        if not version:
            QMessageBox.warning(self, "Invalid Input", "Please enter a version number.")
            return

        session = get_session()
        try:
            # Check if path already exists
            existing = (
                session.query(LiveInstallation)
                .filter(LiveInstallation.executable_path == str(path))
                .first()
            )

            if existing:
                QMessageBox.warning(
                    self,
                    "Installation Exists",
                    f"An installation with this path already exists:\n{existing.name}",
                )
                return

            # Create new installation
            install = LiveInstallation(
                name=name,
                version=version,
                executable_path=str(path),
                is_suite=self.suite_check.isChecked(),
                is_auto_detected=False,
                notes=self.notes_input.toPlainText().strip() or None,
            )

            session.add(install)
            session.commit()
            self.installation_id = install.id

            # Auto-set as default if this is the only installation
            installations = session.query(LiveInstallation).all()
            if len(installations) == 1:
                install.is_favorite = True
                session.commit()
                from ..controllers.live_controller import LiveController

                live_controller = LiveController()
                live_controller.installations_changed.emit()

            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to add installation:\n{str(e)}")
        finally:
            session.close()
