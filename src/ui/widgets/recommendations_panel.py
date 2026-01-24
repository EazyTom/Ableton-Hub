"""Recommendations panel widget showing similar projects and recommendations."""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QGroupBox, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from ...database import get_session, Project
from ...services.similarity_analyzer import SimilarityAnalyzer
from ...services.recommendation_engine import RecommendationEngine
from ..theme import AbletonTheme


class RecommendationsPanel(QWidget):
    """Panel showing project recommendations based on similarity."""
    
    project_selected = pyqtSignal(int)  # Emitted when a project is selected
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._analyzer = SimilarityAnalyzer()
        self._recommendation_engine = RecommendationEngine()
        self._current_project_id: Optional[int] = None
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Recommendations")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.addWidget(title)
        
        header.addStretch()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_recommendations)
        header.addWidget(refresh_btn)
        
        layout.addLayout(header)
        
        # Info label
        self.info_label = QLabel("Select a project to see similar projects and recommendations")
        self.info_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 12px;")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        # Current project display
        self.current_project_group = QGroupBox("Current Project")
        current_layout = QVBoxLayout(self.current_project_group)
        
        self.current_project_label = QLabel("No project selected")
        self.current_project_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        current_layout.addWidget(self.current_project_label)
        
        select_btn = QPushButton("Select Project...")
        select_btn.clicked.connect(self._select_project)
        current_layout.addWidget(select_btn)
        
        self.current_project_group.setVisible(False)
        layout.addWidget(self.current_project_group)
        
        # Similar projects group
        similar_group = QGroupBox("Similar Projects")
        similar_layout = QVBoxLayout(similar_group)
        
        self.similar_list = QListWidget()
        self.similar_list.itemDoubleClicked.connect(self._on_project_double_click)
        similar_layout.addWidget(self.similar_list)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        similar_layout.addWidget(self.progress_bar)
        
        layout.addWidget(similar_group)
        
        # Recommendations group
        recommendations_group = QGroupBox("Recommendations")
        recommendations_layout = QVBoxLayout(recommendations_group)
        
        self.recommendations_list = QListWidget()
        self.recommendations_list.itemDoubleClicked.connect(self._on_project_double_click)
        recommendations_layout.addWidget(self.recommendations_list)
        
        layout.addWidget(recommendations_group)
        
        layout.addStretch()
    
    def set_project(self, project_id: int) -> None:
        """Set the current project and load recommendations."""
        self._current_project_id = project_id
        self._update_current_project_display()
        self._refresh_recommendations()
    
    def _select_project(self) -> None:
        """Show dialog to select a project."""
        from PyQt6.QtWidgets import QInputDialog
        
        session = get_session()
        try:
            projects = session.query(Project).order_by(Project.name).all()
            
            if not projects:
                QMessageBox.information(self, "No Projects", "No projects found.")
                return
            
            project_names = [p.name for p in projects]
            name, ok = QInputDialog.getItem(
                self,
                "Select Project",
                "Choose a project to see recommendations:",
                project_names,
                editable=False
            )
            
            if ok and name:
                project = next((p for p in projects if p.name == name), None)
                if project:
                    self.set_project(project.id)
        finally:
            session.close()
    
    def _update_current_project_display(self) -> None:
        """Update the current project display."""
        if not self._current_project_id:
            self.current_project_group.setVisible(False)
            return
        
        session = get_session()
        try:
            project = session.query(Project).get(self._current_project_id)
            if project:
                self.current_project_label.setText(f"📁 {project.name}")
                self.current_project_group.setVisible(True)
            else:
                self.current_project_group.setVisible(False)
        finally:
            session.close()
    
    def _refresh_recommendations(self) -> None:
        """Refresh recommendations for the current project."""
        if not self._current_project_id:
            self.similar_list.clear()
            self.recommendations_list.clear()
            self.similar_list.addItem(QListWidgetItem("Select a project to see similar projects"))
            return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        
        try:
            session = get_session()
            try:
                project = session.query(Project).get(self._current_project_id)
                if not project:
                    return
                
                # Convert to dict format
                project_dict = self._project_to_dict(project)
                
                # Get all other projects
                all_projects = session.query(Project).filter(
                    Project.id != self._current_project_id
                ).all()
                
                if not all_projects:
                    self.similar_list.clear()
                    self.similar_list.addItem(QListWidgetItem("No other projects found"))
                    self.progress_bar.setVisible(False)
                    return
                
                candidate_dicts = [self._project_to_dict(p) for p in all_projects]
                
                # Find similar projects
                similar = self._analyzer.find_similar_projects(
                    reference_project=project_dict,
                    candidate_projects=candidate_dicts,
                    top_n=15,
                    min_similarity=0.3
                )
                
                # Populate similar projects list
                self.similar_list.clear()
                if similar:
                    for sim_project in similar:
                        score_percent = int(sim_project.similarity_score * 100)
                        item_text = f"{sim_project.project_name} ({score_percent}% similar)"
                        item = QListWidgetItem(item_text)
                        item.setData(Qt.ItemDataRole.UserRole, sim_project.project_id)
                        
                        # Build tooltip
                        tooltip = f"Similarity: {score_percent}%"
                        if sim_project.similarity_result:
                            explanation = self._analyzer.get_similarity_explanation(
                                sim_project.similarity_result
                            )
                            tooltip += f"\n{explanation}"
                        item.setToolTip(tooltip)
                        
                        self.similar_list.addItem(item)
                else:
                    self.similar_list.addItem(QListWidgetItem("No similar projects found"))
                
                # Get recommendations
                recommendations = self._recommendation_engine.recommend_similar_projects(
                    project=project_dict,
                    n_recommendations=10,
                    exclude_ids=set()
                )
                
                # Populate recommendations list
                self.recommendations_list.clear()
                if recommendations.recommendations:
                    for rec in recommendations.recommendations:
                        score_percent = int(rec.score * 100)
                        item_text = f"{rec.item_name} ({score_percent}% match)"
                        item = QListWidgetItem(item_text)
                        item.setData(Qt.ItemDataRole.UserRole, rec.item_id)
                        item.setToolTip(f"{rec.reason}\nScore: {score_percent}%")
                        self.recommendations_list.addItem(item)
                else:
                    self.recommendations_list.addItem(QListWidgetItem("No recommendations available"))
                
            finally:
                session.close()
            
            self.progress_bar.setVisible(False)
            
        except Exception as e:
            self.similar_list.clear()
            self.recommendations_list.clear()
            self.similar_list.addItem(QListWidgetItem(f"Error: {str(e)}"))
            self.progress_bar.setVisible(False)
    
    def _project_to_dict(self, project: Project) -> dict:
        """Convert Project model to dictionary."""
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
        """Handle double-click on a project."""
        project_id = item.data(Qt.ItemDataRole.UserRole)
        if project_id:
            self.project_selected.emit(project_id)
