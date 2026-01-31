"""Search bar widget for project filtering."""

from typing import Optional, Tuple
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox, QPushButton, QMenu, QLabel, 
    QSpinBox, QFrame, QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QMouseEvent, QResizeEvent, QPalette

from ..theme import AbletonTheme


class TempoButton(QPushButton):
    """Toggle button for tempo range selection."""
    
    # Consistent width for all tempo buttons and Go button
    BUTTON_WIDTH = 60
    
    def __init__(self, text: str, min_tempo: int, max_tempo: int, parent=None):
        super().__init__(text, parent)
        self.min_tempo = min_tempo
        self.max_tempo = max_tempo
        self.setCheckable(True)
        self.setFixedHeight(24)
        self.setFixedWidth(TempoButton.BUTTON_WIDTH)  # Fixed width to ensure text fits
        self._update_style()
    
    def _update_style(self):
        # Get current theme colors from palette
        palette = QApplication.instance().palette()
        accent = palette.color(QPalette.ColorRole.Highlight).name()
        text_on_accent = palette.color(QPalette.ColorRole.HighlightedText).name()
        surface = palette.color(QPalette.ColorRole.Button).name()
        text_primary = palette.color(QPalette.ColorRole.ButtonText).name()
        border = palette.color(QPalette.ColorRole.Mid).name()
        
        # Calculate hover colors (slightly lighter)
        accent_hover = self._lighten_color(accent)
        surface_hover = self._lighten_color(surface)
        
        if self.isChecked():
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {accent};
                    color: {text_on_accent};
                    border: none;
                    border-radius: 3px;
                    padding: 2px 4px;
                    font-size: 11px;
                    text-align: center;
                }}
                QPushButton:hover {{
                    background-color: {accent_hover};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {surface};
                    color: {text_primary};
                    border: 1px solid {border};
                    border-radius: 3px;
                    padding: 2px 4px;
                    font-size: 11px;
                    text-align: center;
                }}
                QPushButton:hover {{
                    background-color: {surface_hover};
                }}
            """)
    
    def _lighten_color(self, hex_color: str, factor: float = 1.2) -> str:
        """Lighten a hex color by a factor."""
        from PyQt6.QtGui import QColor
        color = QColor(hex_color)
        h, s, v, a = color.getHsv()
        v = min(255, int(v * factor))
        color.setHsv(h, s, v, a)
        return color.name()


class SearchBar(QWidget):
    """Search bar with filters and tempo range - responsive layout."""
    
    search_changed = pyqtSignal(str)
    filter_changed = pyqtSignal(str, str)
    tempo_filter_changed = pyqtSignal(int, int)
    sort_changed = pyqtSignal(str)
    advanced_search = pyqtSignal()
    create_collection_from_filter = pyqtSignal(dict)  # Emits current filter state as dict
    
    # Width threshold for switching to two-row layout
    WRAP_THRESHOLD = 900
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._emit_search)
        self._active_date_filter = None
        self._tempo_min = 0
        self._tempo_max = 0
        self._current_sort = "modified_desc"
        self._is_two_row = False
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        # Ensure search bar never completely disappears
        self.setMinimumWidth(200)
        self.setMinimumHeight(30)
        
        # Main vertical layout to hold one or two rows
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(4)
        
        h = 26
        
        # === ROW 1: Search, filter, advanced ===
        self.row1_widget = QWidget()
        self.row1_layout = QHBoxLayout(self.row1_widget)
        self.row1_layout.setContentsMargins(0, 0, 0, 0)
        self.row1_layout.setSpacing(6)
        
        # Search input - stretches to fill available space
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search projects...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_text_changed)
        self.search_input.returnPressed.connect(self._emit_search)
        self.search_input.setFixedHeight(h)
        self.search_input.setMinimumWidth(100)
        # Note: Focus border color is handled by the global theme stylesheet
        self.row1_layout.addWidget(self.search_input, 1)  # Stretch factor
        
        # Filter type
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Name", "Export", "Tags", "Notes"])
        self.filter_combo.setFixedSize(65, h)
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        # Note: Styling is handled by the global theme stylesheet
        self.row1_layout.addWidget(self.filter_combo)
        
        # Advanced button (narrower)
        self.advanced_btn = QPushButton("⚙")
        self.advanced_btn.setFixedSize(22, h)
        self.advanced_btn.clicked.connect(self._show_advanced_menu)
        # Note: Styling is handled by the global theme stylesheet
        self.row1_layout.addWidget(self.advanced_btn)
        
        # Date filter indicator
        self.date_filter_label = QLabel()
        self.date_filter_label.setVisible(False)
        self.date_filter_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.date_filter_label.mousePressEvent = lambda e: self.clear_date_filter()
        self._update_date_filter_style()
        self.row1_layout.addWidget(self.date_filter_label)
        
        self.main_layout.addWidget(self.row1_widget)
        
        # === ROW 2: Tempo controls and Sort ===
        self.row2_widget = QWidget()
        self.row2_layout = QHBoxLayout(self.row2_widget)
        self.row2_layout.setContentsMargins(0, 0, 0, 0)
        self.row2_layout.setSpacing(6)
        
        # Tempo label
        tempo_lbl = QLabel("Tempo:")
        tempo_lbl.setObjectName("secondary")  # Use theme's secondary label style
        tempo_lbl.setStyleSheet("font-size: 11px;")
        self.row2_layout.addWidget(tempo_lbl)
        
        # Tempo preset buttons
        self.tempo_buttons = []
        tempo_ranges = [
            ("Any", 0, 0),
            ("60-90", 60, 90),
            ("90-120", 90, 120),
            ("120-150", 120, 150),
            ("150+", 150, 999),
        ]
        
        for text, min_t, max_t in tempo_ranges:
            btn = TempoButton(text, min_t, max_t)
            btn.clicked.connect(lambda checked, b=btn: self._on_tempo_button_clicked(b))
            self.tempo_buttons.append(btn)
            self.row2_layout.addWidget(btn)
        
        self.tempo_buttons[0].setChecked(True)
        self.tempo_buttons[0]._update_style()
        
        # Custom tempo: Min-Max with Go button
        self.tempo_min_spin = QSpinBox()
        self.tempo_min_spin.setRange(0, 999)
        self.tempo_min_spin.setFixedSize(70, h)  # Wider for readability
        self.tempo_min_spin.setSpecialValueText("Min")
        # Note: Styling is handled by the global theme stylesheet
        # Connect Enter key to apply filter
        self.tempo_min_spin.editingFinished.connect(self._apply_custom_tempo)
        self.row2_layout.addWidget(self.tempo_min_spin)
        
        self.tempo_max_spin = QSpinBox()
        self.tempo_max_spin.setRange(0, 999)
        self.tempo_max_spin.setFixedSize(70, h)  # Wider for readability
        self.tempo_max_spin.setSpecialValueText("Max")
        # Note: Styling is handled by the global theme stylesheet
        # Connect Enter key to apply filter
        self.tempo_max_spin.editingFinished.connect(self._apply_custom_tempo)
        self.row2_layout.addWidget(self.tempo_max_spin)
        
        self.apply_btn = QPushButton("Go")
        self.apply_btn.setFixedSize(TempoButton.BUTTON_WIDTH, h)  # Match tempo button width
        self.apply_btn.clicked.connect(self._apply_custom_tempo)
        self._update_go_button_style()
        self.row2_layout.addWidget(self.apply_btn)
        
        # Spacer to push sort to right
        self.row2_layout.addStretch()
        
        # Sort
        sort_lbl = QLabel("Sort:")
        sort_lbl.setObjectName("secondary")  # Use theme's secondary label style
        sort_lbl.setStyleSheet("font-size: 11px;")
        self.row2_layout.addWidget(sort_lbl)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Modified ↓", "Modified ↑", "Name A-Z", "Name Z-A", "Tempo ↓", "Tempo ↑", "Length ↓", "Length ↑", "Size ↓", "Size ↑", "Version ↓", "Version ↑", "Key A-Z", "Key Z-A", "Location"])
        self.sort_combo.setFixedSize(110, h)
        self.sort_combo.currentTextChanged.connect(self._on_sort_changed)
        # Note: Styling is handled by the global theme stylesheet
        self.row2_layout.addWidget(self.sort_combo)
        
        self.main_layout.addWidget(self.row2_widget)
        
        # Initially check if we need two-row layout
        QTimer.singleShot(0, self._check_layout)
    
    def resizeEvent(self, event: QResizeEvent) -> None:
        """Handle resize to switch between one-row and two-row layout."""
        super().resizeEvent(event)
        self._check_layout()
    
    def _check_layout(self) -> None:
        """Check width and adjust layout accordingly."""
        width = self.width()
        
        # Always show row1 (search input)
        # Only hide row2 (tempo/sort) if extremely narrow
        if width < 300:
            self.row2_widget.setVisible(False)
        else:
            self.row2_widget.setVisible(True)
    
    def _on_tempo_button_clicked(self, clicked_btn: TempoButton) -> None:
        for btn in self.tempo_buttons:
            if btn != clicked_btn:
                btn.setChecked(False)
                btn._update_style()
        clicked_btn.setChecked(True)
        clicked_btn._update_style()
        self._tempo_min = clicked_btn.min_tempo
        self._tempo_max = clicked_btn.max_tempo
        if clicked_btn.min_tempo > 0:
            self.tempo_min_spin.setValue(clicked_btn.min_tempo)
            self.tempo_max_spin.setValue(clicked_btn.max_tempo if clicked_btn.max_tempo < 999 else 0)
        else:
            self.tempo_min_spin.setValue(0)
            self.tempo_max_spin.setValue(0)
        self.tempo_filter_changed.emit(self._tempo_min, self._tempo_max)
    
    def _apply_custom_tempo(self) -> None:
        min_val = self.tempo_min_spin.value()
        max_val = self.tempo_max_spin.value()
        if min_val == 0 and max_val == 0:
            self.clear_tempo_filter()
            return
        if max_val > 0 and min_val > max_val:
            min_val, max_val = max_val, min_val
            self.tempo_min_spin.setValue(min_val)
            self.tempo_max_spin.setValue(max_val)
        if min_val > 0 and max_val == 0:
            max_val = 999
        self._tempo_min = min_val
        self._tempo_max = max_val
        for btn in self.tempo_buttons:
            btn.setChecked(False)
            btn._update_style()
        self.tempo_filter_changed.emit(min_val, max_val)
    
    def clear_tempo_filter(self) -> None:
        self._tempo_min = 0
        self._tempo_max = 0
        self.tempo_min_spin.setValue(0)
        self.tempo_max_spin.setValue(0)
        for btn in self.tempo_buttons:
            btn.setChecked(btn.min_tempo == 0 and btn.max_tempo == 0)
            btn._update_style()
        self.tempo_filter_changed.emit(0, 0)
    
    def _on_text_changed(self, text: str) -> None:
        self._debounce_timer.start(300)
    
    def _emit_search(self) -> None:
        self.search_changed.emit(self.search_input.text())
    
    def _on_filter_changed(self, filter_type: str) -> None:
        self.filter_changed.emit(filter_type, self.search_input.text())
        self._emit_search()
    
    def _show_advanced_menu(self) -> None:
        menu = QMenu(self)
        date_menu = menu.addMenu("📅 Date Filter")
        date_menu.addAction("Today").triggered.connect(lambda: self._apply_date_filter("today"))
        date_menu.addAction("This Week").triggered.connect(lambda: self._apply_date_filter("week"))
        date_menu.addAction("This Month").triggered.connect(lambda: self._apply_date_filter("month"))
        date_menu.addAction("Last 7 Days").triggered.connect(lambda: self._apply_date_filter("7days"))
        date_menu.addAction("Last 30 Days").triggered.connect(lambda: self._apply_date_filter("30days"))
        date_menu.addSeparator()
        date_menu.addAction("Clear Date Filter").triggered.connect(lambda: self._apply_date_filter("clear"))
        menu.addSeparator()
        menu.addAction("📁 Filter by Location...").triggered.connect(lambda: self.filter_changed.emit("location", ""))
        menu.addAction("🏷 Filter by Tag...").triggered.connect(lambda: self.filter_changed.emit("tag", ""))
        menu.addSeparator()
        menu.addAction("🔍 Search Entire System...").triggered.connect(self.advanced_search.emit)
        menu.addSeparator()
        create_action = menu.addAction("📦 Create Collection from Current Filter...")
        create_action.triggered.connect(self._on_create_collection_from_filter)
        menu.exec(self.advanced_btn.mapToGlobal(self.advanced_btn.rect().bottomLeft()))
    
    def _on_create_collection_from_filter(self) -> None:
        """Emit signal to create collection from current filter state."""
        filter_state = self.get_current_filter_state()
        self.create_collection_from_filter.emit(filter_state)
    
    def get_current_filter_state(self) -> dict:
        """Get the current filter state as a dictionary for creating collections."""
        state = {}
        
        # Tempo range
        if self._tempo_min > 0:
            state['tempo_min'] = self._tempo_min
        if self._tempo_max > 0 and self._tempo_max < 999:
            state['tempo_max'] = self._tempo_max
        
        # Date filter
        if self._active_date_filter:
            days_map = {"today": 1, "week": 7, "month": 30, "7days": 7, "30days": 30}
            if self._active_date_filter in days_map:
                state['days_ago'] = days_map[self._active_date_filter]
        
        # Search text (could be used for name matching)
        search_text = self.search_input.text().strip()
        if search_text:
            state['search_text'] = search_text
        
        return state
    
    def _apply_date_filter(self, filter_type: str) -> None:
        self._active_date_filter = filter_type if filter_type != "clear" else None
        self._update_date_filter_indicator()
        self.filter_changed.emit("date", filter_type)
    
    def _update_date_filter_indicator(self) -> None:
        if self._active_date_filter:
            names = {"today": "Today", "week": "Week", "month": "Month", "7days": "7d", "30days": "30d"}
            self.date_filter_label.setText(f"📅 {names.get(self._active_date_filter, 'Date')}")
            self.date_filter_label.setVisible(True)
        else:
            self.date_filter_label.setVisible(False)
    
    def _update_date_filter_style(self) -> None:
        """Update date filter label style with current theme colors."""
        palette = QApplication.instance().palette()
        accent = palette.color(QPalette.ColorRole.Highlight).name()
        text_on_accent = palette.color(QPalette.ColorRole.HighlightedText).name()
        self.date_filter_label.setStyleSheet(f"""
            QLabel {{
                background-color: {accent};
                color: {text_on_accent};
                padding: 2px 6px;
                border-radius: 3px;
                font-size: 10px;
            }}
        """)
    
    def _update_go_button_style(self) -> None:
        """Update Go button style with current theme colors."""
        palette = QApplication.instance().palette()
        accent = palette.color(QPalette.ColorRole.Highlight).name()
        text_on_accent = palette.color(QPalette.ColorRole.HighlightedText).name()
        
        # Calculate hover color (slightly lighter)
        from PyQt6.QtGui import QColor
        color = QColor(accent)
        h, s, v, a = color.getHsv()
        v = min(255, int(v * 1.2))
        color.setHsv(h, s, v, a)
        accent_hover = color.name()
        
        self.apply_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: {text_on_accent};
                border: none;
                border-radius: 3px;
                font-size: 10px;
                font-weight: bold;
                text-align: center;
            }}
            QPushButton:hover {{ background-color: {accent_hover}; }}
        """)
    
    def clear_date_filter(self) -> None:
        self._active_date_filter = None
        self._update_date_filter_indicator()
        self.filter_changed.emit("date", "clear")
    
    def get_tempo_filter(self) -> Tuple[int, int]:
        return (self._tempo_min, self._tempo_max)
    
    def _on_sort_changed(self, sort_text: str) -> None:
        sort_map = {
            "Modified ↓": "modified_desc", "Modified ↑": "modified_asc",
            "Name A-Z": "name_asc", "Name Z-A": "name_desc",
            "Tempo ↓": "tempo_desc", "Tempo ↑": "tempo_asc",
            "Length ↓": "length_desc", "Length ↑": "length_asc",
            "Size ↓": "size_desc", "Size ↑": "size_asc",
            "Version ↓": "version_desc", "Version ↑": "version_asc",
            "Key A-Z": "key_asc", "Key Z-A": "key_desc",
            "Location": "location_asc"
        }
        self._current_sort = sort_map.get(sort_text, "modified_desc")
        self.sort_changed.emit(self._current_sort)
    
    def get_current_sort(self) -> str:
        return self._current_sort
    
    def text(self) -> str:
        return self.search_input.text()
    
    def setText(self, text: str) -> None:
        self.search_input.setText(text)
    
    def clear(self) -> None:
        self.search_input.clear()
    
    def setFocus(self) -> None:
        self.search_input.setFocus()
    
    def selectAll(self) -> None:
        self.search_input.selectAll()
    
    def refresh_theme(self) -> None:
        """Refresh all theme-dependent styles. Call this after theme changes."""
        # Update tempo buttons
        for btn in self.tempo_buttons:
            btn._update_style()
        
        # Update Go button
        self._update_go_button_style()
        
        # Update date filter label
        self._update_date_filter_style()
    
    def showEvent(self, event) -> None:
        """Handle show event to refresh theme on display."""
        super().showEvent(event)
        # Refresh theme when widget is shown to ensure correct colors
        QTimer.singleShot(0, self.refresh_theme)
