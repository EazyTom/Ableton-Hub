"""Controller for managing project loading, filtering, and sorting."""

from PyQt6.QtCore import QObject, pyqtSignal

from ...database import Location, Project, get_session
from ...utils.logging import get_logger


class ProjectController(QObject):
    """Manages project loading, filtering, and sorting operations."""

    # Signals
    projects_loaded = pyqtSignal(list)  # List of Project objects
    project_count_changed = pyqtSignal(int)

    def __init__(self, parent: QObject | None = None):
        """Initialize the project controller.

        Args:
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)

    def load_projects(
        self,
        location_id: int | None = None,
        search_query: str | None = None,
        filter_type: str = "All",
        min_tempo: int | None = None,
        max_tempo: int | None = None,
        sort_by: str = "modified_desc",
        arrangement_length: float | None = None,
    ) -> list[Project]:
        """Load projects with optional filtering and sorting.

        Args:
            location_id: Optional location ID to filter by.
            search_query: Optional search query string.
            filter_type: Filter type ("All", "Name", "Export", "Tags", "Notes").
            min_tempo: Minimum tempo filter.
            max_tempo: Maximum tempo filter.
            sort_by: Sort field and direction (e.g., "modified_desc", "tempo_asc").
            arrangement_length: Optional arrangement length filter.

        Returns:
            List of Project objects. Returns empty list on error.
        """
        try:
            with get_session() as session:
                query = session.query(Project)

                # Filter by location
                if location_id:
                    query = query.filter(Project.location_id == location_id)

                # Apply search filter
                if search_query:
                    if filter_type == "Name":
                        query = query.filter(Project.name.ilike(f"%{search_query}%"))
                    elif filter_type == "Export":
                        query = query.filter(Project.export_song_name.ilike(f"%{search_query}%"))
                    elif filter_type == "Tags":
                        # Search in tags using junction table
                        from ...database import ProjectTag, Tag

                        query = (
                            query.join(ProjectTag)
                            .join(Tag)
                            .filter(Tag.name.ilike(f"%{search_query}%"))
                            .distinct()
                        )
                    elif filter_type == "Notes":
                        query = query.filter(Project.notes.ilike(f"%{search_query}%"))
                    else:  # All
                        query = query.filter(
                            (Project.name.ilike(f"%{search_query}%"))
                            | (Project.export_song_name.ilike(f"%{search_query}%"))
                            | (Project.notes.ilike(f"%{search_query}%"))
                        )

                # Apply tempo filter
                if min_tempo is not None:
                    query = query.filter(Project.tempo >= min_tempo)
                if max_tempo is not None:
                    query = query.filter(Project.tempo <= max_tempo)

                # Apply arrangement length filter
                if arrangement_length is not None:
                    query = query.filter(Project.arrangement_length >= arrangement_length)

                # Apply sorting
                sort_parts = sort_by.split("_")
                if len(sort_parts) == 2:
                    field, direction = sort_parts
                    if field == "modified":
                        order_by = (
                            Project.modified_date.desc()
                            if direction == "desc"
                            else Project.modified_date.asc()
                        )
                    elif field == "name":
                        order_by = Project.name.asc() if direction == "asc" else Project.name.desc()
                    elif field == "tempo":
                        order_by = (
                            Project.tempo.desc() if direction == "desc" else Project.tempo.asc()
                        )
                    elif field == "length":
                        order_by = (
                            Project.arrangement_length.desc()
                            if direction == "desc"
                            else Project.arrangement_length.asc()
                        )
                    elif field == "size":
                        order_by = (
                            Project.file_size.desc()
                            if direction == "desc"
                            else Project.file_size.asc()
                        )
                    elif field == "location":
                        order_by = Location.name.asc()
                        query = query.join(Location)
                    else:
                        order_by = Project.modified_date.desc()

                    query = query.order_by(order_by)
                else:
                    # Default sort
                    query = query.order_by(Project.modified_date.desc())

                projects = query.all()
                self.projects_loaded.emit(projects)
                self.project_count_changed.emit(len(projects))

                return projects
        except Exception as e:
            self.logger.error(f"Error loading projects: {e}", exc_info=True)
            self.projects_loaded.emit([])
            self.project_count_changed.emit(0)
            return []

    def get_project_count(self, location_id: int | None = None) -> int:
        """Get the total count of projects.

        Args:
            location_id: Optional location ID to filter by.

        Returns:
            Total project count. Returns 0 on error.
        """
        try:
            with get_session() as session:
                query = session.query(Project)
                if location_id:
                    query = query.filter(Project.location_id == location_id)
                return query.count()
        except Exception as e:
            self.logger.error(f"Error getting project count: {e}", exc_info=True)
            return 0
