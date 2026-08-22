"""Dialog for choosing which Ableton Live installation opens a project."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
)

from ...database import LiveInstallation, Project
from ...services.archive_service import ArchiveService
from ...utils.live_version import format_live_version_display, is_prerelease_version
from ..theme import AbletonTheme


class OpenWithLiveDialog(QDialog):
    """Pick a Live installation and optionally back up before opening."""

    def __init__(
        self,
        project: Project,
        installations: list[LiveInstallation],
        *,
        recommended_id: int | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._project = project
        self._installations = installations
        self._recommended_id = recommended_id
        self.selected_installation: LiveInstallation | None = None
        self.make_backup_first = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Open With Ableton Live")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)

        project_version = self._project.ableton_version or "Unknown"
        title = QLabel(f"Project: {self._project.name}")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        version_label = QLabel(
            f"Created with: {format_live_version_display(project_version, prefix='')}"
        )
        layout.addWidget(version_label)

        warning = self._build_warning_text()
        if warning:
            warn_label = QLabel(warning)
            warn_label.setWordWrap(True)
            warn_label.setStyleSheet(f"color: {AbletonTheme.COLORS['warning']};")
            layout.addWidget(warn_label)

        layout.addWidget(QLabel("Choose Ableton Live installation:"))

        self.install_list = QListWidget()
        for install in self._installations:
            pre = " [Pre-release]" if is_prerelease_version(install.version) else ""
            suite = " Suite" if install.is_suite else ""
            label = f"{install.name} — v{install.version}{suite}{pre}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, install.id)
            if install.id == self._recommended_id:
                item.setToolTip("Recommended for this project")
            self.install_list.addItem(item)

        if self.install_list.count() > 0:
            select_row = 0
            if self._recommended_id is not None:
                for row in range(self.install_list.count()):
                    if self.install_list.item(row).data(Qt.ItemDataRole.UserRole) == self._recommended_id:
                        select_row = row
                        break
            self.install_list.setCurrentRow(select_row)

        layout.addWidget(self.install_list)

        self.backup_checkbox = QCheckBox("Make backup before opening in a newer Live version")
        project_major = self._project.get_live_version_major()
        recommended = self._find_installation(self._recommended_id)
        show_backup = bool(
            project_major
            and recommended
            and recommended.get_major_version()
            and recommended.get_major_version() > project_major
        )
        self.backup_checkbox.setVisible(show_backup)
        self.backup_checkbox.setChecked(show_backup)
        layout.addWidget(self.backup_checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_warning_text(self) -> str:
        project_major = self._project.get_live_version_major()
        if project_major is None:
            return ""

        newer = [
            inst
            for inst in self._installations
            if inst.get_major_version() and inst.get_major_version() > project_major
        ]
        if newer:
            return (
                "Opening this project in a newer major Live version may permanently upgrade "
                "the .als file format. Consider backing up first."
            )
        return ""

    def _find_installation(self, install_id: int | None) -> LiveInstallation | None:
        if install_id is None:
            return None
        for inst in self._installations:
            if inst.id == install_id:
                return inst
        return None

    def _on_accept(self) -> None:
        item = self.install_list.currentItem()
        if item is None:
            QMessageBox.warning(self, "No Selection", "Please select a Live installation.")
            return

        install_id = item.data(Qt.ItemDataRole.UserRole)
        self.selected_installation = self._find_installation(install_id)
        self.make_backup_first = self.backup_checkbox.isChecked()
        self.accept()


def maybe_backup_project(project: Project, backup_location: str | None, parent=None) -> bool:
    """Create a backup copy if backup location is configured. Returns True if ok to proceed."""
    if not backup_location:
        reply = QMessageBox.question(
            parent,
            "No Backup Location",
            "No backup location is configured. Continue without backing up?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    try:
        ArchiveService().archive_project(
            project.file_path,
            backup_location,
            compress=False,
            include_timestamp=True,
        )
        return True
    except Exception as exc:
        QMessageBox.warning(
            parent,
            "Backup Failed",
            f"Could not create backup before opening:\n{exc}\n\nContinue anyway?",
        )
        reply = QMessageBox.question(
            parent,
            "Continue?",
            "Open project without backup?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes
