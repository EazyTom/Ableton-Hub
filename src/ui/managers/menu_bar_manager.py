"""Menu bar manager for MainWindow."""

from typing import cast

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QMainWindow, QMenu, QMenuBar

from ...utils.logging import get_logger


class MenuBarManager(QObject):
    """Manages menu bar creation and actions.

    This class centralizes menu creation logic, reducing complexity in MainWindow.
    Actions are communicated back to MainWindow via signals.
    """

    # Action signals - emitted when menu actions are triggered
    add_location_requested = pyqtSignal()
    scan_all_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    exit_requested = pyqtSignal()
    search_projects_requested = pyqtSignal()
    select_all_requested = pyqtSignal()
    grid_view_requested = pyqtSignal()
    list_view_requested = pyqtSignal()
    toggle_sidebar_requested = pyqtSignal()
    toggle_show_missing_requested = pyqtSignal()
    refresh_requested = pyqtSignal()
    global_search_requested = pyqtSignal()
    song_name_generator_requested = pyqtSignal()
    show_link_panel_requested = pyqtSignal()
    force_rescan_metadata_requested = pyqtSignal()
    clear_thumbnail_cache_requested = pyqtSignal()
    cleanup_missing_projects_requested = pyqtSignal()
    cleanup_backup_projects_requested = pyqtSignal()
    reset_database_requested = pyqtSignal()
    view_logs_requested = pyqtSignal()
    user_guide_requested = pyqtSignal()
    check_for_updates_requested = pyqtSignal()
    about_requested = pyqtSignal()

    def __init__(self, main_window: QMainWindow, parent: QObject | None = None):
        """Initialize the menu bar manager.

        Args:
            main_window: The main window instance.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self._main_window = main_window
        # menuBar() always returns a QMenuBar, but PyQt6 stubs say it can be None
        self._menubar = cast(QMenuBar, main_window.menuBar())
        self._actions: dict[str, QAction] = {}
        self._menus: dict[str, QMenu] = {}

    def create_menus(self) -> None:
        """Create all menus."""
        self._create_file_menu()
        self._create_edit_menu()
        self._create_view_menu()
        self._create_tools_menu()
        self._create_help_menu()

    def _create_file_menu(self) -> None:
        """Create File menu."""
        file_menu = cast(QMenu, self._menubar.addMenu("&File"))
        self._menus["file"] = file_menu

        add_location_action = QAction("Add Location...", self._main_window)
        add_location_action.setShortcut(QKeySequence("Ctrl+L"))
        add_location_action.triggered.connect(self.add_location_requested.emit)
        file_menu.addAction(add_location_action)
        self._actions["add_location"] = add_location_action

        scan_all_action = QAction("Scan All Locations", self._main_window)
        scan_all_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        scan_all_action.triggered.connect(self.scan_all_requested.emit)
        file_menu.addAction(scan_all_action)
        self._actions["scan_all"] = scan_all_action

        file_menu.addSeparator()

        settings_action = QAction("Settings...", self._main_window)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self.settings_requested.emit)
        file_menu.addAction(settings_action)
        self._actions["settings"] = settings_action

        file_menu.addSeparator()

        exit_action = QAction("Exit", self._main_window)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.exit_requested.emit)
        file_menu.addAction(exit_action)
        self._actions["exit"] = exit_action

    def _create_edit_menu(self) -> None:
        """Create Edit menu."""
        edit_menu = cast(QMenu, self._menubar.addMenu("&Edit"))
        self._menus["edit"] = edit_menu

        search_action = QAction("Search Projects...", self._main_window)
        search_action.setShortcut(QKeySequence("Ctrl+F"))
        search_action.triggered.connect(self.search_projects_requested.emit)
        edit_menu.addAction(search_action)
        self._actions["search_projects"] = search_action

        edit_menu.addSeparator()

        select_all_action = QAction("Select All", self._main_window)
        select_all_action.setShortcut(QKeySequence("Ctrl+A"))
        select_all_action.triggered.connect(self.select_all_requested.emit)
        edit_menu.addAction(select_all_action)
        self._actions["select_all"] = select_all_action

    def _create_view_menu(self) -> None:
        """Create View menu."""
        view_menu = cast(QMenu, self._menubar.addMenu("&View"))
        self._menus["view"] = view_menu

        grid_view_action = QAction("Grid View", self._main_window)
        grid_view_action.setShortcut(QKeySequence("Ctrl+1"))
        grid_view_action.triggered.connect(self.grid_view_requested.emit)
        view_menu.addAction(grid_view_action)
        self._actions["grid_view"] = grid_view_action

        list_view_action = QAction("List View", self._main_window)
        list_view_action.setShortcut(QKeySequence("Ctrl+2"))
        list_view_action.triggered.connect(self.list_view_requested.emit)
        view_menu.addAction(list_view_action)
        self._actions["list_view"] = list_view_action

        view_menu.addSeparator()

        sidebar_action = QAction("Show Sidebar", self._main_window)
        sidebar_action.setShortcut(QKeySequence("Ctrl+B"))
        sidebar_action.setCheckable(True)
        sidebar_action.setChecked(True)
        sidebar_action.triggered.connect(self.toggle_sidebar_requested.emit)
        view_menu.addAction(sidebar_action)
        self._actions["sidebar"] = sidebar_action

        view_menu.addSeparator()

        show_missing_action = QAction("Show Missing Projects", self._main_window)
        show_missing_action.setCheckable(True)
        show_missing_action.setChecked(False)
        show_missing_action.triggered.connect(self.toggle_show_missing_requested.emit)
        view_menu.addAction(show_missing_action)
        self._actions["show_missing"] = show_missing_action

        view_menu.addSeparator()

        refresh_action = QAction("Refresh", self._main_window)
        refresh_action.setShortcut(QKeySequence("F5"))
        refresh_action.triggered.connect(self.refresh_requested.emit)
        view_menu.addAction(refresh_action)
        self._actions["refresh"] = refresh_action

    def _create_tools_menu(self) -> None:
        """Create Tools menu."""
        tools_menu = cast(QMenu, self._menubar.addMenu("&Tools"))
        self._menus["tools"] = tools_menu

        global_search_action = QAction("Global Search...", self._main_window)
        global_search_action.setShortcut(QKeySequence("Ctrl+Shift+F"))
        global_search_action.triggered.connect(self.global_search_requested.emit)
        tools_menu.addAction(global_search_action)
        self._actions["global_search"] = global_search_action

        song_names_action = QAction("Random Song Name Generator...", self._main_window)
        song_names_action.setToolTip("Generate 10 random song names for project naming")
        song_names_action.triggered.connect(self.song_name_generator_requested.emit)
        tools_menu.addAction(song_names_action)
        self._actions["song_names"] = song_names_action

        tools_menu.addSeparator()

        link_panel_action = QAction("Ableton Link WiFi...", self._main_window)
        link_panel_action.triggered.connect(self.show_link_panel_requested.emit)
        tools_menu.addAction(link_panel_action)
        self._actions["link_panel"] = link_panel_action

        tools_menu.addSeparator()

        rescan_metadata_action = QAction("Force Re-scan Metadata...", self._main_window)
        rescan_metadata_action.setToolTip(
            "Clear parse timestamps and re-extract all project metadata on next scan"
        )
        rescan_metadata_action.triggered.connect(self.force_rescan_metadata_requested.emit)
        tools_menu.addAction(rescan_metadata_action)
        self._actions["rescan_metadata"] = rescan_metadata_action

        clear_cache_action = QAction("Clear Thumbnail Cache...", self._main_window)
        clear_cache_action.setToolTip(
            "Delete all generated waveform thumbnails and regenerate them"
        )
        clear_cache_action.triggered.connect(self.clear_thumbnail_cache_requested.emit)
        tools_menu.addAction(clear_cache_action)
        self._actions["clear_cache"] = clear_cache_action

        tools_menu.addSeparator()

        cleanup_missing_action = QAction("Clean Up Missing Projects...", self._main_window)
        cleanup_missing_action.setToolTip(
            "Remove MISSING projects from database (including backup projects)"
        )
        cleanup_missing_action.triggered.connect(self.cleanup_missing_projects_requested.emit)
        tools_menu.addAction(cleanup_missing_action)
        self._actions["cleanup_missing"] = cleanup_missing_action

        cleanup_backups_action = QAction(
            "Remove Backup Projects from Database...", self._main_window
        )
        cleanup_backups_action.setToolTip(
            "Remove projects that are in Backup folders from database"
        )
        cleanup_backups_action.triggered.connect(self.cleanup_backup_projects_requested.emit)
        tools_menu.addAction(cleanup_backups_action)
        self._actions["cleanup_backups"] = cleanup_backups_action

        reset_db_action = QAction("Reset Database...", self._main_window)
        reset_db_action.setToolTip("Delete all data and start fresh (use with caution!)")
        reset_db_action.triggered.connect(self.reset_database_requested.emit)
        tools_menu.addAction(reset_db_action)
        self._actions["reset_database"] = reset_db_action

    def _create_help_menu(self) -> None:
        """Create Help menu."""
        help_menu = cast(QMenu, self._menubar.addMenu("&Help"))
        self._menus["help"] = help_menu

        view_logs_action = QAction("View Logs", self._main_window)
        view_logs_action.triggered.connect(self.view_logs_requested.emit)
        help_menu.addAction(view_logs_action)
        self._actions["view_logs"] = view_logs_action

        user_guide_action = QAction("User Guide", self._main_window)
        user_guide_action.setShortcut(QKeySequence("F1"))
        user_guide_action.triggered.connect(self.user_guide_requested.emit)
        help_menu.addAction(user_guide_action)
        self._actions["user_guide"] = user_guide_action

        check_updates_action = QAction("Check for Updates", self._main_window)
        check_updates_action.triggered.connect(self.check_for_updates_requested.emit)
        help_menu.addAction(check_updates_action)
        self._actions["check_updates"] = check_updates_action

        help_menu.addSeparator()

        about_action = QAction("About Ableton Hub", self._main_window)
        about_action.triggered.connect(self.about_requested.emit)
        help_menu.addAction(about_action)
        self._actions["about"] = about_action

    def get_action(self, name: str) -> QAction | None:
        """Get an action by name.

        Args:
            name: Action name.

        Returns:
            QAction if found, None otherwise.
        """
        return self._actions.get(name)

    def get_menu(self, name: str) -> QMenu | None:
        """Get a menu by name.

        Args:
            name: Menu name ("file", "edit", "view", "collections", "tools", "help").

        Returns:
            QMenu if found, None otherwise.
        """
        return self._menus.get(name)
