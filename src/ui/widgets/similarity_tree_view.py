"""Similarity Cluster Tree — groups projects by metadata (tempo-first) in a tree."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...database import Location, get_session
from ...services.similarity_tree_models import SimilarityGroupNode, SimilarityTreeResult
from ...utils.logging import get_logger
from ..theme import AbletonTheme
from ..workers.similarity_tree_worker import SimilarityTreeWorker
from .similarity_tree_item_delegate import SimilarityTreeItemDelegate


class SimilarityTreeView(QWidget):
    """Panel showing hierarchical similarity clusters from indexed metadata."""

    open_in_live_requested = pyqtSignal(int)
    show_in_library_requested = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self._worker: SimilarityTreeWorker | None = None
        self._orphaned_threads: list[SimilarityTreeWorker] = []

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Similarity Tree")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._start_worker)
        header.addWidget(self.refresh_btn)

        layout.addLayout(header)

        self.banner = QLabel("")
        self.banner.setWordWrap(True)
        self.banner.setStyleSheet(
            f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 11px; padding: 8px;"
        )
        self.banner.hide()
        layout.addWidget(self.banner)

        scope_row = QHBoxLayout()
        scope_row.addWidget(QLabel("Location:"))
        self.location_combo = QComboBox()
        self.location_combo.addItem("All locations", None)
        self._populate_locations()
        self.location_combo.currentIndexChanged.connect(lambda: self._start_worker())
        scope_row.addWidget(self.location_combo, stretch=1)
        layout.addLayout(scope_row)

        self._stack = QWidget()
        stack_layout = QVBoxLayout(self._stack)
        stack_layout.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel("Loading…")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stack_layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        stack_layout.addWidget(self.progress)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Projects grouped by tempo & tools"])
        self.tree.setColumnCount(1)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        self.tree.itemExpanded.connect(self._on_item_expanded)
        self._apply_similarity_tree_visuals()
        self.tree.setItemDelegateForColumn(0, SimilarityTreeItemDelegate(self.tree, self.tree))
        stack_layout.addWidget(self.tree)

        layout.addWidget(self._stack, stretch=1)

        help_lbl = QLabel(
            "Groups use indexed metadata: tempo and plugins/devices are weighted strongest; "
            "structural fields, optional ML feature vectors, key/time signature, automation, "
            "and markers also contribute. No project files are modified."
        )
        help_lbl.setWordWrap(True)
        help_lbl.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 11px;")
        layout.addWidget(help_lbl)

    def _apply_similarity_tree_visuals(self) -> None:
        """Indentation, animation, alternating rows, theme-aware QSS for branch lines (Phase 8)."""
        t = self.tree
        t.setIndentation(24)
        t.setAnimated(True)
        t.setAlternatingRowColors(True)
        t.setRootIsDecorated(True)
        c = AbletonTheme.COLORS
        t.setStyleSheet(
            f"""
            QTreeWidget {{
                background-color: {c["surface"]};
                color: {c["text_primary"]};
                alternate-background-color: {c["background_alt"]};
                border: 1px solid {c["border"]};
                border-radius: 4px;
                outline: none;
                show-decoration-selected: 1;
            }}
            QTreeWidget::item {{
                padding: 3px 6px;
            }}
            QTreeWidget::item:selected {{
                background-color: {c["accent"]};
                color: {c["text_on_accent"]};
            }}
            QTreeWidget::item:hover:!selected {{
                background-color: {c["surface_hover"]};
            }}
            QTreeView::branch:has-siblings:!adjoins-item {{
                border-left: 1px solid {c["border_light"]};
            }}
            QTreeView::branch:has-siblings:adjoins-item {{
                border-left: 1px solid {c["border_light"]};
            }}
            """
        )

    def _populate_locations(self) -> None:
        """Fill location combo from database."""
        session = get_session()
        try:
            locs = session.query(Location).order_by(Location.name.asc()).all()
            for loc in locs:
                self.location_combo.addItem(loc.name or f"Location {loc.id}", loc.id)
        finally:
            session.close()

    def showEvent(self, event: Any) -> None:
        super().showEvent(event)
        if not self.tree.topLevelItemCount() and self.status_label.text() in ("Loading…", ""):
            QTimer.singleShot(0, self._start_worker)

    def _scope_location_id(self) -> int | None:
        return self.location_combo.currentData()

    def _start_worker(self) -> None:
        """Run clustering in background."""
        self._safe_stop_worker()

        self._set_loading(True)
        self.tree.clear()
        self.banner.hide()

        loc_id = self._scope_location_id()
        self._worker = SimilarityTreeWorker(location_id=loc_id)
        self._worker.finished_ok.connect(self._on_worker_finished)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.finished.connect(self._on_worker_thread_finished)
        self._worker.start()

    def _safe_stop_worker(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.request_cancel()
            self._worker.wait(3000)
            self._orphaned_threads.append(self._worker)
            self._worker = None

    def _on_worker_thread_finished(self) -> None:
        """Thread cleanup."""
        self._worker = None

    def _set_loading(self, loading: bool) -> None:
        if loading:
            self.status_label.setText("Building similarity tree…")
            self.status_label.show()
            self.progress.show()
            self.tree.hide()
        else:
            self.progress.hide()

    def _on_worker_finished(self, result: object) -> None:
        if not isinstance(result, SimilarityTreeResult):
            self._show_error("Unexpected result from worker.")
            return

        self._set_loading(False)
        self.status_label.hide()
        self.tree.show()

        if result.warnings:
            self.banner.setText(" · ".join(result.warnings))
            self.banner.show()
        else:
            self.banner.hide()

        self.tree.clear()
        if not result.root_nodes:
            self.status_label.setText("No clusters to display — try a different scope or add projects.")
            self.status_label.show()
            self.tree.hide()
            return

        self._populate_tree(result)

    def _populate_tree(self, result: SimilarityTreeResult) -> None:
        self.tree.clear()

        def add_node(
            parent_item: QTreeWidgetItem | None, node: SimilarityGroupNode, branch_index: int
        ) -> QTreeWidgetItem:
            if node.kind == "group":
                item = QTreeWidgetItem([node.label])
            else:
                pid = node.project_id
                meta = result.projects.get(str(pid), {}) if pid else {}
                display_name = str(meta.get("display_name") or node.label)
                pct = meta.get("similarity_to_branch_percent")
                if pct is None:
                    pct = node.similarity_to_branch_percent
                if pct is not None:
                    row_text = f"{pct}% — {display_name}"
                else:
                    row_text = f"— — {display_name}"
                item = QTreeWidgetItem([row_text])
            item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                {"kind": node.kind, "pid": node.project_id, "branch_index": branch_index},
            )
            bc = SimilarityTreeItemDelegate.branch_color(branch_index)
            bg = QColor(bc)
            bg.setAlpha(48)
            item.setBackground(0, QBrush(bg))
            if node.kind == "group":
                tip_parts = [node.label]
                tip_parts.extend(node.breakdown_lines)
                if result.warnings:
                    tip_parts.append("Note: see banner for sampling / missing metadata.")
                item.setToolTip(0, "\n".join(tip_parts))
            else:
                pid = node.project_id
                meta = result.projects.get(str(pid), {}) if pid else {}
                display_name = str(meta.get("display_name") or node.label)
                tempo = meta.get("tempo")
                pct = meta.get("similarity_to_branch_percent")
                if pct is None:
                    pct = node.similarity_to_branch_percent
                tip_lines = [display_name]
                if pct is not None:
                    tip_lines.append(f"Similarity to branch: {pct}%")
                else:
                    tip_lines.append("Similarity to branch: unavailable")
                if tempo is not None:
                    tip_lines.append(f"Tempo: {tempo} BPM")
                elif result.warnings:
                    tip_lines.append("Tempo may be missing.")
                extra = meta.get("similarity_tooltip")
                if extra:
                    tip_lines.append(extra)
                item.setToolTip(0, "\n".join(tip_lines))

            if parent_item is None:
                self.tree.addTopLevelItem(item)
            else:
                parent_item.addChild(item)

            for ch in node.children:
                add_node(item, ch, branch_index)
            return item

        for branch_i, root in enumerate(result.root_nodes):
            add_node(None, root, branch_i)

        self.tree.expandToDepth(2)

    def _on_item_expanded(self, item: QTreeWidgetItem) -> None:
        """Placeholder for future lazy loading."""
        _ = item

    def _on_worker_failed(self, message: str) -> None:
        self._set_loading(False)
        self._show_error(message)

    def _show_error(self, message: str) -> None:
        self.status_label.setText("Could not build similarity tree.")
        self.status_label.show()
        self.tree.hide()
        QMessageBox.warning(self, "Similarity Tree", message)

    def _on_tree_context_menu(self, pos: Any) -> None:
        item = self.tree.itemAt(pos)
        if not item:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        if data.get("kind") != "project":
            return
        pid = data.get("pid")
        if not pid:
            return

        menu = QMenu(self)
        open_live = menu.addAction("Open in Ableton Live")
        show_lib = menu.addAction("Show in library")
        chosen = menu.exec(self.tree.mapToGlobal(pos))
        if chosen == open_live:
            self.open_in_live_requested.emit(int(pid))
        elif chosen == show_lib:
            self.show_in_library_requested.emit(int(pid))

    def cleanup(self) -> None:
        """Stop worker when leaving view."""
        self._safe_stop_worker()
