"""Toolbar manager for MainWindow."""

from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QEvent
from PyQt6.QtWidgets import QToolBar, QWidget, QLabel, QSizePolicy
from PyQt6.QtGui import QAction, QPixmap, QFont as QtFont
from PyQt6.QtCore import Qt

from ...utils.logging import get_logger
from ...utils.paths import get_resources_path
from ..widgets.search_bar import SearchBar


class ToolBarManager(QObject):
    """Manages toolbar creation and actions.
    
    This class centralizes toolbar creation logic, reducing complexity in MainWindow.
    """
    
    # Action signals
    scan_requested = pyqtSignal()
    grid_view_requested = pyqtSignal()
    list_view_requested = pyqtSignal()
    
    def __init__(self, main_window, parent: Optional[QObject] = None):
        """Initialize the toolbar manager.
        
        Args:
            main_window: The main window instance.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self._main_window = main_window
        self._toolbar: Optional[QToolBar] = None
        self._search_bar: Optional[SearchBar] = None
        self._grid_btn: Optional[QAction] = None
        self._list_btn: Optional[QAction] = None
    
    def create_toolbar(self) -> QToolBar:
        """Create the main toolbar.
        
        Returns:
            The created QToolBar instance.
        """
        toolbar = QToolBar("Main Toolbar", self._main_window)
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        
        # Ensure toolbar has valid font
        font = toolbar.font()
        if font.pointSize() <= 0:
            font.setPixelSize(12)
            toolbar.setFont(font)
        
        self._main_window.addToolBar(toolbar)
        self._toolbar = toolbar
        
        # Add logo
        self._add_logo(toolbar)
        
        # Add spacer
        spacer = QWidget()
        spacer.setFixedWidth(10)
        toolbar.addWidget(spacer)
        
        # Add search bar
        self._add_search_bar(toolbar)
        
        # Add scan button
        self._add_scan_button(toolbar)
        
        toolbar.addSeparator()
        
        # Add view toggle buttons
        self._add_view_buttons(toolbar)
        
        # Set fonts on toolbar buttons
        self._setup_toolbar_fonts(toolbar)
        
        return toolbar
    
    def _add_logo(self, toolbar: QToolBar) -> None:
        """Add logo to toolbar."""
        try:
            logo_path = get_resources_path() / "images" / "hub-logo.png"
            if logo_path.exists():
                logo_label = QLabel()
                pixmap = QPixmap(str(logo_path))
                # Scale logo to reasonable size (max height 40px for toolbar)
                scaled_pixmap = pixmap.scaledToHeight(40, Qt.TransformationMode.SmoothTransformation)
                logo_label.setPixmap(scaled_pixmap)
                logo_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                logo_label.setStyleSheet("padding: 4px;")
                toolbar.addWidget(logo_label)
        except Exception as e:
            self.logger.warning(f"Could not load logo: {e}", exc_info=True)
    
    def _add_search_bar(self, toolbar: QToolBar) -> None:
        """Add search bar to toolbar."""
        self._search_bar = SearchBar()
        self._search_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(self._search_bar)
    
    def _add_scan_button(self, toolbar: QToolBar) -> None:
        """Add scan button to toolbar."""
        scan_action = QAction("Scan", self._main_window)
        scan_action.setToolTip("")  # No tooltip to avoid font errors
        scan_action.setStatusTip("")  # No status tip either
        scan_action.triggered.connect(self.scan_requested.emit)
        toolbar.addAction(scan_action)
    
    def _add_view_buttons(self, toolbar: QToolBar) -> None:
        """Add view toggle buttons to toolbar."""
        config = self._main_window.config
        
        self._grid_btn = QAction("Grid", self._main_window)
        self._grid_btn.setCheckable(True)
        self._grid_btn.setChecked(config.ui.default_view == "grid")
        self._grid_btn.setToolTip("")  # No tooltip to avoid font errors
        self._grid_btn.setStatusTip("")  # No status tip either
        self._grid_btn.triggered.connect(self.grid_view_requested.emit)
        toolbar.addAction(self._grid_btn)
        
        self._list_btn = QAction("List", self._main_window)
        self._list_btn.setCheckable(True)
        self._list_btn.setChecked(config.ui.default_view == "list")
        self._list_btn.setToolTip("")  # No tooltip to avoid font errors
        self._list_btn.setStatusTip("")  # No status tip either
        self._list_btn.triggered.connect(self.list_view_requested.emit)
        toolbar.addAction(self._list_btn)
    
    def _setup_toolbar_fonts(self, toolbar: QToolBar) -> None:
        """Set up fonts on toolbar buttons and block tooltips."""
        from PyQt6.QtWidgets import QToolButton
        
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
    
    def get_search_bar(self) -> Optional[SearchBar]:
        """Get the search bar widget.
        
        Returns:
            SearchBar widget if created, None otherwise.
        """
        return self._search_bar
    
    def get_grid_button(self) -> Optional[QAction]:
        """Get the grid view button action.
        
        Returns:
            QAction for grid button if created, None otherwise.
        """
        return self._grid_btn
    
    def get_list_button(self) -> Optional[QAction]:
        """Get the list view button action.
        
        Returns:
            QAction for list button if created, None otherwise.
        """
        return self._list_btn
