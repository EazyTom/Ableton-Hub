"""Project properties view widget - replaces the dialog with a main window view."""

from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QStringListModel, Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...database import Collection, Project, ProjectCollection, ProjectTag, get_session
from ...services.audio_player import AudioPlayer, format_duration
from ...utils.fuzzy_match import extract_song_name
from ..theme import AbletonTheme
from ..widgets.tag_editor import ProjectTagSelector
from ..workers import BackupScanWorker, SimilarProjectsWorker


class ProjectPropertiesView(QWidget):
    """View for displaying and editing project properties - embedded in main window."""

    back_requested = pyqtSignal()
    project_selected = pyqtSignal(int)  # For similar project navigation
    tags_modified = pyqtSignal()  # Emitted when tags are created/modified
    project_saved = pyqtSignal()  # Emitted when changes are saved
    no_live_installation_requested = (
        pyqtSignal()
    )  # Emitted when user needs to add Live (e.g. backup launch)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.project_id: int | None = None
        self._project: Project | None = None
        self._als_metadata: dict[str, Any] = {}

        # Background workers and their threads
        self._backup_thread: QThread | None = None
        self._backup_worker: BackupScanWorker | None = None
        self._similar_thread: QThread | None = None
        self._similar_worker: SimilarProjectsWorker | None = None

        # Keep references to threads that are still running when we detach them,
        # so Python's garbage collector doesn't destroy the C++ QThread object
        # while the OS thread is still active (which causes a fatal crash).
        self._orphaned_threads: list[QThread] = []

        self._setup_ui()
        self._connect_audio_signals()

    def _setup_ui(self) -> None:
        """Set up the view UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header row with back button
        header = QWidget()
        header.setStyleSheet(
            f"background-color: {AbletonTheme.COLORS['surface']}; border-bottom: 1px solid {AbletonTheme.COLORS['border']};"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 8, 16, 8)

        back_btn = QPushButton("← Back to Projects")
        back_btn.clicked.connect(self.back_requested.emit)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {AbletonTheme.COLORS['accent']};
                font-weight: bold;
                padding: 8px 12px;
            }}
            QPushButton:hover {{
                background-color: {AbletonTheme.COLORS['surface_hover']};
                border-radius: 4px;
            }}
        """)
        header_layout.addWidget(back_btn)

        header_layout.addStretch()

        # Save button in header
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.setObjectName("primary")
        self.save_btn.setToolTip(
            "Save all changes including Export Name Match.\nThe Export Name Match is used to link audio exports to this project."
        )
        self.save_btn.clicked.connect(self._on_save)
        self.save_btn.setStyleSheet(f"""
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
        header_layout.addWidget(self.save_btn)

        main_layout.addWidget(header)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background-color: {AbletonTheme.COLORS['background']};")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Project title header
        self.title_label = QLabel()
        self.title_label.setStyleSheet(
            f"font-size: 28px; font-weight: bold; color: {AbletonTheme.COLORS['text_primary']};"
        )
        layout.addWidget(self.title_label)

        # Project info (read-only) - 2 column layout
        project_group = QGroupBox("Project Information")
        project_group.setStyleSheet(self._group_box_style())
        project_layout = QGridLayout(project_group)
        project_layout.setSpacing(8)
        project_layout.setColumnStretch(1, 1)
        project_layout.setColumnStretch(3, 1)

        label_style = f"color: {AbletonTheme.COLORS['text_secondary']}; font-weight: bold;"

        # Left column
        row = 0
        lbl = QLabel("Path:")
        lbl.setStyleSheet(label_style)
        project_layout.addWidget(lbl, row, 0)
        self.path_label = QLabel()
        self.path_label.setWordWrap(True)
        self.path_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']};")
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        project_layout.addWidget(self.path_label, row, 1, 1, 3)  # Span across columns

        row += 1
        lbl = QLabel("Location:")
        lbl.setStyleSheet(label_style)
        project_layout.addWidget(lbl, row, 0)
        self.location_label = QLabel()
        project_layout.addWidget(self.location_label, row, 1)

        lbl = QLabel("Size:")
        lbl.setStyleSheet(label_style)
        project_layout.addWidget(lbl, row, 2)
        self.size_label = QLabel()
        project_layout.addWidget(self.size_label, row, 3)

        row += 1
        lbl = QLabel("Ableton Version:")
        lbl.setStyleSheet(label_style)
        project_layout.addWidget(lbl, row, 0)
        self.version_label = QLabel()
        project_layout.addWidget(self.version_label, row, 1)

        row += 1
        lbl = QLabel("Tempo:")
        lbl.setStyleSheet(label_style)
        project_layout.addWidget(lbl, row, 0)
        self.tempo_label = QLabel()
        project_layout.addWidget(self.tempo_label, row, 1)

        lbl = QLabel("Time Signature:")
        lbl.setStyleSheet(label_style)
        project_layout.addWidget(lbl, row, 2)
        self.time_sig_label = QLabel()
        project_layout.addWidget(self.time_sig_label, row, 3)

        row += 1
        lbl = QLabel("Key:")
        lbl.setStyleSheet(label_style)
        project_layout.addWidget(lbl, row, 0)
        self.key_label = QLabel()
        project_layout.addWidget(self.key_label, row, 1)

        lbl = QLabel("Arrangement Length:")
        lbl.setStyleSheet(label_style)
        project_layout.addWidget(lbl, row, 2)
        self.length_label = QLabel()
        project_layout.addWidget(self.length_label, row, 3)

        row += 1
        lbl = QLabel("Session Clip Length:")
        lbl.setStyleSheet(label_style)
        project_layout.addWidget(lbl, row, 0)
        self.sample_length_label = QLabel()
        project_layout.addWidget(self.sample_length_label, row, 1)

        lbl = QLabel("Markers:")
        lbl.setStyleSheet(label_style)
        project_layout.addWidget(lbl, row, 2)
        self.markers_label = QLabel()
        project_layout.addWidget(self.markers_label, row, 3)

        row += 1
        lbl = QLabel("Tracks:")
        lbl.setStyleSheet(label_style)
        project_layout.addWidget(lbl, row, 0)
        self.track_count_label = QLabel()
        project_layout.addWidget(self.track_count_label, row, 1)

        lbl = QLabel("Clips:")
        lbl.setStyleSheet(label_style)
        project_layout.addWidget(lbl, row, 2)
        self.clip_count_label = QLabel()
        project_layout.addWidget(self.clip_count_label, row, 3)

        row += 1
        lbl = QLabel("Samples:")
        lbl.setStyleSheet(label_style)
        project_layout.addWidget(lbl, row, 0)
        self.sample_count_label = QLabel()
        project_layout.addWidget(self.sample_count_label, row, 1)

        lbl = QLabel("Automation:")
        lbl.setStyleSheet(label_style)
        project_layout.addWidget(lbl, row, 2)
        self.automation_label = QLabel()
        project_layout.addWidget(self.automation_label, row, 3)

        row += 1
        lbl = QLabel("Annotation:")
        lbl.setStyleSheet(label_style)
        project_layout.addWidget(lbl, row, 0)
        self.annotation_label = QLabel()
        self.annotation_label.setWordWrap(True)
        project_layout.addWidget(self.annotation_label, row, 1, 1, 3)

        row += 1
        lbl = QLabel("Created:")
        lbl.setStyleSheet(label_style)
        project_layout.addWidget(lbl, row, 0)
        self.created_label = QLabel()
        project_layout.addWidget(self.created_label, row, 1)

        lbl = QLabel("Modified:")
        lbl.setStyleSheet(label_style)
        project_layout.addWidget(lbl, row, 2)
        self.modified_label = QLabel()
        project_layout.addWidget(self.modified_label, row, 3)

        row += 1
        lbl = QLabel("Last Scanned:")
        lbl.setStyleSheet(label_style)
        project_layout.addWidget(lbl, row, 0)
        self.scanned_label = QLabel()
        project_layout.addWidget(self.scanned_label, row, 1)

        lbl = QLabel("Last Parsed:")
        lbl.setStyleSheet(label_style)
        project_layout.addWidget(lbl, row, 2)
        self.parsed_label = QLabel()
        project_layout.addWidget(self.parsed_label, row, 3)

        row += 1
        open_folder_btn = QPushButton("Open in File Manager")
        open_folder_btn.clicked.connect(self._open_folder)
        project_layout.addWidget(open_folder_btn, row, 0, 1, 2)

        layout.addWidget(project_group)

        # Timeline Markers section
        markers_group = QGroupBox("Timeline Markers")
        markers_group.setStyleSheet(self._group_box_style())
        markers_layout = QVBoxLayout(markers_group)

        # Markers list widget
        self.markers_list = QListWidget()
        self.markers_list.setMaximumHeight(200)
        self.markers_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {AbletonTheme.COLORS['surface']};
                border: 1px solid {AbletonTheme.COLORS['border']};
                border-radius: 4px;
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 6px;
                border-bottom: 1px solid {AbletonTheme.COLORS['border']};
            }}
            QListWidget::item:selected {{
                background-color: {AbletonTheme.COLORS['accent']};
                color: {AbletonTheme.COLORS['text_on_accent']};
            }}
        """)
        markers_layout.addWidget(self.markers_list)

        # Export markers button
        export_markers_btn = QPushButton("Export Markers...")
        export_markers_btn.clicked.connect(self._export_markers)
        export_markers_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {AbletonTheme.COLORS['surface']};
                border: 1px solid {AbletonTheme.COLORS['border']};
                border-radius: 4px;
                padding: 6px 12px;
                color: {AbletonTheme.COLORS['text_primary']};
            }}
            QPushButton:hover {{
                background-color: {AbletonTheme.COLORS['surface_hover']};
            }}
        """)
        markers_layout.addWidget(export_markers_btn)

        layout.addWidget(markers_group)

        # Collections
        collections_group = QGroupBox("Collections")
        collections_group.setStyleSheet(self._group_box_style())
        collections_layout = QVBoxLayout(collections_group)

        self.collections_label = QLabel("Not in any collections")
        self.collections_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']};")
        collections_layout.addWidget(self.collections_label)

        add_to_collection_btn = QPushButton("Add to Collection...")
        add_to_collection_btn.clicked.connect(self._add_to_collection)
        collections_layout.addWidget(add_to_collection_btn)

        layout.addWidget(collections_group)

        # Metadata (editable)
        meta_group = QGroupBox("Metadata")
        meta_group.setStyleSheet(self._group_box_style())
        meta_layout = QFormLayout(meta_group)
        meta_layout.setSpacing(8)

        # Export song name with auto-suggest
        export_name_layout = QHBoxLayout()
        self.export_name_input = QLineEdit()
        self.export_name_input.setPlaceholderText("Song name for exports (used for fuzzy matching)")

        self._export_name_completer = QCompleter()
        self._export_name_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._export_name_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.export_name_input.setCompleter(self._export_name_completer)
        export_name_layout.addWidget(self.export_name_input)

        self.save_export_name_btn = QPushButton("Save")
        self.save_export_name_btn.setFixedWidth(70)
        self.save_export_name_btn.setToolTip(
            "Save this export name to associate audio exports with this project.\nExports matching this name will be automatically linked."
        )
        self.save_export_name_btn.clicked.connect(self._on_save)
        export_name_layout.addWidget(self.save_export_name_btn)

        self.suggest_name_btn = QPushButton("Suggest")
        self.suggest_name_btn.setFixedWidth(70)
        self.suggest_name_btn.setToolTip("Auto-suggest export name from project metadata")
        self.suggest_name_btn.clicked.connect(self._suggest_export_name)
        export_name_layout.addWidget(self.suggest_name_btn)

        meta_layout.addRow("Export Name Match:", export_name_layout)

        # Rating
        rating_row = QHBoxLayout()
        self.rating_combo = QComboBox()
        self.rating_combo.addItems(["No Rating", "★", "★★", "★★★", "★★★★", "★★★★★"])
        rating_row.addWidget(self.rating_combo)
        rating_row.addStretch()
        meta_layout.addRow("Rating:", rating_row)

        # Favorite
        self.favorite_checkbox = QCheckBox("Mark as favorite")
        meta_layout.addRow("", self.favorite_checkbox)

        # Notes
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Add notes about this project...")
        self.notes_input.setMaximumHeight(100)
        meta_layout.addRow("Notes:", self.notes_input)

        layout.addWidget(meta_group)

        # Tags
        tags_group = QGroupBox("Tags")
        tags_group.setStyleSheet(self._group_box_style())
        tags_layout = QVBoxLayout(tags_group)

        self.tag_selector = ProjectTagSelector()
        self.tag_selector.tag_created.connect(self.tags_modified.emit)
        tags_layout.addWidget(self.tag_selector)

        layout.addWidget(tags_group)

        # Linked Exports with audio playback
        exports_group = QGroupBox("Linked Exports (audio files)")
        exports_group.setStyleSheet(self._group_box_style())
        exports_layout = QVBoxLayout(exports_group)

        self.exports_list = QListWidget()
        self.exports_list.setMaximumHeight(120)
        self.exports_list.itemDoubleClicked.connect(self._on_export_double_click)
        exports_layout.addWidget(self.exports_list)

        # Audio player controls
        player_layout = QHBoxLayout()

        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedWidth(40)
        self.play_btn.setToolTip("Play/Pause selected export")
        self.play_btn.clicked.connect(self._toggle_playback)
        player_layout.addWidget(self.play_btn)

        self.stop_btn = QPushButton("⬛")
        self.stop_btn.setFixedWidth(40)
        self.stop_btn.setToolTip("Stop playback")
        self.stop_btn.clicked.connect(self._stop_playback)
        player_layout.addWidget(self.stop_btn)

        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setEnabled(False)
        self.position_slider.sliderMoved.connect(self._on_slider_moved)
        player_layout.addWidget(self.position_slider)

        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setFixedWidth(100)
        player_layout.addWidget(self.time_label)

        exports_layout.addLayout(player_layout)

        # Volume control
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("🔊"))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setMaximumWidth(100)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addStretch()

        browse_exports_btn = QPushButton("Browse Exports...")
        browse_exports_btn.setToolTip(
            "Browse and select one or multiple audio files to link to this project"
        )
        browse_exports_btn.clicked.connect(self._browse_select_exports)
        volume_layout.addWidget(browse_exports_btn)

        find_exports_btn = QPushButton("Find Exports...")
        find_exports_btn.setToolTip("Scan for audio exports matching this project")
        find_exports_btn.clicked.connect(self._find_exports)
        volume_layout.addWidget(find_exports_btn)

        exports_layout.addLayout(volume_layout)

        layout.addWidget(exports_group)

        # Plugins section
        plugins_group = QGroupBox("Plugins (VST/AU)")
        plugins_group.setStyleSheet(self._group_box_style())
        plugins_layout = QVBoxLayout(plugins_group)

        self.plugins_list = QListWidget()
        self.plugins_list.setMaximumHeight(120)
        self.plugins_list.setAlternatingRowColors(True)
        plugins_layout.addWidget(self.plugins_list)

        layout.addWidget(plugins_group)

        # Ableton Devices section
        devices_group = QGroupBox("Ableton Devices")
        devices_group.setStyleSheet(self._group_box_style())
        devices_layout = QVBoxLayout(devices_group)

        self.devices_list = QListWidget()
        self.devices_list.setMaximumHeight(120)
        self.devices_list.setAlternatingRowColors(True)
        devices_layout.addWidget(self.devices_list)

        layout.addWidget(devices_group)

        # Export history from project metadata (found in ALS file)
        als_exports_group = QGroupBox("Export History (from project file)")
        als_exports_group.setStyleSheet(self._group_box_style())
        als_exports_layout = QVBoxLayout(als_exports_group)

        self.als_exports_label = QLabel("Loading...")
        self.als_exports_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']};")
        self.als_exports_label.setWordWrap(True)
        als_exports_layout.addWidget(self.als_exports_label)

        layout.addWidget(als_exports_group)

        # Available Project Backups
        backups_group = QGroupBox("Available Project Backups")
        backups_group.setStyleSheet(self._group_box_style())
        backups_layout = QVBoxLayout(backups_group)

        self.backups_list = QListWidget()
        self.backups_list.setMaximumHeight(120)
        self.backups_list.itemDoubleClicked.connect(self._on_backup_double_click)
        backups_layout.addWidget(self.backups_list)

        self.backups_loading_label = QLabel("Scanning for backups...")
        self.backups_loading_label.setStyleSheet(
            f"color: {AbletonTheme.COLORS['text_secondary']}; font-style: italic;"
        )
        backups_layout.addWidget(self.backups_loading_label)

        layout.addWidget(backups_group)

        # Similar Projects section
        similar_group = QGroupBox("Similar Projects")
        similar_group.setStyleSheet(self._group_box_style())
        similar_layout = QVBoxLayout(similar_group)

        self.similar_projects_list = QListWidget()
        self.similar_projects_list.setMaximumHeight(150)
        self.similar_projects_list.itemDoubleClicked.connect(self._on_similar_project_double_click)
        similar_layout.addWidget(self.similar_projects_list)

        self.similar_loading_label = QLabel("Analyzing similar projects...")
        self.similar_loading_label.setStyleSheet(
            f"color: {AbletonTheme.COLORS['text_secondary']}; font-style: italic;"
        )
        similar_layout.addWidget(self.similar_loading_label)

        refresh_similar_btn = QPushButton("Refresh Similar Projects")
        refresh_similar_btn.clicked.connect(self._load_similar_projects)
        similar_layout.addWidget(refresh_similar_btn)

        layout.addWidget(similar_group)

        # Add stretch at bottom
        layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _group_box_style(self) -> str:
        """Return consistent group box styling."""
        return f"""
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {AbletonTheme.COLORS['border']};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: {AbletonTheme.COLORS['surface']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: {AbletonTheme.COLORS['text_primary']};
            }}
        """

    def _connect_audio_signals(self) -> None:
        """Connect audio player signals."""
        self._audio_player = AudioPlayer.instance()
        self._audio_player.position_changed.connect(self._on_position_changed)
        self._audio_player.duration_changed.connect(self._on_duration_changed)
        self._audio_player.playback_started.connect(self._on_playback_started)
        self._audio_player.playback_stopped.connect(self._on_playback_stopped)
        self._audio_player.playback_paused.connect(self._on_playback_paused)
        self._audio_player.playback_finished.connect(self._on_playback_finished)
        self._audio_player.error_occurred.connect(self._on_playback_error)

    def set_project(self, project_id: int) -> None:
        """Load and display a project's properties."""
        # Stop any running threads
        self._stop_workers()

        self.project_id = project_id
        self._als_metadata = {}

        # Load basic project data immediately (fast DB query)
        self._load_project_sync()

        # Start background workers for heavy operations
        if self._project:
            self._start_backup_scan()
            self._start_similar_analysis()

    def _load_project_sync(self) -> None:
        """Load project data synchronously (fast operations only)."""
        session = get_session()
        try:
            self._project = session.query(Project).get(self.project_id)
            if not self._project:
                self.title_label.setText("Project not found")
                return

            # Title
            self.title_label.setText(self._project.name)

            # File info
            self.path_label.setText(self._project.file_path)
            self.path_label.setToolTip(self._project.file_path)

            # Size
            if self._project.file_size:
                size_mb = self._project.file_size / (1024 * 1024)
                if size_mb < 1:
                    self.size_label.setText(f"{size_mb * 1024:.0f} KB")
                else:
                    self.size_label.setText(f"{size_mb:.2f} MB")
            else:
                self.size_label.setText("Unknown")

            # Location
            if self._project.location:
                self.location_label.setText(self._project.location.name)
            else:
                self.location_label.setText("Unknown")

            # Ableton Version
            version_display = (
                self._project.ableton_version or self._project.get_live_version_display()
                if hasattr(self._project, "get_live_version_display")
                else None
            )
            self.version_label.setText(version_display or "Unknown")

            # Tempo
            if self._project.tempo and self._project.tempo > 0:
                self.tempo_label.setText(f"{self._project.tempo:.1f} BPM")
            else:
                self.tempo_label.setText("Unknown")

            # Time Signature
            time_sig = getattr(self._project, "time_signature", None)
            self.time_sig_label.setText(time_sig if time_sig else "Unknown")

            # Key/Scale
            key_display = (
                self._project.get_key_display()
                if hasattr(self._project, "get_key_display")
                else None
            )
            self.key_label.setText(key_display or "Unknown")

            # Arrangement Length (bars + duration)
            if self._project.arrangement_length and self._project.arrangement_length > 0:
                bars = int(self._project.arrangement_length)
                length_str = f"{bars} bars"
                # Add duration if available
                if (
                    hasattr(self._project, "arrangement_duration_seconds")
                    and self._project.arrangement_duration_seconds
                    and self._project.arrangement_duration_seconds > 0
                ):
                    dur_sec = int(self._project.arrangement_duration_seconds)
                    minutes = dur_sec // 60
                    seconds = dur_sec % 60
                    length_str += f" ({minutes}:{seconds:02d})"
                self.length_label.setText(length_str)
            else:
                self.length_label.setText("None")

            # Sample Length (longest session clip)
            if (
                hasattr(self._project, "furthest_sample_end")
                and self._project.furthest_sample_end
                and self._project.furthest_sample_end > 0
            ):
                sample_bars = int(self._project.furthest_sample_end)
                sample_str = f"{sample_bars} bars"
                if (
                    hasattr(self._project, "sample_duration_seconds")
                    and self._project.sample_duration_seconds
                    and self._project.sample_duration_seconds > 0
                ):
                    dur_sec = int(self._project.sample_duration_seconds)
                    minutes = dur_sec // 60
                    seconds = dur_sec % 60
                    sample_str += f" ({minutes}:{seconds:02d})"
                self.sample_length_label.setText(sample_str)
            else:
                self.sample_length_label.setText("None")

            # Timeline Markers
            markers = (
                self._project.get_timeline_markers_list()
                if hasattr(self._project, "get_timeline_markers_list")
                else []
            )
            marker_count = len(markers) if markers else 0
            if marker_count > 0:
                marker_names = [m.get("text", "") for m in markers if m.get("text")]
                if marker_names:
                    self.markers_label.setText(f"{marker_count} ({', '.join(marker_names[:5])})")
                    if len(marker_names) > 5:
                        self.markers_label.setToolTip(", ".join(marker_names))
                else:
                    self.markers_label.setText(str(marker_count))
            else:
                self.markers_label.setText("None")

            # Track count (with type breakdown)
            if self._project.track_count and self._project.track_count > 0:
                track_str = str(self._project.track_count)
                parts = []
                audio = getattr(self._project, "audio_tracks", 0) or 0
                midi = getattr(self._project, "midi_tracks", 0) or 0
                ret = getattr(self._project, "return_tracks", 0) or 0
                if audio:
                    parts.append(f"{audio}A")
                if midi:
                    parts.append(f"{midi}M")
                if ret:
                    parts.append(f"{ret}R")
                if parts:
                    track_str += f" ({', '.join(parts)})"
                self.track_count_label.setText(track_str)
            else:
                self.track_count_label.setText("Unknown")

            # Clip count
            clip_count = None
            if self._project.custom_metadata and isinstance(self._project.custom_metadata, dict):
                clip_count = self._project.custom_metadata.get(
                    "total_clip_count"
                ) or self._project.custom_metadata.get("clip_count")
            self.clip_count_label.setText(str(clip_count) if clip_count else "Unknown")

            # Sample count
            samples = (
                self._project.get_sample_references_list()
                if hasattr(self._project, "get_sample_references_list")
                else []
            )
            sample_count = len(samples) if samples else 0
            self.sample_count_label.setText(str(sample_count) if sample_count > 0 else "None")

            # Automation
            has_automation = getattr(self._project, "has_automation", None)
            self.automation_label.setText(
                "Yes" if has_automation else "No" if has_automation is not None else "Unknown"
            )

            # Annotation (project notes from ALS file)
            annotation = getattr(self._project, "annotation", None)
            if annotation and annotation.strip():
                # Truncate long annotations for display
                display_text = annotation.strip()
                if len(display_text) > 200:
                    self.annotation_label.setText(display_text[:200] + "...")
                    self.annotation_label.setToolTip(display_text)
                else:
                    self.annotation_label.setText(display_text)
            else:
                self.annotation_label.setText("None")

            # Dates
            if self._project.created_date:
                self.created_label.setText(self._project.created_date.strftime("%Y-%m-%d %H:%M:%S"))
            else:
                self.created_label.setText("Unknown")

            if self._project.modified_date:
                self.modified_label.setText(
                    self._project.modified_date.strftime("%Y-%m-%d %H:%M:%S")
                )
            else:
                self.modified_label.setText("Unknown")

            if self._project.last_scanned:
                self.scanned_label.setText(self._project.last_scanned.strftime("%Y-%m-%d %H:%M:%S"))
            else:
                self.scanned_label.setText("Never")

            if self._project.last_parsed:
                self.parsed_label.setText(self._project.last_parsed.strftime("%Y-%m-%d %H:%M:%S"))
            else:
                self.parsed_label.setText("Never")

            # Timeline Markers
            self._update_markers_display()

            # Plugins
            self.plugins_list.clear()
            plugins = (
                self._project.get_plugins_list()
                if hasattr(self._project, "get_plugins_list")
                else (self._project.plugins or [])
            )
            if plugins:
                for plugin in sorted(set(plugins)):  # Deduplicate and sort
                    item = QListWidgetItem(f"🔌 {plugin}")
                    self.plugins_list.addItem(item)
            else:
                item = QListWidgetItem("No plugins detected")
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.plugins_list.addItem(item)

            # Devices
            self.devices_list.clear()
            devices = (
                self._project.get_devices_list()
                if hasattr(self._project, "get_devices_list")
                else (self._project.devices or [])
            )
            if devices:
                for device in sorted(set(devices)):  # Deduplicate and sort
                    item = QListWidgetItem(f"🎛️ {device}")
                    self.devices_list.addItem(item)
            else:
                item = QListWidgetItem("No Ableton devices detected")
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.devices_list.addItem(item)

            # Metadata
            self.export_name_input.setText(self._project.export_song_name or "")
            self.rating_combo.setCurrentIndex(self._project.rating or 0)
            self.favorite_checkbox.setChecked(self._project.is_favorite)
            self.notes_input.setText(self._project.notes or "")

            # Populate export name suggestions
            self._populate_export_name_suggestions()

            # Tags - use junction table
            tag_ids = (
                [pt.tag_id for pt in self._project.project_tags]
                if self._project.project_tags
                else []
            )
            if not tag_ids and self._project.tags:
                # Fallback to legacy JSON field for backward compatibility
                tag_ids = self._project.tags if isinstance(self._project.tags, list) else []
            self.tag_selector.set_selected_tags(tag_ids)

            # Collections
            if self._project.project_collections:
                coll_names = [pc.collection.name for pc in self._project.project_collections]
                self.collections_label.setText(", ".join(coll_names))
            else:
                self.collections_label.setText("Not in any collections")

            # Exports (fast - from DB)
            self.exports_list.clear()
            if self._project.exports:
                for export in self._project.exports:
                    item = QListWidgetItem(f"🎵 {export.export_name}")
                    item.setData(Qt.ItemDataRole.UserRole, export.export_path)
                    item.setToolTip(export.export_path)
                    self.exports_list.addItem(item)
            else:
                item = QListWidgetItem("No exports linked")
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.exports_list.addItem(item)

            # Export history from ALS metadata (stored in DB from scan)
            self._update_als_exports_display()

            self.backups_list.clear()
            self.backups_loading_label.setText("Scanning for backups...")
            self.backups_loading_label.setVisible(True)

            self.similar_projects_list.clear()
            self.similar_loading_label.setText("Analyzing similar projects...")
            self.similar_loading_label.setVisible(True)

        finally:
            session.close()

    def _update_als_exports_display(self) -> None:
        """Update the export history display from stored DB metadata."""
        if not self._project:
            self.als_exports_label.setText("No project loaded")
            self.als_exports_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']};")
            return

        info_parts = []

        # Export filenames (stored as JSON)
        export_filenames = self._project.export_filenames
        if isinstance(export_filenames, str):
            import json

            try:
                export_filenames = json.loads(export_filenames)
            except (json.JSONDecodeError, TypeError):
                export_filenames = []

        if export_filenames:
            info_parts.append(f"📁 Export names: {', '.join(export_filenames)}")
            # Store in als_metadata for suggest button
            self._als_metadata["export_filenames"] = export_filenames

        if self._project.annotation:
            anno = self._project.annotation.strip()
            if len(anno) < 200:
                info_parts.append(f"📝 Annotation: {anno}")
            self._als_metadata["annotation"] = self._project.annotation

        if self._project.master_track_name:
            info_parts.append(f"🎚️ Master track: {self._project.master_track_name}")
            self._als_metadata["master_track_name"] = self._project.master_track_name

        if info_parts:
            self.als_exports_label.setText("\n".join(info_parts))
            self.als_exports_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_primary']};")
        else:
            self.als_exports_label.setText("No export history found in project file")
            self.als_exports_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']};")

    def _start_backup_scan(self) -> None:
        """Start backup scanning in background thread."""
        if not self._project:
            return

        self._backup_thread = QThread()
        # Create worker without parent - required for moveToThread
        self._backup_worker = BackupScanWorker(self._project.file_path, None)
        self._backup_worker.moveToThread(self._backup_thread)

        self._backup_thread.started.connect(self._backup_worker.run)
        self._backup_worker.finished.connect(self._on_backups_found)
        self._backup_worker.error.connect(self._on_backup_error)
        self._backup_worker.finished.connect(self._backup_thread.quit)
        self._backup_worker.error.connect(self._backup_thread.quit)

        self._backup_thread.start()

    def _on_backups_found(self, backups: list) -> None:
        """Handle backup scan completion."""
        self.backups_loading_label.setVisible(False)
        self.backups_list.clear()

        if backups:
            for backup in backups:
                item = QListWidgetItem(f"💾 {backup['name']} ({backup['date']})")
                item.setData(Qt.ItemDataRole.UserRole, backup["path"])
                item.setToolTip(backup["path"])
                self.backups_list.addItem(item)
        else:
            item = QListWidgetItem("No backup files found")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.backups_list.addItem(item)

    def _on_backup_error(self, error: str) -> None:
        """Handle backup scan error."""
        self.backups_loading_label.setVisible(False)
        item = QListWidgetItem(f"Error loading backups: {error}")
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        self.backups_list.addItem(item)

    def _start_similar_analysis(self) -> None:
        """Start similar projects analysis in background thread."""
        self._load_similar_projects()

    def _load_similar_projects(self) -> None:
        """Load and display similar projects (async)."""
        if not self._project:
            return

        # Reset UI
        self.similar_projects_list.clear()
        self.similar_loading_label.setText("Analyzing similar projects...")
        self.similar_loading_label.setVisible(True)

        # Prepare project data for worker (include stored feature vector)
        project_data: dict[str, Any] = {
            "id": self._project.id,
            "name": self._project.name,
            "plugins": self._project.get_plugins_list(),
            "devices": self._project.get_devices_list(),
            "tempo": self._project.tempo,
            "track_count": self._project.track_count,
            "audio_tracks": getattr(self._project, "audio_tracks", 0),
            "midi_tracks": getattr(self._project, "midi_tracks", 0),
            "arrangement_length": self._project.arrangement_length,
            "als_path": self._project.file_path,
            "feature_vector": (
                self._project.get_feature_vector_list()
                if hasattr(self._project, "get_feature_vector_list")
                else None
            ),
        }

        # Stop existing thread if running
        if self._similar_thread and self._similar_thread.isRunning():
            self._safely_stop_thread(self._similar_thread, self._similar_worker)
            self._similar_thread = None
            self._similar_worker = None

        self._similar_thread = QThread()
        # Create worker without parent - required for moveToThread
        self._similar_worker = SimilarProjectsWorker(self._project.id, project_data, None)
        self._similar_worker.moveToThread(self._similar_thread)

        self._similar_thread.started.connect(self._similar_worker.run)
        self._similar_worker.finished.connect(self._on_similar_found)
        self._similar_worker.error.connect(self._on_similar_error)
        self._similar_worker.finished.connect(self._similar_thread.quit)
        self._similar_worker.error.connect(self._similar_thread.quit)

        self._similar_thread.start()

    def _on_similar_found(self, similar: list) -> None:
        """Handle similar projects analysis completion."""
        self.similar_loading_label.setVisible(False)
        self.similar_projects_list.clear()

        if not similar:
            item = QListWidgetItem("No similar projects found (min similarity: 30%)")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.similar_projects_list.addItem(item)
            return

        for sim in similar:
            item_text = f"{sim['name']} ({sim['score']}%)"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, sim["id"])
            item.setToolTip(sim["explanation"] or f"Similarity: {sim['score']}%")
            self.similar_projects_list.addItem(item)

    def _on_similar_error(self, error: str) -> None:
        """Handle similar projects analysis error."""
        self.similar_loading_label.setVisible(False)
        item = QListWidgetItem(f"Error finding similar projects: {error}")
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        self.similar_projects_list.addItem(item)

    def _safely_stop_thread(self, thread: QThread | None, worker: object | None) -> None:
        """Safely stop a worker thread without blocking the UI.

        Disconnects all worker signals, requests cancellation, asks the thread to quit,
        and keeps a reference to still-running threads so Python's GC doesn't destroy
        the C++ QThread object while the OS thread is still active.

        This method is non-blocking - it never waits for threads to stop.

        Args:
            thread: The QThread to stop.
            worker: The worker object running on the thread.
        """
        # Purge orphaned threads that have since finished or been deleted by Qt
        still_running = []
        for t in self._orphaned_threads:
            try:
                if t.isRunning():
                    still_running.append(t)
            except RuntimeError:
                pass  # C++ object already deleted by deleteLater
        self._orphaned_threads = still_running

        if worker:
            # Cancel the worker so it exits at the next checkpoint
            if hasattr(worker, "cancel"):
                worker.cancel()
            # Disconnect all signals to prevent callbacks into stale UI state
            try:
                worker.finished.disconnect()
            except (TypeError, RuntimeError):
                pass
            try:
                worker.error.disconnect()
            except (TypeError, RuntimeError):
                pass

        if thread is None:
            if worker:
                worker.deleteLater()
            return

        if not thread.isRunning():
            # Thread already stopped - safe to clean up immediately
            thread.deleteLater()
            if worker:
                worker.deleteLater()
            return

        # Thread is still running - request quit, defer cleanup, don't block.
        # Connect finished->deleteLater so cleanup happens when thread stops.
        thread.finished.connect(thread.deleteLater)
        if worker:
            thread.finished.connect(worker.deleteLater)
        thread.quit()

        # Keep a Python reference so GC doesn't destroy the QThread
        # while the OS thread is still active (causes fatal crash).
        self._orphaned_threads.append(thread)

    def _stop_workers(self) -> None:
        """Stop all background workers."""
        self._safely_stop_thread(self._backup_thread, self._backup_worker)
        self._backup_thread = None
        self._backup_worker = None

        self._safely_stop_thread(self._similar_thread, self._similar_worker)
        self._similar_thread = None
        self._similar_worker = None

    def _populate_export_name_suggestions(self) -> None:
        """Populate the export name completer with suggestions."""
        suggestions = set()

        if self._project:
            suggestions.add(self._project.name)

            extracted = extract_song_name(self._project.name)
            if extracted:
                suggestions.add(extracted)

            if self._project.exports:
                for export in self._project.exports:
                    suggestions.add(export.export_name)
                    extracted = extract_song_name(export.export_name)
                    if extracted:
                        suggestions.add(extracted)

        model = QStringListModel(sorted(suggestions))
        self._export_name_completer.setModel(model)

    def _suggest_export_name(self) -> None:
        """Auto-suggest an export name based on project metadata and exports."""
        if not self._project:
            return

        suggestion = None
        source = "project name"

        # Try ALS metadata first (already loaded async)
        if self._als_metadata:
            if self._als_metadata.get("export_filenames"):
                suggestion = self._als_metadata["export_filenames"][0]
                source = "project export history"
            elif self._als_metadata.get("annotation"):
                anno = self._als_metadata["annotation"].strip()
                if len(anno) < 100 and "\n" not in anno:
                    suggestion = anno
                    source = "project annotation"
            elif self._als_metadata.get("master_track_name"):
                suggestion = self._als_metadata["master_track_name"]
                source = "master track name"

        # Try linked exports
        if not suggestion and self._project.exports:
            sorted_exports = sorted(
                self._project.exports, key=lambda e: e.export_date or datetime.min, reverse=True
            )
            if sorted_exports:
                suggestion = extract_song_name(sorted_exports[0].export_name)
                source = "linked exports"

        # Fall back to project name
        if not suggestion:
            suggestion = extract_song_name(self._project.name)
            source = "project name"

        if not suggestion:
            suggestion = self._project.name
            source = "project name"

        self.export_name_input.setText(suggestion)

        QMessageBox.information(
            self,
            "Export Name Suggested",
            f"Suggested export name: {suggestion}\n\n"
            f"Source: {source}\n\n"
            "This was derived from your project metadata. "
            "You can edit it as needed.",
        )

    def _on_save(self) -> None:
        """Save changes."""
        session = get_session()
        try:
            project = session.query(Project).get(self.project_id)
            if project:
                project.export_song_name = self.export_name_input.text().strip() or None
                project.rating = self.rating_combo.currentIndex() or None
                project.is_favorite = self.favorite_checkbox.isChecked()
                project.notes = self.notes_input.toPlainText().strip() or None

                # Update tags using junction table
                selected_tag_ids = set(self.tag_selector.get_selected_tags())
                current_tag_ids = {pt.tag_id for pt in project.project_tags}

                # Remove tags that are no longer selected
                for pt in list(project.project_tags):
                    if pt.tag_id not in selected_tag_ids:
                        session.delete(pt)

                # Add new tags
                for tag_id in selected_tag_ids:
                    if tag_id not in current_tag_ids:
                        # Verify tag exists
                        from ...database import Tag

                        tag = session.query(Tag).get(tag_id)
                        if tag:
                            pt = ProjectTag(project_id=project.id, tag_id=tag_id)
                            session.add(pt)

                # Also update legacy JSON field for backward compatibility
                project.tags = list(selected_tag_ids)

                session.commit()

                # Update local reference
                self._project = project

                self.project_saved.emit()

                QMessageBox.information(self, "Saved", "Project properties saved successfully.")
        finally:
            session.close()

    def _open_folder(self) -> None:
        """Open the project folder in file manager."""
        import subprocess
        import sys

        if self._project:
            path = Path(self._project.file_path)
            if path.exists():
                if sys.platform == "win32":
                    subprocess.run(["explorer", "/select,", str(path)])
                elif sys.platform == "darwin":
                    subprocess.run(["open", "-R", str(path)])
                else:
                    subprocess.run(["xdg-open", str(path.parent)])

    def _add_to_collection(self) -> None:
        """Show dialog to add project to a collection."""
        from PyQt6.QtWidgets import QInputDialog

        session = get_session()
        try:
            collections = session.query(Collection).order_by(Collection.name).all()

            if not collections:
                QMessageBox.information(
                    self, "No Collections", "No collections exist. Create a collection first."
                )
                return

            coll_names = [c.name for c in collections]

            name, ok = QInputDialog.getItem(
                self, "Add to Collection", "Select collection:", coll_names, editable=False
            )

            if ok and name:
                collection = next((c for c in collections if c.name == name), None)
                if collection:
                    existing = (
                        session.query(ProjectCollection)
                        .filter(
                            ProjectCollection.project_id == self.project_id,
                            ProjectCollection.collection_id == collection.id,
                        )
                        .first()
                    )

                    if existing:
                        QMessageBox.information(
                            self, "Already Added", f"This project is already in '{name}'."
                        )
                        return

                    max_track = (
                        session.query(ProjectCollection)
                        .filter(ProjectCollection.collection_id == collection.id)
                        .count()
                    )

                    pc = ProjectCollection(
                        project_id=self.project_id,
                        collection_id=collection.id,
                        track_number=max_track + 1,
                    )
                    session.add(pc)
                    session.commit()

                    # Refresh collections display
                    self._load_project_sync()
        finally:
            session.close()

    # Audio playback methods
    def _get_selected_export_path(self) -> str | None:
        """Get the file path of the selected export."""
        item = self.exports_list.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def _on_export_double_click(self, item: QListWidgetItem) -> None:
        """Handle double-click on export item to play it."""
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path and Path(file_path).exists():
            self._audio_player.play(file_path)

    def _toggle_playback(self) -> None:
        """Toggle play/pause for selected export."""
        file_path = self._get_selected_export_path()
        if file_path:
            if Path(file_path).exists():
                self._audio_player.toggle_play_pause(file_path)
            else:
                QMessageBox.warning(self, "File Not Found", f"Export file not found:\n{file_path}")
        else:
            QMessageBox.information(self, "No Selection", "Please select an export to play.")

    def _stop_playback(self) -> None:
        """Stop audio playback."""
        self._audio_player.stop()

    def _on_slider_moved(self, position: int) -> None:
        """Handle position slider being moved by user."""
        self._audio_player.seek(position)

    def _on_volume_changed(self, value: int) -> None:
        """Handle volume slider change."""
        self._audio_player.volume = value / 100.0

    def _on_position_changed(self, position: int) -> None:
        """Handle playback position change."""
        if not self.position_slider.isSliderDown():
            self.position_slider.setValue(position)

        duration = self._audio_player.duration
        self.time_label.setText(f"{format_duration(position)} / {format_duration(duration)}")

    def _on_duration_changed(self, duration: int) -> None:
        """Handle duration change when new file is loaded."""
        self.position_slider.setRange(0, duration)
        self.position_slider.setEnabled(True)

    def _on_playback_started(self, file_path: str) -> None:
        """Handle playback started."""
        self.play_btn.setText("⏸")
        self.play_btn.setToolTip("Pause playback")

    def _on_playback_stopped(self) -> None:
        """Handle playback stopped."""
        self.play_btn.setText("▶")
        self.play_btn.setToolTip("Play selected export")
        self.position_slider.setValue(0)
        self.time_label.setText("0:00 / 0:00")

    def _on_playback_paused(self) -> None:
        """Handle playback paused."""
        self.play_btn.setText("▶")
        self.play_btn.setToolTip("Resume playback")

    def _on_playback_finished(self) -> None:
        """Handle playback finished naturally."""
        self._on_playback_stopped()

    def _on_playback_error(self, error: str) -> None:
        """Handle playback error."""
        QMessageBox.warning(self, "Playback Error", error)
        self._on_playback_stopped()

    def _on_backup_double_click(self, item: QListWidgetItem) -> None:
        """Handle double-click on backup item to launch it."""
        backup_path_str = item.data(Qt.ItemDataRole.UserRole)
        if not backup_path_str:
            return

        backup_path = Path(backup_path_str)
        if not backup_path.exists():
            QMessageBox.warning(
                self, "Backup Not Found", f"The backup file could not be found:\n{backup_path}"
            )
            return

        from ...services.live_detector import LiveVersion
        from ...services.live_launcher import LiveLauncher
        from ...controllers.live_controller import LiveController

        launcher = LiveLauncher()
        live_controller = LiveController()

        # Get best installation for this backup (matches version or uses default)
        matching_install = live_controller.get_installation_for_project_path(backup_path)

        if not matching_install:
            self.no_live_installation_requested.emit()
            return

        exe_path = Path(matching_install.executable_path)
        if not exe_path.exists():
            QMessageBox.warning(
                self,
                "Installation Not Found",
                f"The Live installation could not be found:\n{matching_install.executable_path}\n\n"
                "Please update or remove this installation.",
            )
            return

        # Convert LiveInstallation to LiveVersion for launcher
        live_version = LiveVersion(
            version=matching_install.version,
            path=exe_path,
            build=matching_install.build,
            is_suite=matching_install.is_suite,
        )

        # Launch directly - no confirmation dialog
        success = launcher.launch_project(backup_path, live_version)
        if success:
            QMessageBox.information(
                self,
                "Backup Launched",
                f"Opening backup:\n{backup_path.name}\n\nwith {matching_install.name}",
            )
        else:
            QMessageBox.critical(
                self,
                "Launch Failed",
                f"Failed to launch {matching_install.name} with backup:\n{backup_path.name}\n\n"
                "Please check that Live is installed and try again.",
            )

    def _on_similar_project_double_click(self, item: QListWidgetItem) -> None:
        """Handle double-click on similar project - navigate to its properties."""
        project_id = item.data(Qt.ItemDataRole.UserRole)
        if project_id:
            self.set_project(project_id)

    def _browse_select_exports(self) -> None:
        """Browse and select audio files to link as exports."""
        if not self._project:
            return

        from PyQt6.QtWidgets import QFileDialog

        from ...services.export_tracker import ExportTracker

        # Get project path for initial directory
        initial_dir = str(Path(self._project.file_path).parent)

        # Open file dialog for multiple files
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Export Files",
            initial_dir,
            "Audio Files (*.wav *.mp3 *.flac *.aiff *.aif *.ogg *.m4a);;All Files (*.*)",
        )

        if not file_paths:
            return

        # Link selected files to project
        tracker = ExportTracker()
        linked_count = 0

        session = get_session()
        try:
            for file_path in file_paths:
                path = Path(file_path)
                if path.suffix.lower() not in {
                    ".wav",
                    ".mp3",
                    ".flac",
                    ".aiff",
                    ".aif",
                    ".ogg",
                    ".m4a",
                }:
                    continue

                # Add export to database and link to project
                export_id = tracker.add_export(file_path, self.project_id)
                if export_id:
                    linked_count += 1

            if linked_count > 0:
                session.commit()
                QMessageBox.information(
                    self,
                    "Exports Linked",
                    f"Successfully linked {linked_count} export(s) to this project.",
                )
                # Reload project to show newly linked exports
                self._load_project_sync()
            else:
                QMessageBox.information(
                    self,
                    "No Files Linked",
                    "No valid audio files were selected or files could not be linked.",
                )
        finally:
            session.close()

    def _update_markers_display(self) -> None:
        """Update the timeline markers display."""
        if not self._project:
            return

        self.markers_list.clear()

        # Get markers from project
        markers = (
            self._project.get_timeline_markers_list()
            if hasattr(self._project, "get_timeline_markers_list")
            else []
        )

        if not markers:
            item = QListWidgetItem("No timeline markers found")
            item.setFlags(Qt.ItemFlag.NoItemFlags)  # Make it non-selectable
            self.markers_list.addItem(item)
            return

        # Display markers with formatted time
        for marker in markers:
            time_sec = marker.get("time", 0.0)
            text = marker.get("text", "")

            # Format time as MM:SS.mmm
            minutes = int(time_sec // 60)
            seconds = int(time_sec % 60)
            milliseconds = int((time_sec % 1) * 1000)

            if minutes > 0:
                time_str = f"{minutes}:{seconds:02d}.{milliseconds:03d}"
            else:
                time_str = f"{seconds}.{milliseconds:03d}"

            item_text = f"{time_str}  {text}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, marker)  # Store full marker data
            self.markers_list.addItem(item)

    def _export_markers(self) -> None:
        """Export timeline markers to a text or CSV file."""
        if not self._project:
            return

        markers = (
            self._project.get_timeline_markers_list()
            if hasattr(self._project, "get_timeline_markers_list")
            else []
        )

        if not markers:
            QMessageBox.information(
                self, "No Markers", "This project has no timeline markers to export."
            )
            return

        from PyQt6.QtWidgets import QFileDialog

        # Get project directory for initial save location
        project_dir = Path(self._project.file_path).parent
        default_filename = f"{self._project.name}_markers.txt"
        default_path = project_dir / default_filename

        # Open save dialog
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Timeline Markers",
            str(default_path),
            "Text Files (*.txt);;CSV Files (*.csv);;All Files (*.*)",
        )

        if not file_path:
            return

        try:
            from ...services.marker_export import export_markers_to_csv, export_markers_to_text

            path = Path(file_path)
            if path.suffix.lower() == ".csv":
                export_markers_to_csv(markers, path)
            else:
                export_markers_to_text(markers, path)

            QMessageBox.information(
                self, "Export Successful", f"Timeline markers exported to:\n{file_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export markers:\n{str(e)}")

    def _find_exports(self) -> None:
        """Find and link exports for this project."""
        from ...services.export_tracker import ExportTracker

        if not self._project:
            return

        tracker = ExportTracker()

        session = get_session()
        try:
            matched = tracker.auto_match_exports(threshold=60.0)

            if matched > 0:
                QMessageBox.information(
                    self, "Exports Found", f"Found and linked {matched} export(s)."
                )
                self._load_project_sync()
            else:
                QMessageBox.information(
                    self,
                    "No Exports Found",
                    "No matching exports were found.\n\n"
                    "Make sure your export folders are added as locations "
                    "and have been scanned.",
                )
        finally:
            session.close()

    def cleanup(self) -> None:
        """Clean up resources when view is hidden or destroyed."""
        self._stop_workers()
        self._audio_player.stop()
