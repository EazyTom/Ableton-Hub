"""Find Audio Exports view - lists audio files under a location with project mapping."""

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QSize, Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...database import Export, Location, Project, get_session
from ...services.audio_player import AudioPlayer
from ...services.export_tracker import ExportTracker
from ...utils.paths import normalize_path
from ..theme import AbletonTheme
from ..workers import AudioScanWorker


class FindAudioExportsView(QWidget):
    """View for finding and mapping audio exports under a location."""

    back_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._location_id: int | None = None
        self._location: Location | None = None
        self._projects: list[tuple[int, str]] = []  # (id, name)
        self._path_to_export: dict[str, Export] = {}  # normalized path -> Export (unmapped only)
        self._mapped_paths: set[str] = set()  # normalized paths already mapped to a project
        self._tracker = ExportTracker()
        self._audio_player = AudioPlayer.instance()
        self._unmapped_count = 0

        self._scan_thread: QThread | None = None
        self._scan_worker: AudioScanWorker | None = None
        self._orphaned_threads: list[QThread] = []

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the view UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet(
            f"background-color: {AbletonTheme.COLORS['surface']}; "
            f"border-bottom: 1px solid {AbletonTheme.COLORS['border']};"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 8, 16, 8)

        back_btn = QPushButton("← Back")
        back_btn.clicked.connect(self.back_requested.emit)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {AbletonTheme.COLORS['text_primary']};
                font-weight: bold;
                padding: 8px 12px;
            }}
            QPushButton:hover {{
                background-color: {AbletonTheme.COLORS['surface_hover']};
                border-radius: 4px;
            }}
        """)
        header_layout.addWidget(back_btn)

        self._location_label = QLabel("Find Audio Exports")
        self._location_label.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: {AbletonTheme.COLORS['text_primary']};"
        )
        header_layout.addWidget(self._location_label)

        header_layout.addStretch()

        self._rescan_btn = QPushButton("Rescan")
        self._rescan_btn.clicked.connect(self._start_scan)
        self._rescan_btn.setEnabled(False)
        self._rescan_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {AbletonTheme.COLORS['surface_light']};
                color: {AbletonTheme.COLORS['text_primary']};
                border: 1px solid {AbletonTheme.COLORS['border']};
            }}
            QPushButton:hover {{
                background-color: {AbletonTheme.COLORS['surface_hover']};
            }}
        """)
        header_layout.addWidget(self._rescan_btn)

        main_layout.addWidget(header)

        # Table - no orange highlighting (override theme selection/hover)
        self._table = QTableWidget()
        self._table.setObjectName("findExportsTable")
        self._table.setStyleSheet(f"""
            QTableView#findExportsTable::item:hover {{
                background-color: {AbletonTheme.COLORS['surface_hover']};
            }}
            QTableView#findExportsTable::item:selected {{
                background-color: {AbletonTheme.COLORS['surface_light']};
                color: {AbletonTheme.COLORS['text_primary']};
            }}
        """)
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            ["", "Name", "Size", "Path", "Modified", "Associate to Project"]
        )
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        main_layout.addWidget(self._table)

        # Status
        self._status_label = QLabel("Select a location to scan.")
        self._status_label.setStyleSheet(
            f"color: {AbletonTheme.COLORS['text_secondary']}; padding: 8px 16px;"
        )
        main_layout.addWidget(self._status_label)

    def set_location(self, location_id: int) -> None:
        """Set the location to scan and start the scan.

        Args:
            location_id: The location ID.
        """
        self._location_id = location_id
        self._path_to_export.clear()
        self._mapped_paths.clear()

        session = get_session()
        try:
            self._location = session.query(Location).get(location_id)
            if not self._location:
                self._status_label.setText("Location not found.")
                return

            self._location_label.setText(f"Find Audio Exports — {self._location.name}")

            # Load projects for this location, excluding backup paths
            from sqlalchemy import not_

            projects = (
                session.query(Project)
                .filter(Project.location_id == location_id)
                .filter(
                    not_(Project.file_path.ilike("%/Backup/%")),
                    not_(Project.file_path.ilike("%\\Backup\\%")),
                )
                .order_by(Project.name)
                .all()
            )
            # Deduplicate: prefer projects whose file exists, then by normalized name
            projects_sorted = sorted(
                projects,
                key=lambda p: (
                    0 if Path(p.file_path).exists() else 1,
                    (p.name or "").strip().lower(),
                ),
            )
            seen_keys: set[str] = set()
            self._projects = []
            for p in projects_sorted:
                key = (p.name or "").strip().lower()
                if not key:
                    continue
                if key not in seen_keys:
                    seen_keys.add(key)
                    self._projects.append((p.id, p.name))

            # Load existing exports under this location path
            # Only keep unmapped exports; track mapped paths to exclude from list
            location_path = Path(self._location.path)
            base_norm = normalize_path(location_path)
            exports = session.query(Export).all()
            for exp in exports:
                exp_norm = normalize_path(exp.export_path)
                if exp_norm.startswith(base_norm):
                    if exp.project_id is not None:
                        self._mapped_paths.add(exp_norm)
                    else:
                        self._path_to_export[exp_norm] = exp

        finally:
            session.close()

        self._rescan_btn.setEnabled(True)
        try:
            self._audio_player.playback_stopped.disconnect(self._on_playback_stopped)
        except (TypeError, RuntimeError):
            pass
        try:
            self._audio_player.playback_finished.disconnect(self._on_playback_stopped)
        except (TypeError, RuntimeError):
            pass
        self._audio_player.playback_stopped.connect(self._on_playback_stopped)
        self._audio_player.playback_finished.connect(self._on_playback_stopped)
        self._start_scan()

    def _start_scan(self) -> None:
        """Start the audio scan worker."""
        if not self._location:
            return

        self._stop_workers()

        self._table.setRowCount(0)
        self._unmapped_count = 0
        self._status_label.setText("Scanning for audio files...")

        location_path = Path(self._location.path)
        if not location_path.exists():
            self._status_label.setText("Location path does not exist.")
            return

        self._scan_worker = AudioScanWorker(location_path)
        self._scan_thread = self._scan_worker
        self._scan_worker.file_found.connect(self._on_file_found)
        self._scan_worker.scan_complete.connect(self._on_scan_complete)
        self._scan_worker.start()

    def _on_file_found(self, path: str, size: int, mtime: float) -> None:
        """Handle a file found during scan."""
        norm_path = normalize_path(path)
        if norm_path in self._mapped_paths:
            return  # Skip files already mapped to a project

        self._unmapped_count += 1
        p = Path(path)
        row = self._table.rowCount()
        self._table.insertRow(row)

        # Play button (column 0) - square, no hover, top-center aligned
        play_btn = QPushButton()
        play_icon = QApplication.instance().style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        play_btn.setIcon(play_icon)
        play_btn.setIconSize(QSize(18, 18))
        play_btn.setFlat(True)
        play_btn.setFixedSize(15, 15)
        play_btn.setToolTip("Play / Stop")
        play_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {AbletonTheme.COLORS['surface']};
                border: none;
                border-radius: 0;
                color: {AbletonTheme.COLORS['text_primary']};
                padding: 0;
            }}
            QPushButton:hover, QPushButton:pressed, QPushButton:focus {{
                background-color: {AbletonTheme.COLORS['surface']};
            }}
        """)
        play_btn.setProperty("file_path", path)
        play_btn.clicked.connect(lambda checked, fp=path: self._on_play_clicked(fp))
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        btn_layout.addWidget(play_btn)
        self._table.setCellWidget(row, 0, btn_container)

        # Name (column 1)
        name_item = QTableWidgetItem(p.name)
        name_item.setData(Qt.ItemDataRole.UserRole, path)
        self._table.setItem(row, 1, name_item)

        # Size (column 2)
        if size >= 1024 * 1024:
            size_str = f"{size / (1024 * 1024):.2f} MB"
        else:
            size_str = f"{size / 1024:.1f} KB"
        self._table.setItem(row, 2, QTableWidgetItem(size_str))

        # Path (column 3)
        path_item = QTableWidgetItem(path)
        path_item.setToolTip(path)
        self._table.setItem(row, 3, path_item)

        # Modified (column 4)
        mod_dt = datetime.fromtimestamp(mtime)
        self._table.setItem(row, 4, QTableWidgetItem(mod_dt.strftime("%Y-%m-%d %H:%M")))

        # Project dropdown (column 5) - no orange
        combo = QComboBox()
        combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {AbletonTheme.COLORS['surface']};
                color: {AbletonTheme.COLORS['text_primary']};
                border: 1px solid {AbletonTheme.COLORS['border']};
            }}
            QComboBox:hover {{
                background-color: {AbletonTheme.COLORS['surface_hover']};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {AbletonTheme.COLORS['surface_light']};
                color: {AbletonTheme.COLORS['text_primary']};
            }}
        """)
        combo.addItem("—", None)
        for pid, pname in self._projects:
            combo.addItem(pname, pid)
        combo.currentIndexChanged.connect(lambda idx, r=row: self._on_project_changed(r, idx))
        self._table.setCellWidget(row, 5, combo)

        # Pre-select if already in exports (unmapped - would have "—" selected)
        # No pre-select needed since we only show unmapped

    def _on_play_clicked(self, path: str) -> None:
        """Handle play button click - toggle play/stop for this row's file."""
        if not path:
            return

        if self._audio_player.current_file == path and self._audio_player.is_playing:
            self._audio_player.stop()
            self._update_play_button_for_path(path, False)
            return

        self._update_all_play_buttons(False)

        if self._audio_player.play(path):
            self._update_play_button_for_path(path, True)

    def _find_row_for_path(self, path: str) -> int | None:
        """Find table row containing the given file path."""
        for row in range(self._table.rowCount()):
            path_item = self._table.item(row, 1)
            if path_item and path_item.data(Qt.ItemDataRole.UserRole) == path:
                return row
        return None

    def _get_play_button(self, row: int) -> QPushButton | None:
        """Get the play button for a row (may be inside a container)."""
        cell = self._table.cellWidget(row, 0)
        if cell:
            btn = cell.findChild(QPushButton)
            return btn if isinstance(btn, QPushButton) else None
        return None

    def _update_play_button_for_path(self, path: str, is_playing: bool) -> None:
        """Update play button appearance for the row with this path."""
        row = self._find_row_for_path(path)
        if row is not None:
            play_btn = self._get_play_button(row)
            if play_btn:
                icon = (
                    QApplication.instance()
                    .style()
                    .standardIcon(
                        QStyle.StandardPixmap.SP_MediaStop
                        if is_playing
                        else QStyle.StandardPixmap.SP_MediaPlay
                    )
                )
                play_btn.setIcon(icon)

    def _update_all_play_buttons(self, is_playing: bool) -> None:
        """Update all play buttons to the given state."""
        icon = (
            QApplication.instance()
            .style()
            .standardIcon(
                QStyle.StandardPixmap.SP_MediaStop
                if is_playing
                else QStyle.StandardPixmap.SP_MediaPlay
            )
        )
        for row in range(self._table.rowCount()):
            play_btn = self._get_play_button(row)
            if play_btn:
                play_btn.setIcon(icon)

    def _on_playback_stopped(self) -> None:
        """Handle playback stopped - update play button."""
        if self._audio_player.current_file:
            self._update_play_button_for_path(self._audio_player.current_file, False)

    def _on_project_changed(self, row: int, index: int) -> None:
        """Handle project selection change in dropdown."""
        path_item = self._table.item(row, 1)
        if not path_item:
            return

        path = path_item.data(Qt.ItemDataRole.UserRole)
        if not path:
            return

        combo = self._table.cellWidget(row, 5)
        if not combo:
            return

        project_id = combo.itemData(index)

        norm_path = normalize_path(path)
        existing = self._path_to_export.get(norm_path)

        if existing:
            if project_id:
                self._tracker.link_export_to_project(existing.id, project_id)
                existing.project_id = project_id
                self._mapped_paths.add(norm_path)
                # Keep in _path_to_export for reassignment
            else:
                session = get_session()
                try:
                    exp = session.query(Export).get(existing.id)
                    if exp:
                        exp.project_id = None
                        session.commit()
                        existing.project_id = None
                        self._mapped_paths.discard(norm_path)
                finally:
                    session.close()
        else:
            if project_id:
                export_id = self._tracker.add_export(path, project_id)
                if export_id:
                    self._mapped_paths.add(norm_path)
                    session = get_session()
                    try:
                        exp = session.query(Export).get(export_id)
                        if exp:
                            self._path_to_export[norm_path] = exp
                    finally:
                        session.close()

    def _on_scan_complete(self, count: int) -> None:
        """Handle scan completion."""
        unmapped = getattr(self, "_unmapped_count", 0)
        if unmapped == 0:
            self._status_label.setText("No unmapped audio files found.")
        else:
            self._status_label.setText(f"Found {unmapped} unmapped audio file(s).")

    def _safely_stop_thread(self, thread: QThread | None, worker: AudioScanWorker | None) -> None:
        """Safely stop the scan worker without blocking UI."""
        still_running = []
        for t in self._orphaned_threads:
            try:
                if t.isRunning():
                    still_running.append(t)
            except RuntimeError:
                pass
        self._orphaned_threads = still_running

        if worker:
            worker.stop()
            try:
                worker.file_found.disconnect()
            except (TypeError, RuntimeError):
                pass
            try:
                worker.scan_complete.disconnect()
            except (TypeError, RuntimeError):
                pass

        if thread is None:
            if worker:
                worker.deleteLater()
            return

        if not thread.isRunning():
            thread.deleteLater()
            if worker:
                worker.deleteLater()
            return

        thread.finished.connect(thread.deleteLater)
        if worker:
            thread.finished.connect(worker.deleteLater)
        thread.quit()
        self._orphaned_threads.append(thread)

    def _stop_workers(self) -> None:
        """Stop all background workers."""
        self._safely_stop_thread(self._scan_thread, self._scan_worker)
        self._scan_thread = None
        self._scan_worker = None

    def cleanup(self) -> None:
        """Clean up resources when leaving the view."""
        self._audio_player.stop()
        try:
            self._audio_player.playback_stopped.disconnect(self._on_playback_stopped)
        except (TypeError, RuntimeError):
            pass
        try:
            self._audio_player.playback_finished.disconnect(self._on_playback_stopped)
        except (TypeError, RuntimeError):
            pass
        self._stop_workers()
