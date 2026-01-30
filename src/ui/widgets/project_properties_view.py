"""Project properties view widget - replaces the dialog with a main window view."""

from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QLineEdit, QTextEdit, QComboBox,
    QMessageBox, QGroupBox, QCheckBox, QSlider,
    QListWidget, QListWidgetItem, QCompleter, QScrollArea, QFrame,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QStringListModel, pyqtSignal, QThread, QObject
from PyQt6.QtGui import QColor

from ...database import get_session, Project, Location, Collection, ProjectCollection, Export
from ...services.audio_player import AudioPlayer, format_duration
from ...utils.fuzzy_match import extract_song_name
from ...utils.paths import find_backup_files
from ..widgets.tag_editor import ProjectTagSelector
from ..theme import AbletonTheme


class ALSParserWorker(QObject):
    """Worker for parsing ALS files in background thread."""
    
    finished = pyqtSignal(dict)  # Emits metadata dict
    error = pyqtSignal(str)
    
    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
    
    def run(self):
        """Parse the ALS file and emit results."""
        try:
            from ...services.als_parser import ALSParser
            parser = ALSParser()
            metadata = parser.parse(Path(self.file_path))
            
            result = {}
            if metadata:
                result['export_filenames'] = metadata.export_filenames or []
                result['annotation'] = metadata.annotation
                result['master_track_name'] = metadata.master_track_name
            
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e)[:100])


class BackupScanWorker(QObject):
    """Worker for scanning backup files in background thread."""
    
    finished = pyqtSignal(list)  # Emits list of backup file paths
    error = pyqtSignal(str)
    
    def __init__(self, project_path: str):
        super().__init__()
        self.project_path = project_path
    
    def run(self):
        """Scan for backup files and emit results."""
        try:
            backup_files = find_backup_files(Path(self.project_path))
            result = []
            for backup_path in backup_files:
                mod_time = datetime.fromtimestamp(backup_path.stat().st_mtime)
                result.append({
                    'path': str(backup_path),
                    'name': backup_path.name,
                    'date': mod_time.strftime("%Y-%m-%d %H:%M")
                })
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e)[:100])


class SimilarProjectsWorker(QObject):
    """Worker for finding similar projects in background thread."""
    
    finished = pyqtSignal(list)  # Emits list of similar projects
    error = pyqtSignal(str)
    
    def __init__(self, project_id: int, project_data: dict):
        super().__init__()
        self.project_id = project_id
        self.project_data = project_data
    
    def run(self):
        """Find similar projects and emit results."""
        try:
            from ...services.similarity_analyzer import SimilarityAnalyzer
            from ...database import get_session, Project as ProjectModel
            
            analyzer = SimilarityAnalyzer()
            
            session = get_session()
            try:
                all_projects = session.query(ProjectModel).filter(
                    ProjectModel.id != self.project_id
                ).all()
                
                if not all_projects:
                    self.finished.emit([])
                    return
                
                candidate_dicts = []
                for p in all_projects:
                    candidate_dicts.append({
                        'id': p.id,
                        'name': p.name,
                        'plugins': p.plugins or [],
                        'devices': p.devices or [],
                        'tempo': p.tempo,
                        'track_count': p.track_count,
                        'audio_tracks': getattr(p, 'audio_tracks', 0),
                        'midi_tracks': getattr(p, 'midi_tracks', 0),
                        'arrangement_length': p.arrangement_length,
                        'als_path': p.file_path
                    })
                
                similar = analyzer.find_similar_projects(
                    reference_project=self.project_data,
                    candidate_projects=candidate_dicts,
                    top_n=10,
                    min_similarity=0.3
                )
                
                result = []
                for sim_project in similar:
                    score_percent = int(sim_project.similarity_score * 100)
                    explanation = ""
                    if sim_project.similarity_result:
                        explanation = analyzer.get_similarity_explanation(sim_project.similarity_result)
                    
                    result.append({
                        'id': sim_project.project_id,
                        'name': sim_project.project_name,
                        'score': score_percent,
                        'explanation': explanation
                    })
                
                self.finished.emit(result)
            finally:
                session.close()
        except Exception as e:
            self.error.emit(str(e)[:100])


class ProjectPropertiesView(QWidget):
    """View for displaying and editing project properties - embedded in main window."""
    
    back_requested = pyqtSignal()
    project_selected = pyqtSignal(int)  # For similar project navigation
    tags_modified = pyqtSignal()  # Emitted when tags are created/modified
    project_saved = pyqtSignal()  # Emitted when changes are saved
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.project_id: Optional[int] = None
        self._project: Optional[Project] = None
        self._als_metadata: Dict[str, Any] = {}
        
        # Background workers and their threads
        self._als_thread: Optional[QThread] = None
        self._als_worker: Optional[ALSParserWorker] = None
        self._backup_thread: Optional[QThread] = None
        self._backup_worker: Optional[BackupScanWorker] = None
        self._similar_thread: Optional[QThread] = None
        self._similar_worker: Optional[SimilarProjectsWorker] = None
        
        self._setup_ui()
        self._connect_audio_signals()
    
    def _setup_ui(self) -> None:
        """Set up the view UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header row with back button
        header = QWidget()
        header.setStyleSheet(f"background-color: {AbletonTheme.COLORS['surface']}; border-bottom: 1px solid {AbletonTheme.COLORS['border']};")
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
        self.save_btn.setToolTip("Save all changes including Export Name Match.\nThe Export Name Match is used to link audio exports to this project.")
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
        self.title_label.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {AbletonTheme.COLORS['text_primary']};")
        layout.addWidget(self.title_label)
        
        # File info (read-only)
        file_group = QGroupBox("File Information")
        file_group.setStyleSheet(self._group_box_style())
        file_layout = QFormLayout(file_group)
        file_layout.setSpacing(8)
        
        self.path_label = QLabel()
        self.path_label.setWordWrap(True)
        self.path_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']};")
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        file_layout.addRow("Path:", self.path_label)
        
        self.size_label = QLabel()
        file_layout.addRow("Size:", self.size_label)
        
        self.modified_label = QLabel()
        file_layout.addRow("Modified:", self.modified_label)
        
        self.location_label = QLabel()
        file_layout.addRow("Location:", self.location_label)
        
        # Open folder button
        open_folder_btn = QPushButton("Open in File Manager")
        open_folder_btn.clicked.connect(self._open_folder)
        file_layout.addRow("", open_folder_btn)
        
        layout.addWidget(file_group)
        
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
        self.save_export_name_btn.setToolTip("Save this export name to associate audio exports with this project.\nExports matching this name will be automatically linked.")
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
        
        # Export history from project metadata (found in ALS file)
        als_exports_group = QGroupBox("Export History (from project file)")
        als_exports_group.setStyleSheet(self._group_box_style())
        als_exports_layout = QVBoxLayout(als_exports_group)
        
        self.als_exports_label = QLabel("Loading...")
        self.als_exports_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']};")
        self.als_exports_label.setWordWrap(True)
        als_exports_layout.addWidget(self.als_exports_label)
        
        layout.addWidget(als_exports_group)
        
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
        
        find_exports_btn = QPushButton("Find Exports...")
        find_exports_btn.setToolTip("Scan for audio exports matching this project")
        find_exports_btn.clicked.connect(self._find_exports)
        volume_layout.addWidget(find_exports_btn)
        
        exports_layout.addLayout(volume_layout)
        
        layout.addWidget(exports_group)
        
        # Available Project Backups
        backups_group = QGroupBox("Available Project Backups")
        backups_group.setStyleSheet(self._group_box_style())
        backups_layout = QVBoxLayout(backups_group)
        
        self.backups_list = QListWidget()
        self.backups_list.setMaximumHeight(120)
        self.backups_list.itemDoubleClicked.connect(self._on_backup_double_click)
        backups_layout.addWidget(self.backups_list)
        
        self.backups_loading_label = QLabel("Scanning for backups...")
        self.backups_loading_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-style: italic;")
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
        self.similar_loading_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-style: italic;")
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
            self._start_als_parser()
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
                self.size_label.setText(f"{size_mb:.2f} MB")
            else:
                self.size_label.setText("Unknown")
            
            # Modified
            if self._project.modified_date:
                self.modified_label.setText(
                    self._project.modified_date.strftime("%Y-%m-%d %H:%M:%S")
                )
            else:
                self.modified_label.setText("Unknown")
            
            # Location
            if self._project.location:
                self.location_label.setText(self._project.location.name)
            else:
                self.location_label.setText("Unknown")
            
            # Metadata
            self.export_name_input.setText(self._project.export_song_name or "")
            self.rating_combo.setCurrentIndex(self._project.rating or 0)
            self.favorite_checkbox.setChecked(self._project.is_favorite)
            self.notes_input.setText(self._project.notes or "")
            
            # Populate export name suggestions
            self._populate_export_name_suggestions()
            
            # Tags
            if self._project.tags:
                self.tag_selector.set_selected_tags(self._project.tags)
            else:
                self.tag_selector.set_selected_tags([])
            
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
            
            # Reset loading indicators
            self.als_exports_label.setText("Loading export history...")
            self.als_exports_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-style: italic;")
            
            self.backups_list.clear()
            self.backups_loading_label.setText("Scanning for backups...")
            self.backups_loading_label.setVisible(True)
            
            self.similar_projects_list.clear()
            self.similar_loading_label.setText("Analyzing similar projects...")
            self.similar_loading_label.setVisible(True)
            
        finally:
            session.close()
    
    def _start_als_parser(self) -> None:
        """Start ALS parsing in background thread."""
        if not self._project:
            return
        
        self._als_thread = QThread()
        self._als_worker = ALSParserWorker(self._project.file_path)
        self._als_worker.moveToThread(self._als_thread)
        
        self._als_thread.started.connect(self._als_worker.run)
        self._als_worker.finished.connect(self._on_als_parsed)
        self._als_worker.error.connect(self._on_als_error)
        self._als_worker.finished.connect(self._als_thread.quit)
        self._als_worker.error.connect(self._als_thread.quit)
        
        self._als_thread.start()
    
    def _on_als_parsed(self, metadata: dict) -> None:
        """Handle ALS parsing completion."""
        self._als_metadata = metadata
        
        info_parts = []
        
        if metadata.get('export_filenames'):
            info_parts.append(f"📁 Export names: {', '.join(metadata['export_filenames'])}")
        
        if metadata.get('annotation'):
            anno = metadata['annotation'].strip()
            if len(anno) < 200:
                info_parts.append(f"📝 Annotation: {anno}")
        
        if metadata.get('master_track_name'):
            info_parts.append(f"🎚️ Master track: {metadata['master_track_name']}")
        
        if info_parts:
            self.als_exports_label.setText("\n".join(info_parts))
            self.als_exports_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_primary']};")
        else:
            self.als_exports_label.setText("No export history found in project file")
            self.als_exports_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']};")
    
    def _on_als_error(self, error: str) -> None:
        """Handle ALS parsing error."""
        self.als_exports_label.setText(f"Error reading project: {error}")
        self.als_exports_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']};")
    
    def _start_backup_scan(self) -> None:
        """Start backup scanning in background thread."""
        if not self._project:
            return
        
        self._backup_thread = QThread()
        self._backup_worker = BackupScanWorker(self._project.file_path)
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
                item.setData(Qt.ItemDataRole.UserRole, backup['path'])
                item.setToolTip(backup['path'])
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
        
        # Prepare project data for worker
        project_data = {
            'id': self._project.id,
            'name': self._project.name,
            'plugins': self._project.plugins or [],
            'devices': self._project.devices or [],
            'tempo': self._project.tempo,
            'track_count': self._project.track_count,
            'audio_tracks': getattr(self._project, 'audio_tracks', 0),
            'midi_tracks': getattr(self._project, 'midi_tracks', 0),
            'arrangement_length': self._project.arrangement_length,
            'als_path': self._project.file_path
        }
        
        # Stop existing thread if running
        if self._similar_thread and self._similar_thread.isRunning():
            self._similar_thread.quit()
            self._similar_thread.wait()
        
        self._similar_thread = QThread()
        self._similar_worker = SimilarProjectsWorker(self._project.id, project_data)
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
            item.setData(Qt.ItemDataRole.UserRole, sim['id'])
            item.setToolTip(sim['explanation'] or f"Similarity: {sim['score']}%")
            self.similar_projects_list.addItem(item)
    
    def _on_similar_error(self, error: str) -> None:
        """Handle similar projects analysis error."""
        self.similar_loading_label.setVisible(False)
        item = QListWidgetItem(f"Error finding similar projects: {error}")
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        self.similar_projects_list.addItem(item)
    
    def _stop_workers(self) -> None:
        """Stop all background workers."""
        if self._als_thread and self._als_thread.isRunning():
            self._als_thread.quit()
            self._als_thread.wait(1000)
        self._als_thread = None
        self._als_worker = None
        
        if self._backup_thread and self._backup_thread.isRunning():
            self._backup_thread.quit()
            self._backup_thread.wait(1000)
        self._backup_thread = None
        self._backup_worker = None
        
        if self._similar_thread and self._similar_thread.isRunning():
            self._similar_thread.quit()
            self._similar_thread.wait(1000)
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
            if self._als_metadata.get('export_filenames'):
                suggestion = self._als_metadata['export_filenames'][0]
                source = "project export history"
            elif self._als_metadata.get('annotation'):
                anno = self._als_metadata['annotation'].strip()
                if len(anno) < 100 and '\n' not in anno:
                    suggestion = anno
                    source = "project annotation"
            elif self._als_metadata.get('master_track_name'):
                suggestion = self._als_metadata['master_track_name']
                source = "master track name"
        
        # Try linked exports
        if not suggestion and self._project.exports:
            sorted_exports = sorted(
                self._project.exports,
                key=lambda e: e.export_date or datetime.min,
                reverse=True
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
            self, "Export Name Suggested",
            f"Suggested export name: {suggestion}\n\n"
            f"Source: {source}\n\n"
            "This was derived from your project metadata. "
            "You can edit it as needed."
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
                project.tags = self.tag_selector.get_selected_tags()
                
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
                    self, "No Collections",
                    "No collections exist. Create a collection first."
                )
                return
            
            coll_names = [c.name for c in collections]
            
            name, ok = QInputDialog.getItem(
                self,
                "Add to Collection",
                "Select collection:",
                coll_names,
                editable=False
            )
            
            if ok and name:
                collection = next((c for c in collections if c.name == name), None)
                if collection:
                    existing = session.query(ProjectCollection).filter(
                        ProjectCollection.project_id == self.project_id,
                        ProjectCollection.collection_id == collection.id
                    ).first()
                    
                    if existing:
                        QMessageBox.information(
                            self, "Already Added",
                            f"This project is already in '{name}'."
                        )
                        return
                    
                    max_track = session.query(ProjectCollection).filter(
                        ProjectCollection.collection_id == collection.id
                    ).count()
                    
                    pc = ProjectCollection(
                        project_id=self.project_id,
                        collection_id=collection.id,
                        track_number=max_track + 1
                    )
                    session.add(pc)
                    session.commit()
                    
                    # Refresh collections display
                    self._load_project_sync()
        finally:
            session.close()
    
    # Audio playback methods
    def _get_selected_export_path(self) -> Optional[str]:
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
                QMessageBox.warning(
                    self, "File Not Found",
                    f"Export file not found:\n{file_path}"
                )
        else:
            QMessageBox.information(
                self, "No Selection",
                "Please select an export to play."
            )
    
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
                self,
                "Backup Not Found",
                f"The backup file could not be found:\n{backup_path}"
            )
            return
        
        from ...services.live_launcher import LiveLauncher
        from ...services.live_detector import LiveVersion
        from ...database import LiveInstallation
        
        session = get_session()
        try:
            favorite_install = session.query(LiveInstallation).filter(
                LiveInstallation.is_favorite == True
            ).first()
            
            launcher = LiveLauncher()
            
            if favorite_install:
                exe_path = Path(favorite_install.executable_path)
                if exe_path.exists():
                    live_version = LiveVersion(
                        version=favorite_install.version,
                        path=exe_path,
                        build=favorite_install.build,
                        is_suite=favorite_install.is_suite
                    )
                    success = launcher.launch_project(backup_path, live_version)
                    if success:
                        QMessageBox.information(
                            self,
                            "Backup Launched",
                            f"Opening backup:\n{backup_path.name}\n\nwith {favorite_install.name}"
                        )
                        return
                    else:
                        QMessageBox.critical(
                            self,
                            "Launch Failed",
                            f"Failed to launch {favorite_install.name} with backup:\n{backup_path.name}"
                        )
                        return
            
            from ..dialogs.live_version_dialog import LiveVersionDialog
            from PyQt6.QtWidgets import QDialog
            dialog = LiveVersionDialog(backup_path.name, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_version = dialog.get_selected_version()
                if selected_version:
                    success = launcher.launch_project(backup_path, selected_version)
                    if not success:
                        QMessageBox.critical(
                            self,
                            "Launch Failed",
                            f"Failed to launch Ableton Live with this backup.\n\n"
                            f"Please check that Live is installed and try again."
                        )
        finally:
            session.close()
    
    def _on_similar_project_double_click(self, item: QListWidgetItem) -> None:
        """Handle double-click on similar project - navigate to its properties."""
        project_id = item.data(Qt.ItemDataRole.UserRole)
        if project_id:
            self.set_project(project_id)
    
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
                    self, "Exports Found",
                    f"Found and linked {matched} export(s)."
                )
                self._load_project_sync()
            else:
                QMessageBox.information(
                    self, "No Exports Found",
                    "No matching exports were found.\n\n"
                    "Make sure your export folders are added as locations "
                    "and have been scanned."
                )
        finally:
            session.close()
    
    def cleanup(self) -> None:
        """Clean up resources when view is hidden or destroyed."""
        self._stop_workers()
        self._audio_player.stop()
