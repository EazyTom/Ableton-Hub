"""Worker for finding similar projects in background thread."""

from typing import Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal

from .base_worker import BaseWorker


class SimilarProjectsWorker(BaseWorker):
    """Worker for finding similar projects in background thread."""
    
    finished = pyqtSignal(list)  # Emits list of similar projects
    
    def __init__(self, project_id: int, project_data: Dict[str, Any], parent=None):
        """Initialize the similar projects worker.
        
        Args:
            project_id: ID of the reference project.
            project_data: Dictionary containing project data for comparison.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.project_id = project_id
        self.project_data = project_data
    
    def run(self) -> None:
        """Find similar projects and emit results."""
        if self.is_cancelled():
            return
        
        try:
            from ...services.similarity_analyzer import SimilarityAnalyzer
            from ...database import get_session, Project as ProjectModel
            
            analyzer = SimilarityAnalyzer()
            
            session = get_session()
            try:
                all_projects = session.query(ProjectModel).filter(
                    ProjectModel.id != self.project_id
                ).all()
                
                if self.is_cancelled():
                    return
                
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
                
                if self.is_cancelled():
                    return
                
                similar = analyzer.find_similar_projects(
                    reference_project=self.project_data,
                    candidate_projects=candidate_dicts,
                    top_n=10,
                    min_similarity=0.3
                )
                
                if self.is_cancelled():
                    return
                
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
            error_msg = str(e)[:100]
            self.emit_error(error_msg, context={'project_id': self.project_id})
