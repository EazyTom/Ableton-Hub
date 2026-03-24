"""Background worker: load projects and build similarity tree (metadata-only)."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from ...database.repositories.project_repository import ProjectRepository
from ...services.similarity_tree_models import SimilarityTreeResult
from ...services.similarity_tree_service import build_similarity_tree
from ...utils.logging import get_logger


def _project_to_dict(p: Any) -> dict[str, Any]:
    """Map SQLAlchemy Project to clustering dict (DB fields only; no .als reads)."""
    fv = p.feature_vector
    if isinstance(fv, str):
        import json

        try:
            fv = json.loads(fv)
        except (json.JSONDecodeError, TypeError):
            fv = None

    return {
        "id": p.id,
        "name": p.name,
        "tempo": p.tempo,
        "plugins": p.get_plugins_list(),
        "devices": p.get_devices_list(),
        "track_count": p.track_count or 0,
        "arrangement_length": p.arrangement_length or 0.0,
        "audio_tracks": p.audio_tracks or 0,
        "midi_tracks": p.midi_tracks or 0,
        "return_tracks": p.return_tracks or 0,
        "feature_vector": fv if isinstance(fv, list) else None,
        "musical_key": p.musical_key,
        "scale_type": p.scale_type,
        "time_signature": p.time_signature,
        "has_automation": bool(p.has_automation),
        "timeline_markers": p.timeline_markers if isinstance(p.timeline_markers, list) else [],
        "ableton_version": p.ableton_version,
    }


class SimilarityTreeWorker(QThread):
    """Runs ``build_similarity_tree`` off the GUI thread."""

    finished_ok = pyqtSignal(object)  # SimilarityTreeResult
    failed = pyqtSignal(str)

    def __init__(
        self,
        *,
        location_id: int | None = None,
        collection_id: int | None = None,
        tag_id: int | None = None,
        search_query: str | None = None,
        date_filter: str | None = None,
        tempo_min: int | None = None,
        tempo_max: int | None = None,
        sort_by: str = "modified_desc",
        parent: Any | None = None,
    ) -> None:
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self._location_id = location_id
        self._collection_id = collection_id
        self._tag_id = tag_id
        self._search_query = search_query
        self._date_filter = date_filter
        self._tempo_min = tempo_min
        self._tempo_max = tempo_max
        self._sort_by = sort_by
        self._cancel = False

    def request_cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            if self._cancel:
                return
            repo = ProjectRepository()
            projects = repo.get_all(
                location_id=self._location_id,
                collection_id=self._collection_id,
                tag_id=self._tag_id,
                search_query=self._search_query,
                date_filter=self._date_filter,
                tempo_min=self._tempo_min,
                tempo_max=self._tempo_max,
                sort_by=self._sort_by,
            )
            if self._cancel:
                return
            dicts = [_project_to_dict(p) for p in projects]
            result = build_similarity_tree(dicts)
            if self._cancel:
                return
            self.finished_ok.emit(result)
        except Exception as e:
            self.logger.exception("SimilarityTreeWorker failed")
            self.failed.emit(str(e))
