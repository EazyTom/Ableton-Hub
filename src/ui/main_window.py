"""Main application window for Ableton Hub."""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import case

from .. import __version__, get_whats_new_html
from ..config import Config, save_config
from ..database import Location, Project, ProjectStatus, get_session
from ..services.watcher import FileWatcher
from ..utils.logging import get_logger
from ..utils.paths import get_resources_path
from .controllers.scan_controller import ScanController
from .managers.menu_bar_manager import MenuBarManager
from .managers.toolbar_manager import ToolBarManager
from .managers.view_manager import ViewManager
from .theme import AbletonTheme
from .widgets.collection_view import CollectionView
from .widgets.find_audio_exports_view import FindAudioExportsView
from .widgets.link_panel import LinkPanel
from .widgets.location_panel import LocationPanel
from .widgets.project_grid import ProjectGrid
from .widgets.project_properties_view import ProjectPropertiesView
from .widgets.sidebar import Sidebar


class MainWindow(QMainWindow):
    """Main application window with navigation and content areas."""

    # Signals
    scan_requested = pyqtSignal()

    def __init__(self, config: Config, theme: AbletonTheme | None = None):
        """Initialize the main window.

        Args:
            config: Application configuration.
            theme: Optional theme instance (will get from app if not provided).
        """
        self.logger = get_logger(__name__)
        super().__init__()

        self.config = config
        self.theme = theme
        self._scanner = None
        self._watcher = None
        self._link_scanner = None
        self._show_missing_projects = False

        # Initialize controllers
        self.scan_controller = ScanController(self)

        # ViewManager will be initialized after content_stack is created
        self.view_manager: ViewManager | None = None

        # MenuBarManager will be initialized before menus are created
        self.menu_manager: MenuBarManager | None = None

        # ToolBarManager will be initialized before toolbar is created
        self.toolbar_manager: ToolBarManager | None = None

        self._setup_window()
        self._set_window_icon()
        self._create_menus()
        self._create_toolbar()
        self._create_central_widget()
        self._create_status_bar()
        self._connect_signals()

        # Initial data load
        QTimer.singleShot(100, self._initial_load)

    def _setup_window(self) -> None:
        """Configure the main window properties."""
        self.setWindowTitle("Ableton Hub")
        self.setMinimumSize(1000, 700)

        # Enable drag and drop
        self.setAcceptDrops(True)

    def _set_window_icon(self) -> None:
        """Set the window icon from resources."""
        try:
            import sys

            resources = get_resources_path()

            # Try icons in order of preference (PNG works on all platforms)
            if sys.platform == "win32":
                icon_paths = [
                    resources / "icons" / "AProject.ico",
                    resources / "images" / "als-icon.png",
                ]
            else:
                # macOS/Linux - prefer PNG
                icon_paths = [
                    resources / "images" / "als-icon.png",
                    resources / "icons" / "AProject.ico",
                ]

            for icon_path in icon_paths:
                if icon_path.exists():
                    icon = QIcon(str(icon_path))
                    if not icon.isNull():
                        self.setWindowIcon(icon)
                        from PyQt6.QtWidgets import QApplication

                        QApplication.instance().setWindowIcon(icon)
                        self.logger.info(f"Set window icon from: {icon_path}")
                        return

            self.logger.warning("No valid window icon found")
        except Exception as e:
            self.logger.error(f"Failed to set window icon: {e}", exc_info=True)

    def _create_menus(self) -> None:
        """Create the menu bar and menus."""
        # Create menu manager
        self.menu_manager = MenuBarManager(self, self)

        # Connect menu signals to MainWindow methods
        self.menu_manager.add_location_requested.connect(self._on_add_location)
        self.menu_manager.scan_all_requested.connect(self._on_scan_all)
        self.menu_manager.settings_requested.connect(self._on_settings)
        self.menu_manager.exit_requested.connect(self.close)
        self.menu_manager.search_projects_requested.connect(self._focus_search)
        self.menu_manager.select_all_requested.connect(self._select_all_projects)
        self.menu_manager.grid_view_requested.connect(lambda: self._set_view_mode("grid"))
        self.menu_manager.list_view_requested.connect(lambda: self._set_view_mode("list"))
        self.menu_manager.toggle_sidebar_requested.connect(self._toggle_sidebar)
        self.menu_manager.toggle_show_missing_requested.connect(self._toggle_show_missing)
        self.menu_manager.refresh_requested.connect(self._refresh_view)
        self.menu_manager.global_search_requested.connect(self._on_global_search)
        self.menu_manager.show_link_panel_requested.connect(self._show_link_panel)
        self.menu_manager.force_rescan_metadata_requested.connect(self._on_force_rescan_metadata)
        self.menu_manager.clear_thumbnail_cache_requested.connect(self._on_clear_thumbnail_cache)
        self.menu_manager.cleanup_missing_projects_requested.connect(
            self._on_cleanup_missing_projects
        )
        self.menu_manager.cleanup_backup_projects_requested.connect(
            self._on_cleanup_backup_projects
        )
        self.menu_manager.reset_database_requested.connect(self._on_reset_database)
        self.menu_manager.view_logs_requested.connect(self._on_view_logs)
        self.menu_manager.user_guide_requested.connect(self._on_user_guide)
        self.menu_manager.about_requested.connect(self._show_about)

        # Create menus
        self.menu_manager.create_menus()

        # Store references to actions that are accessed elsewhere
        self.sidebar_action = self.menu_manager.get_action("sidebar")
        self.show_missing_action = self.menu_manager.get_action("show_missing")

    def _create_toolbar(self) -> None:
        """Create the main toolbar."""
        # Create toolbar manager
        self.toolbar_manager = ToolBarManager(self, self)

        # Connect toolbar signals
        self.toolbar_manager.scan_requested.connect(self._on_scan_all)
        self.toolbar_manager.grid_view_requested.connect(lambda: self._set_view_mode("grid"))
        self.toolbar_manager.list_view_requested.connect(lambda: self._set_view_mode("list"))

        # Create toolbar
        toolbar = self.toolbar_manager.create_toolbar()

        # Get search bar and connect its signals
        self.search_bar = self.toolbar_manager.get_search_bar()
        if self.search_bar:
            self.search_bar.search_changed.connect(self._on_search)
            self.search_bar.filter_changed.connect(self._on_filter_changed)
            self.search_bar.tempo_filter_changed.connect(self._on_tempo_filter_changed)
            self.search_bar.sort_changed.connect(self._on_sort_changed)
            self.search_bar.create_collection_from_filter.connect(
                self._on_create_collection_from_filter
            )

        # Store references to view buttons
        self.grid_btn = self.toolbar_manager.get_grid_button()
        self.list_btn = self.toolbar_manager.get_list_button()

        # Store current filters
        self._current_date_filter = None
        self._current_tempo_min = 0
        self._current_tempo_max = 0
        self._current_sort = "modified"

    def _create_central_widget(self) -> None:
        """Create the central widget with sidebar and content area."""
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create splitter for resizable sidebar
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.setMinimumWidth(200)
        self.sidebar.setMaximumWidth(400)

        # Connect sidebar signals (removed duplicates)
        self.sidebar.navigation_changed.connect(self._on_navigation_changed)
        self.sidebar.location_selected.connect(self._on_location_filter)
        self.sidebar.collection_selected.connect(self._on_collection_selected)
        self.sidebar.location_delete_requested.connect(self._on_delete_location_from_sidebar)
        self.sidebar.find_audio_exports_requested.connect(self._on_find_audio_exports)
        self.sidebar.cleanup_orphaned_projects_requested.connect(self._on_cleanup_orphaned_projects)
        self.sidebar.collection_edit_requested.connect(self._on_edit_collection_from_sidebar)
        self.sidebar.collection_delete_requested.connect(self._on_delete_collection_from_sidebar)
        self.sidebar.auto_detect_live_versions_requested.connect(self._on_auto_detect_live_versions)
        self.sidebar.add_manual_installation_requested.connect(self._on_add_manual_installation)
        self.sidebar.set_favorite_installation_requested.connect(self._on_set_favorite_installation)
        self.sidebar.remove_installation_requested.connect(self._on_remove_installation)
        self.sidebar.tag_selected.connect(self._on_tag_filter)
        self.sidebar.manage_tags_requested.connect(self._on_manage_tags)
        self.splitter.addWidget(self.sidebar)

        # Content stack
        self.content_stack = QStackedWidget()

        # Projects view (index 0)
        self.project_grid = ProjectGrid()
        self.project_grid.project_selected.connect(self._on_project_selected)
        self.project_grid.project_double_clicked.connect(self._on_project_open)
        self.project_grid.sort_requested.connect(self._on_grid_sort_requested)
        self.project_grid.tags_modified.connect(self._refresh_sidebar)
        # Store reference to main window for refresh
        self.project_grid._main_window = self
        self.content_stack.addWidget(self.project_grid)

        # Collections view (index 1)
        self.collection_view = CollectionView()
        self.collection_view.collection_selected.connect(self._on_collection_selected)
        self.content_stack.addWidget(self.collection_view)

        # Locations view (index 2)
        self.location_panel = LocationPanel()
        self.location_panel.location_added.connect(self._on_location_added)
        self.location_panel.scan_requested.connect(self._on_scan_location)
        self.location_panel.find_audio_exports_requested.connect(self._on_find_audio_exports)
        self.content_stack.addWidget(self.location_panel)

        # Link panel (index 3)
        self.link_panel = LinkPanel()
        self.content_stack.addWidget(self.link_panel)

        # Health dashboard (index 4)
        from .widgets.health_dashboard import HealthDashboard

        self.health_dashboard = HealthDashboard()
        self.health_dashboard.project_selected.connect(self._on_project_selected)
        self.content_stack.addWidget(self.health_dashboard)

        # Recommendations panel (index 5)
        from .widgets.recommendations_panel import RecommendationsPanel

        self.recommendations_panel = RecommendationsPanel()
        self.recommendations_panel.project_selected.connect(self._on_project_selected)
        self.content_stack.addWidget(self.recommendations_panel)

        # Project properties view (index 6)
        self.project_properties_view = ProjectPropertiesView()
        self.project_properties_view.back_requested.connect(self._on_properties_back)
        self.project_properties_view.project_selected.connect(self._on_project_selected)
        self.project_properties_view.tags_modified.connect(self._refresh_sidebar)
        self.project_properties_view.project_saved.connect(self._on_project_saved)
        self.project_properties_view.no_live_installation_requested.connect(
            self._show_no_live_installation_dialog
        )
        self.content_stack.addWidget(self.project_properties_view)

        # Find Audio Exports view (index 7)
        self.find_audio_exports_view = FindAudioExportsView()
        self.find_audio_exports_view.back_requested.connect(self._on_find_exports_back)
        self.content_stack.addWidget(self.find_audio_exports_view)

        self.splitter.addWidget(self.content_stack)

        # Initialize ViewManager and register all views
        self.view_manager = ViewManager(self.content_stack, self)
        self.view_manager.register_view(ViewManager.VIEW_PROJECTS, self.project_grid, 0)
        self.view_manager.register_view(ViewManager.VIEW_COLLECTIONS, self.collection_view, 1)
        self.view_manager.register_view(ViewManager.VIEW_LOCATIONS, self.location_panel, 2)
        self.view_manager.register_view(ViewManager.VIEW_LINK, self.link_panel, 3)
        self.view_manager.register_view(ViewManager.VIEW_HEALTH, self.health_dashboard, 4)
        self.view_manager.register_view(
            ViewManager.VIEW_SIMILARITIES, self.recommendations_panel, 5
        )
        self.view_manager.register_view(
            ViewManager.VIEW_PROPERTIES, self.project_properties_view, 6
        )
        self.view_manager.register_view(
            ViewManager.VIEW_FIND_EXPORTS, self.find_audio_exports_view, 7
        )

        # Set initial sizes
        self.splitter.setSizes([self.config.window.sidebar_width, 1000])

        layout.addWidget(self.splitter)

    def _create_status_bar(self) -> None:
        """Create the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Track base project count for status updates
        self._base_project_count = 0

        # Project count label
        self.project_count_label = QLabel("0 projects")
        self.status_bar.addWidget(self.project_count_label)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.status_bar.addWidget(spacer)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

        # Scan status label
        self.scan_status_label = QLabel("")
        self.status_bar.addPermanentWidget(self.scan_status_label)

        # Connect audio player for playback status
        from ..services.audio_player import AudioPlayer

        self._audio_player = AudioPlayer.instance()
        self._audio_player.playback_started.connect(self._on_audio_playback_started)
        self._audio_player.playback_stopped.connect(self._on_audio_playback_stopped)
        self._audio_player.playback_finished.connect(self._on_audio_playback_stopped)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        # Connect controller signals
        self.scan_controller.scan_started.connect(self._on_scan_started)
        self.scan_controller.scan_progress.connect(self._on_scan_progress)
        self.scan_controller.scan_complete.connect(self._on_scan_complete)
        self.scan_controller.scan_error.connect(self._on_scan_error)
        self.scan_controller.project_found.connect(self._on_project_found)

        # Start file watcher for automatic updates
        self._start_watcher()

    def _auto_scan_on_startup(self) -> None:
        """Trigger automatic scan on startup after app is fully loaded."""
        # Check if there are any active locations to scan
        session = get_session()
        try:
            active_locations = session.query(Location).filter(Location.is_active == True).all()
            if not active_locations:
                return  # No locations to scan

            # Set flag to indicate this is an auto-scan
            self._is_auto_scan = True

            # Update status bar
            self.scan_status_label.setText("Auto-Scanning on Startup...")

            # Start the scan
            self.scan_controller.start_scan()
        finally:
            session.close()

    def _show_startup_dialogs(self) -> None:
        """Show FTUE dialog (if enabled) and Add Location (if no locations)."""
        # Show FTUE / User Guide if enabled
        if self.config.ui.show_ftue_at_startup:
            from .dialogs.ftue_dialog import FTUEDialog

            dialog = FTUEDialog(self, show_startup_checkbox=True)
            dialog.exec()

        # If no locations, prompt user to add one
        session = get_session()
        try:
            if session.query(Location).count() == 0:
                self._on_add_location()
        finally:
            session.close()

    def _initial_load(self) -> None:
        """Load initial data on startup."""
        self._refresh_sidebar()
        self._load_projects()

        # Show FTUE and Add Location dialogs after UI is ready
        QTimer.singleShot(500, self._show_startup_dialogs)

        # Start file watcher for automatic updates
        # Auto-scan on startup after app is fully loaded
        # Delay scan to ensure UI is fully rendered
        QTimer.singleShot(1000, self._auto_scan_on_startup)

    def _start_watcher(self) -> None:
        """Start the file system watcher for automatic project updates."""
        try:
            if self._watcher is None:
                self._watcher = FileWatcher(self)

                # Connect watcher signals to refresh UI
                self._watcher.project_created.connect(self._on_watcher_project_created)
                self._watcher.project_modified.connect(self._on_watcher_project_modified)
                self._watcher.project_deleted.connect(self._on_watcher_project_deleted)
                self._watcher.project_moved.connect(self._on_watcher_project_moved)
                self._watcher.error_occurred.connect(self._on_watcher_error)

            # Start watching all active locations
            self._watcher.start()
            self.logger.info("File watcher started")
        except Exception as e:
            self.logger.error(f"Failed to start file watcher: {e}", exc_info=True)

    def _on_watcher_project_created(self, path: str) -> None:
        """Handle project created by watcher."""
        self.logger.info(f"Watcher: Project created: {path}")
        # Refresh UI to show new project
        QTimer.singleShot(500, self._refresh_view)  # Small delay to ensure DB commit

    def _on_watcher_project_modified(self, path: str) -> None:
        """Handle project modified by watcher."""
        self.logger.info(f"Watcher: Project modified: {path}")
        # Refresh UI to show updated metadata
        QTimer.singleShot(500, self._refresh_view)  # Small delay to ensure DB commit

    def _on_watcher_project_deleted(self, path: str) -> None:
        """Handle project deleted by watcher."""
        self.logger.info(f"Watcher: Project deleted: {path}")
        # Refresh UI to reflect deletion
        QTimer.singleShot(500, self._refresh_view)

    def _on_watcher_project_moved(self, old_path: str, new_path: str) -> None:
        """Handle project moved/renamed by watcher."""
        self.logger.info(f"Watcher: Project moved: {old_path} -> {new_path}")
        # Refresh UI to show updated path
        QTimer.singleShot(500, self._refresh_view)

    def _on_watcher_error(self, error_msg: str) -> None:
        """Handle watcher error."""
        self.logger.warning(f"Watcher error: {error_msg}")

    def _refresh_sidebar(self) -> None:
        """Refresh the sidebar with current data."""
        self.sidebar.refresh()

    def _load_projects(
        self,
        location_id: int | None = None,
        collection_id: int | None = None,
        tag_id: int | None = None,
        search_query: str = "",
        date_filter: str | None = None,
        tempo_min: int | None = None,
        tempo_max: int | None = None,
        sort_by: str | None = None,
        favorites_only: bool = False,
    ) -> None:
        """Load and display projects.

        Args:
            location_id: Filter by location ID.
            collection_id: Filter by collection ID.
            tag_id: Filter by tag ID.
            search_query: Search query string.
            date_filter: Date filter type (e.g., "today", "week", "month", "7days", "30days", "custom").
            tempo_min: Minimum tempo filter (BPM).
            tempo_max: Maximum tempo filter (BPM).
            sort_by: Sort field ("modified", "name", "created", "tempo").
        """
        from datetime import datetime, timedelta

        from sqlalchemy.orm import joinedload

        session = get_session()
        try:
            # Eagerly load relationships to avoid DetachedInstanceError
            from sqlalchemy.orm import joinedload

            query = session.query(Project).options(
                joinedload(Project.location),
                joinedload(Project.exports),
                joinedload(Project.project_tags),
            )

            # Always exclude backup projects (files in Backup folders)
            # Using case-insensitive check for "/Backup/" or "\Backup\" in path
            from sqlalchemy import not_, or_

            query = query.filter(
                not_(Project.file_path.ilike("%/Backup/%")),
                not_(Project.file_path.ilike("%\\Backup\\%")),
            )

            # Conditionally exclude MISSING projects based on view setting
            # When "Show Missing Projects" is unchecked, exclude MISSING projects
            # When checked, include all projects (both normal and MISSING)
            if not self._show_missing_projects:
                query = query.filter(Project.status != ProjectStatus.MISSING)

            if location_id:
                query = query.filter(Project.location_id == location_id)

            if collection_id:
                from ..database import ProjectCollection

                query = query.join(ProjectCollection).filter(
                    ProjectCollection.collection_id == collection_id
                )

            if tag_id:
                # Use junction table for tag filtering
                from ..database import ProjectTag

                query = query.join(ProjectTag).filter(ProjectTag.tag_id == tag_id).distinct()

            # Apply favorites filter
            if favorites_only:
                query = query.filter(Project.is_favorite == True)

            # Apply date filter
            date_filter_to_use = (
                date_filter if date_filter is not None else self._current_date_filter
            )
            if date_filter_to_use and date_filter_to_use != "clear":
                now = datetime.utcnow()
                if date_filter_to_use == "today":
                    # Today (from midnight)
                    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    query = query.filter(Project.modified_date >= start_date)
                elif date_filter_to_use == "week":
                    # This week (last 7 days)
                    start_date = now - timedelta(days=7)
                    query = query.filter(Project.modified_date >= start_date)
                elif date_filter_to_use == "month":
                    # This month (last 30 days)
                    start_date = now - timedelta(days=30)
                    query = query.filter(Project.modified_date >= start_date)
                elif date_filter_to_use == "7days":
                    # Last 7 days - modified OR created
                    from sqlalchemy import or_

                    start_date = now - timedelta(days=7)
                    query = query.filter(
                        or_(Project.modified_date >= start_date, Project.created_date >= start_date)
                    )
                elif date_filter_to_use == "30days":
                    # Last 30 days
                    start_date = now - timedelta(days=30)
                    query = query.filter(Project.modified_date >= start_date)
                elif date_filter_to_use == "custom":
                    # TODO: Implement custom date range dialog
                    pass

                # Only show projects that have a date (modified or created for 7days filter)
                if date_filter_to_use == "7days":
                    from sqlalchemy import or_

                    query = query.filter(
                        or_(Project.modified_date.isnot(None), Project.created_date.isnot(None))
                    )
                else:
                    query = query.filter(Project.modified_date.isnot(None))

            # Apply tempo filter
            tempo_min_to_use = tempo_min if tempo_min is not None else self._current_tempo_min
            tempo_max_to_use = tempo_max if tempo_max is not None else self._current_tempo_max

            if tempo_min_to_use > 0:
                query = query.filter(Project.tempo >= tempo_min_to_use)
            if tempo_max_to_use > 0 and tempo_max_to_use < 999:
                query = query.filter(Project.tempo <= tempo_max_to_use)

            # If tempo filter is active, only show projects with tempo data
            if tempo_min_to_use > 0 or (tempo_max_to_use > 0 and tempo_max_to_use < 999):
                query = query.filter(Project.tempo.isnot(None))

            if search_query:
                # Use FTS search
                from sqlalchemy import String

                from ..database.db import search_projects_fts

                project_ids = search_projects_fts(search_query)
                if project_ids:
                    query = query.filter(Project.id.in_(project_ids))
                else:
                    # Fallback to LIKE search including plugins and devices
                    search_pattern = f"%{search_query}%"
                    query = query.filter(
                        Project.name.ilike(search_pattern)
                        | Project.export_song_name.ilike(search_pattern)
                        | Project.notes.ilike(search_pattern)
                        |
                        # Search in plugins JSON array
                        Project.plugins.cast(String).ilike(search_pattern)
                        |
                        # Search in devices JSON array
                        Project.devices.cast(String).ilike(search_pattern)
                    )

            # Apply sorting
            sort_field = sort_by if sort_by is not None else self._current_sort
            from sqlalchemy import nullsfirst, nullslast

            if sort_field == "name" or sort_field == "name_asc":
                query = query.order_by(Project.name.asc())
            elif sort_field == "name_desc":
                query = query.order_by(Project.name.desc())
            elif sort_field == "created" or sort_field == "created_desc":
                query = query.order_by(Project.created_date.desc())
            elif sort_field == "created_asc":
                query = query.order_by(Project.created_date.asc())
            elif sort_field == "tempo" or sort_field == "tempo_desc":
                # Sort by tempo descending, nulls last
                query = query.order_by(nullslast(Project.tempo.desc()))
            elif sort_field == "tempo_asc":
                # Sort by tempo ascending, nulls last
                query = query.order_by(nullslast(Project.tempo.asc()))
            elif sort_field == "location" or sort_field == "location_asc":
                # Sort by location name
                from ..database import Location

                query = query.outerjoin(Location).order_by(nullslast(Location.name.asc()))
            elif sort_field == "location_desc":
                from ..database import Location

                query = query.outerjoin(Location).order_by(nullsfirst(Location.name.desc()))
            elif sort_field == "length" or sort_field == "length_desc":
                # Sort by arrangement length descending, nulls last
                query = query.order_by(nullslast(Project.arrangement_length.desc()))
            elif sort_field == "length_asc":
                # Sort by arrangement length ascending, nulls last
                query = query.order_by(nullslast(Project.arrangement_length.asc()))
            elif sort_field == "size" or sort_field == "size_desc":
                # Sort by file size descending, nulls last
                query = query.order_by(nullslast(Project.file_size.desc()))
            elif sort_field == "size_asc":
                # Sort by file size ascending, nulls last
                query = query.order_by(nullslast(Project.file_size.asc()))
            elif sort_field == "version_desc":
                # Sort by version descending (v12, v11, v10, v9, None)
                # Use a CASE statement to order versions numerically
                version_order = case(
                    (Project.ableton_version.like("%Live 12%"), 12),
                    (Project.ableton_version.like("%Live 11%"), 11),
                    (Project.ableton_version.like("%Live 10%"), 10),
                    (Project.ableton_version.like("%Live 9%"), 9),
                    else_=0,
                )
                query = query.order_by(nullslast(version_order.desc()))
            elif sort_field == "version_asc":
                # Sort by version ascending (v9, v10, v11, v12, None)
                version_order = case(
                    (Project.ableton_version.like("%Live 9%"), 9),
                    (Project.ableton_version.like("%Live 10%"), 10),
                    (Project.ableton_version.like("%Live 11%"), 11),
                    (Project.ableton_version.like("%Live 12%"), 12),
                    else_=0,
                )
                query = query.order_by(nullslast(version_order.asc()))
            elif sort_field == "key_asc":
                # Sort by musical key alphabetically (A, A#, B, C, etc.), nulls last
                query = query.order_by(
                    nullslast(Project.musical_key.asc()), nullslast(Project.scale_type.asc())
                )
            elif sort_field == "key_desc":
                # Sort by musical key reverse alphabetically, nulls last
                query = query.order_by(
                    nullslast(Project.musical_key.desc()), nullslast(Project.scale_type.desc())
                )
            elif sort_field == "modified_asc":
                query = query.order_by(Project.modified_date.asc())
            else:  # "modified" or "modified_desc" is default
                query = query.order_by(Project.modified_date.desc())

            projects = query.all()

            self.project_grid.set_projects(projects)
            self._base_project_count = len(projects)
            self.project_count_label.setText(f"{self._base_project_count} projects")
        finally:
            session.close()

    def _update_project_count(self, count: int) -> None:
        """Update the project count in status bar."""
        self._base_project_count = count
        self.project_count_label.setText(f"{count} projects")

    def _on_audio_playback_started(self, file_path: str) -> None:
        """Handle audio playback started - update status bar."""
        from pathlib import Path

        filename = Path(file_path).name
        self.project_count_label.setText(
            f"{self._base_project_count} projects  🔊 Playing: {filename}"
        )
        self.project_count_label.setStyleSheet("color: #4CAF50;")  # Green when playing

    def _on_audio_playback_stopped(self) -> None:
        """Handle audio playback stopped - restore status bar."""
        self.project_count_label.setText(f"{self._base_project_count} projects")
        self.project_count_label.setStyleSheet("")

    # Menu actions
    def _on_add_location(self) -> None:
        """Show add location dialog."""
        from .dialogs.add_location import AddLocationDialog

        dialog = AddLocationDialog(self)
        if dialog.exec():
            self._refresh_sidebar()
            self.location_panel.refresh()

    def _on_scan_all(self) -> None:
        """Scan all active locations."""
        self.scan_controller.start_scan(None)

    def _on_scan_location(self, location_id: int) -> None:
        """Scan a specific location."""
        self.scan_controller.start_scan(location_id)

    def _on_scan_started(self) -> None:
        """Handle scan started signal."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        # Status message will be set by _auto_scan_on_startup if it's an auto-scan
        if not hasattr(self, "_is_auto_scan") or not self._is_auto_scan:
            self.scan_status_label.setText("Scanning...")

    def _on_scan_error(self, error_msg: str) -> None:
        """Handle scan errors."""
        self.scan_status_label.setText(f"Scan error: {error_msg}")
        self.progress_bar.setVisible(False)
        QTimer.singleShot(10000, lambda: self.scan_status_label.setText(""))

    def _on_scan_progress(self, current: int, total: int, message: str) -> None:
        """Update scan progress."""
        if total > 0:
            self.progress_bar.setValue(int(100 * current / total))
        self.scan_status_label.setText(message)

    def _on_scan_complete(self, found_count: int) -> None:
        """Handle scan completion."""
        self.progress_bar.setVisible(False)
        if hasattr(self, "_is_auto_scan") and self._is_auto_scan:
            status_msg = f"Auto-scan complete: Found {found_count} new project(s)"
            self._is_auto_scan = False
        else:
            status_msg = f"Scan complete: Found {found_count} new project(s)"
        self.scan_status_label.setText(status_msg)
        self._load_projects()
        self._refresh_sidebar()

        # Clear after 5 seconds
        QTimer.singleShot(5000, lambda: self.scan_status_label.setText(""))

    def _on_project_found(self, path: str) -> None:
        """Handle a project being found during scan."""
        pass  # Could show toast notification

    def _on_reset_database(self) -> None:
        """Reset the database - delete all data and start fresh."""
        from ..database import close_database, reset_database

        # Confirm with user
        reply = QMessageBox.question(
            self,
            "Reset Database",
            "This will DELETE ALL DATA including:\n"
            "• All projects\n"
            "• All collections\n"
            "• All locations\n"
            "• All tags\n"
            "• All exports\n\n"
            "This action cannot be undone!\n\n"
            "Are you absolutely sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Stop all services before reset
        self.logger.info("Stopping all services before database reset...")

        # Stop scanner
        self.scan_controller.stop_scan()
        if self._scanner:
            self._scanner.stop()
            self._scanner = None

        # Stop watcher
        if self._watcher:
            self._watcher.stop()
            self._watcher = None

        # Stop link scanner
        if self._link_scanner:
            self._link_scanner.stop()
            self._link_scanner = None

        # Stop link panel scanner if running
        if hasattr(self, "link_panel"):
            if hasattr(self.link_panel, "cleanup"):
                self.link_panel.cleanup()
            elif hasattr(self.link_panel, "_scanner") and self.link_panel._scanner:
                self.link_panel._scanner.stop()

        # Close database connections
        close_database()

        # Reset database
        self.logger.info("Resetting database...")
        success = reset_database()

        if success:
            QMessageBox.information(
                self,
                "Database Reset",
                "Database has been reset successfully.\n"
                "The application will now refresh with an empty database.",
            )

            # Refresh UI
            self._refresh_sidebar()
            self._load_projects()
            self.logger.info("Database reset successful - UI refreshed")
            self.scan_status_label.setText("Database reset complete")
        else:
            QMessageBox.critical(
                self,
                "Database Reset Failed",
                "Failed to reset the database.\n" "Please check the console for error messages.",
            )

    def _on_cleanup_missing_projects(self) -> None:
        """Clean up MISSING projects from the database."""
        from ..database import Project, ProjectCollection, ProjectStatus, get_session

        session = get_session()
        try:
            # Find all MISSING projects
            missing_projects = (
                session.query(Project).filter(Project.status == ProjectStatus.MISSING).all()
            )

            if not missing_projects:
                QMessageBox.information(
                    self, "No Missing Projects", "There are no MISSING projects to clean up."
                )
                return

            # Separate projects into those in collections and those not
            projects_in_collections = []
            projects_not_in_collections = []

            for project in missing_projects:
                # Check if project is in any collection
                in_collection = (
                    session.query(ProjectCollection)
                    .filter(ProjectCollection.project_id == project.id)
                    .first()
                    is not None
                )

                if in_collection:
                    projects_in_collections.append(project)
                else:
                    projects_not_in_collections.append(project)

            # Confirm deletion
            message = "Remove MISSING projects from database?\n\n"
            message += f"Found {len(missing_projects)} MISSING project(s):\n\n"
            if projects_not_in_collections:
                message += f"• {len(projects_not_in_collections)} project(s) will be removed from database (not in collections)\n"
            if projects_in_collections:
                message += (
                    f"• {len(projects_in_collections)} project(s) will be KEPT (in collections)\n"
                )
            message += "\n⚠️ IMPORTANT: This only removes database records. Your actual project files (.als) will NOT be deleted.\n\n"
            message += "This action cannot be undone. Are you sure?"

            reply = QMessageBox.question(
                self,
                "Clean Up Missing Projects",
                message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            # Delete projects not in collections
            deleted_count = 0
            for project in projects_not_in_collections:
                session.delete(project)
                deleted_count += 1

            # Keep projects in collections (they remain MISSING but are preserved)
            kept_count = len(projects_in_collections)

            session.commit()

            self.logger.info(f"Removed {deleted_count} MISSING project(s) not in collections")
            if kept_count > 0:
                self.logger.info(f"Kept {kept_count} MISSING project(s) that are in collections")

            # Refresh UI
            self._refresh_sidebar()
            self._load_projects()

            # Show summary message
            summary = "Cleanup complete.\n\n"
            if deleted_count > 0:
                summary += f"Removed {deleted_count} MISSING project(s) from database.\n"
            if kept_count > 0:
                summary += f"Kept {kept_count} MISSING project(s) that are in collections."

            QMessageBox.information(self, "Cleanup Complete", summary)
        finally:
            session.close()

    def _on_cleanup_backup_projects(self) -> None:
        """Remove backup projects (files in Backup folders) from the database."""
        from sqlalchemy import or_

        from ..database import Project, ProjectCollection, get_session

        session = get_session()
        try:
            # Find all projects with "Backup" in their path
            backup_projects = (
                session.query(Project)
                .filter(
                    or_(
                        Project.file_path.ilike("%/Backup/%"),
                        Project.file_path.ilike("%\\Backup\\%"),
                    )
                )
                .all()
            )

            if not backup_projects:
                QMessageBox.information(
                    self, "No Backup Projects", "No backup projects found in the database."
                )
                return

            # Separate projects into those in collections and those not
            projects_in_collections = []
            projects_not_in_collections = []

            for project in backup_projects:
                in_collection = (
                    session.query(ProjectCollection)
                    .filter(ProjectCollection.project_id == project.id)
                    .first()
                    is not None
                )

                if in_collection:
                    projects_in_collections.append(project)
                else:
                    projects_not_in_collections.append(project)

            # Confirm deletion
            message = f"Found {len(backup_projects)} backup project(s) in the database.\n\n"
            message += "These are .als files located in Backup folders.\n\n"
            if projects_not_in_collections:
                message += f"• {len(projects_not_in_collections)} project(s) will be removed (not in collections)\n"
            if projects_in_collections:
                message += (
                    f"• {len(projects_in_collections)} project(s) will be KEPT (in collections)\n"
                )
            message += "\nThis will NOT delete any files - only database records.\n\n"
            message += "Continue?"

            reply = QMessageBox.question(
                self,
                "Remove Backup Projects",
                message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            # Delete projects not in collections
            deleted_count = 0
            for project in projects_not_in_collections:
                session.delete(project)
                deleted_count += 1

            kept_count = len(projects_in_collections)

            session.commit()

            self.logger.info(f"Removed {deleted_count} backup project(s) from database")

            # Refresh UI
            self._refresh_sidebar()
            self._load_projects()

            # Show summary message
            summary = "Cleanup complete.\n\n"
            summary += f"Removed {deleted_count} backup project(s) from database.\n"
            if kept_count > 0:
                summary += f"Kept {kept_count} backup project(s) that are in collections."

            QMessageBox.information(self, "Cleanup Complete", summary)
        finally:
            session.close()

    def _on_settings(self, initial_tab: str | None = None) -> None:
        """Show settings dialog.

        Args:
            initial_tab: Optional tab to open to ("live", "locations", etc.).
        """
        from PyQt6.QtWidgets import QApplication

        from .dialogs.settings_dialog import SettingsDialog
        from .theme import AbletonTheme

        dialog = SettingsDialog(self.config, self, initial_tab=initial_tab)
        old_theme = self.config.ui.theme
        if dialog.exec():
            # Settings were saved, refresh UI if needed
            # Check if theme changed
            if old_theme != self.config.ui.theme:
                # Reload theme
                self.theme = AbletonTheme(self.config.ui.theme)
                self.theme.apply(QApplication.instance())
                # Refresh search bar theme-dependent styles
                self.search_bar.refresh_theme()
            self._refresh_view()

    def _focus_search(self) -> None:
        """Focus the search bar."""
        self.search_bar.setFocus()
        self.search_bar.selectAll()

    def _select_all_projects(self) -> None:
        """Select all projects in current view."""
        self.project_grid.select_all()

    def _set_view_mode(self, mode: str) -> None:
        """Set the project view mode.

        Args:
            mode: "grid" or "list"
        """
        self.project_grid.set_view_mode(mode)
        self.grid_btn.setChecked(mode == "grid")
        self.list_btn.setChecked(mode == "list")
        self.config.ui.default_view = mode
        save_config()

    def _toggle_show_missing(self) -> None:
        """Toggle showing/hiding MISSING projects."""
        self._show_missing_projects = self.show_missing_action.isChecked()
        # Reload projects with the new filter
        self._load_projects()

    def _toggle_sidebar(self) -> None:
        """Toggle sidebar visibility."""
        visible = not self.sidebar.isVisible()
        self.sidebar.setVisible(visible)
        self.sidebar_action.setChecked(visible)

    def _refresh_view(self) -> None:
        """Refresh the current view."""
        self._load_projects()
        self._refresh_sidebar()

    def _on_new_collection(self) -> None:
        """Show new collection dialog."""
        from .dialogs.create_collection import CreateCollectionDialog

        dialog = CreateCollectionDialog(self)
        if dialog.exec():
            self._refresh_sidebar()
            self.collection_view.refresh()
            # Switch to collections view to show the new collection
            self.view_manager.switch_to_view(ViewManager.VIEW_COLLECTIONS)

    def _on_new_smart_collection(self) -> None:
        """Show new smart collection dialog."""
        from .dialogs.smart_collection import SmartCollectionDialog

        dialog = SmartCollectionDialog(self)
        if dialog.exec():
            self._refresh_sidebar()
            self.collection_view.refresh()
            # Switch to collections view
            self.view_manager.switch_to_view(ViewManager.VIEW_COLLECTIONS)

    def _on_create_collection_from_filter(self, filter_state: dict) -> None:
        """Create a smart collection from the current filter state."""
        from .dialogs.smart_collection import SmartCollectionDialog

        # Create dialog and pre-populate with filter state
        dialog = SmartCollectionDialog(self)

        # Apply filter state to dialog
        if "tempo_min" in filter_state:
            dialog.tempo_min_spin.setValue(filter_state["tempo_min"])
            dialog.use_tempo_filter.setChecked(True)
        if "tempo_max" in filter_state:
            dialog.tempo_max_spin.setValue(filter_state["tempo_max"])
            dialog.use_tempo_filter.setChecked(True)
        if "days_ago" in filter_state:
            dialog.days_spin.setValue(filter_state["days_ago"])
            dialog.use_date_filter.setChecked(True)
        if "search_text" in filter_state:
            # Suggest collection name based on search text
            dialog.name_input.setText(f"Search: {filter_state['search_text']}")

        if dialog.exec():
            self._refresh_sidebar()
            self.collection_view.refresh()
            # Switch to collections view
            self.view_manager.switch_to_view(ViewManager.VIEW_COLLECTIONS)

    def _on_global_search(self) -> None:
        """Show global search dialog."""
        pass  # TODO: Implement global search dialog

    def _show_link_panel(self) -> None:
        """Show the Link network panel."""
        self.view_manager.switch_to_view(ViewManager.VIEW_LINK)
        self.sidebar.clear_selection()

    def _on_force_rescan_metadata(self) -> None:
        """Force re-scan of all project metadata by clearing parse timestamps."""
        from ..database import Project, get_session

        reply = QMessageBox.question(
            self,
            "Force Re-scan Metadata",
            "This will clear all parse timestamps and re-extract metadata\n"
            "(tempo, arrangement length, plugins, etc.) for all projects\n"
            "on the next scan.\n\n"
            "Proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        session = get_session()
        try:
            count = session.query(Project).update({Project.last_parsed: None})
            session.commit()
            self.logger.info(f"Cleared last_parsed for {count} projects")

            QMessageBox.information(
                self,
                "Ready to Re-scan",
                f"Cleared parse timestamps for {count} project(s).\n\n"
                "Click 'Scan' in the toolbar to re-extract all metadata.",
            )
        except Exception as e:
            session.rollback()
            self.logger.error(f"Failed to clear parse timestamps: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to clear timestamps:\n{str(e)}")
        finally:
            session.close()

    def _on_clear_thumbnail_cache(self) -> None:
        """Clear all thumbnail cache files and database references."""

        from ..database import Project, get_session
        from ..utils.paths import get_thumbnail_cache_dir

        # Confirm with user
        reply = QMessageBox.question(
            self,
            "Clear Thumbnail Cache",
            "This will delete all generated waveform thumbnails.\n\n"
            "Thumbnails will be regenerated automatically when you view projects.\n\n"
            "This action cannot be undone. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            # Get thumbnail cache directory
            cache_dir = get_thumbnail_cache_dir()

            # Count files before deletion
            thumbnail_files = list(cache_dir.glob("*.png"))
            file_count = len(thumbnail_files)

            # Delete all thumbnail files
            deleted_count = 0
            for thumbnail_file in thumbnail_files:
                try:
                    thumbnail_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to delete thumbnail {thumbnail_file}: {e}")

            # Clear thumbnail_path references from database and force regeneration
            session = get_session()
            try:
                # Get all projects that have thumbnails
                projects_with_thumbnails = (
                    session.query(Project).filter(Project.thumbnail_path.isnot(None)).all()
                )
                projects_updated = len(projects_with_thumbnails)

                # Clear thumbnail_path for all projects
                for project in projects_with_thumbnails:
                    project.thumbnail_path = None

                session.commit()
                self.logger.info(f"Cleared thumbnail_path for {projects_updated} projects")

                # Force regenerate thumbnails for ALL projects with exports using current color mode
                # This ensures all thumbnails use the latest color mode (including new gradients)
                from ..config import get_config
                from ..database import Export
                from ..services.audio_preview import AudioPreviewGenerator

                config = get_config()
                color_mode = config.ui.waveform_color_mode

                # Get all projects that have exports (needed for thumbnail generation)
                all_projects_with_exports = session.query(Project).join(Export).distinct().all()

                regenerated_count = 0
                for project in all_projects_with_exports:
                    # Force regenerate with current color mode
                    # For random mode, this will select from all available gradients including new ones
                    preview_path = AudioPreviewGenerator.get_or_generate_preview(
                        project.id, color_mode=color_mode, force_regenerate=True
                    )
                    if preview_path:
                        regenerated_count += 1

                self.logger.info(
                    f"Regenerated {regenerated_count} thumbnails with color mode: {color_mode}"
                )

            except Exception as e:
                session.rollback()
                self.logger.error(f"Failed to clear thumbnail_path references: {e}", exc_info=True)
            finally:
                session.close()

            # Refresh UI to show regenerated thumbnails
            self._load_projects()

            # Show success message
            QMessageBox.information(
                self,
                "Cache Cleared",
                f"Successfully cleared thumbnail cache.\n\n"
                f"• Deleted {deleted_count} thumbnail file(s)\n"
                f"• Cleared {projects_updated} database reference(s)\n\n"
                f"Thumbnails will be regenerated with new colors when you view projects.",
            )

        except Exception as e:
            self.logger.error(f"Failed to clear thumbnail cache: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to clear thumbnail cache:\n{str(e)}")

    def _on_view_logs(self) -> None:
        """Show log viewer dialog."""
        from .dialogs.log_viewer_dialog import LogViewerDialog

        dialog = LogViewerDialog(self)
        dialog.exec()

    def _on_user_guide(self) -> None:
        """Show User Guide / FTUE dialog."""
        from .dialogs.ftue_dialog import FTUEDialog

        dialog = FTUEDialog(self, show_startup_checkbox=True)
        dialog.exec()

    def _show_about(self) -> None:
        """Show about dialog with compact README content."""
        from PyQt6.QtWidgets import QPushButton, QTextBrowser

        dialog = QDialog(self)
        dialog.setWindowTitle("About Ableton Hub")
        dialog.setMinimumSize(700, 500)
        dialog.resize(800, 600)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)

        # Create text browser for scrollable content
        text_browser = QTextBrowser()
        text_browser.setOpenExternalLinks(True)
        text_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {AbletonTheme.COLORS['surface']};
                border: 1px solid {AbletonTheme.COLORS['border']};
                border-radius: 4px;
                padding: 10px;
                font-size: 12px;
            }}
        """)

        # Generate What's New content from single source of truth
        whats_new_html = get_whats_new_html()

        # About dialog content - version is imported from package
        about_html = f"""
        <h1 style="color: #FF764D; margin-bottom: 5px;">Ableton Hub</h1>
        <p style="color: #888; margin-top: 0;"><b>Version {__version__}</b></p>
        
        <p>A comprehensive cross-platform desktop application for organizing, managing, and 
        discovering Ableton Live projects. Built with Python and PyQt6.</p>
        
        {whats_new_html}
        
        <h2 style="color: #FF764D;">🎵 Complete Feature List</h2>
        
        <h3>Project Discovery & Management</h3>
        <ul>
            <li>Multi-location scanning (local, network, cloud, USB)</li>
            <li>Automatic file watching for real-time updates</li>
            <li>Rich metadata extraction (plugins, tempo, tracks, samples, automation)</li>
            <li>File hash tracking for duplicate detection</li>
            <li>Project health dashboard</li>
            <li>Backup project exclusion (Backup folders automatically filtered)</li>
            <li>Missing project detection and cleanup</li>
            <li>Duplicate detection with hash comparison</li>
        </ul>
        
        <h3>Collections & Organization</h3>
        <ul>
            <li>Static collections (albums, EPs, sessions, compilations)</li>
            <li>Smart collections with dynamic rules (tags, dates, tempo, plugins, metadata)</li>
            <li>Track management with custom names and artwork</li>
            <li>Flexible tagging system with color coding</li>
            <li>Drag-and-drop reordering</li>
        </ul>
        
        <h3>Search & Discovery</h3>
        <ul>
            <li>Full-text search (FTS5) across names, exports, notes, plugins, devices</li>
            <li>Advanced filtering (date, location, tags, tempo range, plugins)</li>
            <li>Grid and sortable list views</li>
            <li>Real-time debounced search</li>
            <li>View Missing Projects toggle</li>
        </ul>
        
        <h3>Export Tracking & Playback</h3>
        <ul>
            <li>Automatic export detection during scanning</li>
            <li>Smart fuzzy matching (exact → normalized → fuzzy)</li>
            <li>Click-to-play on project cards (cycle through multiple exports)</li>
            <li>In-app audio playback with transport controls</li>
            <li>Waveform thumbnails</li>
            <li>Export metadata tracking (format, bit depth, sample rate)</li>
        </ul>
        
        <h3>Ableton Live Integration</h3>
        <ul>
            <li>Live version auto-detection</li>
            <li>Project launcher with version selection</li>
            <li>Version management in sidebar</li>
            <li>Preferences folder access</li>
            <li>Options.txt editor</li>
            <li>Backup project launch from Properties dialog</li>
        </ul>
        
        <h3>Backup & Archive</h3>
        <ul>
            <li>Backup location management</li>
            <li>View all project backups in Properties</li>
            <li>Launch backup versions with double-click</li>
            <li>Archive service (ZIP backups)</li>
            <li>One-click archiving</li>
        </ul>
        
        <h3>Additional Features</h3>
        <ul>
            <li>Ableton Link WiFi network monitoring</li>
            <li>MCP Agents integration links</li>
            <li>Learning resources (Making Music, Learning Music, Max for Live docs)</li>
            <li>Multiple themes (Orange, Blue, Green, Pink)</li>
            <li>Database cleanup tools</li>
        </ul>
        
        <h2 style="color: #FF764D;">📋 Requirements</h2>
        <ul>
            <li>Python 3.11+</li>
            <li>Windows 10/11, macOS 10.15+, or Linux</li>
        </ul>
        
        <h2 style="color: #FF764D;">👤 Author</h2>
        <p><b>Tom Carlile</b><br>
        Email: <a href="mailto:carlile.tom@gmail.com" style="color: #FF764D;">carlile.tom@gmail.com</a></p>
        
        <p style="color: #666; font-size: 10px; margin-top: 20px;">
        <i>This application is not affiliated with or endorsed by Ableton AG. 
        Ableton Live is a trademark of Ableton AG.</i></p>
        """

        text_browser.setHtml(about_html)
        layout.addWidget(text_browser)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(dialog.accept)
        close_btn.setStyleSheet(f"""
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

        # Center the button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        dialog.exec()

    # Navigation handlers
    def _on_navigation_changed(self, view: str) -> None:
        """Handle sidebar navigation change.

        Args:
            view: View to show ("projects", "collections", "locations", "link", "new_collection", "favorites", "recent")
        """
        # Clean up properties view workers when navigating away via sidebar
        if self.view_manager.get_current_view() == ViewManager.VIEW_PROPERTIES:
            self.project_properties_view.cleanup()

        # Clean up Find Audio Exports view when navigating away via sidebar
        if self.view_manager.get_current_view() == ViewManager.VIEW_FIND_EXPORTS:
            self.find_audio_exports_view.cleanup()

        # Reset missing projects view when navigating away from projects view
        if view != "projects" and self._show_missing_projects:
            self._show_missing_projects = False
            self.show_missing_action.setChecked(False)

        if view == "projects":
            self.view_manager.switch_to_view(ViewManager.VIEW_PROJECTS)
            self._load_projects()
        elif view == "favorites":
            self.view_manager.switch_to_view(ViewManager.VIEW_PROJECTS)
            self._load_projects(favorites_only=True)
        elif view == "recent":
            self.view_manager.switch_to_view(ViewManager.VIEW_PROJECTS)
            self._load_projects(date_filter="7days")
        elif view == "collections":
            self.view_manager.switch_to_view(ViewManager.VIEW_COLLECTIONS)
            self.collection_view.refresh()
        elif view == "locations":
            self.view_manager.switch_to_view(ViewManager.VIEW_LOCATIONS)
            self.location_panel.refresh()
        elif view == "link":
            self.view_manager.switch_to_view(ViewManager.VIEW_LINK)
        elif view == "health":
            self.view_manager.switch_to_view(ViewManager.VIEW_HEALTH)
            self.health_dashboard.refresh()
        elif view == "similarities":
            self.view_manager.switch_to_view(ViewManager.VIEW_SIMILARITIES)
            # If a project is selected, set it in similarities panel
            selected_ids = self.project_grid.get_selected_ids()
            if selected_ids and len(selected_ids) == 1:
                self.recommendations_panel.set_project(selected_ids[0])
        elif view == "new_collection":
            # Show new collection dialog
            self._on_new_collection()
        elif view == "new_smart_collection":
            # Show new smart collection dialog
            self._on_new_smart_collection()

    def _on_location_filter(self, location_id: int) -> None:
        """Filter projects by location."""
        self.view_manager.switch_to_view(ViewManager.VIEW_PROJECTS)
        self._load_projects(location_id=location_id)

    def _on_collection_selected(self, collection_id: int) -> None:
        """Show collection details view."""
        self.view_manager.switch_to_view(ViewManager.VIEW_COLLECTIONS)
        self.collection_view.set_collection(collection_id)

    def show_project_properties(self, project_id: int) -> None:
        """Show project properties view for a project.

        Args:
            project_id: The project ID to show properties for.
        """
        self.view_manager.switch_to_view(ViewManager.VIEW_PROPERTIES)
        self.project_properties_view.set_project(project_id)
        self.sidebar.clear_selection()

    def _on_properties_back(self) -> None:
        """Handle back button from properties view."""
        self.project_properties_view.cleanup()
        self.view_manager.switch_to_view(ViewManager.VIEW_PROJECTS)
        self._load_projects()

    def _on_find_audio_exports(self, location_id: int) -> None:
        """Handle Find Audio Exports request from sidebar."""
        self.find_audio_exports_view.set_location(location_id)
        self.view_manager.switch_to_view(ViewManager.VIEW_FIND_EXPORTS)
        self.sidebar.clear_selection()

    def _on_find_exports_back(self) -> None:
        """Handle back button from Find Audio Exports view."""
        self.find_audio_exports_view.cleanup()
        self.view_manager.switch_to_view(ViewManager.VIEW_LOCATIONS)
        self.location_panel.refresh()

    def _on_project_saved(self) -> None:
        """Handle project being saved in properties view."""
        # Refresh the project grid to reflect any changes
        self._load_projects()
        self._refresh_sidebar()

    def _on_edit_collection_from_sidebar(self, collection_id: int) -> None:
        """Edit collection from sidebar context menu."""
        from ..database import Collection, get_session
        from .dialogs.create_collection import CreateCollectionDialog
        from .dialogs.smart_collection import SmartCollectionDialog

        session = get_session()
        try:
            collection = session.query(Collection).get(collection_id)
            if collection:
                if collection.is_smart:
                    dialog = SmartCollectionDialog(self, collection_id=collection_id)
                else:
                    dialog = CreateCollectionDialog(self, collection_id=collection_id)

                if dialog.exec():
                    self._refresh_sidebar()
                    self.collection_view.refresh()
                    # If currently viewing this collection, update it
                    if (
                        hasattr(self.collection_view, "_collection")
                        and self.collection_view._collection
                        and self.collection_view._collection.id == collection_id
                    ):
                        self.collection_view.set_collection(collection_id)
        finally:
            session.close()

    def _on_delete_location_from_sidebar(self, location_id: int) -> None:
        """Delete location from sidebar context menu."""
        from ..database import Location, Project, ProjectCollection, get_session

        session = get_session()
        try:
            location = session.query(Location).filter(Location.id == location_id).first()
            if not location:
                return

            # Get all projects in this location
            projects = session.query(Project).filter(Project.location_id == location_id).all()
            project_count = len(projects)

            # Separate projects into those in collections and those not
            projects_in_collections = []
            projects_not_in_collections = []

            for project in projects:
                # Check if project is in any collection
                in_collection = (
                    session.query(ProjectCollection)
                    .filter(ProjectCollection.project_id == project.id)
                    .first()
                    is not None
                )

                if in_collection:
                    projects_in_collections.append(project)
                else:
                    projects_not_in_collections.append(project)

            # Confirm deletion
            if project_count > 0:
                message = f"Remove location '{location.name}'?\n\n"
                message += f"This location has {project_count} project(s).\n\n"
                if projects_not_in_collections:
                    message += f"• {len(projects_not_in_collections)} project(s) will be removed from the database (not in collections)\n"
                if projects_in_collections:
                    message += f"• {len(projects_in_collections)} project(s) will be KEPT (in collections, location cleared)\n"
                message += "\n⚠️ IMPORTANT: This only removes database records. Your actual project files (.als) will NOT be deleted and remain on your computer.\n\n"
                message += "Are you sure?"

                reply = QMessageBox.question(
                    self,
                    "Remove Location",
                    message,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
            else:
                reply = QMessageBox.question(
                    self,
                    "Remove Location",
                    f"Remove location '{location.name}'?\n\n" f"Are you sure?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )

            if reply != QMessageBox.StandardButton.Yes:
                return

            # Delete projects not in collections
            deleted_count = 0
            for project in projects_not_in_collections:
                session.delete(project)
                deleted_count += 1

            # Clear location from projects in collections (keep the projects)
            kept_count = 0
            for project in projects_in_collections:
                project.location_id = None
                kept_count += 1

            # Delete the location
            session.delete(location)
            session.commit()

            self.logger.info(f"Removed location: {location.name} (ID: {location_id})")
            if deleted_count > 0:
                self.logger.info(f"Deleted {deleted_count} project(s) not in collections")
            if kept_count > 0:
                self.logger.info(f"Kept {kept_count} project(s) in collections (location cleared)")

            # Refresh UI
            self._refresh_sidebar()
            self._load_projects()
            self.location_panel.refresh()

            # Show summary message
            summary = f"Location '{location.name}' has been removed.\n\n"
            if deleted_count > 0:
                summary += (
                    f"Removed {deleted_count} project(s) from database (not in collections).\n"
                )
            if kept_count > 0:
                summary += f"Kept {kept_count} project(s) (in collections, location cleared).\n"
            summary += "\nNote: Your actual project files (.als) were NOT deleted and remain on your computer."

            QMessageBox.information(self, "Location Removed", summary)
        except Exception as e:
            session.rollback()
            self.logger.error(f"Failed to remove location: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to remove location:\n{str(e)}")
        finally:
            session.close()

    def _on_cleanup_orphaned_projects(self) -> None:
        """Clean up projects that are not in any location."""
        from ..database import Project, ProjectCollection, get_session

        session = get_session()
        try:
            # Find all projects with no location
            orphaned_projects = session.query(Project).filter(Project.location_id == None).all()

            if not orphaned_projects:
                QMessageBox.information(
                    self, "No Orphaned Projects", "All projects are associated with a location."
                )
                return

            # Separate projects into those in collections and those not
            projects_in_collections = []
            projects_not_in_collections = []

            for project in orphaned_projects:
                # Check if project is in any collection
                in_collection = (
                    session.query(ProjectCollection)
                    .filter(ProjectCollection.project_id == project.id)
                    .first()
                    is not None
                )

                if in_collection:
                    projects_in_collections.append(project)
                else:
                    projects_not_in_collections.append(project)

            # Confirm deletion
            message = "Remove projects that are not in any location?\n\n"
            message += f"Found {len(orphaned_projects)} project(s) without a location:\n\n"
            if projects_not_in_collections:
                message += f"• {len(projects_not_in_collections)} project(s) will be removed from the database (not in collections)\n"
            if projects_in_collections:
                message += (
                    f"• {len(projects_in_collections)} project(s) will be KEPT (in collections)\n"
                )
            message += "\n⚠️ IMPORTANT: This only removes database records. Your actual project files (.als) will NOT be deleted and remain on your computer.\n\n"
            message += "This action cannot be undone. Are you sure?"

            reply = QMessageBox.question(
                self,
                "Remove Orphaned Projects",
                message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            # Delete projects not in collections
            deleted_count = 0
            deleted_names = []
            for project in projects_not_in_collections:
                deleted_names.append(project.name)
                session.delete(project)
                deleted_count += 1

            # Keep projects in collections (they remain orphaned but are preserved)
            kept_count = len(projects_in_collections)

            session.commit()

            self.logger.info(f"Removed {deleted_count} orphaned project(s) not in collections")
            if kept_count > 0:
                self.logger.info(f"Kept {kept_count} orphaned project(s) that are in collections")

            # Refresh UI
            self._refresh_sidebar()
            self._load_projects()

            # Show summary message
            summary = "Cleanup complete.\n\n"
            if deleted_count > 0:
                summary += (
                    f"Removed {deleted_count} project(s) from database (not in collections).\n"
                )
                if deleted_count <= 10:
                    summary += "\nRemoved projects:\n"
                    for name in deleted_names[:10]:
                        summary += f"  • {name}\n"
            if kept_count > 0:
                summary += f"\nKept {kept_count} project(s) that are in collections (location will remain empty).\n"
            if deleted_count > 0:
                summary += "\nNote: Your actual project files (.als) were NOT deleted and remain on your computer."

            QMessageBox.information(self, "Cleanup Complete", summary)
        except Exception as e:
            session.rollback()
            self.logger.error(f"Failed to cleanup orphaned projects: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to cleanup orphaned projects:\n{str(e)}")
        finally:
            session.close()

    def _on_delete_collection_from_sidebar(self, collection_id: int) -> None:
        """Delete collection from sidebar context menu."""
        from PyQt6.QtWidgets import QMessageBox

        from ..database import Collection, get_session

        session = get_session()
        try:
            collection = session.query(Collection).get(collection_id)
            if collection:
                reply = QMessageBox.question(
                    self,
                    "Delete Collection",
                    f"Are you sure you want to delete '{collection.name}'?\n\nThis will remove the collection but not the projects themselves.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    session.delete(collection)
                    session.commit()
                    self._refresh_sidebar()
                    self.collection_view.refresh()
                    # If currently viewing this collection, switch to collections list
                    if (
                        hasattr(self.collection_view, "_collection")
                        and self.collection_view._collection
                        and self.collection_view._collection.id == collection_id
                    ):
                        self.collection_view.refresh()
        finally:
            session.close()

    def _on_tag_filter(self, tag_id: int) -> None:
        """Filter projects by tag."""
        self.view_manager.switch_to_view(ViewManager.VIEW_PROJECTS)
        self._load_projects(tag_id=tag_id)

    def _on_manage_tags(self) -> None:
        """Show the manage tags dialog."""
        from .widgets.tag_editor import ManageTagsDialog

        dialog = ManageTagsDialog(self)
        dialog.tags_changed.connect(self._refresh_sidebar)
        dialog.exec()

    def _on_search(self, query: str) -> None:
        """Handle search query change."""
        self._load_projects(search_query=query, date_filter=self._current_date_filter)

    def _on_filter_changed(self, filter_type: str, value: str) -> None:
        """Handle filter change from search bar."""
        if filter_type == "date":
            # Store the date filter and reload projects
            self._current_date_filter = value if value != "clear" else None
            self._load_projects(
                search_query=self.search_bar.text(), date_filter=self._current_date_filter
            )
        elif filter_type == "location":
            # TODO: Implement location filter dialog
            pass
        elif filter_type == "tag":
            # TODO: Implement tag filter dialog
            pass

    def _on_tempo_filter_changed(self, min_tempo: int, max_tempo: int) -> None:
        """Handle tempo filter change from search bar."""
        self._current_tempo_min = min_tempo
        self._current_tempo_max = max_tempo
        self._load_projects(
            search_query=self.search_bar.text(),
            date_filter=self._current_date_filter,
            tempo_min=min_tempo,
            tempo_max=max_tempo,
        )

    def _on_sort_changed(self, sort_field: str) -> None:
        """Handle sort change from search bar."""
        self._current_sort = sort_field
        self._load_projects(
            search_query=self.search_bar.text(),
            date_filter=self._current_date_filter,
            tempo_min=self._current_tempo_min,
            tempo_max=self._current_tempo_max,
            sort_by=sort_field,
        )

    def _on_grid_sort_requested(self, column: str, direction: str) -> None:
        """Handle sort request from grid column header click."""
        # Combine column and direction into sort field
        sort_field = f"{column}_{direction}"
        self._current_sort = sort_field

        # Update the sort combo in search bar to match (if applicable)
        sort_map = {
            "modified_desc": "Modified ↓",
            "modified_asc": "Modified ↑",
            "name_asc": "Name A-Z",
            "name_desc": "Name Z-A",
            "tempo_desc": "Tempo ↓",
            "tempo_asc": "Tempo ↑",
            "length_desc": "Length ↓",
            "length_asc": "Length ↑",
            "version_desc": "Version ↓",
            "version_asc": "Version ↑",
            "key_asc": "Key A-Z",
            "key_desc": "Key Z-A",
            "location_asc": "Location",
        }
        combo_text = sort_map.get(sort_field)
        if combo_text:
            self.search_bar.sort_combo.blockSignals(True)
            index = self.search_bar.sort_combo.findText(combo_text)
            if index >= 0:
                self.search_bar.sort_combo.setCurrentIndex(index)
            self.search_bar.sort_combo.blockSignals(False)

        self._load_projects(
            search_query=self.search_bar.text(),
            date_filter=self._current_date_filter,
            tempo_min=self._current_tempo_min,
            tempo_max=self._current_tempo_max,
            sort_by=sort_field,
        )

    # Project handlers
    def _on_project_selected(self, project_id: int) -> None:
        """Handle project selection."""
        # Update recommendations panel if it's visible
        if self.content_stack.currentIndex() == 5:  # Recommendations panel
            self.recommendations_panel.set_project(project_id)
        # Could show details panel

    def _on_project_open(self, project_id: int) -> None:
        """Open a project with Ableton Live."""
        from pathlib import Path

        from ..database import LiveInstallation
        from ..services.live_launcher import LiveLauncher
        from ..services.live_detector import LiveVersion
        from .controllers.live_controller import LiveController

        session = get_session()
        try:
            project = session.query(Project).get(project_id)
            if not project:
                return

            path = Path(project.file_path)
            if not path.exists():
                QMessageBox.warning(
                    self, "Project Not Found", f"The project file could not be found:\n{path}"
                )
                return

            launcher = LiveLauncher()
            live_controller = LiveController()

            # Get project's major version
            project_major_version = project.get_live_version_major()

            # Try to find matching installation by major version
            matching_install = None
            if project_major_version:
                matching_install = live_controller.find_matching_installation(project_major_version)

            # If no match, get default installation (favorite or first if only one)
            if not matching_install:
                matching_install = live_controller.get_default_installation()

            # If still no installation found, show actionable dialog
            if not matching_install:
                self._show_no_live_installation_dialog()
                return

            # Launch with the selected installation
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
            success = launcher.launch_project(path, live_version)
            if success:
                version_info = f" (v{project_major_version})" if project_major_version else ""
                self.logger.info(
                    f"Opened {project.name}{version_info} with: {matching_install.name}"
                )
            else:
                QMessageBox.critical(
                    self,
                    "Launch Failed",
                    f"Failed to launch {matching_install.name} with project:\n{project.name}\n\n"
                    "Please check that Live is installed and try again.",
                )
        finally:
            session.close()

    def _show_no_live_installation_dialog(self) -> None:
        """Show dialog when no Live installation is configured, with actionable buttons."""
        msg = QMessageBox(self)
        msg.setWindowTitle("No Live Installation Found")
        msg.setText(
            "No Ableton Live installation is configured.\n\n"
            "Double-clicking projects opens them in Ableton Live."
        )
        open_settings_btn = msg.addButton("Open Settings", QMessageBox.ButtonRole.AcceptRole)
        add_install_btn = msg.addButton("Add Live Installation", QMessageBox.ButtonRole.AcceptRole)
        msg.addButton("OK", QMessageBox.ButtonRole.RejectRole)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.move(self.geometry().center() - msg.rect().center())
        result = msg.exec()
        if msg.clickedButton() == open_settings_btn:
            self._on_settings(initial_tab="live")
        elif msg.clickedButton() == add_install_btn:
            self._on_add_manual_installation()

    def _on_auto_detect_live_versions(self) -> None:
        """Auto-detect Live versions from default locations."""
        import os

        from ..database import LiveInstallation
        from ..services.live_detector import LiveDetector

        self.logger.info("Starting auto-detection...")
        self.logger.debug(f"ProgramFiles: {os.environ.get('ProgramFiles', 'N/A')}")
        self.logger.debug(f"ProgramFiles(x86): {os.environ.get('ProgramFiles(x86)', 'N/A')}")
        self.logger.debug(f"ProgramData: {os.environ.get('ProgramData', 'N/A')}")
        self.logger.debug(f"LOCALAPPDATA: {os.environ.get('LOCALAPPDATA', 'N/A')}")
        self.logger.debug(f"APPDATA: {os.environ.get('APPDATA', 'N/A')}")

        detector = LiveDetector()
        detected_versions = detector.get_versions()

        self.logger.info(f"Found {len(detected_versions)} version(s)")
        for v in detected_versions:
            self.logger.debug(f"  - {v} at {v.path}")

        if not detected_versions:
            msg = QMessageBox(self)
            msg.setWindowTitle("No Versions Found")
            msg.setText(
                "No Ableton Live installations were detected in default locations.\n\n"
                "You can manually add an installation using 'Add Manual Installation...'"
            )
            msg.addButton("Add Manual Installation", QMessageBox.ButtonRole.AcceptRole)
            msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            msg.setIcon(QMessageBox.Icon.Information)
            # Center dialog on main window
            msg.move(self.geometry().center() - msg.rect().center())
            result = msg.exec()
            if result == 0:  # Add Manual Installation button
                self._on_add_manual_installation()
            return

        session = get_session()
        try:
            added_count = 0
            skipped_count = 0

            for version in detected_versions:
                # Check if already exists
                existing = (
                    session.query(LiveInstallation)
                    .filter(LiveInstallation.executable_path == str(version.path))
                    .first()
                )

                if existing:
                    skipped_count += 1
                    continue

                # Create installation
                install = LiveInstallation(
                    name=str(version),
                    version=version.version,
                    executable_path=str(version.path),
                    build=version.build,
                    is_suite=version.is_suite,
                    is_auto_detected=True,
                )
                session.add(install)
                added_count += 1

            session.commit()

            # Auto-set default if only one installation exists
            from .controllers.live_controller import LiveController

            live_controller = LiveController()
            # Check if we need to set default (after commit, so use new session)
            installations = session.query(LiveInstallation).all()
            if len(installations) == 1:
                install = installations[0]
                if not install.is_favorite:
                    install.is_favorite = True
                    session.commit()
                    live_controller.installations_changed.emit()

            # Refresh sidebar
            self._refresh_sidebar()

            # Show summary
            message = "Auto-detection complete.\n\n"
            message += f"• Added {added_count} installation(s)\n"
            if skipped_count > 0:
                message += f"• Skipped {skipped_count} installation(s) (already exist)"
            if added_count == 1:
                message += "\n\n• Set as default installation (only one available)"

            msg = QMessageBox(self)
            msg.setWindowTitle("Auto-Detection Complete")
            msg.setText(message)
            msg.setIcon(QMessageBox.Icon.Information)
            # Center dialog on main window
            msg.move(self.geometry().center() - msg.rect().center())
            msg.exec()
        except Exception as e:
            session.rollback()
            msg = QMessageBox(self)
            msg.setWindowTitle("Error")
            msg.setText(f"Failed to auto-detect installations:\n{str(e)}")
            msg.setIcon(QMessageBox.Icon.Critical)
            # Center dialog on main window
            msg.move(self.geometry().center() - msg.rect().center())
            msg.exec()
        finally:
            session.close()

    def _on_add_manual_installation(self) -> None:
        """Show dialog to add manual installation."""
        from .dialogs.add_live_installation import AddLiveInstallationDialog

        dialog = AddLiveInstallationDialog(self)
        # Center dialog on main window
        dialog.move(self.geometry().center() - dialog.rect().center())
        if dialog.exec():
            self._refresh_sidebar()
            msg = QMessageBox(self)
            msg.setWindowTitle("Installation Added")
            msg.setText("Live installation has been added successfully.")
            msg.setIcon(QMessageBox.Icon.Information)
            # Center dialog on main window
            msg.move(self.geometry().center() - msg.rect().center())
            msg.exec()

    def _on_set_favorite_installation(self, install_id: int) -> None:
        """Set or unset favorite installation."""
        from ..database import LiveInstallation

        session = get_session()
        try:
            install = session.query(LiveInstallation).get(install_id)
            if not install:
                return

            # Toggle favorite status
            if install.is_favorite:
                # Unset favorite
                install.is_favorite = False
            else:
                # Set as favorite (unset all others first)
                session.query(LiveInstallation).update({"is_favorite": False})
                install.is_favorite = True

            session.commit()
            self._refresh_sidebar()
        except Exception as e:
            session.rollback()
            msg = QMessageBox(self)
            msg.setWindowTitle("Error")
            msg.setText(f"Failed to set favorite installation:\n{str(e)}")
            msg.setIcon(QMessageBox.Icon.Critical)
            # Center dialog on main window
            msg.move(self.geometry().center() - msg.rect().center())
            msg.exec()
        finally:
            session.close()

    def _on_remove_installation(self, install_id: int) -> None:
        """Remove a Live installation."""
        from ..database import LiveInstallation

        session = get_session()
        try:
            install = session.query(LiveInstallation).get(install_id)
            if not install:
                return

            msg = QMessageBox(self)
            msg.setWindowTitle("Remove Installation")
            msg.setText(
                f"Are you sure you want to remove '{install.name}'?\n\n"
                "This will only remove it from the list. The actual Live installation will not be affected."
            )
            msg.setIcon(QMessageBox.Icon.Question)
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setDefaultButton(QMessageBox.StandardButton.No)
            # Center dialog on main window
            msg.move(self.geometry().center() - msg.rect().center())
            reply = msg.exec()

            if reply == QMessageBox.StandardButton.Yes:
                session.delete(install)
                session.commit()
                self._refresh_sidebar()
        except Exception as e:
            session.rollback()
            msg = QMessageBox(self)
            msg.setWindowTitle("Error")
            msg.setText(f"Failed to remove installation:\n{str(e)}")
            msg.setIcon(QMessageBox.Icon.Critical)
            # Center dialog on main window
            msg.move(self.geometry().center() - msg.rect().center())
            msg.exec()
        finally:
            session.close()

    def _on_location_added(self, location_id: int) -> None:
        """Handle a new location being added."""
        self._refresh_sidebar()
        self._on_scan_location(location_id)
        # Restart watcher to include new location
        if self._watcher:
            self._watcher.start()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event."""
        self.cleanup()
        event.accept()

    def cleanup(self) -> None:
        """Clean up resources on application exit."""
        import time

        try:
            # Stop scanner via controller
            if hasattr(self, "scan_controller"):
                self.scan_controller.stop_scan()
            if self._scanner:
                self._scanner.stop()
                time.sleep(0.1)  # Brief wait for thread to finish
                self._scanner = None

            # Stop watcher (this has the Observer thread)
            if self._watcher:
                self._watcher.stop()
                # Give Observer thread time to stop (reduced timeout)
                time.sleep(0.1)
                self._watcher = None

            # Stop link scanner
            if self._link_scanner:
                self._link_scanner.stop()
                time.sleep(0.05)
                self._link_scanner = None

            # Stop link panel scanner if running
            if hasattr(self, "link_panel"):
                if hasattr(self.link_panel, "cleanup"):
                    self.link_panel.cleanup()
                elif hasattr(self.link_panel, "_scanner") and self.link_panel._scanner:
                    self.link_panel._scanner.stop()

            # Stop project properties view workers
            if hasattr(self, "project_properties_view"):
                self.project_properties_view.cleanup()

            # Stop Find Audio Exports view workers
            if hasattr(self, "find_audio_exports_view"):
                self.find_audio_exports_view.cleanup()

            # Stop all timers
            if hasattr(self, "search_bar") and hasattr(self.search_bar, "_debounce_timer"):
                self.search_bar._debounce_timer.stop()
        except Exception:
            # Ignore errors during cleanup to prevent hanging
            pass
