"""Log viewer dialog for viewing application logs."""

from pathlib import Path

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices, QTextCursor
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ...config import get_config
from ...utils.logging import get_logs_directory
from ..theme import AbletonTheme


class LogViewerDialog(QDialog):
    """Dialog for viewing application log files."""

    def __init__(self, parent: QDialog | None = None, log_file_path: Path | None = None):
        """Initialize the log viewer dialog.

        Args:
            parent: Parent widget.
            log_file_path: Optional path to a specific log file to view.
                         If None, uses Ableton Hub application logs.
        """
        super().__init__(parent)
        self.config = get_config()
        self._custom_log_path = log_file_path
        self._setup_ui()
        self._load_logs()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        # Set window title based on whether it's a custom log file
        if self._custom_log_path:
            self.setWindowTitle(f"View Log - {self._custom_log_path.name}")
        else:
            self.setWindowTitle("View Logs")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header
        if self._custom_log_path:
            header_text = f"Live Log: {self._custom_log_path.name}"
        else:
            header_text = "Application Logs"
        header_label = QLabel(header_text)
        header_label.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {AbletonTheme.COLORS['text_primary']};"
        )
        layout.addWidget(header_label)

        # Log file selection (only show for Ableton Hub logs)
        if not self._custom_log_path:
            file_layout = QHBoxLayout()
            file_layout.addWidget(QLabel("Log file:"))

            self.log_file_combo = QComboBox()
            self.log_file_combo.addItems(["All logs", "Errors only"])
            self.log_file_combo.currentIndexChanged.connect(self._load_logs)
            file_layout.addWidget(self.log_file_combo)

            file_layout.addStretch()
            layout.addLayout(file_layout)
        else:
            # Hide combo box for custom log files
            self.log_file_combo = None

        # Log display
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFontFamily("Consolas")
        self.log_text.setFontPointSize(9)
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {AbletonTheme.COLORS['surface']};
                border: 1px solid {AbletonTheme.COLORS['border']};
                border-radius: 4px;
                padding: 8px;
                color: {AbletonTheme.COLORS['text_primary']};
            }}
        """)
        layout.addWidget(self.log_text)

        # Buttons
        buttons = QHBoxLayout()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._load_logs)
        buttons.addWidget(refresh_btn)

        if self._custom_log_path:
            # For custom log files, open the file's parent folder
            open_folder_btn = QPushButton("Open Log Folder")
            open_folder_btn.clicked.connect(self._open_custom_log_folder)
        else:
            # For Ableton Hub logs, open the logs directory
            open_folder_btn = QPushButton("Open Log Folder")
            open_folder_btn.clicked.connect(self._open_log_folder)
        buttons.addWidget(open_folder_btn)

        copy_btn = QPushButton("Copy Selected")
        copy_btn.clicked.connect(self._copy_selected)
        buttons.addWidget(copy_btn)

        buttons.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)

        layout.addLayout(buttons)

    def _get_log_file_path(self) -> Path:
        """Get the path to the log file to display.

        Returns:
            Path to log file.
        """
        # If custom log path provided, use it
        if self._custom_log_path:
            return self._custom_log_path

        # Otherwise use Ableton Hub logs
        logs_dir = get_logs_directory(self.config.logging)
        if self.log_file_combo.currentIndex() == 1:  # "Errors only"
            return logs_dir / "ableton_hub_errors.log"
        else:  # "All logs"
            return logs_dir / "ableton_hub.log"

    def _load_logs(self) -> None:
        """Load log file content."""
        log_path = self._get_log_file_path()

        if not log_path.exists():
            self.log_text.setPlainText(
                f"Log file not found: {log_path}\n\nLogs will be created when the application runs."
            )
            return

        try:
            # Read last 1000 lines
            with open(log_path, encoding="utf-8") as f:
                lines = f.readlines()

            # Get last 1000 lines
            total_lines = len(lines)
            if total_lines > 1000:
                lines = lines[-1000:]
                header = f"[Showing last 1000 lines of {total_lines} total lines]\n\n"
            else:
                header = ""

            content = header + "".join(lines)
            self.log_text.setPlainText(content)

            # Scroll to bottom
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.log_text.setTextCursor(cursor)

        except Exception as e:
            self.log_text.setPlainText(f"Error reading log file: {e}")

    def _open_log_folder(self) -> None:
        """Open the log folder in file explorer."""
        logs_dir = get_logs_directory(self.config.logging)
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(logs_dir)))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open log folder:\n{e}")

    def _open_custom_log_folder(self) -> None:
        """Open the custom log file's parent folder in file explorer."""
        if self._custom_log_path:
            try:
                folder_path = self._custom_log_path.parent
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder_path)))
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not open log folder:\n{e}")

    def _copy_selected(self) -> None:
        """Copy selected text to clipboard."""
        selected_text = self.log_text.textCursor().selectedText()
        if selected_text:
            from PyQt6.QtWidgets import QApplication

            clipboard = QApplication.clipboard()
            clipboard.setText(selected_text)
            QMessageBox.information(self, "Copied", "Selected text copied to clipboard.")
        else:
            QMessageBox.information(self, "No Selection", "Please select text to copy.")
