"""Log viewer dialog for viewing application logs."""

from typing import Optional
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QCheckBox, QMessageBox, QComboBox
)
from PyQt6.QtCore import Qt, QDesktopServices, QUrl
from PyQt6.QtGui import QTextCursor

from ...config import get_config
from ...utils.logging import get_logs_directory
from ..theme import AbletonTheme


class LogViewerDialog(QDialog):
    """Dialog for viewing application log files."""
    
    def __init__(self, parent: Optional[QDialog] = None):
        """Initialize the log viewer dialog.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.config = get_config()
        self._setup_ui()
        self._load_logs()
    
    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("View Logs")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Header
        header_label = QLabel("Application Logs")
        header_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {AbletonTheme.COLORS['text_primary']};")
        layout.addWidget(header_label)
        
        # Log file selection
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("Log file:"))
        
        self.log_file_combo = QComboBox()
        self.log_file_combo.addItems(["All logs", "Errors only"])
        self.log_file_combo.currentIndexChanged.connect(self._load_logs)
        file_layout.addWidget(self.log_file_combo)
        
        file_layout.addStretch()
        layout.addLayout(file_layout)
        
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
        logs_dir = get_logs_directory(self.config.logging)
        if self.log_file_combo.currentIndex() == 1:  # "Errors only"
            return logs_dir / "ableton_hub_errors.log"
        else:  # "All logs"
            return logs_dir / "ableton_hub.log"
    
    def _load_logs(self) -> None:
        """Load log file content."""
        log_path = self._get_log_file_path()
        
        if not log_path.exists():
            self.log_text.setPlainText(f"Log file not found: {log_path}\n\nLogs will be created when the application runs.")
            return
        
        try:
            # Read last 1000 lines
            with open(log_path, 'r', encoding='utf-8') as f:
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
            QMessageBox.warning(
                self,
                "Error",
                f"Could not open log folder:\n{e}"
            )
    
    def _copy_selected(self) -> None:
        """Copy selected text to clipboard."""
        selected_text = self.log_text.textCursor().selectedText()
        if selected_text:
            from PyQt6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(selected_text)
            QMessageBox.information(
                self,
                "Copied",
                "Selected text copied to clipboard."
            )
        else:
            QMessageBox.information(
                self,
                "No Selection",
                "Please select text to copy."
            )
