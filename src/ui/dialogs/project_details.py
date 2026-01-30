"""Project details/properties dialog."""

from typing import Optional, List
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QLineEdit, QTextEdit, QComboBox, QSpinBox,
    QDialogButtonBox, QMessageBox, QGroupBox, QCheckBox, QSlider,
    QWidget, QListWidget, QListWidgetItem, QCompleter
)
from PyQt6.QtCore import Qt, QStringListModel, pyqtSignal
from PyQt6.QtGui import QColor

from ...database import get_session, Project, Location, Collection, ProjectCollection, Export
from ...services.audio_player import AudioPlayer, format_duration
from ...utils.fuzzy_match import extract_song_name
from ...utils.paths import find_backup_files
from ..widgets.tag_editor import ProjectTagSelector
from ..theme import AbletonTheme


class ProjectDetailsDialog(QDialog):
    """Dialog for viewing and editing project details."""
    
    tags_modified = pyqtSignal()  # Emitted when tags are created/modified
    
    def __init__(self, project_id: int, parent=None):
        super().__init__(parent)
        
        self.project_id = project_id
        self._project: Optional[Project] = None
        
        self.setWindowTitle("Project Properties")
        self.setMinimumSize(600, 500)
        
        self._setup_ui()
        self._load_project()
    
    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # File info (read-only)
        file_group = QGroupBox("File Information")
        file_layout = QFormLayout(file_group)
        
        self.name_label = QLabel()
        self.name_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        file_layout.addRow("Name:", self.name_label)
        
        self.path_label = QLabel()
        self.path_label.setWordWrap(True)
        self.path_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']};")
        file_layout.addRow("Path:", self.path_label)
        
        self.size_label = QLabel()
        file_layout.addRow("Size:", self.size_label)
        
        self.modified_label = QLabel()
        file_layout.addRow("Modified:", self.modified_label)
        
        self.location_label = QLabel()
        file_layout.addRow("Location:", self.location_label)
        
        layout.addWidget(file_group)
        
        # Metadata (editable)
        meta_group = QGroupBox("Metadata")
        meta_layout = QFormLayout(meta_group)
        
        # Export song name with auto-suggest
        export_name_layout = QHBoxLayout()
        self.export_name_input = QLineEdit()
        self.export_name_input.setPlaceholderText("Song name for exports (used for fuzzy matching)")
        
        # Set up completer for export name suggestions
        self._export_name_completer = QCompleter()
        self._export_name_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._export_name_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.export_name_input.setCompleter(self._export_name_completer)
        export_name_layout.addWidget(self.export_name_input)
        
        # Auto-suggest button
        self.suggest_name_btn = QPushButton("Suggest")
        self.suggest_name_btn.setFixedWidth(60)
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
        tags_layout = QVBoxLayout(tags_group)
        
        self.tag_selector = ProjectTagSelector()
        self.tag_selector.tag_created.connect(self.tags_modified.emit)
        tags_layout.addWidget(self.tag_selector)
        
        layout.addWidget(tags_group)
        
        # Collections
        collections_group = QGroupBox("Collections")
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
        als_exports_layout = QVBoxLayout(als_exports_group)
        
        self.als_exports_label = QLabel("No export history found in project")
        self.als_exports_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']};")
        self.als_exports_label.setWordWrap(True)
        als_exports_layout.addWidget(self.als_exports_label)
        
        layout.addWidget(als_exports_group)
        
        # Linked Exports with audio playback
        exports_group = QGroupBox("Linked Exports (audio files)")
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
        backups_layout = QVBoxLayout(backups_group)
        
        self.backups_list = QListWidget()
        self.backups_list.setMaximumHeight(120)
        self.backups_list.itemDoubleClicked.connect(self._on_backup_double_click)
        backups_layout.addWidget(self.backups_list)
        
        layout.addWidget(backups_group)
        
        # Similar Projects section
        similar_group = QGroupBox("Similar Projects")
        similar_layout = QVBoxLayout(similar_group)
        
        self.similar_projects_list = QListWidget()
        self.similar_projects_list.setMaximumHeight(150)
        self.similar_projects_list.itemDoubleClicked.connect(self._on_similar_project_double_click)
        similar_layout.addWidget(self.similar_projects_list)
        
        refresh_similar_btn = QPushButton("Refresh Similar Projects")
        refresh_similar_btn.clicked.connect(self._load_similar_projects)
        similar_layout.addWidget(refresh_similar_btn)
        
        layout.addWidget(similar_group)
        
        # Connect audio player signals
        self._audio_player = AudioPlayer.instance()
        self._audio_player.position_changed.connect(self._on_position_changed)
        self._audio_player.duration_changed.connect(self._on_duration_changed)
        self._audio_player.playback_started.connect(self._on_playback_started)
        self._audio_player.playback_stopped.connect(self._on_playback_stopped)
        self._audio_player.playback_paused.connect(self._on_playback_paused)
        self._audio_player.playback_finished.connect(self._on_playback_finished)
        self._audio_player.error_occurred.connect(self._on_playback_error)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        open_folder_btn = QPushButton("Open in File Manager")
        open_folder_btn.clicked.connect(self._open_folder)
        buttons_layout.addWidget(open_folder_btn)
        
        buttons_layout.addStretch()
        
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)
        buttons_layout.addWidget(button_box)
        
        layout.addLayout(buttons_layout)
    
    def _load_project(self) -> None:
        """Load project data."""
        session = get_session()
        try:
            self._project = session.query(Project).get(self.project_id)
            if not self._project:
                QMessageBox.warning(self, "Error", "Project not found.")
                self.reject()
                return
            
            # File info
            self.name_label.setText(self._project.name)
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
            
            # Populate export name suggestions from existing exports
            self._populate_export_name_suggestions()
            
            # Load export history from ALS metadata
            self._load_als_export_history()
            
            # Tags
            if self._project.tags:
                self.tag_selector.set_selected_tags(self._project.tags)
            
            # Collections
            if self._project.project_collections:
                coll_names = [pc.collection.name for pc in self._project.project_collections]
                self.collections_label.setText(", ".join(coll_names))
            
            # Exports
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
            
            # Backups
            self._load_backups()
            
            # Similar projects
            self._load_similar_projects()
        finally:
            session.close()
    
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
            
            self.accept()
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
    
    def _load_als_export_history(self) -> None:
        """Load export history from the ALS project file metadata."""
        if not self._project:
            return
        
        try:
            from ...services.als_parser import ALSParser
            parser = ALSParser()
            metadata = parser.parse(Path(self._project.file_path))
            
            if metadata:
                info_parts = []
                
                # Export filenames found in project
                if metadata.export_filenames:
                    info_parts.append(f"📁 Export names: {', '.join(metadata.export_filenames)}")
                
                # Annotation
                if metadata.annotation:
                    anno = metadata.annotation.strip()
                    if len(anno) < 200:
                        info_parts.append(f"📝 Annotation: {anno}")
                
                # Master track name
                if metadata.master_track_name:
                    info_parts.append(f"🎚️ Master track: {metadata.master_track_name}")
                
                if info_parts:
                    self.als_exports_label.setText("\n".join(info_parts))
                    self.als_exports_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_primary']};")
                else:
                    self.als_exports_label.setText("No export history found in project file")
            else:
                self.als_exports_label.setText("Could not parse project file")
        except Exception as e:
            self.als_exports_label.setText(f"Error reading project: {str(e)[:50]}")
    
    def _populate_export_name_suggestions(self) -> None:
        """Populate the export name completer with suggestions."""
        suggestions = set()
        
        # Add project name as a suggestion
        if self._project:
            suggestions.add(self._project.name)
            
            # Add extracted song name from project name
            extracted = extract_song_name(self._project.name)
            if extracted:
                suggestions.add(extracted)
            
            # Add export names from linked exports
            if self._project.exports:
                for export in self._project.exports:
                    suggestions.add(export.export_name)
                    # Also extract song name from export
                    extracted = extract_song_name(export.export_name)
                    if extracted:
                        suggestions.add(extracted)
        
        # Set up completer model
        model = QStringListModel(sorted(suggestions))
        self._export_name_completer.setModel(model)
    
    def _suggest_export_name(self) -> None:
        """Auto-suggest an export name based on project metadata and exports."""
        if not self._project:
            return
        
        # Priority order for suggestions:
        # 1. Export filenames from ALS project metadata (export history in project)
        # 2. Extracted song name from most recent linked export
        # 3. Annotation from project metadata
        # 4. Extracted song name from project name
        # 5. Project name itself
        
        suggestion = None
        source = "project name"
        
        # Try to parse project metadata for export info
        try:
            from ...services.als_parser import ALSParser
            parser = ALSParser()
            metadata = parser.parse(Path(self._project.file_path))
            
            if metadata:
                # Try export filenames from project (Live stores recent exports)
                if metadata.export_filenames:
                    suggestion = metadata.export_filenames[0]
                    source = "project export history"
                
                # Try annotation (might be song title)
                if not suggestion and metadata.annotation:
                    anno = metadata.annotation.strip()
                    if len(anno) < 100 and '\n' not in anno:
                        suggestion = anno
                        source = "project annotation"
                
                # Try master track name
                if not suggestion and metadata.master_track_name:
                    suggestion = metadata.master_track_name
                    source = "master track name"
        except Exception:
            pass  # Fall back to other methods
        
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
        
        # Set the suggestion
        self.export_name_input.setText(suggestion)
        
        QMessageBox.information(
            self, "Export Name Suggested",
            f"Suggested export name: {suggestion}\n\n"
            f"Source: {source}\n\n"
            "This was derived from your project metadata. "
            "You can edit it as needed."
        )
    
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
            
            # Get collection names
            coll_names = [c.name for c in collections]
            
            name, ok = QInputDialog.getItem(
                self,
                "Add to Collection",
                "Select collection:",
                coll_names,
                editable=False
            )
            
            if ok and name:
                # Find collection
                collection = next((c for c in collections if c.name == name), None)
                if collection:
                    # Check if already in collection
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
                    
                    # Get next track number
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
                    
                    # Refresh display
                    self._load_project()
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
    
    def _load_backups(self) -> None:
        """Load and display backup files for the project."""
        if not self._project:
            return
        
        self.backups_list.clear()
        project_path = Path(self._project.file_path)
        
        try:
            backup_files = find_backup_files(project_path)
            if backup_files:
                for backup_path in backup_files:
                    # Format backup name with modification date
                    mod_time = datetime.fromtimestamp(backup_path.stat().st_mtime)
                    date_str = mod_time.strftime("%Y-%m-%d %H:%M")
                    item = QListWidgetItem(f"💾 {backup_path.name} ({date_str})")
                    item.setData(Qt.ItemDataRole.UserRole, str(backup_path))
                    item.setToolTip(str(backup_path))
                    self.backups_list.addItem(item)
            else:
                item = QListWidgetItem("No backup files found")
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.backups_list.addItem(item)
        except Exception as e:
            item = QListWidgetItem(f"Error loading backups: {str(e)}")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.backups_list.addItem(item)
    
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
        
        # Launch the backup project using the same mechanism as regular projects
        from ...services.live_launcher import LiveLauncher
        from ...services.live_detector import LiveVersion
        from ...database import LiveInstallation
        
        session = get_session()
        try:
            # Check for favorite installation first
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
            
            # No favorite - show dialog to select Live version
            from .live_version_dialog import LiveVersionDialog
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
    
    def _load_similar_projects(self) -> None:
        """Load and display similar projects."""
        if not self._project:
            return
        
        self.similar_projects_list.clear()
        
        try:
            from ...services.similarity_analyzer import SimilarityAnalyzer
            from ...database import Project as ProjectModel
            
            analyzer = SimilarityAnalyzer()
            
            # Get all projects except current one
            session = get_session()
            try:
                all_projects = session.query(ProjectModel).filter(
                    ProjectModel.id != self.project_id
                ).all()
                
                if not all_projects:
                    item = QListWidgetItem("No other projects found")
                    item.setFlags(Qt.ItemFlag.NoItemFlags)
                    self.similar_projects_list.addItem(item)
                    return
                
                # Convert current project to dict format
                project_dict = {
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
                
                # Convert all projects to dict format
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
                
                # Find similar projects
                similar = analyzer.find_similar_projects(
                    reference_project=project_dict,
                    candidate_projects=candidate_dicts,
                    top_n=10,
                    min_similarity=0.3
                )
                
                if not similar:
                    item = QListWidgetItem("No similar projects found (min similarity: 30%)")
                    item.setFlags(Qt.ItemFlag.NoItemFlags)
                    self.similar_projects_list.addItem(item)
                    return
                
                # Display similar projects
                for sim_project in similar:
                    score_percent = int(sim_project.similarity_score * 100)
                    explanation = ""
                    if sim_project.similarity_result:
                        explanation = analyzer.get_similarity_explanation(sim_project.similarity_result)
                    
                    item_text = f"{sim_project.project_name} ({score_percent}%)"
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.ItemDataRole.UserRole, sim_project.project_id)
                    item.setToolTip(explanation or f"Similarity: {score_percent}%")
                    self.similar_projects_list.addItem(item)
                    
            finally:
                session.close()
        except Exception as e:
            item = QListWidgetItem(f"Error loading similar projects: {str(e)}")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.similar_projects_list.addItem(item)
    
    def _on_similar_project_double_click(self, item: QListWidgetItem) -> None:
        """Handle double-click on similar project - open its details."""
        project_id = item.data(Qt.ItemDataRole.UserRole)
        if project_id:
            # Close current dialog and open new one
            self.accept()  # Close current dialog
            # Emit signal to open new project details (if parent handles it)
            # Or create new dialog
            dialog = ProjectDetailsDialog(project_id, self.parent())
            dialog.exec()
    
    def _find_exports(self) -> None:
        """Find and link exports for this project."""
        from ...services.export_tracker import ExportTracker
        
        if not self._project:
            return
        
        # Get export tracker
        tracker = ExportTracker()
        
        # Try to auto-match exports
        session = get_session()
        try:
            # First, scan for new exports in known locations
            # (This would ideally show a progress dialog)
            
            # Then try to match unlinked exports
            matched = tracker.auto_match_exports(threshold=60.0)
            
            if matched > 0:
                QMessageBox.information(
                    self, "Exports Found",
                    f"Found and linked {matched} export(s)."
                )
                self._load_project()
            else:
                QMessageBox.information(
                    self, "No Exports Found",
                    "No matching exports were found.\n\n"
                    "Make sure your export folders are added as locations "
                    "and have been scanned."
                )
        finally:
            session.close()
    
    def closeEvent(self, event) -> None:
        """Handle dialog close - stop playback."""
        self._audio_player.stop()
        super().closeEvent(event)