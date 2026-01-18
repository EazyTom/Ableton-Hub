"""Project card widget for grid view."""

from typing import Optional, List
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QMouseEvent, QContextMenuEvent, QColor, QPainter, QPen, QPixmap

from ...database.models import Project, ProjectStatus
from ...services.audio_preview import AudioPreviewGenerator
from ..theme import AbletonTheme


class ProjectCard(QFrame):
    """Card widget representing a single project."""
    
    # Signals
    clicked = pyqtSignal(int)          # Project ID
    double_clicked = pyqtSignal(int)   # Project ID
    context_menu = pyqtSignal(int, object)  # Project ID, QPoint
    
    def __init__(self, project: Project, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.project = project
        self._selected = False
        
        self._setup_ui()
        self._update_display()
    
    def _setup_ui(self) -> None:
        """Set up the card UI."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedSize(180, 140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._apply_style()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        
        # Preview thumbnail
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(156, 60)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet(f"""
            QLabel {{
                background-color: {AbletonTheme.COLORS['surface_light']};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.preview_label)
        
        # Project name (centered)
        self.name_label = QLabel()
        self.name_label.setWordWrap(True)
        self.name_label.setMaximumHeight(40)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.name_label.font()
        font.setBold(True)
        if font.pointSize() > 0:
            font.setPointSize(11)
        else:
            font.setPixelSize(15)
        self.name_label.setFont(font)
        layout.addWidget(self.name_label)
        
        layout.addStretch()
        
        # Tempo row (centered)
        tempo_row = QHBoxLayout()
        tempo_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tempo_row.setSpacing(2)
        
        self.bpm_label = QLabel("bpm")
        self.bpm_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 10px;")
        tempo_row.addWidget(self.bpm_label)
        
        self.tempo_label = QLabel()
        tempo_row.addWidget(self.tempo_label)
        
        self.tempo_sep = QLabel("|")
        self.tempo_sep.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 10px; padding: 0 4px;")
        tempo_row.addWidget(self.tempo_sep)
        
        self.length_label = QLabel()
        self.length_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 10px;")
        tempo_row.addWidget(self.length_label)
        
        self.duration_label = QLabel()
        self.duration_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 10px; padding-left: 4px;")
        tempo_row.addWidget(self.duration_label)
        
        layout.addLayout(tempo_row)
        
        # Bottom row (centered)
        bottom_row = QHBoxLayout()
        bottom_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_row.setSpacing(8)
        
        self.date_label = QLabel()
        self.date_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 10px;")
        bottom_row.addWidget(self.date_label)
        
        self.bottom_sep = QLabel("•")
        self.bottom_sep.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 10px; padding: 0 4px;")
        bottom_row.addWidget(self.bottom_sep)
        
        self.location_label = QLabel()
        self.location_label.setStyleSheet(f"""
            QLabel {{
                background-color: {AbletonTheme.COLORS['surface_light']};
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 10px;
                color: {AbletonTheme.COLORS['text_secondary']};
            }}
        """)
        bottom_row.addWidget(self.location_label)
        
        self.export_indicator = QLabel()
        bottom_row.addWidget(self.export_indicator)
        
        self.favorite_indicator = QLabel()
        bottom_row.addWidget(self.favorite_indicator)
        
        layout.addLayout(bottom_row)
    
    def _set_default_logo(self) -> None:
        """Set the default logo as preview based on export status.
        
        Uses AProject.ico for projects without exports, ableton-logo.png for projects with exports.
        """
        from ...utils.paths import get_resources_path
        
        # Check if project has exports
        try:
            has_exports = bool(self.project.exports) if hasattr(self.project, 'exports') else False
        except Exception:
            has_exports = False
        
        # Choose icon based on export status
        if has_exports:
            logo_path = get_resources_path() / "images" / "ableton-logo.png"
        else:
            # Use AProject.ico for projects without exports
            logo_path = get_resources_path() / "icons" / "AProject.ico"
            # Fallback to ableton-logo if ico doesn't exist
            if not logo_path.exists():
                logo_path = get_resources_path() / "images" / "ableton-logo.png"
        
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    156, 60,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled)
                return
        # Fallback to music note emoji
        self.preview_label.setText("🎵")
    
    def _apply_style(self) -> None:
        """Apply visual style to the card.
        
        Projects with exports get a highlighted accent border color.
        """
        bg_color = AbletonTheme.COLORS['surface']
        border_color = AbletonTheme.COLORS['border']
        
        # Check if project has exports for highlighting
        try:
            has_exports = bool(self.project.exports) if hasattr(self.project, 'exports') else False
        except Exception:
            has_exports = False
        
        if self._selected:
            border_color = AbletonTheme.COLORS['accent']
            bg_color = AbletonTheme.COLORS['surface_light']
        elif has_exports:
            # Highlight projects with exports using a green accent
            border_color = "#4CAF50"  # Green color for projects with exports
        
        # Apply project color if set (overrides export highlight)
        if self.project.color:
            border_color = self.project.color
        
        # Determine border width - thicker for projects with exports
        border_width = "3px" if has_exports and not self._selected else "2px"
        
        self.setStyleSheet(f"""
            ProjectCard {{
                background-color: {bg_color};
                border: {border_width} solid {border_color};
                border-radius: 8px;
            }}
            ProjectCard:hover {{
                background-color: {AbletonTheme.COLORS['surface_hover']};
                border-color: {AbletonTheme.COLORS['border_light']};
            }}
        """)
    
    def _update_display(self) -> None:
        """Update the display with project data."""
        # Preview thumbnail
        preview_path = None
        if self.project.thumbnail_path and Path(self.project.thumbnail_path).exists():
            preview_path = self.project.thumbnail_path
        else:
            # Try to generate preview
            preview_path = AudioPreviewGenerator.get_or_generate_preview(self.project.id)
        
        if preview_path and Path(preview_path).exists():
            pixmap = QPixmap(preview_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    156, 60,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled)
            else:
                self._set_default_logo()
        else:
            self._set_default_logo()
        
        # Name
        self.name_label.setText(self.project.name)
        self.name_label.setToolTip(self.project.name)
        
        # Tempo with rainbow color based on BPM (purple=60 -> blue -> cyan -> green -> yellow -> orange -> red=200+)
        has_tempo = self.project.tempo and self.project.tempo > 0
        has_length = self.project.arrangement_length and self.project.arrangement_length > 0
        
        if has_tempo:
            tempo = self.project.tempo
            self.tempo_label.setText(f"{tempo:.0f}")
            self.tempo_label.setToolTip(f"Tempo: {tempo:.1f} BPM")
            
            # Calculate color based on tempo (60-200 BPM range mapped to rainbow)
            tempo_color = self._get_tempo_color(tempo)
            self.tempo_label.setStyleSheet(f"""
                QLabel {{
                    color: {tempo_color};
                    font-size: 11px;
                    font-weight: bold;
                    padding: 0px 2px;
                }}
            """)
            self.tempo_label.setVisible(True)
            self.bpm_label.setVisible(True)
        else:
            self.tempo_label.setVisible(False)
            self.bpm_label.setVisible(False)
        
        # Arrangement length in bars
        if has_length:
            bars = int(self.project.arrangement_length)
            self.length_label.setText(f"{bars} bars")
            self.length_label.setToolTip(f"Arrangement length: {bars} bars")
            self.length_label.setVisible(True)
        else:
            self.length_label.setVisible(False)
        
        # Duration in min:sec (calculated from bars and tempo)
        has_duration = (hasattr(self.project, 'arrangement_duration_seconds') and 
                       self.project.arrangement_duration_seconds and 
                       self.project.arrangement_duration_seconds > 0)
        if has_duration:
            duration_sec = int(self.project.arrangement_duration_seconds)
            minutes = duration_sec // 60
            seconds = duration_sec % 60
            duration_str = f"{minutes}:{seconds:02d}"
            self.duration_label.setText(duration_str)
            self.duration_label.setToolTip(f"Duration: {duration_str} ({duration_sec} seconds)")
            self.duration_label.setVisible(True)
        else:
            self.duration_label.setVisible(False)
        
        # Show separator only if both tempo and length are visible
        self.tempo_sep.setVisible(has_tempo and has_length)
        
        # Show bottom separator only if both date and location are visible
        has_date = bool(self.project.modified_date)
        has_location = self.location_label.isVisible()
        self.bottom_sep.setVisible(has_date and has_location)
        
        # Location
        # Access location safely (may be detached)
        try:
            location = self.project.location if hasattr(self.project, 'location') else None
            if location:
                loc_name = location.name
                if len(loc_name) > 12:
                    loc_name = loc_name[:10] + "..."
                self.location_label.setText(loc_name)
                self.location_label.setVisible(True)
            else:
                self.location_label.setVisible(False)
        except Exception:
            # If relationship is detached, hide location
            self.location_label.setVisible(False)
        
        # Export indicator
        # Access exports list safely (may be detached)
        try:
            has_exports = bool(self.project.exports) if hasattr(self.project, 'exports') else False
            export_count = len(self.project.exports) if has_exports else 0
        except Exception:
            # If relationship is detached, check if we have export count
            has_exports = False
            export_count = 0
        
        if has_exports:
            # Show colorized indicator with count
            self.export_indicator.setText(f"🎵 {export_count}" if export_count > 1 else "🎵")
            self.export_indicator.setStyleSheet(f"""
                QLabel {{
                    color: #4CAF50;
                    font-weight: bold;
                }}
            """)
            self.export_indicator.setToolTip(f"Has {export_count} export(s)")
        else:
            self.export_indicator.setText("")
            self.export_indicator.setStyleSheet("")
            self.export_indicator.setToolTip("No exports")
        
        # Favorite indicator
        self.favorite_indicator.setText("⭐" if self.project.is_favorite else "")
        
        # Modified date
        if self.project.modified_date:
            date_str = self._format_date(self.project.modified_date)
            self.date_label.setText(date_str)
        else:
            self.date_label.setText("")
    
    def _get_tempo_color(self, tempo: float) -> str:
        """Get a rainbow color based on tempo (purple=60 -> red=200+).
        
        Args:
            tempo: The tempo in BPM.
            
        Returns:
            Hex color string.
        """
        # Clamp tempo to range 60-200
        tempo = max(60, min(200, tempo))
        
        # Normalize to 0-1 range
        t = (tempo - 60) / 140.0
        
        # Rainbow colors: purple -> blue -> cyan -> green -> yellow -> orange -> red
        if t < 0.167:  # Purple to Blue
            r = int(128 - 128 * (t / 0.167))
            g = 0
            b = int(128 + 127 * (t / 0.167))
        elif t < 0.333:  # Blue to Cyan
            r = 0
            g = int(255 * ((t - 0.167) / 0.167))
            b = 255
        elif t < 0.5:  # Cyan to Green
            r = 0
            g = 255
            b = int(255 - 255 * ((t - 0.333) / 0.167))
        elif t < 0.667:  # Green to Yellow
            r = int(255 * ((t - 0.5) / 0.167))
            g = 255
            b = 0
        elif t < 0.833:  # Yellow to Orange
            r = 255
            g = int(255 - 100 * ((t - 0.667) / 0.167))
            b = 0
        else:  # Orange to Red
            r = 255
            g = int(155 - 155 * ((t - 0.833) / 0.167))
            b = 0
        
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _format_date(self, dt: datetime) -> str:
        """Format a date for display."""
        now = datetime.now()
        delta = now - dt
        
        if delta.days == 0:
            hours = delta.seconds // 3600
            if hours == 0:
                minutes = delta.seconds // 60
                return f"{minutes}m ago"
            return f"{hours}h ago"
        elif delta.days == 1:
            return "Yesterday"
        elif delta.days < 7:
            return f"{delta.days}d ago"
        elif delta.days < 30:
            weeks = delta.days // 7
            return f"{weeks}w ago"
        elif delta.days < 365:
            months = delta.days // 30
            return f"{months}mo ago"
        else:
            return dt.strftime("%Y-%m-%d")
    
    def set_selected(self, selected: bool) -> None:
        """Set the selection state."""
        self._selected = selected
        self._apply_style()
    
    def is_selected(self) -> bool:
        """Check if the card is selected."""
        return self._selected
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.project.id)
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Handle double click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.project.id)
        super().mouseDoubleClickEvent(event)
    
    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Handle context menu request."""
        self.context_menu.emit(self.project.id, event.globalPos())
