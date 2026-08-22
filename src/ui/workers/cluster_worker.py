"""Background worker for ML project clustering."""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal
from sqlalchemy import not_

from ...database import Project, ProjectStatus, get_session
from ...services.ml_clustering import ClusteringResult, MLClusteringService
from ...utils.logging import get_logger


class ClusterWorker(QThread):
    """Run K-means clustering on indexed projects."""

    finished_with_result = pyqtSignal(object)  # ClusteringResult | None
    failed = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, n_clusters: int = 5, parent=None) -> None:
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self._n_clusters = n_clusters
        self._cancel_requested = False

    def cancel(self) -> None:
        self._cancel_requested = True

    def run(self) -> None:
        try:
            self.progress.emit("Loading projects...")
            projects = self._load_projects()
            if self._cancel_requested:
                return
            if len(projects) < 2:
                self.failed.emit("Need at least 2 projects with feature vectors to cluster.")
                return

            self.progress.emit("Running clustering...")
            service = MLClusteringService()
            result = service.cluster_kmeans(projects, n_clusters=self._n_clusters)
            if self._cancel_requested:
                return
            self.finished_with_result.emit(result)
        except ImportError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.logger.error("Cluster worker failed: %s", exc, exc_info=True)
            self.failed.emit(str(exc))

    def _load_projects(self) -> list[dict]:
        payload: list[dict] = []
        with get_session() as session:
            rows = (
                session.query(Project)
                .filter(
                    Project.status != ProjectStatus.MISSING,
                    Project.feature_vector.isnot(None),
                    not_(Project.file_path.ilike("%/Backup/%")),
                    not_(Project.file_path.ilike("%\\Backup\\%")),
                )
                .all()
            )
            for project in rows:
                vector = project.get_feature_vector_list()
                if not vector:
                    continue
                payload.append(
                    {
                        "id": project.id,
                        "name": project.name,
                        "als_path": project.file_path,
                        "feature_vector": vector,
                        "tempo": project.tempo,
                        "plugins": project.get_plugins_list(),
                        "devices": project.get_devices_list(),
                        "ableton_version": project.ableton_version,
                    }
                )
        return payload
