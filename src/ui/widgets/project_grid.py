"""Project grid/list view widget."""

from typing import Optional, List, Set
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QStackedWidget, QMenu, QLabel, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QAction

from ...database.models import Project
from .project_card import ProjectCard
from ..theme import AbletonTheme


class ProjectGrid(QWidget):
    """Widget displaying projects in grid or list view."""
    
    # Signals
    project_selected = pyqtSignal(int)        # Project ID
    project_double_clicked = pyqtSignal(int)  # Project ID
    selection_changed = pyqtSignal(list)       # List of project IDs
    sort_requested = pyqtSignal(str, str)      # Column name, direction (asc/desc)
    tags_modified = pyqtSignal()               # Emitted when tags are created/modified
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._projects: List[Project] = []
        self._selected_ids: Set[int] = set()
        self._view_mode = "grid"
        self._cards: dict = {}  # project_id -> ProjectCard
        self._sort_column = 5  # Default: Modified (index 5, after adding Size column)
        self._sort_order = Qt.SortOrder.DescendingOrder
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # View stack
        self.stack = QStackedWidget()
        
        # Grid view
        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.grid_scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(16, 16, 16, 16)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.grid_scroll.setWidget(self.grid_container)
        self.stack.addWidget(self.grid_scroll)
        
        # List view (table)
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "Name", "Location", "Tempo", "Length", "Size", "Modified", "Version", "Key", "Tags", "Export", "Status"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(False)  # We handle sorting ourselves
        
        # Configure header
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Length
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Size
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Modified
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Version
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Tags
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)  # Export
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)  # Status
        
        # Enable clickable headers for sorting
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self._on_header_clicked)
        header.setSortIndicatorShown(True)
        header.setSortIndicator(self._sort_column, self._sort_order)
        
        self.table.cellDoubleClicked.connect(self._on_table_double_click)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_table_context_menu)
        
        self.stack.addWidget(self.table)
        
        layout.addWidget(self.stack)
        
        # Empty state
        self.empty_label = QLabel("No projects found")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(f"""
            QLabel {{
                color: {AbletonTheme.COLORS['text_secondary']};
                font-size: 16px;
                padding: 40px;
            }}
        """)
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)
    
    def set_projects(self, projects: List[Project]) -> None:
        """Set the projects to display.
        
        Args:
            projects: List of Project objects.
        """
        self._projects = projects
        self._selected_ids.clear()
        self._refresh_view()
    
    def set_view_mode(self, mode: str) -> None:
        """Set the view mode.
        
        Args:
            mode: "grid" or "list"
        """
        self._view_mode = mode
        self._refresh_view()
    
    def _refresh_view(self) -> None:
        """Refresh the current view with project data."""
        # Show empty state if no projects
        if not self._projects:
            self.empty_label.setVisible(True)
            self.stack.setVisible(False)
            return
        
        self.empty_label.setVisible(False)
        self.stack.setVisible(True)
        
        if self._view_mode == "grid":
            self._populate_grid()
            self.stack.setCurrentIndex(0)
        else:
            self._populate_table()
            self.stack.setCurrentIndex(1)
    
    def _populate_grid(self) -> None:
        """Populate the grid view with project cards."""
        # Clear existing cards
        for card in self._cards.values():
            card.deleteLater()
        self._cards.clear()
        
        # Clear grid layout
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Calculate columns based on width
        width = self.grid_scroll.viewport().width()
        card_width = 196  # 180 + spacing
        columns = max(1, width // card_width)
        
        # Add cards
        for idx, project in enumerate(self._projects):
            card = ProjectCard(project)
            card.clicked.connect(self._on_card_clicked)
            card.double_clicked.connect(self._on_card_double_clicked)
            card.context_menu.connect(self._on_card_context_menu)
            
            row = idx // columns
            col = idx % columns
            self.grid_layout.addWidget(card, row, col)
            
            self._cards[project.id] = card
            
            # Update selection state
            card.set_selected(project.id in self._selected_ids)
    
    def _populate_table(self) -> None:
        """Populate the table view."""
        self.table.setRowCount(len(self._projects))
        
        for row, project in enumerate(self._projects):
            # Name
            name_item = QTableWidgetItem(project.name)
            name_item.setData(Qt.ItemDataRole.UserRole, project.id)
            self.table.setItem(row, 0, name_item)
            
            # Location
            # Access location safely (may be detached)
            try:
                location = project.location if hasattr(project, 'location') else None
                loc_name = location.name if location else "Unknown"
            except Exception:
                loc_name = "Unknown"
            self.table.setItem(row, 1, QTableWidgetItem(loc_name))
            
            # Tempo
            tempo_str = f"{project.tempo:.1f}" if project.tempo else ""
            tempo_item = QTableWidgetItem(tempo_str)
            tempo_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 2, tempo_item)
            
            # Length (arrangement length in bars and time)
            length_parts = []
            if project.arrangement_length and project.arrangement_length > 0:
                bars = int(project.arrangement_length)
                length_parts.append(f"{bars} bars")
            
            # Add duration in min:sec if available
            if hasattr(project, 'arrangement_duration_seconds') and project.arrangement_duration_seconds and project.arrangement_duration_seconds > 0:
                duration_sec = int(project.arrangement_duration_seconds)
                minutes = duration_sec // 60
                seconds = duration_sec % 60
                length_parts.append(f"({minutes}:{seconds:02d})")
            
            length_str = " ".join(length_parts) if length_parts else ""
            length_item = QTableWidgetItem(length_str)
            length_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 3, length_item)
            
            # Size (file size in MB)
            if project.file_size and project.file_size > 0:
                size_mb = project.file_size / (1024 * 1024)  # Convert bytes to MB
                if size_mb < 1:
                    size_str = f"{size_mb * 1024:.0f} KB"
                else:
                    size_str = f"{size_mb:.1f} MB"
            else:
                size_str = ""
            size_item = QTableWidgetItem(size_str)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 4, size_item)
            
            # Modified date
            if project.modified_date:
                date_str = project.modified_date.strftime("%Y-%m-%d %H:%M")
            else:
                date_str = ""
            self.table.setItem(row, 5, QTableWidgetItem(date_str))
            
            # Version
            version_display = project.get_live_version_display() or ""
            version_item = QTableWidgetItem(version_display)
            version_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 6, version_item)
            
            # Key/Scale
            key_display = project.get_key_display() or ""
            key_item = QTableWidgetItem(key_display)
            key_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 7, key_item)
            
            # Tags - tags are stored as JSON array of tag IDs
            tags_str = ""
            try:
                if project.tags and isinstance(project.tags, list):
                    # Tags are stored as list of tag IDs, need to look up names
                    from ...database import get_session, Tag
                    session = get_session()
                    try:
                        tag_ids = [t for t in project.tags if isinstance(t, int)]
                        if tag_ids:
                            tags = session.query(Tag).filter(Tag.id.in_(tag_ids)).all()
                            tag_names = [tag.name for tag in tags]
                            tags_str = ", ".join(tag_names) if tag_names else ""
                    finally:
                        session.close()
            except (AttributeError, TypeError, Exception):
                # Tags not loaded or invalid
                tags_str = ""
            self.table.setItem(row, 8, QTableWidgetItem(tags_str))
            
            # Export status
            # Access exports safely (may be detached)
            try:
                has_exports = bool(project.exports) if hasattr(project, 'exports') else False
            except Exception:
                has_exports = False
            export_str = "✓" if has_exports else ""
            self.table.setItem(row, 9, QTableWidgetItem(export_str))
            
            # Status
            status_str = project.status.value if project.status else ""
            self.table.setItem(row, 10, QTableWidgetItem(status_str))
    
    def _on_card_clicked(self, project_id: int) -> None:
        """Handle card click."""
        # Clear other selections and select this one
        for pid, card in self._cards.items():
            card.set_selected(pid == project_id)
        
        self._selected_ids = {project_id}
        self.project_selected.emit(project_id)
        self.selection_changed.emit(list(self._selected_ids))
    
    def _on_card_double_clicked(self, project_id: int) -> None:
        """Handle card double click."""
        self.project_double_clicked.emit(project_id)
    
    def _on_card_context_menu(self, project_id: int, pos: QPoint) -> None:
        """Handle card context menu."""
        self._show_context_menu(project_id, pos)
    
    def _on_table_double_click(self, row: int, column: int) -> None:
        """Handle table row double click."""
        item = self.table.item(row, 0)
        if item:
            project_id = item.data(Qt.ItemDataRole.UserRole)
            self.project_double_clicked.emit(project_id)
    
    def _on_table_selection_changed(self) -> None:
        """Handle table selection change."""
        self._selected_ids.clear()
        for item in self.table.selectedItems():
            if item.column() == 0:
                project_id = item.data(Qt.ItemDataRole.UserRole)
                self._selected_ids.add(project_id)
        
        if len(self._selected_ids) == 1:
            self.project_selected.emit(list(self._selected_ids)[0])
        self.selection_changed.emit(list(self._selected_ids))
    
    def _on_header_clicked(self, column: int) -> None:
        """Handle column header click for sorting."""
        # Map column index to sort field
        column_map = {
            0: "name",
            1: "location",
            2: "tempo",
            3: "length",
            4: "size",
            5: "modified",
            6: "version",
            7: "key",
            8: "tags",
            9: "export",
            10: "status"
        }
        
        sort_field = column_map.get(column)
        if not sort_field:
            return
        
        # Toggle sort order if clicking same column, otherwise default to ascending
        if column == self._sort_column:
            if self._sort_order == Qt.SortOrder.AscendingOrder:
                self._sort_order = Qt.SortOrder.DescendingOrder
            else:
                self._sort_order = Qt.SortOrder.AscendingOrder
        else:
            self._sort_column = column
            # Default order: numeric columns (tempo, length, size, modified) default descending
            if column in (2, 3, 4, 5):  # Tempo, Length, Size, Modified - default descending
                self._sort_order = Qt.SortOrder.DescendingOrder
            else:
                self._sort_order = Qt.SortOrder.AscendingOrder
        
        # Update visual indicator
        self.table.horizontalHeader().setSortIndicator(self._sort_column, self._sort_order)
        
        # Emit signal with sort field and direction
        direction = "asc" if self._sort_order == Qt.SortOrder.AscendingOrder else "desc"
        self.sort_requested.emit(sort_field, direction)
    
    def _on_table_context_menu(self, pos: QPoint) -> None:
        """Handle table context menu."""
        item = self.table.itemAt(pos)
        if item:
            project_id = self.table.item(item.row(), 0).data(Qt.ItemDataRole.UserRole)
            self._show_context_menu(project_id, self.table.viewport().mapToGlobal(pos))
    
    def _show_context_menu(self, project_id: int, pos: QPoint) -> None:
        """Show context menu for a project."""
        menu = QMenu(self)
        
        open_action = menu.addAction("Open in File Manager")
        open_action.triggered.connect(lambda: self.project_double_clicked.emit(project_id))
        
        menu.addSeparator()
        
        # Add to collection submenu
        collection_menu = menu.addMenu("Add to Collection")
        
        # New collection action
        new_coll_action = collection_menu.addAction("New Collection...")
        new_coll_action.triggered.connect(lambda: self._create_and_add_to_collection(project_id))
        
        collection_menu.addSeparator()
        
        # Populate with existing collections
        from ...database import get_session, Collection, ProjectCollection
        session = get_session()
        try:
            collections = session.query(Collection).order_by(Collection.name).all()
            
            if not collections:
                no_coll_action = collection_menu.addAction("(No collections yet)")
                no_coll_action.setEnabled(False)
            else:
                for coll in collections:
                    # Check if already in this collection
                    existing = session.query(ProjectCollection).filter(
                        ProjectCollection.project_id == project_id,
                        ProjectCollection.collection_id == coll.id
                    ).first()
                    
                    if existing:
                        coll_action = collection_menu.addAction(f"✓ {coll.name}")
                        coll_action.setEnabled(False)
                    else:
                        coll_action = collection_menu.addAction(coll.name)
                        coll_action.triggered.connect(
                            lambda checked, cid=coll.id: self._add_to_collection(project_id, cid)
                        )
        finally:
            session.close()
        
        # Tags submenu
        tag_menu = menu.addMenu("Tags")
        tag_menu.addAction("Add Tag...")
        tag_menu.addSeparator()
        # TODO: Populate with existing tags
        
        menu.addSeparator()
        
        favorite_action = menu.addAction("Toggle Favorite")
        favorite_action.triggered.connect(lambda: self._toggle_favorite(project_id))
        
        menu.addSeparator()
        
        # Find similar projects
        similar_action = menu.addAction("Find Similar Projects...")
        similar_action.triggered.connect(lambda: self._find_similar_projects(project_id))
        
        menu.addSeparator()
        
        properties_action = menu.addAction("Properties...")
        properties_action.triggered.connect(lambda: self._show_properties(project_id))
        
        menu.exec(pos)
    
    def _toggle_favorite(self, project_id: int) -> None:
        """Toggle favorite status for a project."""
        from ...database import get_session, Project
        
        session = get_session()
        try:
            project = session.query(Project).get(project_id)
            if project:
                new_favorite_status = not project.is_favorite
                project.is_favorite = new_favorite_status
                session.commit()
                
                # Update the project object in the list with the new favorite status
                for idx, p in enumerate(self._projects):
                    if p.id == project_id:
                        # Update the favorite status on the existing project object
                        self._projects[idx].is_favorite = new_favorite_status
                        break
                
                self._refresh_view()
        finally:
            session.close()
    
    def _find_similar_projects(self, project_id: int) -> None:
        """Show dialog with similar projects."""
        from ..dialogs.similar_projects_dialog import SimilarProjectsDialog
        dialog = SimilarProjectsDialog(project_id, self)
        dialog.exec()
    
    def _show_properties(self, project_id: int) -> None:
        """Show project properties in main window view."""
        # Use main window's properties view instead of dialog
        if hasattr(self, '_main_window') and self._main_window:
            self._main_window.show_project_properties(project_id)
        else:
            # Fallback to dialog if main window reference not available
            from ..dialogs.project_details import ProjectDetailsDialog
            dialog = ProjectDetailsDialog(project_id, self)
            dialog.tags_modified.connect(self.tags_modified.emit)
            if dialog.exec():
                self._refresh_view()
    
    def select_all(self) -> None:
        """Select all projects."""
        self._selected_ids = {p.id for p in self._projects}
        
        if self._view_mode == "grid":
            for card in self._cards.values():
                card.set_selected(True)
        else:
            self.table.selectAll()
        
        self.selection_changed.emit(list(self._selected_ids))
    
    def get_selected_ids(self) -> List[int]:
        """Get the list of selected project IDs."""
        return list(self._selected_ids)
    
    def _create_and_add_to_collection(self, project_id: int) -> None:
        """Create a new collection and add the project to it."""
        from ..dialogs.create_collection import CreateCollectionDialog
        
        dialog = CreateCollectionDialog(self)
        if dialog.exec():
            # Get the collection_id - it's set in the dialog after creation
            collection_id = getattr(dialog, 'collection_id', None)
            if collection_id:
                # Add project to the newly created collection
                self._add_to_collection(project_id, collection_id)
            else:
                # Fallback: Get the most recently created collection
                from ...database import get_session, Collection
                session = get_session()
                try:
                    collection = session.query(Collection).order_by(
                        Collection.created_date.desc()
                    ).first()
                    if collection:
                        self._add_to_collection(project_id, collection.id)
                    else:
                        QMessageBox.warning(
                            self, "Error",
                            "Collection was created but could not be found."
                        )
                finally:
                    session.close()
    
    def _add_to_collection(self, project_id: int, collection_id: int) -> None:
        """Add a project to a collection."""
        from ...database import get_session, ProjectCollection, Collection
        
        session = get_session()
        try:
            # Check if already in collection
            existing = session.query(ProjectCollection).filter(
                ProjectCollection.project_id == project_id,
                ProjectCollection.collection_id == collection_id
            ).first()
            
            if existing:
                collection = session.query(Collection).get(collection_id)
                QMessageBox.information(
                    self, "Already Added",
                    f"This project is already in '{collection.name}'."
                )
                return
            
            # Get next track number
            max_track = session.query(ProjectCollection).filter(
                ProjectCollection.collection_id == collection_id
            ).count()
            
            pc = ProjectCollection(
                project_id=project_id,
                collection_id=collection_id,
                track_number=max_track + 1
            )
            session.add(pc)
            session.commit()
            
            # Show success message
            collection = session.query(Collection).get(collection_id)
            QMessageBox.information(
                self, "Added to Collection",
                f"Project added to '{collection.name}' as track {max_track + 1}."
            )
            
            # Refresh the view
            self._refresh_view()
            
            # Refresh sidebar if main window reference exists
            if hasattr(self, '_main_window') and hasattr(self._main_window, '_refresh_sidebar'):
                self._main_window._refresh_sidebar()
            
        finally:
            session.close()
    
    def resizeEvent(self, event) -> None:
        """Handle resize to reflow grid."""
        super().resizeEvent(event)
        if self._view_mode == "grid" and self._projects:
            self._populate_grid()
