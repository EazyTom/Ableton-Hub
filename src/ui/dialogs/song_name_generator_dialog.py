"""Random song name generator dialog - generates 10 names at once."""

import html
import random

from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ...services.song_name_generator import generate_song_names
from ..theme import AbletonTheme

# Bright neon/vivid hex colors - guaranteed visible on dark background
_BRIGHT_COLORS = [
    "#ff6b6b",
    "#ff8787",
    "#ffa502",
    "#ffbe0b",
    "#ffdd59",
    "#e8ff6b",
    "#7bed9f",
    "#2ed573",
    "#00ff88",
    "#70a1ff",
    "#5352ed",
    "#a55eea",
    "#ff6b81",
    "#ff9ff3",
    "#54a0ff",
    "#00d2d3",
    "#1dd1a1",
    "#feca57",
    "#ff9f43",
    "#ee5a24",
    "#5f27cd",
    "#00cec9",
    "#81ecec",
    "#74b9ff",
    "#a29bfe",
    "#fd79a8",
    "#fdcb6e",
    "#e17055",
    "#6c5ce7",
    "#00b894",
]

_TEXT_EDIT_STYLE = """
    QTextEdit {{
        background-color: {surface};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 8px;
        font-size: 13px;
        color: {text_primary};
    }}
"""


class SongNameGeneratorDialog(QDialog):
    """Dialog that displays 10 randomly generated song names in 2 columns with a Generate button."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Random Song Name Generator")
        self.setMinimumSize(500, 320)

        self._setup_ui()
        self._refresh_names()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info = QLabel(
            "Click Generate to create 10 new random song names. Select and copy any name."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']};")
        layout.addWidget(info)

        # Two columns of 5 names each - QTextEdit for selectable text
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(12)

        style = _TEXT_EDIT_STYLE.format(**AbletonTheme.COLORS)

        self.left_text = QTextEdit()
        self.left_text.setReadOnly(True)
        self.left_text.setStyleSheet(style)
        self.left_text.setMinimumHeight(180)
        self.left_text.setTabChangesFocus(True)
        columns_layout.addWidget(self.left_text)

        self.right_text = QTextEdit()
        self.right_text.setReadOnly(True)
        self.right_text.setStyleSheet(style)
        self.right_text.setMinimumHeight(180)
        self.right_text.setTabChangesFocus(True)
        columns_layout.addWidget(self.right_text)

        layout.addLayout(columns_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        generate_btn = QPushButton("Generate")
        generate_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {AbletonTheme.COLORS['accent']};
                color: {AbletonTheme.COLORS['text_on_accent']};
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {AbletonTheme.COLORS['accent_hover']};
            }}
            """)
        generate_btn.clicked.connect(self._refresh_names)
        btn_layout.addWidget(generate_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _random_color_hex(self) -> str:
        """Return a random bright color as hex for dark background."""
        return random.choice(_BRIGHT_COLORS)

    def _refresh_names(self) -> None:
        """Generate 10 new names and populate both columns with selectable colored text."""
        names = generate_song_names(10)
        left_html_parts = []
        right_html_parts = []
        for i, name in enumerate(names):
            color = self._random_color_hex()
            escaped = html.escape(name)
            line = f'<div style="color: {color}; padding: 2px 0;">{escaped}</div>'
            if i < 5:
                left_html_parts.append(line)
            else:
                right_html_parts.append(line)
        self.left_text.setHtml("".join(left_html_parts))
        self.right_text.setHtml("".join(right_html_parts))
