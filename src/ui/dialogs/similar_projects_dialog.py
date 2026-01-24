"""Dialog for displaying similar projects."""

from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QDialogButtonBox, QMessageBox,
    QGroupBox, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal

from ...database import get_session, Project
from ...services.similarity_analyzer import SimilarityAnalyzer
from ..theme import AbletonTheme


class SimilarProjectsDialog(QDialog):
    """Dialog showing projects similar to a reference project."""
    
    project_selected = pyqtSignal(int)  # Emitted when a project is double-clicked
    
    def __init__(self, project_id: int, parent=None):
        super().__init__(parent)
        
        self.project_id = project_id
        self._project: Optional[Project] = None
        self._analyzer = SimilarityAnalyzer()
        
        self.setWindowTitle("Similar Projects")
        self.setMinimumSize(600, 500)
        
        self._setup_ui()
        self._load_similar_projects()
    
    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Reference project info
        ref_group = QGroupBox("Reference Project")
        ref_layout = QVBoxLayout(ref_group)
        
        self.ref_project_label = QLabel()
        self.ref_project_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        ref_layout.addWidget(self.ref_project_label)
        
        layout.addWidget(ref_group)
        
        # Similar projects list
        similar_group = QGroupBox("Similar Projects")
        similar_layout = QVBoxLayout(similar_group)
        
        info_label = QLabel("Double-click a project to view its details")
        info_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 11px;")
        similar_layout.addWidget(info_label)
        
        self.similar_list = QListWidget()
        self.similar_list.itemDoubleClicked.connect(self._on_project_double_click)
        similar_layout.addWidget(self.similar_list)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        similar_layout.addWidget(self.progress_bar)
        
        layout.addWidget(similar_group)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._load_similar_projects)
        button_box.addButton(refresh_btn, QDialogButtonBox.ButtonRole.ActionRole)
        
        layout.addWidget(button_box)
    
    def _load_similar_projects(self) -> None:
        """Load and display similar projects."""
        session = get_session()
        try:
            self._project = session.query(Project).get(self.project_id)
            if not self._project:
                QMessageBox.warning(self, "Error", "Project not found.")
                self.reject()
                return
            
            # Update reference project label
            self.ref_project_label.setText(f"Finding projects similar to: {self._project.name}")
            
            # Show progress
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate
            self.similar_list.clear()
            self.similar_list.addItem(QListWidgetItem("Loading similar projects..."))
            
            # Process in background (simplified - in real app would use QThread)
            self._process_similarity()
            
        finally:
            session.close()
    
    def _process_similarity(self) -> None:
        """Process similarity analysis."""
        try:
            session = get_session()
            try:
                # Get all projects except current one
                all_projects = session.query(Project).filter(
                    Project.id != self.project_id
                ).all()
                
                if not all_projects:
                    self.similar_list.clear()
                    item = QListWidgetItem("No other projects found")
                    item.setFlags(Qt.ItemFlag.NoItemFlags)
                    self.similar_list.addItem(item)
                    self.progress_bar.setVisible(False)
                    return
                
                # Convert current project to dict format
                project_dict = self._project_to_dict(self._project)
                
                # Convert all projects to dict format
                candidate_dicts = [self._project_to_dict(p) for p in all_projects]
                
                # Find similar projects
                similar = self._analyzer.find_similar_projects(
                    reference_project=project_dict,
                    candidate_projects=candidate_dicts,
                    top_n=20,
                    min_similarity=0.2
                )
                
                # Clear and populate list
                self.similar_list.clear()
                
                if not similar:
                    item = QListWidgetItem("No similar projects found (min similarity: 20%)")
                    item.setFlags(Qt.ItemFlag.NoItemFlags)
                    self.similar_list.addItem(item)
                    self.progress_bar.setVisible(False)
                    return
                
                # Display similar projects
                for sim_project in similar:
                    score_percent = int(sim_project.similarity_score * 100)
                    
                    # Get project details
                    project = session.query(Project).get(sim_project.project_id)
                    if not project:
                        continue
                    
                    # Build display text
                    location_name = project.location.name if project.location else "Unknown"
                    tempo_str = f"{project.tempo:.0f} BPM" if project.tempo else "No tempo"
                    
                    item_text = f"{sim_project.project_name} - {score_percent}% similar"
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.ItemDataRole.UserRole, sim_project.project_id)
                    
                    # Build tooltip with explanation
                    tooltip_parts = [
                        f"Similarity: {score_percent}%",
                        f"Location: {location_name}",
                        f"Tempo: {tempo_str}"
                    ]
                    
                    if sim_project.similarity_result:
                        explanation = self._analyzer.get_similarity_explanation(
                            sim_project.similarity_result
                        )
                        tooltip_parts.append(f"\n{explanation}")
                        
                        # Add breakdown
                        breakdown = []
                        if sim_project.similarity_result.plugin_similarity > 0:
                            breakdown.append(
                                f"Plugins: {int(sim_project.similarity_result.plugin_similarity * 100)}%"
                            )
                        if sim_project.similarity_result.device_similarity > 0:
                            breakdown.append(
                                f"Devices: {int(sim_project.similarity_result.device_similarity * 100)}%"
                            )
                        if sim_project.similarity_result.tempo_similarity > 0:
                            breakdown.append(
                                f"Tempo: {int(sim_project.similarity_result.tempo_similarity * 100)}%"
                            )
                        if breakdown:
                            tooltip_parts.append("\nBreakdown: " + ", ".join(breakdown))
                    
                    item.setToolTip("\n".join(tooltip_parts))
                    self.similar_list.addItem(item)
                
            finally:
                session.close()
            
            self.progress_bar.setVisible(False)
            
        except Exception as e:
            self.similar_list.clear()
            item = QListWidgetItem(f"Error: {str(e)}")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.similar_list.addItem(item)
            self.progress_bar.setVisible(False)
    
    def _project_to_dict(self, project: Project) -> dict:
        """Convert Project model to dictionary for similarity analyzer."""
        return {
            'id': project.id,
            'name': project.name,
            'plugins': project.plugins or [],
            'devices': project.devices or [],
            'tempo': project.tempo,
            'track_count': project.track_count,
            'audio_tracks': getattr(project, 'audio_tracks', 0),
            'midi_tracks': getattr(project, 'midi_tracks', 0),
            'arrangement_length': project.arrangement_length,
            'als_path': project.file_path
        }
    
    def _on_project_double_click(self, item: QListWidgetItem) -> None:
        """Handle double-click on similar project."""
        project_id = item.data(Qt.ItemDataRole.UserRole)
        if project_id:
            self.project_selected.emit(project_id)
            # Open project details dialog
            from .project_details import ProjectDetailsDialog
            dialog = ProjectDetailsDialog(project_id, self)
            dialog.exec()
