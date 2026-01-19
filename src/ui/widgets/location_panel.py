"""Location management panel widget."""

from typing import Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMenu, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction

from ...database import get_session, Location, LocationType
from ..theme import AbletonTheme


class LocationPanel(QWidget):
    """Panel for managing project locations."""
    
    # Signals
    location_added = pyqtSignal(int)    # Location ID
    location_removed = pyqtSignal(int)  # Location ID
    scan_requested = pyqtSignal(int)    # Location ID (0 for all)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._locations: List[Location] = []
        
        self._setup_ui()
        self.refresh()
    
    def _setup_ui(self) -> None:
        """Set up the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("Locations")
        title.setObjectName("title")
        title.setStyleSheet(f"""
            QLabel {{
                font-size: 24px;
                font-weight: bold;
                color: {AbletonTheme.COLORS['text_primary']};
            }}
        """)
        header.addWidget(title)
        
        header.addStretch()
        
        # Action buttons
        scan_all_btn = QPushButton("Scan All")
        scan_all_btn.clicked.connect(lambda: self.scan_requested.emit(0))
        header.addWidget(scan_all_btn)
        
        add_btn = QPushButton("+ Add Location")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._on_add_location)
        header.addWidget(add_btn)
        
        layout.addLayout(header)
        
        # Locations table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "", "Name", "Type", "Path", "Projects", "Last Scan"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        
        # Configure header
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        
        layout.addWidget(self.table)
        
        # Status bar
        self.status_label = QLabel()
        self.status_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']};")
        layout.addWidget(self.status_label)
    
    def refresh(self) -> None:
        """Refresh the locations list from database."""
        session = get_session()
        try:
            self._locations = session.query(Location).order_by(
                Location.sort_order, Location.name
            ).all()
            
            self._populate_table()
            self._update_status()
        finally:
            session.close()
    
    def _populate_table(self) -> None:
        """Populate the table with location data."""
        self.table.setRowCount(len(self._locations))
        
        icon_map = {
            LocationType.LOCAL: "📁",
            LocationType.NETWORK: "🌐",
            LocationType.DROPBOX: "☁️",
            LocationType.CLOUD: "☁️",
            LocationType.USB: "💾",
            LocationType.COLLAB: "👥",
            LocationType.CUSTOM: "📁",
        }
        
        for row, loc in enumerate(self._locations):
            # Favorite indicator
            fav_item = QTableWidgetItem("💎" if loc.is_favorite else "")
            fav_item.setData(Qt.ItemDataRole.UserRole, loc.id)
            fav_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, fav_item)
            
            # Name with icon
            icon = icon_map.get(loc.location_type, "📁")
            name_item = QTableWidgetItem(f"{icon} {loc.name}")
            
            # Color indicator
            if loc.color:
                name_item.setForeground(AbletonTheme.get_qcolor("accent"))
            
            # Status indicator
            if not loc.is_active:
                name_item.setForeground(AbletonTheme.get_qcolor("text_disabled"))
            
            self.table.setItem(row, 1, name_item)
            
            # Type
            type_str = loc.location_type.value.title()
            self.table.setItem(row, 2, QTableWidgetItem(type_str))
            
            # Path
            path_item = QTableWidgetItem(loc.path)
            path_item.setToolTip(loc.path)
            self.table.setItem(row, 3, path_item)
            
            # Project count
            count = len(loc.projects)
            self.table.setItem(row, 4, QTableWidgetItem(str(count)))
            
            # Last scan
            if loc.last_scan_time:
                scan_str = loc.last_scan_time.strftime("%Y-%m-%d %H:%M")
            else:
                scan_str = "Never"
            self.table.setItem(row, 5, QTableWidgetItem(scan_str))
    
    def _update_status(self) -> None:
        """Update the status label."""
        total = len(self._locations)
        active = sum(1 for loc in self._locations if loc.is_active)
        projects = sum(len(loc.projects) for loc in self._locations)
        
        self.status_label.setText(
            f"{total} locations ({active} active) • {projects} total projects"
        )
    
    def _on_add_location(self) -> None:
        """Show add location dialog."""
        from ..dialogs.add_location import AddLocationDialog
        dialog = AddLocationDialog(self)
        if dialog.exec():
            self.refresh()
            if dialog.location_id:
                self.location_added.emit(dialog.location_id)
    
    def _on_context_menu(self, pos) -> None:
        """Show context menu for location."""
        item = self.table.itemAt(pos)
        if not item:
            return
        
        row = item.row()
        location_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        location = next((loc for loc in self._locations if loc.id == location_id), None)
        
        if not location:
            return
        
        menu = QMenu(self)
        
        scan_action = menu.addAction("Scan Now")
        scan_action.triggered.connect(lambda: self.scan_requested.emit(location_id))
        
        menu.addSeparator()
        
        if location.is_active:
            disable_action = menu.addAction("Disable")
            disable_action.triggered.connect(lambda: self._toggle_active(location_id, False))
        else:
            enable_action = menu.addAction("Enable")
            enable_action.triggered.connect(lambda: self._toggle_active(location_id, True))
        
        favorite_action = menu.addAction(
            "Remove from Favorites" if location.is_favorite else "Add to Favorites"
        )
        favorite_action.triggered.connect(lambda: self._toggle_favorite(location_id))
        
        menu.addSeparator()
        
        edit_action = menu.addAction("Edit...")
        edit_action.triggered.connect(lambda: self._edit_location(location_id))
        
        menu.addSeparator()
        
        remove_action = menu.addAction("Remove")
        remove_action.triggered.connect(lambda: self._remove_location(location_id))
        
        menu.exec(self.table.viewport().mapToGlobal(pos))
    
    def _toggle_active(self, location_id: int, active: bool) -> None:
        """Toggle location active state."""
        session = get_session()
        try:
            location = session.query(Location).get(location_id)
            if location:
                location.is_active = active
                session.commit()
                self.refresh()
        finally:
            session.close()
    
    def _toggle_favorite(self, location_id: int) -> None:
        """Toggle location favorite state."""
        session = get_session()
        try:
            location = session.query(Location).get(location_id)
            if location:
                location.is_favorite = not location.is_favorite
                session.commit()
                self.refresh()
        finally:
            session.close()
    
    def _edit_location(self, location_id: int) -> None:
        """Show edit location dialog."""
        from ..dialogs.add_location import AddLocationDialog
        dialog = AddLocationDialog(self, location_id=location_id)
        if dialog.exec():
            self.refresh()
    
    def _remove_location(self, location_id: int) -> None:
        """Remove a location."""
        location = next((loc for loc in self._locations if loc.id == location_id), None)
        if not location:
            return
        
        result = QMessageBox.question(
            self,
            "Remove Location",
            f"Are you sure you want to remove '{location.name}'?\n\n"
            "This will remove the location from tracking but won't delete any files.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            session = get_session()
            try:
                loc = session.query(Location).get(location_id)
                if loc:
                    session.delete(loc)
                    session.commit()
                    self.location_removed.emit(location_id)
                    self.refresh()
            finally:
                session.close()
