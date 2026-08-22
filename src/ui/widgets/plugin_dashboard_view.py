"""Plugin usage dashboard widget."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...services.plugin_analytics import PluginAnalyticsService
from ..theme import AbletonTheme


class PluginDashboardView(QWidget):
    """Dashboard showing plugin frequency and project lookups."""

    project_selected = pyqtSignal(int)
    filter_by_plugin_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = PluginAnalyticsService()
        self._stats = []
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Plugin Usage Dashboard")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']};")
        layout.addWidget(self.summary_label)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Search plugins:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter by plugin name...")
        self.search_input.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self.search_input)
        layout.addLayout(filter_row)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Plugin", "Projects", "Actions"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)

        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)

    def refresh(self) -> None:
        self._stats = self._service.get_plugin_usage_stats()
        total_with_plugins = self._service.get_total_projects_with_plugins()
        unique_count = len(self._stats)
        self.summary_label.setText(
            f"{unique_count} unique plugins across {total_with_plugins} projects with plugin data."
        )
        self._apply_filter()

    def _apply_filter(self) -> None:
        needle = self.search_input.text().strip().lower()
        filtered = self._stats
        if needle:
            filtered = [s for s in self._stats if needle in s.name.lower()]
        self._populate_table(filtered)

    def _populate_table(self, stats) -> None:
        self.table.setRowCount(len(stats))
        for row, stat in enumerate(stats):
            name_item = QTableWidgetItem(stat.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, name_item)

            count_item = QTableWidgetItem(str(stat.project_count))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            count_item.setFlags(count_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, count_item)

            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(4, 0, 4, 0)

            show_btn = QPushButton("Show Projects")
            show_btn.clicked.connect(lambda _checked=False, n=stat.name: self._show_projects(n))
            actions_layout.addWidget(show_btn)

            filter_btn = QPushButton("Filter Library")
            filter_btn.clicked.connect(
                lambda _checked=False, n=stat.name: self.filter_by_plugin_requested.emit(n)
            )
            actions_layout.addWidget(filter_btn)

            self.table.setCellWidget(row, 2, actions)

    def _show_projects(self, plugin_name: str) -> None:
        ids = self._service.get_projects_using_plugin(plugin_name)
        if ids:
            self.project_selected.emit(ids[0])
