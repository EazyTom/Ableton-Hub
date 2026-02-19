"""FTUE (First Time User Experience) dialog - User Guide / Getting Started."""

import markdown
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QVBoxLayout,
)

from ... import __version__
from ...config import get_config_manager, save_config
from ...utils.paths import get_resources_path
from ..theme import AbletonTheme


class FTUEDialog(QDialog):
    """Dialog displaying the User Guide / Getting Started content from FTUE.md."""

    def __init__(self, parent=None, show_startup_checkbox: bool = True):
        """Initialize the FTUE dialog.

        Args:
            parent: Parent widget.
            show_startup_checkbox: If True, show the "Don't show at startup" checkbox.
        """
        super().__init__(parent)

        self._config = get_config_manager().config
        self._show_startup_checkbox = show_startup_checkbox

        self.setWindowTitle("Getting Started - Ableton Hub")
        self.setMinimumSize(700, 500)
        self.resize(800, 600)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Create text browser for scrollable content
        from PyQt6.QtWidgets import QTextBrowser

        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {AbletonTheme.COLORS['surface']};
                border: 1px solid {AbletonTheme.COLORS['border']};
                border-radius: 4px;
                padding: 10px;
                font-size: 12px;
            }}
        """)

        # Load and render FTUE content
        html_content = self._load_and_render_ftue()
        self.text_browser.setHtml(html_content)
        layout.addWidget(self.text_browser)

        # Checkbox: Don't show at startup
        if self._show_startup_checkbox:
            self.dont_show_checkbox = QCheckBox("Don't show this guide at startup")
            self.dont_show_checkbox.setStyleSheet(f"color: {AbletonTheme.COLORS['text_primary']};")
            layout.addWidget(self.dont_show_checkbox)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self._on_accept)

        ok_btn = button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("Close")
            ok_btn.setStyleSheet(f"""
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

        layout.addWidget(button_box)

    def _load_and_render_ftue(self) -> str:
        """Load FTUE.md, prepend version header, and render as HTML."""
        resources_path = get_resources_path()
        ftue_path = resources_path / "FTUE.md"

        if ftue_path.exists():
            try:
                md_text = ftue_path.read_text(encoding="utf-8")
            except OSError:
                md_text = ""
        else:
            md_text = ""

        # Prepend version header
        header = f"## Ableton Hub — Version {__version__}\n\n"
        full_md = header + md_text

        # Convert markdown to HTML
        try:
            html = markdown.markdown(full_md, extensions=["extra"])
        except Exception:
            html = f"<p>Failed to load guide. Expected at: {ftue_path}</p>"

        # Apply accent color to headings for consistency with About dialog
        accent = AbletonTheme.COLORS["accent"]
        styled = html.replace("<h1>", f'<h1 style="color: {accent};">')
        styled = styled.replace("<h2>", f'<h2 style="color: {accent};">')
        styled = styled.replace("<h3>", f'<h3 style="color: {accent};">')

        return f'<div style="color: #e0e0e0;">{styled}</div>'

    def _on_accept(self) -> None:
        """Handle OK/Close - save 'don't show at startup' if checked."""
        if self._show_startup_checkbox and hasattr(self, "dont_show_checkbox"):
            if self.dont_show_checkbox.isChecked():
                self._config.ui.show_ftue_at_startup = False
                save_config()
        self.accept()
