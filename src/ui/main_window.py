"""Main application window for Ableton Hub."""

import logging
from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QStackedWidget, QStatusBar, QMenuBar,
    QMenu, QToolBar, QLabel, QProgressBar, QMessageBox, QSizePolicy, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QCloseEvent, QPixmap

from .. import __version__, get_whats_new_html
from ..config import Config, save_config
from ..database import get_session, Location, Project
from ..utils.paths import get_resources_path
from ..utils.logging import get_logger
from .widgets.sidebar import Sidebar
from .widgets.project_grid import ProjectGrid
from .widgets.location_panel import LocationPanel
from .widgets.collection_view import CollectionView
from .widgets.search_bar import SearchBar
from .widgets.link_panel import LinkPanel
from .theme import AbletonTheme
from .controllers.scan_controller import ScanController
from ..services.watcher import FileWatcher


class MainWindow(QMainWindow):
    """Main application window with navigation and content areas."""
    
    # Signals
    scan_requested = pyqtSignal()
    
    def __init__(self, config: Config, theme: Optional[AbletonTheme] = None):
        self.logger = get_logger(__name__)
        """Initialize the main window.
        
        Args:
            config: Application configuration.
            theme: Optional theme instance (will get from app if not provided).
        """
        super().__init__()
        
        self.config = config
        self.theme = theme
        self._scanner = None
        self._watcher = None
        self._link_scanner = None
        
        # Initialize controllers
        self.scan_controller = ScanController(self)
        
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
            # Use .ico file for better Windows taskbar support
            icon_path = get_resources_path() / "icons" / "AProject.ico"
            if not icon_path.exists():
                # Fallback to png if ico not found
                icon_path = get_resources_path() / "images" / "ableton-logo.png"
            if icon_path.exists():
                icon = QIcon(str(icon_path))
                # Set icon on the window
                self.setWindowIcon(icon)
                # Also set on the application to ensure it shows in taskbar/system tray
                from PyQt6.QtWidgets import QApplication
                QApplication.instance().setWindowIcon(icon)
                self.logger.info(f"Set window icon from: {icon_path}")
            else:
                self.logger.warning(f"Window icon not found at: {icon_path}")
        except Exception as e:
            self.logger.error(f"Failed to set window icon: {e}", exc_info=True)
            import traceback
            traceback.print_exc()
    
    def _create_menus(self) -> None:
        """Create the menu bar and menus."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        add_location_action = QAction("Add Location...", self)
        add_location_action.setShortcut(QKeySequence("Ctrl+L"))
        add_location_action.triggered.connect(self._on_add_location)
        file_menu.addAction(add_location_action)
        
        scan_all_action = QAction("Scan All Locations", self)
        scan_all_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        scan_all_action.triggered.connect(self._on_scan_all)
        file_menu.addAction(scan_all_action)
        
        file_menu.addSeparator()
        
        reset_db_action = QAction("Reset Database...", self)
        reset_db_action.setToolTip("Delete all data and start fresh (use with caution!)")
        reset_db_action.triggered.connect(self._on_reset_database)
        file_menu.addAction(reset_db_action)
        
        file_menu.addSeparator()
        
        settings_action = QAction("Settings...", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._on_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        search_action = QAction("Search Projects...", self)
        search_action.setShortcut(QKeySequence("Ctrl+F"))
        search_action.triggered.connect(self._focus_search)
        edit_menu.addAction(search_action)
        
        edit_menu.addSeparator()
        
        select_all_action = QAction("Select All", self)
        select_all_action.setShortcut(QKeySequence("Ctrl+A"))
        select_all_action.triggered.connect(self._select_all_projects)
        edit_menu.addAction(select_all_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        grid_view_action = QAction("Grid View", self)
        grid_view_action.setShortcut(QKeySequence("Ctrl+1"))
        grid_view_action.triggered.connect(lambda: self._set_view_mode("grid"))
        view_menu.addAction(grid_view_action)
        
        list_view_action = QAction("List View", self)
        list_view_action.setShortcut(QKeySequence("Ctrl+2"))
        list_view_action.triggered.connect(lambda: self._set_view_mode("list"))
        view_menu.addAction(list_view_action)
        
        view_menu.addSeparator()
        
        self.sidebar_action = QAction("Show Sidebar", self)
        self.sidebar_action.setShortcut(QKeySequence("Ctrl+B"))
        self.sidebar_action.setCheckable(True)
        self.sidebar_action.setChecked(True)
        self.sidebar_action.triggered.connect(self._toggle_sidebar)
        view_menu.addAction(self.sidebar_action)
        
        view_menu.addSeparator()
        
        refresh_action = QAction("Refresh", self)
        refresh_action.setShortcut(QKeySequence("F5"))
        refresh_action.triggered.connect(self._refresh_view)
        view_menu.addAction(refresh_action)
        
        # Collection menu
        collection_menu = menubar.addMenu("&Collections")
        
        new_collection_action = QAction("New Collection...", self)
        new_collection_action.setShortcut(QKeySequence("Ctrl+N"))
        new_collection_action.triggered.connect(self._on_new_collection)
        collection_menu.addAction(new_collection_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        
        global_search_action = QAction("Global Search...", self)
        global_search_action.setShortcut(QKeySequence("Ctrl+Shift+F"))
        global_search_action.triggered.connect(self._on_global_search)
        tools_menu.addAction(global_search_action)
        
        tools_menu.addSeparator()
        
        link_panel_action = QAction("Link Network...", self)
        link_panel_action.triggered.connect(self._show_link_panel)
        tools_menu.addAction(link_panel_action)
        
        tools_menu.addSeparator()
        
        rescan_metadata_action = QAction("Force Re-scan Metadata...", self)
        rescan_metadata_action.setToolTip("Clear parse timestamps and re-extract all project metadata on next scan")
        rescan_metadata_action.triggered.connect(self._on_force_rescan_metadata)
        tools_menu.addAction(rescan_metadata_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("About Ableton Hub", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_toolbar(self) -> None:
        """Create the main toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        # Ensure toolbar has valid font
        font = toolbar.font()
        if font.pointSize() <= 0:
            font.setPixelSize(12)
            toolbar.setFont(font)
        self.addToolBar(toolbar)
        
        # Logo at top left
        try:
            from ..utils.paths import get_resources_path
            logo_path = get_resources_path() / "images" / "hub-logo.png"
            if logo_path.exists():
                logo_label = QLabel()
                pixmap = QPixmap(str(logo_path))
                # Scale logo to reasonable size (max height 32px for toolbar)
                scaled_pixmap = pixmap.scaledToHeight(32, Qt.TransformationMode.SmoothTransformation)
                logo_label.setPixmap(scaled_pixmap)
                logo_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                logo_label.setStyleSheet("padding: 4px;")
                toolbar.addWidget(logo_label)
        except Exception as e:
            self.logger.warning(f"Could not load logo: {e}", exc_info=True)
        
        # Add spacer
        spacer = QWidget()
        spacer.setFixedWidth(10)
        toolbar.addWidget(spacer)
        
        # Search bar - expands to fill available space
        self.search_bar = SearchBar()
        self.search_bar.search_changed.connect(self._on_search)
        self.search_bar.filter_changed.connect(self._on_filter_changed)
        self.search_bar.tempo_filter_changed.connect(self._on_tempo_filter_changed)
        self.search_bar.sort_changed.connect(self._on_sort_changed)
        self.search_bar.create_collection_from_filter.connect(self._on_create_collection_from_filter)
        self.search_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(self.search_bar)
        
        # Store current filters
        self._current_date_filter = None
        self._current_tempo_min = 0
        self._current_tempo_max = 0
        self._current_sort = "modified"
        
        # Scan button
        scan_action = QAction("Scan", self)
        scan_action.setToolTip("")  # No tooltip to avoid font errors
        scan_action.setStatusTip("")  # No status tip either
        scan_action.triggered.connect(self._on_scan_all)
        toolbar.addAction(scan_action)
        
        toolbar.addSeparator()
        
        # View toggle buttons
        self.grid_btn = QAction("Grid", self)
        self.grid_btn.setCheckable(True)
        self.grid_btn.setChecked(self.config.ui.default_view == "grid")
        self.grid_btn.setToolTip("")  # No tooltip to avoid font errors
        self.grid_btn.setStatusTip("")  # No status tip either
        self.grid_btn.triggered.connect(lambda: self._set_view_mode("grid"))
        toolbar.addAction(self.grid_btn)
        
        self.list_btn = QAction("List", self)
        self.list_btn.setCheckable(True)
        self.list_btn.setChecked(self.config.ui.default_view == "list")
        self.list_btn.setToolTip("")  # No tooltip to avoid font errors
        self.list_btn.setStatusTip("")  # No status tip either
        self.list_btn.triggered.connect(lambda: self._set_view_mode("list"))
        toolbar.addAction(self.list_btn)
        
        # Set fonts programmatically on toolbar buttons and block tooltips
        from PyQt6.QtWidgets import QToolButton
        from PyQt6.QtCore import QTimer, QObject, QEvent
        from PyQt6.QtGui import QFont as QtFont
        
        class ToolbarTooltipBlocker(QObject):
            """Event filter to block tooltip events on toolbar buttons."""
            def eventFilter(self, obj, event):
                # Block tooltip events completely - this prevents font errors
                if event.type() == QEvent.Type.ToolTip:
                    return True  # Consume the event, don't show tooltip
                return False  # Let other events through
        
        tooltip_blocker = ToolbarTooltipBlocker(self)
        
        def set_toolbar_button_fonts():
            """Set fonts directly on toolbar button widgets and block tooltips."""
            for action in toolbar.actions():
                widget = toolbar.widgetForAction(action)
                if widget and isinstance(widget, QToolButton):
                    # Set a valid font with pixel size
                    font = QtFont("Segoe UI", 9)  # Use point size constructor
                    widget.setFont(font)
                    # Install event filter to block tooltip events
                    widget.installEventFilter(tooltip_blocker)
        
        # Set fonts after widgets are created
        QTimer.singleShot(0, set_toolbar_button_fonts)
    
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
        
        # Connect sidebar signals
        self.sidebar.navigation_changed.connect(self._on_navigation_changed)
        self.sidebar.location_selected.connect(self._on_location_filter)
        self.sidebar.collection_selected.connect(self._on_collection_selected)
        self.sidebar.location_delete_requested.connect(self._on_delete_location_from_sidebar)
        self.sidebar.cleanup_orphaned_projects_requested.connect(self._on_cleanup_orphaned_projects)
        self.sidebar.collection_edit_requested.connect(self._on_edit_collection_from_sidebar)
        self.sidebar.collection_delete_requested.connect(self._on_delete_collection_from_sidebar)
        self.sidebar.auto_detect_live_versions_requested.connect(self._on_auto_detect_live_versions)
        self.sidebar.add_manual_installation_requested.connect(self._on_add_manual_installation)
        self.sidebar.set_favorite_installation_requested.connect(self._on_set_favorite_installation)
        self.sidebar.remove_installation_requested.connect(self._on_remove_installation)
        self.sidebar.navigation_changed.connect(self._on_navigation_changed)
        self.sidebar.location_selected.connect(self._on_location_filter)
        self.sidebar.location_delete_requested.connect(self._on_delete_location_from_sidebar)
        self.sidebar.cleanup_orphaned_projects_requested.connect(self._on_cleanup_orphaned_projects)
        self.sidebar.collection_selected.connect(self._on_collection_selected)
        self.sidebar.collection_edit_requested.connect(self._on_edit_collection_from_sidebar)
        self.sidebar.collection_delete_requested.connect(self._on_delete_collection_from_sidebar)
        self.sidebar.tag_selected.connect(self._on_tag_filter)
        self.splitter.addWidget(self.sidebar)
        
        # Content stack
        self.content_stack = QStackedWidget()
        
        # Projects view (index 0)
        self.project_grid = ProjectGrid()
        self.project_grid.project_selected.connect(self._on_project_selected)
        self.project_grid.project_double_clicked.connect(self._on_project_open)
        self.project_grid.sort_requested.connect(self._on_grid_sort_requested)
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
        self.content_stack.addWidget(self.location_panel)
        
        # Link panel (index 3)
        self.link_panel = LinkPanel()
        self.content_stack.addWidget(self.link_panel)
        
        # Health dashboard (index 4)
        from .widgets.health_dashboard import HealthDashboard
        self.health_dashboard = HealthDashboard()
        self.health_dashboard.project_selected.connect(self._on_project_selected)
        self.content_stack.addWidget(self.health_dashboard)
        
        self.splitter.addWidget(self.content_stack)
        
        # Set initial sizes
        self.splitter.setSizes([self.config.window.sidebar_width, 1000])
        
        layout.addWidget(self.splitter)
    
    def _create_status_bar(self) -> None:
        """Create the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
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
    
    def _initial_load(self) -> None:
        """Load initial data on startup."""
        self._refresh_sidebar()
        self._load_projects()
        
        # Note: Auto-scan on startup is disabled by default
        # Users must manually trigger scans using the Scan button
        # File watcher is started automatically to detect changes
    
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
    
    def _load_projects(self, location_id: Optional[int] = None,
                       collection_id: Optional[int] = None,
                       tag_id: Optional[int] = None,
                       search_query: str = "",
                       date_filter: Optional[str] = None,
                       tempo_min: Optional[int] = None,
                       tempo_max: Optional[int] = None,
                       sort_by: Optional[str] = None) -> None:
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
        from sqlalchemy.orm import joinedload
        from datetime import datetime, timedelta
        
        session = get_session()
        try:
            # Eagerly load relationships to avoid DetachedInstanceError
            query = session.query(Project).options(
                joinedload(Project.location),
                joinedload(Project.exports)
            )
            
            if location_id:
                query = query.filter(Project.location_id == location_id)
            
            if collection_id:
                from ..database import ProjectCollection
                query = query.join(ProjectCollection).filter(
                    ProjectCollection.collection_id == collection_id
                )
            
            if tag_id:
                # Tags stored as JSON array of IDs
                query = query.filter(Project.tags.contains([tag_id]))
            
            # Apply date filter
            date_filter_to_use = date_filter if date_filter is not None else self._current_date_filter
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
                    # Last 7 days
                    start_date = now - timedelta(days=7)
                    query = query.filter(Project.modified_date >= start_date)
                elif date_filter_to_use == "30days":
                    # Last 30 days
                    start_date = now - timedelta(days=30)
                    query = query.filter(Project.modified_date >= start_date)
                elif date_filter_to_use == "custom":
                    # TODO: Implement custom date range dialog
                    pass
                
                # Only show projects that have a modified_date
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
                from ..database.db import search_projects_fts
                from sqlalchemy import String
                project_ids = search_projects_fts(search_query)
                if project_ids:
                    query = query.filter(Project.id.in_(project_ids))
                else:
                    # Fallback to LIKE search including plugins and devices
                    search_pattern = f"%{search_query}%"
                    query = query.filter(
                        Project.name.ilike(search_pattern) |
                        Project.export_song_name.ilike(search_pattern) |
                        Project.notes.ilike(search_pattern) |
                        # Search in plugins JSON array
                        Project.plugins.cast(String).ilike(search_pattern) |
                        # Search in devices JSON array
                        Project.devices.cast(String).ilike(search_pattern)
                    )
            
            # Apply sorting
            sort_field = sort_by if sort_by is not None else self._current_sort
            from sqlalchemy import nullslast, nullsfirst
            
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
            elif sort_field == "modified_asc":
                query = query.order_by(Project.modified_date.asc())
            else:  # "modified" or "modified_desc" is default
                query = query.order_by(Project.modified_date.desc())
            
            projects = query.all()
            
            self.project_grid.set_projects(projects)
            self.project_count_label.setText(f"{len(projects)} projects")
        finally:
            session.close()
    
    def _update_project_count(self, count: int) -> None:
        """Update the project count in status bar."""
        self.project_count_label.setText(f"{count} projects")
    
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
        status_msg = f"Scan complete: Found {found_count} projects"
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
        from ..database import reset_database, close_database
        
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
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Stop all services before reset
        print("[DB] Stopping all services before database reset...")
        
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
        if hasattr(self, 'link_panel'):
            if hasattr(self.link_panel, 'cleanup'):
                self.link_panel.cleanup()
            elif hasattr(self.link_panel, '_scanner') and self.link_panel._scanner:
                self.link_panel._scanner.stop()
        
        # Close database connections
        close_database()
        
        # Reset database
        print("[DB] Resetting database...")
        success = reset_database()
        
        if success:
            QMessageBox.information(
                self,
                "Database Reset",
                "Database has been reset successfully.\n"
                "The application will now refresh with an empty database."
            )
            
            # Refresh UI
            self._refresh_sidebar()
            self._load_projects()
            self.scan_status_label.setText("Database reset complete")
            
            print("[DB] Database reset successful - UI refreshed")
        else:
            QMessageBox.critical(
                self,
                "Database Reset Failed",
                "Failed to reset the database.\n"
                "Please check the console for error messages."
            )
    
    def _on_settings(self) -> None:
        """Show settings dialog."""
        from .dialogs.settings_dialog import SettingsDialog
        from .theme import AbletonTheme
        from PyQt6.QtWidgets import QApplication
        
        dialog = SettingsDialog(self.config, self)
        old_theme = self.config.ui.theme
        if dialog.exec():
            # Settings were saved, refresh UI if needed
            # Check if theme changed
            if old_theme != self.config.ui.theme:
                # Reload theme
                self.theme = AbletonTheme(self.config.ui.theme)
                self.theme.apply(QApplication.instance())
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
            self.content_stack.setCurrentIndex(1)
    
    def _on_new_smart_collection(self) -> None:
        """Show new smart collection dialog."""
        from .dialogs.smart_collection import SmartCollectionDialog
        dialog = SmartCollectionDialog(self)
        if dialog.exec():
            self._refresh_sidebar()
            self.collection_view.refresh()
            # Switch to collections view
            self.content_stack.setCurrentIndex(1)
    
    def _on_create_collection_from_filter(self, filter_state: dict) -> None:
        """Create a smart collection from the current filter state."""
        from .dialogs.smart_collection import SmartCollectionDialog
        
        # Create dialog and pre-populate with filter state
        dialog = SmartCollectionDialog(self)
        
        # Apply filter state to dialog
        if 'tempo_min' in filter_state:
            dialog.tempo_min_spin.setValue(filter_state['tempo_min'])
            dialog.use_tempo_filter.setChecked(True)
        if 'tempo_max' in filter_state:
            dialog.tempo_max_spin.setValue(filter_state['tempo_max'])
            dialog.use_tempo_filter.setChecked(True)
        if 'days_ago' in filter_state:
            dialog.days_spin.setValue(filter_state['days_ago'])
            dialog.use_date_filter.setChecked(True)
        if 'search_text' in filter_state:
            # Suggest collection name based on search text
            dialog.name_input.setText(f"Search: {filter_state['search_text']}")
        
        if dialog.exec():
            self._refresh_sidebar()
            self.collection_view.refresh()
            # Switch to collections view
            self.content_stack.setCurrentIndex(1)
    
    def _on_global_search(self) -> None:
        """Show global search dialog."""
        pass  # TODO: Implement global search dialog
    
    def _show_link_panel(self) -> None:
        """Show the Link network panel."""
        self.content_stack.setCurrentIndex(3)
        self.sidebar.clear_selection()
    
    def _on_force_rescan_metadata(self) -> None:
        """Force re-scan of all project metadata by clearing parse timestamps."""
        from ..database import get_session, Project
        
        reply = QMessageBox.question(
            self,
            "Force Re-scan Metadata",
            "This will clear all parse timestamps and re-extract metadata\n"
            "(tempo, arrangement length, plugins, etc.) for all projects\n"
            "on the next scan.\n\n"
            "Proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
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
                "Click 'Scan' in the toolbar to re-extract all metadata."
            )
        except Exception as e:
            session.rollback()
            self.logger.error(f"Failed to clear parse timestamps: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to clear timestamps:\n{str(e)}")
        finally:
            session.close()
    
    def _show_about(self) -> None:
        """Show about dialog with compact README content."""
        from PyQt6.QtWidgets import QTextBrowser, QVBoxLayout, QPushButton
        from PyQt6.QtCore import QSize
        
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
        
        <h2 style="color: #FF764D;">🎵 Key Features</h2>
        
        <h3>Project Management</h3>
        <ul>
            <li>Multi-location scanning of .als project files</li>
            <li>Automatic file watching for real-time updates</li>
            <li>Rich metadata extraction (plugins, tempo, tracks, samples)</li>
            <li>Project health dashboard</li>
        </ul>
        
        <h3>Collections & Organization</h3>
        <ul>
            <li>Static collections for albums, EPs, sessions</li>
            <li>Smart collections with dynamic rules (tags, dates, tempo, plugins)</li>
            <li>Flexible tagging system with colors</li>
        </ul>
        
        <h3>Search & Discovery</h3>
        <ul>
            <li>Full-text search (FTS5) across projects, exports, notes</li>
            <li>Advanced filtering by date, location, tags, tempo</li>
            <li>Grid and sortable list views</li>
        </ul>
        
        <h3>Ableton Integration</h3>
        <ul>
            <li>Live version detection and launcher</li>
            <li>Export tracking and audio playback</li>
            <li>Ableton Link network monitoring</li>
            <li>Preferences and Options.txt access</li>
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
            view: View to show ("projects", "collections", "locations", "link", "new_collection")
        """
        if view == "projects":
            self.content_stack.setCurrentIndex(0)
            self._load_projects()
        elif view == "collections":
            self.content_stack.setCurrentIndex(1)
            self.collection_view.refresh()
        elif view == "locations":
            self.content_stack.setCurrentIndex(2)
            self.location_panel.refresh()
        elif view == "link":
            self.content_stack.setCurrentIndex(3)
        elif view == "health":
            self.content_stack.setCurrentIndex(4)
            self.health_dashboard.refresh()
        elif view == "new_collection":
            # Show new collection dialog
            self._on_new_collection()
        elif view == "new_smart_collection":
            # Show new smart collection dialog
            self._on_new_smart_collection()
    
    def _on_location_filter(self, location_id: int) -> None:
        """Filter projects by location."""
        self.content_stack.setCurrentIndex(0)
        self._load_projects(location_id=location_id)
    
    def _on_collection_selected(self, collection_id: int) -> None:
        """Show collection details view."""
        self.content_stack.setCurrentIndex(1)  # Show collection view
        self.collection_view.set_collection(collection_id)
    
    def _on_edit_collection_from_sidebar(self, collection_id: int) -> None:
        """Edit collection from sidebar context menu."""
        from .dialogs.create_collection import CreateCollectionDialog
        from .dialogs.smart_collection import SmartCollectionDialog
        from ..database import get_session, Collection
        
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
                    if hasattr(self.collection_view, '_collection') and self.collection_view._collection and self.collection_view._collection.id == collection_id:
                        self.collection_view.set_collection(collection_id)
        finally:
            session.close()
    
    def _on_delete_location_from_sidebar(self, location_id: int) -> None:
        """Delete location from sidebar context menu."""
        from ..database import get_session, Location, Project, ProjectCollection
        
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
                in_collection = session.query(ProjectCollection).filter(
                    ProjectCollection.project_id == project.id
                ).first() is not None
                
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
                    QMessageBox.StandardButton.No
                )
            else:
                reply = QMessageBox.question(
                    self,
                    "Remove Location",
                    f"Remove location '{location.name}'?\n\n"
                    f"Are you sure?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
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
                summary += f"Removed {deleted_count} project(s) from database (not in collections).\n"
            if kept_count > 0:
                summary += f"Kept {kept_count} project(s) (in collections, location cleared).\n"
            summary += "\nNote: Your actual project files (.als) were NOT deleted and remain on your computer."
            
            QMessageBox.information(
                self,
                "Location Removed",
                summary
            )
        except Exception as e:
            session.rollback()
            self.logger.error(f"Failed to remove location: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to remove location:\n{str(e)}"
            )
        finally:
            session.close()
    
    def _on_cleanup_orphaned_projects(self) -> None:
        """Clean up projects that are not in any location."""
        from ..database import get_session, Project, ProjectCollection
        
        session = get_session()
        try:
            # Find all projects with no location
            orphaned_projects = session.query(Project).filter(
                Project.location_id == None
            ).all()
            
            if not orphaned_projects:
                QMessageBox.information(
                    self,
                    "No Orphaned Projects",
                    "All projects are associated with a location."
                )
                return
            
            # Separate projects into those in collections and those not
            projects_in_collections = []
            projects_not_in_collections = []
            
            for project in orphaned_projects:
                # Check if project is in any collection
                in_collection = session.query(ProjectCollection).filter(
                    ProjectCollection.project_id == project.id
                ).first() is not None
                
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
                message += f"• {len(projects_in_collections)} project(s) will be KEPT (in collections)\n"
            message += "\n⚠️ IMPORTANT: This only removes database records. Your actual project files (.als) will NOT be deleted and remain on your computer.\n\n"
            message += "This action cannot be undone. Are you sure?"
            
            reply = QMessageBox.question(
                self,
                "Remove Orphaned Projects",
                message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
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
            summary = f"Cleanup complete.\n\n"
            if deleted_count > 0:
                summary += f"Removed {deleted_count} project(s) from database (not in collections).\n"
                if deleted_count <= 10:
                    summary += "\nRemoved projects:\n"
                    for name in deleted_names[:10]:
                        summary += f"  • {name}\n"
            if kept_count > 0:
                summary += f"\nKept {kept_count} project(s) that are in collections (location will remain empty).\n"
            if deleted_count > 0:
                summary += "\nNote: Your actual project files (.als) were NOT deleted and remain on your computer."
            
            QMessageBox.information(
                self,
                "Cleanup Complete",
                summary
            )
        except Exception as e:
            session.rollback()
            self.logger.error(f"Failed to cleanup orphaned projects: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to cleanup orphaned projects:\n{str(e)}"
            )
        finally:
            session.close()
    
    def _on_delete_collection_from_sidebar(self, collection_id: int) -> None:
        """Delete collection from sidebar context menu."""
        from ..database import get_session, Collection
        from PyQt6.QtWidgets import QMessageBox
        
        session = get_session()
        try:
            collection = session.query(Collection).get(collection_id)
            if collection:
                reply = QMessageBox.question(
                    self, "Delete Collection",
                    f"Are you sure you want to delete '{collection.name}'?\n\nThis will remove the collection but not the projects themselves.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    session.delete(collection)
                    session.commit()
                    self._refresh_sidebar()
                    self.collection_view.refresh()
                    # If currently viewing this collection, switch to collections list
                    if hasattr(self.collection_view, '_collection') and self.collection_view._collection and self.collection_view._collection.id == collection_id:
                        self.collection_view.refresh()
        finally:
            session.close()
    
    def _on_tag_filter(self, tag_id: int) -> None:
        """Filter projects by tag."""
        self.content_stack.setCurrentIndex(0)
        self._load_projects(tag_id=tag_id)
    
    def _on_search(self, query: str) -> None:
        """Handle search query change."""
        self._load_projects(search_query=query, date_filter=self._current_date_filter)
    
    def _on_filter_changed(self, filter_type: str, value: str) -> None:
        """Handle filter change from search bar."""
        if filter_type == "date":
            # Store the date filter and reload projects
            self._current_date_filter = value if value != "clear" else None
            self._load_projects(
                search_query=self.search_bar.text(),
                date_filter=self._current_date_filter
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
            tempo_max=max_tempo
        )
    
    def _on_sort_changed(self, sort_field: str) -> None:
        """Handle sort change from search bar."""
        self._current_sort = sort_field
        self._load_projects(
            search_query=self.search_bar.text(),
            date_filter=self._current_date_filter,
            tempo_min=self._current_tempo_min,
            tempo_max=self._current_tempo_max,
            sort_by=sort_field
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
            sort_by=sort_field
        )
    
    # Project handlers
    def _on_project_selected(self, project_id: int) -> None:
        """Handle project selection."""
        pass  # Could show details panel
    
    def _on_project_open(self, project_id: int) -> None:
        """Open a project with Ableton Live."""
        from pathlib import Path
        from ..services.live_launcher import LiveLauncher
        from .dialogs.live_version_dialog import LiveVersionDialog
        from ..database import LiveInstallation
        
        session = get_session()
        try:
            project = session.query(Project).get(project_id)
            if not project:
                return
            
            path = Path(project.file_path)
            if not path.exists():
                QMessageBox.warning(
                    self,
                    "Project Not Found",
                    f"The project file could not be found:\n{path}"
                )
                return
            
            # Check for favorite installation first
            favorite_install = session.query(LiveInstallation).filter(
                LiveInstallation.is_favorite == True
            ).first()
            
            if favorite_install:
                # Use favorite installation directly - no confirmation dialog
                exe_path = Path(favorite_install.executable_path)
                if exe_path.exists():
                    launcher = LiveLauncher()
                    # Convert LiveInstallation to LiveVersion for launcher
                    from ..services.live_detector import LiveVersion
                    live_version = LiveVersion(
                        version=favorite_install.version,
                        path=exe_path,
                        build=favorite_install.build,
                        is_suite=favorite_install.is_suite
                    )
                    # Launch directly - no confirmation
                    success = launcher.launch_project(path, live_version)
                    if success:
                        self.logger.info(f"Opened {project.name} with favorite: {favorite_install.name}")
                        return
                    else:
                        QMessageBox.critical(
                            self,
                            "Launch Failed",
                            f"Failed to launch {favorite_install.name} with project:\n{project.name}\n\n"
                            f"Please check that Live is installed and try again."
                        )
                        return
                else:
                    QMessageBox.warning(
                        self,
                        "Installation Not Found",
                        f"The favorite Live installation could not be found:\n{favorite_install.executable_path}\n\nPlease update or remove this installation."
                    )
            
            # No favorite or favorite not found - show dialog to select Live version
            dialog = LiveVersionDialog(project.name, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_version = dialog.get_selected_version()
                if selected_version:
                    launcher = LiveLauncher()
                    success = launcher.launch_project(path, selected_version)
                    if not success:
                        QMessageBox.critical(
                            self,
                            "Launch Failed",
                            f"Failed to launch Ableton Live with this project.\n\n"
                            f"Please check that Live is installed and try again."
                        )
        finally:
            session.close()
    
    def _on_auto_detect_live_versions(self) -> None:
        """Auto-detect Live versions from default locations."""
        from ..services.live_detector import LiveDetector
        from ..database import LiveInstallation
        from PyQt6.QtWidgets import QDialog
        import os
        
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
            msg.setText("No Ableton Live installations were detected in default locations.\n\n"
                       "You can manually add an installation using 'Add Manual Installation...'")
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
                existing = session.query(LiveInstallation).filter(
                    LiveInstallation.executable_path == str(version.path)
                ).first()
                
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
                    is_auto_detected=True
                )
                session.add(install)
                added_count += 1
            
            session.commit()
            
            # Refresh sidebar
            self._refresh_sidebar()
            
            # Show summary
            message = f"Auto-detection complete.\n\n"
            message += f"• Added {added_count} installation(s)\n"
            if skipped_count > 0:
                message += f"• Skipped {skipped_count} installation(s) (already exist)"
            
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
            msg.setText(f"Are you sure you want to remove '{install.name}'?\n\n"
                       "This will only remove it from the list. The actual Live installation will not be affected.")
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
        self._start_scan(location_id)
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
            if hasattr(self, 'scan_controller'):
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
            if hasattr(self, 'link_panel'):
                if hasattr(self.link_panel, 'cleanup'):
                    self.link_panel.cleanup()
                elif hasattr(self.link_panel, '_scanner') and self.link_panel._scanner:
                    self.link_panel._scanner.stop()
            
            # Stop all timers
            if hasattr(self, 'search_bar') and hasattr(self.search_bar, '_debounce_timer'):
                self.search_bar._debounce_timer.stop()
        except Exception:
            # Ignore errors during cleanup to prevent hanging
            pass
