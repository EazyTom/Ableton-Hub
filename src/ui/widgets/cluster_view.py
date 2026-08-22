"""ML cluster visualization widget."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...database import Project, get_session
from ...services.ml_clustering import ClusterInfo, ClusteringResult
from ..theme import AbletonTheme
from ..workers.cluster_worker import ClusterWorker


class ClusterView(QWidget):
    """Visualize ML clustering groups for the indexed library."""

    project_selected = pyqtSignal(int)
    create_collection_requested = pyqtSignal(list, str)  # project_ids, label

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._worker: ClusterWorker | None = None
        self._last_result: ClusteringResult | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("ML Cluster Visualization")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        header.addWidget(QLabel("Clusters:"))
        self.cluster_spin = QSpinBox()
        self.cluster_spin.setRange(2, 20)
        self.cluster_spin.setValue(5)
        header.addWidget(self.cluster_spin)

        self.run_btn = QPushButton("Run Clustering")
        self.run_btn.clicked.connect(self._start_worker)
        header.addWidget(self.run_btn)
        layout.addLayout(header)

        self.status_label = QLabel(
            "Groups similar projects using indexed feature vectors. "
            "Re-scan metadata if clusters look empty."
        )
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']};")
        layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Cluster / Project", "Details"])
        self.tree.setAlternatingRowColors(True)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.tree)

    def refresh(self) -> None:
        if self._last_result is None:
            self._start_worker()

    def cleanup(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.quit()

    def _start_worker(self) -> None:
        if self._worker and self._worker.isRunning():
            return

        self.progress.show()
        self.run_btn.setEnabled(False)
        self.status_label.setText("Running clustering...")

        self._worker = ClusterWorker(n_clusters=self.cluster_spin.value(), parent=self)
        self._worker.progress.connect(self.status_label.setText)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished_with_result.connect(self._on_finished)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_worker_finished(self) -> None:
        self.progress.hide()
        self.run_btn.setEnabled(True)

    def _on_failed(self, message: str) -> None:
        self.status_label.setText(message)
        QMessageBox.warning(self, "Clustering", message)

    def _on_finished(self, result: ClusteringResult | None) -> None:
        if result is None:
            return
        self._last_result = result
        self._populate_tree(result)
        self.status_label.setText(
            f"Found {result.n_clusters} clusters across "
            f"{sum(len(c.project_ids) for c in result.clusters)} projects."
        )

    def _populate_tree(self, result: ClusteringResult) -> None:
        self.tree.clear()
        project_names = self._load_project_names(
            [pid for cluster in result.clusters for pid in cluster.project_ids]
        )

        for cluster in result.clusters:
            cluster_item = QTreeWidgetItem(self.tree)
            label = cluster.suggested_label or f"Cluster {cluster.cluster_id + 1}"
            cluster_item.setText(0, f"{label} ({cluster.project_count} projects)")
            details = (
                f"Avg tempo {cluster.avg_tempo:.0f} BPM | "
                f"Plugins: {', '.join(cluster.common_plugins[:3]) or '—'}"
            )
            cluster_item.setText(1, details)
            cluster_item.setData(0, Qt.ItemDataRole.UserRole, ("cluster", cluster))

            collection_btn_item = QTreeWidgetItem(cluster_item)
            collection_btn_item.setText(0, "Create Smart Collection from cluster")
            collection_btn_item.setData(
                0, Qt.ItemDataRole.UserRole, ("action", "collection", cluster)
            )

            for project_id in cluster.project_ids:
                child = QTreeWidgetItem(cluster_item)
                child.setText(0, project_names.get(project_id, f"Project #{project_id}"))
                child.setData(0, Qt.ItemDataRole.UserRole, ("project", project_id))

        self.tree.expandAll()

    def _load_project_names(self, project_ids: list[int]) -> dict[int, str]:
        if not project_ids:
            return {}
        with get_session() as session:
            rows = session.query(Project.id, Project.name).filter(Project.id.in_(project_ids)).all()
            return {row[0]: row[1] for row in rows}

    def _on_item_double_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        kind = data[0]
        if kind == "project":
            self.project_selected.emit(data[1])
        elif kind == "action" and data[1] == "collection":
            cluster: ClusterInfo = data[2]
            label = cluster.suggested_label or f"Cluster {cluster.cluster_id + 1}"
            self.create_collection_requested.emit(cluster.project_ids, label)
