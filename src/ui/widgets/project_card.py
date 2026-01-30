"""Project card widget for grid view."""

from typing import Optional, List
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QMouseEvent, QContextMenuEvent, QColor, QPainter, QPen, QPixmap

from ...database.models import Project, ProjectStatus, Export
from ...services.audio_preview import AudioPreviewGenerator
from ...services.audio_player import AudioPlayer
from ..theme import AbletonTheme


class ProjectCard(QFrame):
    """Card widget representing a single project."""
    
    # Signals
    clicked = pyqtSignal(int)          # Project ID
    double_clicked = pyqtSignal(int)   # Project ID
    context_menu = pyqtSignal(int, object)  # Project ID, QPoint
    export_playing = pyqtSignal(int, str)  # Project ID, Export path
    
    def __init__(self, project: Project, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.project = project
        self._selected = False
        
        # Export playback state
        self._exports: List[Export] = []
        self._current_export_index = 0
        self._load_exports()
        
        # Audio player instance
        self._audio_player = AudioPlayer.instance()
        self._audio_player.playback_finished.connect(self._on_playback_finished)
        self._audio_player.playback_stopped.connect(self._on_playback_stopped)
        
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
        # Tooltip will be set in _update_display
        layout.addWidget(self.preview_label)
        
        # Project name row (centered) with favorite indicator
        name_row = QHBoxLayout()
        name_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_row.setSpacing(4)
        
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
        # Tooltip will be set in _update_display
        name_row.addWidget(self.name_label)
        
        # Favorite indicator (gemstone icon) next to title
        self.favorite_indicator = QLabel()
        self.favorite_indicator.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 12px;")
        name_row.addWidget(self.favorite_indicator)
        
        layout.addLayout(name_row)
        
        # Parent folder label (shown when folder name differs from project name)
        self.folder_label = QLabel()
        self.folder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.folder_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 9px; font-style: italic;")
        self.folder_label.setVisible(False)
        layout.addWidget(self.folder_label)
        
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
        
        # Bottom row (centered with similarity indicator at far right)
        bottom_row = QHBoxLayout()
        bottom_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_row.setSpacing(8)
        
        self.date_label = QLabel()
        self.date_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 10px;")
        # Date tooltip will be set in _update_display
        bottom_row.addWidget(self.date_label)
        
        self.date_location_sep = QLabel("•")
        self.date_location_sep.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 10px; padding: 0 4px;")
        bottom_row.addWidget(self.date_location_sep)
        
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
        
        # Live version indicator
        self.version_label = QLabel()
        self.version_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 10px;")
        self.version_label.setVisible(False)  # Hidden by default until version is set
        bottom_row.addWidget(self.version_label)
        
        self.export_indicator = QLabel()
        bottom_row.addWidget(self.export_indicator)
        
        layout.addLayout(bottom_row)
    
    def _set_default_logo(self) -> None:
        """Set the default logo as preview when no waveform thumbnail is available."""
        from ...utils.paths import get_resources_path
        
        resources = get_resources_path()
        logo_path = resources / "images" / "als-icon.png"
        
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
        
        # Fallback to music note emoji if icon file is missing
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
        
        # Check if project is missing
        is_missing = self.project.status == ProjectStatus.MISSING
        
        if self._selected:
            border_color = AbletonTheme.COLORS['accent']
            bg_color = AbletonTheme.COLORS['surface_light']
        elif is_missing:
            # Red border for missing projects
            border_color = "#FF0000"  # Red color for missing projects
        elif has_exports:
            # Highlight projects with exports using a green accent
            border_color = "#4CAF50"  # Green color for projects with exports
        
        # Apply project color if set (overrides export highlight and missing status)
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
        # Preview thumbnail - use cached path if available, only generate if missing
        preview_path = None
        if self.project.thumbnail_path and Path(self.project.thumbnail_path).exists():
            preview_path = self.project.thumbnail_path
        else:
            # Only generate if no cached thumbnail exists
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
        
        # Name - remove "Project" suffix for brevity
        display_name = self._get_display_name()
        self.name_label.setText(display_name)
        
        # Show parent folder name if it differs from project name (helps distinguish copies)
        self._update_folder_label()
        
        # Style name label for missing projects (dark orange with yellow)
        if self.project.status == ProjectStatus.MISSING:
            self.name_label.setStyleSheet(f"""
                QLabel {{
                    color: #FF8C00;  /* Dark orange */
                    background-color: #FFD700;  /* Yellow background */
                    padding: 2px 4px;
                    border-radius: 3px;
                    font-weight: bold;
                }}
            """)
        else:
            # Reset to default styling (clear any previous styling)
            self.name_label.setStyleSheet("")
        
        # Unified tooltip for preview and name (small font, centered)
        tooltip_html = f'<div style="font-size: 10px; text-align: center;">'
        tooltip_html += f'<b>{self.project.name}</b><br/>'
        
        if self.project.file_path:
            tooltip_html += f'Path: {self.project.file_path}<br/>'
        
        # Track count
        if self.project.track_count and self.project.track_count > 0:
            tooltip_html += f'Tracks: {self.project.track_count}<br/>'
        
        # Clip count (from custom_metadata if available, otherwise N/A)
        clip_count = None
        if self.project.custom_metadata and isinstance(self.project.custom_metadata, dict):
            clip_count = self.project.custom_metadata.get('total_clip_count') or self.project.custom_metadata.get('clip_count')
        if clip_count:
            tooltip_html += f'Clips: {clip_count}<br/>'
        
        # Sample count
        samples = self.project.get_sample_references_list()
        sample_count = len(samples) if samples else 0
        if sample_count > 0:
            tooltip_html += f'Samples: {sample_count}<br/>'
        
        # Automation
        automation_status = "Yes" if self.project.has_automation else "No"
        tooltip_html += f'Automation: {automation_status}<br/>'
        
        # Version
        version_display = self.project.get_live_version_display()
        if version_display:
            full_version = self.project.ableton_version or version_display
            tooltip_html += f'Version: {full_version}<br/>'
        
        # Key/Scale
        key_display = self.project.get_key_display()
        if key_display:
            tooltip_html += f'Key: {key_display}<br/>'
        
        # File size
        if self.project.file_size and self.project.file_size > 0:
            size_mb = self.project.file_size / (1024 * 1024)
            if size_mb < 1:
                size_str = f"{size_mb * 1024:.0f} KB"
            else:
                size_str = f"{size_mb:.1f} MB"
            tooltip_html += f'Size: {size_str}<br/>'
        
        # Exports (with click hint)
        export_count = len(self._exports)
        if export_count > 0:
            tooltip_html += f'<b style="color: #4CAF50;">Exports: {export_count} 🔊 (click to play)</b><br/>'
        
        # Dates
        if self.project.created_date:
            tooltip_html += f'Created: {self.project.created_date.strftime("%Y-%m-%d %H:%M")}<br/>'
        if self.project.modified_date:
            tooltip_html += f'Modified: {self.project.modified_date.strftime("%Y-%m-%d %H:%M")}<br/>'
        if self.project.last_scanned:
            tooltip_html += f'Scanned: {self.project.last_scanned.strftime("%Y-%m-%d %H:%M")}<br/>'
        if self.project.last_parsed:
            tooltip_html += f'Parsed: {self.project.last_parsed.strftime("%Y-%m-%d %H:%M")}<br/>'
        
        tooltip_html += '</div>'
        
        # Set tooltip on both preview and name
        self.preview_label.setToolTip(tooltip_html)
        self.name_label.setToolTip(tooltip_html)
        
        # Tempo with rainbow color based on BPM (purple=60 -> blue -> cyan -> green -> yellow -> orange -> red=200+)
        has_tempo = self.project.tempo and self.project.tempo > 0
        has_length = self.project.arrangement_length and self.project.arrangement_length > 0
        
        if has_tempo:
            tempo = self.project.tempo
            self.tempo_label.setText(f"{tempo:.0f}")
            # Remove individual tooltip - unified tooltip on name/preview
            
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
            # Remove individual tooltip - unified tooltip on name/preview
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
            # Remove individual tooltip - unified tooltip on name/preview
            self.duration_label.setVisible(True)
        else:
            self.duration_label.setVisible(False)
        
        # Show separator only if both tempo and length are visible
        self.tempo_sep.setVisible(has_tempo and has_length)
        
        # Show separator based on visibility
        has_date = bool(self.project.modified_date)
        has_location = self.location_label.isVisible()
        self.date_location_sep.setVisible(has_date and has_location)
        
        # Location
        # Access location safely (may be detached)
        try:
            location = self.project.location if hasattr(self.project, 'location') else None
            if location:
                loc_name = location.name
                if len(loc_name) > 12:
                    loc_name = loc_name[:10] + "..."
                self.location_label.setText(loc_name)
                # Remove individual tooltip - unified tooltip on name/preview
                self.location_label.setVisible(True)
            else:
                self.location_label.setVisible(False)
        except Exception:
            # If relationship is detached, hide location
            self.location_label.setVisible(False)
        
        # Live version
        version_display = self.project.get_live_version_display()
        if version_display:
            self.version_label.setText(version_display)
            self.version_label.setVisible(True)
        else:
            self.version_label.setVisible(False)
        
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
            # Remove individual tooltip - unified tooltip on name/preview
        else:
            self.export_indicator.setText("")
            self.export_indicator.setStyleSheet("")
            # Remove individual tooltip - unified tooltip on name/preview
        
        # Favorite indicator
        self.favorite_indicator.setText("💎" if self.project.is_favorite else "")
        
        # Modified date
        if self.project.modified_date:
            date_str = self._format_date(self.project.modified_date)
            self.date_label.setText(date_str)
            # Remove individual tooltip - unified tooltip on name/preview
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
        # Brightened purple and blue for better readability
        if t < 0.167:  # Purple to Blue
            # Start with bright purple (#cc00ff) instead of dark purple
            r = int(204 - 51 * (t / 0.167))  # 204 -> 153 (bright purple to bright blue-purple)
            g = 0
            b = int(255 - 51 * (t / 0.167))  # 255 -> 204 (bright purple to bright blue-purple)
        elif t < 0.333:  # Blue to Cyan
            # Start with bright blue (#0066ff) instead of dark blue
            r = 0
            g = int(102 + 153 * ((t - 0.167) / 0.167))  # 102 -> 255 (bright blue to cyan)
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
    
    def _load_exports(self) -> None:
        """Load exports for this project from the database."""
        from ...database import get_session
        
        session = get_session()
        try:
            # Get exports sorted by date (most recent first)
            exports = session.query(Export).filter(
                Export.project_id == self.project.id
            ).order_by(Export.export_date.desc()).all()
            
            # Filter to only existing files
            self._exports = [e for e in exports if Path(e.export_path).exists()]
            self._current_export_index = 0
        finally:
            session.close()
    
    def has_exports(self) -> bool:
        """Check if this project has playable exports."""
        return len(self._exports) > 0
    
    def get_export_count(self) -> int:
        """Get the number of playable exports."""
        return len(self._exports)
    
    def _play_current_export(self) -> None:
        """Play the current export in the cycle."""
        if not self._exports:
            return
        
        export = self._exports[self._current_export_index]
        export_path = export.export_path
        
        if Path(export_path).exists():
            # Stop any current playback first
            self._audio_player.stop()
            # Play the export
            self._audio_player.play(export_path)
            self.export_playing.emit(self.project.id, export_path)
            
            # Update visual indicator
            self._update_playing_indicator(True)
    
    def _cycle_to_next_export(self) -> None:
        """Move to the next export in the list."""
        if self._exports:
            self._current_export_index = (self._current_export_index + 1) % len(self._exports)
    
    def _on_playback_finished(self) -> None:
        """Handle when playback finishes naturally."""
        self._update_playing_indicator(False)
    
    def _on_playback_stopped(self) -> None:
        """Handle when playback is stopped."""
        self._update_playing_indicator(False)
    
    def _get_display_name(self) -> str:
        """Get the display name for the project, removing 'Project' for brevity."""
        import re
        name = self.project.name
        # Remove all instances of "project" (case-insensitive) - they're all projects anyway
        # Also clean up any resulting double spaces, leading/trailing separators
        name = re.sub(r'[Pp]roject', '', name)
        name = re.sub(r'[\s_-]+', ' ', name)  # Normalize multiple spaces/separators to single space
        return name.strip(' -_')
    
    def _update_folder_label(self) -> None:
        """Update folder label to show parent folder when it differs from project name.
        
        This helps distinguish copies and projects with the same .als filename
        but in different folders (e.g., 'Project - Copy/Project.als').
        """
        if not self.project.file_path:
            self.folder_label.setVisible(False)
            return
        
        from pathlib import Path
        project_path = Path(self.project.file_path)
        parent_folder = project_path.parent.name
        project_name = self.project.name
        
        # Check if parent folder name is meaningfully different from project name
        # Normalize both for comparison (remove common suffixes like "Project")
        parent_lower = parent_folder.lower().replace(" project", "").replace("_project", "").strip()
        name_lower = project_name.lower().replace(" project", "").replace("_project", "").strip()
        
        # Show folder label if they're different (indicates copy or alternate naming)
        if parent_lower != name_lower and parent_folder:
            # Truncate long folder names
            display_folder = parent_folder
            if len(display_folder) > 30:
                display_folder = display_folder[:27] + "..."
            self.folder_label.setText(display_folder)
            self.folder_label.setVisible(True)
        else:
            self.folder_label.setVisible(False)
    
    def _update_playing_indicator(self, playing: bool) -> None:
        """Update visual indicator for playback state."""
        if playing and self._exports:
            export = self._exports[self._current_export_index]
            export_name = Path(export.export_path).stem
            # Truncate long names
            if len(export_name) > 20:
                export_name = export_name[:17] + "..."
            idx = self._current_export_index + 1
            total = len(self._exports)
            self.name_label.setText(f"🔊 {export_name} ({idx}/{total})")
            self.name_label.setStyleSheet(f"color: {AbletonTheme.COLORS['accent']}; font-weight: bold;")
        else:
            # Restore original name (with "Project" removed)
            name = self._get_display_name()
            if len(name) > 25:
                name = name[:22] + "..."
            self.name_label.setText(name)
            self.name_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_primary']}; font-weight: bold;")
    
    def _is_this_card_playing(self) -> bool:
        """Check if this card's export is currently playing."""
        if not self._audio_player.is_playing or not self._exports:
            return False
        current_file = self._audio_player.current_file
        if current_file:
            # Check if current file matches any of this project's exports
            for export in self._exports:
                if export.export_path == current_file:
                    return True
        return False
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press - single click plays exports if available."""
        if event.button() == Qt.MouseButton.LeftButton:
            if self._exports:
                # If something is playing from this card
                if self._is_this_card_playing():
                    # If on last export, stop playback
                    if self._current_export_index == len(self._exports) - 1:
                        self._audio_player.stop()
                        self._current_export_index = 0  # Reset for next time
                    else:
                        # Cycle to next export and play
                        self._cycle_to_next_export()
                        self._play_current_export()
                else:
                    # First click or returning to this card - play current export
                    self._play_current_export()
            
            # Always emit clicked signal for selection
            self.clicked.emit(self.project.id)
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Handle double click - opens project details."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.project.id)
        super().mouseDoubleClickEvent(event)
    
    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Handle context menu request."""
        self.context_menu.emit(self.project.id, event.globalPos())
