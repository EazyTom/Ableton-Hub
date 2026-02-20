"""Collection management view widget."""

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStyle,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import joinedload

from ...database import Collection, CollectionType, Project, ProjectCollection, get_session
from ...services.audio_player import AudioPlayer
from ..theme import AbletonTheme


class CollectionCard(QFrame):
    """Card widget for a collection in grid view."""

    clicked = pyqtSignal(int)  # Collection ID
    edit_requested = pyqtSignal(int)  # Collection ID

    def __init__(self, collection: Collection, parent: QWidget | None = None):
        super().__init__(parent)

        self.collection = collection
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the card UI."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedSize(200, 240)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.setStyleSheet(f"""
            CollectionCard {{
                background-color: {AbletonTheme.COLORS['surface']};
                border: 1px solid {AbletonTheme.COLORS['border']};
                border-radius: 8px;
            }}
            CollectionCard:hover {{
                background-color: {AbletonTheme.COLORS['surface_hover']};
                border-color: {AbletonTheme.COLORS['border_light']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Artwork placeholder
        self.artwork = QLabel()
        self.artwork.setFixedSize(176, 120)
        self.artwork.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.artwork.setStyleSheet(f"""
            QLabel {{
                background-color: {AbletonTheme.COLORS['surface_light']};
                border-radius: 6px;
                font-size: 48px;
            }}
        """)

        # Show artwork or icon
        if self.collection.artwork_path:
            pixmap = QPixmap(self.collection.artwork_path)
            if not pixmap.isNull():
                self.artwork.setPixmap(
                    pixmap.scaled(
                        176,
                        120,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                self._set_default_icon()
        else:
            self._set_default_icon()

        layout.addWidget(self.artwork)

        # Collection name
        name_label = QLabel(self.collection.name)
        name_label.setWordWrap(True)
        font = AbletonTheme.safe_font_modify(name_label.font(), bold=True, pixel_size=16)
        name_label.setFont(font)
        layout.addWidget(name_label)

        # Type and track count
        type_icon = "⚡" if self.collection.is_smart else self._get_type_icon()
        if self.collection.is_smart:
            # For smart collections, show dynamic count
            from ...services.smart_collections import SmartCollectionService

            matching_ids = SmartCollectionService.evaluate_smart_collection(self.collection.id)
            track_count = len(matching_ids) + len(self.collection.project_collections)
        else:
            track_count = len(self.collection.project_collections)
        info_label = QLabel(
            f"{type_icon} {self.collection.collection_type.value.title()} • {track_count} tracks"
        )
        info_label.setStyleSheet(
            f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 11px;"
        )
        layout.addWidget(info_label)

        layout.addStretch()

    def _set_default_icon(self) -> None:
        """Set default icon based on collection type."""
        icon_map = {
            CollectionType.ALBUM: "💿",
            CollectionType.EP: "📀",
            CollectionType.SINGLE: "🎵",
            CollectionType.COMPILATION: "📚",
            CollectionType.SESSION: "🎤",
            CollectionType.CLIENT: "💼",
            CollectionType.CUSTOM: "📁",
        }
        icon = icon_map.get(self.collection.collection_type, "📁")
        self.artwork.setText(icon)

    def _get_type_icon(self) -> str:
        """Get icon for collection type."""
        icon_map = {
            CollectionType.ALBUM: "💿",
            CollectionType.EP: "📀",
            CollectionType.SINGLE: "🎵",
            CollectionType.COMPILATION: "📚",
            CollectionType.SESSION: "🎤",
            CollectionType.CLIENT: "💼",
            CollectionType.CUSTOM: "📁",
        }
        return icon_map.get(self.collection.collection_type, "📁")

    def mousePressEvent(self, event) -> None:
        """Handle mouse press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.collection.id)
        super().mousePressEvent(event)

    def _on_context_menu(self, pos) -> None:
        """Show context menu for collection card."""
        menu = QMenu(self)

        edit_action = menu.addAction("Edit Collection...")
        edit_action.triggered.connect(lambda: self.edit_requested.emit(self.collection.id))

        menu.addSeparator()

        delete_action = menu.addAction("Delete Collection")
        delete_action.triggered.connect(lambda: self._delete_collection())

        menu.exec(self.mapToGlobal(pos))

    def _delete_collection(self) -> None:
        """Delete this collection."""
        result = QMessageBox.question(
            self,
            "Delete Collection",
            f"Are you sure you want to delete '{self.collection.name}'?\n\n"
            "This will remove the collection but not the projects in it.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if result == QMessageBox.StandardButton.Yes:
            session = get_session()
            try:
                collection = session.query(Collection).get(self.collection.id)
                if collection:
                    session.delete(collection)
                    session.commit()
                    # Emit signal to refresh - find CollectionView parent
                    parent = self.parent()
                    while parent:
                        if hasattr(parent, "refresh") and isinstance(parent, CollectionView):
                            parent.refresh()
                            break
                        parent = parent.parent()
            finally:
                session.close()


class CollectionDetailView(QWidget):
    """Detailed view of a single collection with track listing."""

    back_requested = pyqtSignal()
    project_selected = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._collection: Collection | None = None
        self._audio_player = AudioPlayer.instance()
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the detail view UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header row
        header = QHBoxLayout()

        back_btn = QPushButton("← Back")
        back_btn.clicked.connect(self.back_requested.emit)
        header.addWidget(back_btn)

        header.addStretch()

        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self._on_edit)
        header.addWidget(edit_btn)

        layout.addLayout(header)

        # Collection info
        info_layout = QHBoxLayout()

        # Artwork
        self.artwork = QLabel()
        self.artwork.setFixedSize(200, 200)
        self.artwork.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.artwork.setStyleSheet(f"""
            QLabel {{
                background-color: {AbletonTheme.COLORS['surface_light']};
                border-radius: 8px;
            }}
        """)
        info_layout.addWidget(self.artwork)

        # Details
        details = QVBoxLayout()

        # Artist name (if available)
        self.artist_label = QLabel()
        self.artist_label.setStyleSheet(
            f"font-size: 18px; color: {AbletonTheme.COLORS['text_secondary']};"
        )
        details.addWidget(self.artist_label)

        # Collection name
        self.name_label = QLabel()
        self.name_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        details.addWidget(self.name_label)

        # Type and release date
        self.type_label = QLabel()
        self.type_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']};")
        details.addWidget(self.type_label)

        # Release date (full date if available)
        self.release_date_label = QLabel()
        self.release_date_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']};")
        details.addWidget(self.release_date_label)

        # Description
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet(
            f"color: {AbletonTheme.COLORS['text_secondary']}; margin-top: 8px;"
        )
        details.addWidget(self.description_label)

        details.addStretch()

        self.stats_label = QLabel()
        details.addWidget(self.stats_label)

        info_layout.addLayout(details)
        info_layout.addStretch()

        layout.addLayout(info_layout)

        # Track list
        self.track_table = QTableWidget()
        self.track_table.setColumnCount(6)
        self.track_table.setHorizontalHeaderLabels(
            ["#", "Artwork", "Track Name", "Project", "Export", "Actions"]
        )
        self.track_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.track_table.setAlternatingRowColors(True)
        self.track_table.setShowGrid(False)
        self.track_table.verticalHeader().setVisible(False)

        # Set row height
        self.track_table.verticalHeader().setDefaultSectionSize(45)

        # Drag and drop disabled - use Move Up/Down buttons instead
        self.track_table.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)

        # Make track name column editable
        self.track_table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked
        )

        header = self.track_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # #
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Artwork
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Track Name
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Project
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Export
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Actions - fixed width

        # Set Actions column to a wider fixed width (includes play button)
        header.resizeSection(5, 320)

        self.track_table.cellDoubleClicked.connect(self._on_track_double_click)
        self.track_table.cellChanged.connect(self._on_track_name_changed)
        self.track_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.track_table.customContextMenuRequested.connect(self._on_track_context_menu)

        layout.addWidget(self.track_table)

    def set_collection(self, collection_id: int) -> None:
        """Load and display a collection."""
        # Connect playback signals for play button updates
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

        session = get_session()
        try:
            # Eagerly load relationships (including ProjectCollection.export to avoid DetachedInstanceError)
            self._collection = (
                session.query(Collection)
                .options(
                    joinedload(Collection.project_collections)
                    .joinedload(ProjectCollection.project)
                    .joinedload(Project.location),
                    joinedload(Collection.project_collections)
                    .joinedload(ProjectCollection.project)
                    .joinedload(Project.exports),
                    joinedload(Collection.project_collections).joinedload(ProjectCollection.export),
                )
                .get(collection_id)
            )
            if self._collection:
                self._update_display()
        finally:
            session.close()

    def _refresh_collection_from_db(self) -> None:
        """Refresh collection from database with proper relationships."""
        if not self._collection:
            return
        session = get_session()
        try:
            self._collection = (
                session.query(Collection)
                .options(
                    joinedload(Collection.project_collections)
                    .joinedload(ProjectCollection.project)
                    .joinedload(Project.location),
                    joinedload(Collection.project_collections)
                    .joinedload(ProjectCollection.project)
                    .selectinload(Project.exports),
                    joinedload(Collection.project_collections).joinedload(ProjectCollection.export),
                )
                .get(self._collection.id)
            )

            # Clean up invalid export_id references (exports that were deleted)
            if self._collection:
                from ...database import Export

                for pc in self._collection.project_collections:
                    if pc.export_id:
                        # Check if export still exists
                        export = session.query(Export).get(pc.export_id)
                        if not export or export.project_id != pc.project_id:
                            # Export doesn't exist or belongs to different project, clear it
                            pc.export_id = None
                            session.commit()
        finally:
            session.close()

    def _update_display(self) -> None:
        """Update the display with collection data."""
        if not self._collection:
            # Show empty state
            self.name_label.setText("Collection not found")
            self.artist_label.setVisible(False)
            self.type_label.setText("")
            self.release_date_label.setVisible(False)
            self.description_label.setVisible(False)
            self.artwork.setText("📁")
            self.track_table.setRowCount(0)
            return

        # Artist name
        if self._collection.artist_name:
            self.artist_label.setText(self._collection.artist_name)
            self.artist_label.setVisible(True)
        else:
            self.artist_label.setVisible(False)

        # Collection name
        self.name_label.setText(self._collection.name)

        # Type
        self.type_label.setText(f"{self._collection.collection_type.value.title()}")

        # Release date (full date format)
        if self._collection.release_date:
            from datetime import date, datetime

            release_date = self._collection.release_date
            if isinstance(release_date, datetime):
                release_str = release_date.strftime("%B %d, %Y")
            elif isinstance(release_date, date):
                release_str = release_date.strftime("%B %d, %Y")
            else:
                release_str = str(release_date)
            self.release_date_label.setText(f"Released: {release_str}")
            self.release_date_label.setVisible(True)
        else:
            self.release_date_label.setVisible(False)

        # Description
        if self._collection.description:
            self.description_label.setText(self._collection.description)
            self.description_label.setVisible(True)
        else:
            self.description_label.setVisible(False)

        # Artwork
        if self._collection.artwork_path:
            pixmap = QPixmap(self._collection.artwork_path)
            if not pixmap.isNull():
                self.artwork.setPixmap(
                    pixmap.scaled(
                        200,
                        200,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
        else:
            icon_map = {
                CollectionType.ALBUM: "💿",
                CollectionType.EP: "📀",
                CollectionType.SINGLE: "🎵",
            }
            self.artwork.setText(icon_map.get(self._collection.collection_type, "📁"))
            self.artwork.setStyleSheet(self.artwork.styleSheet() + "font-size: 64px;")

        # Stats
        track_count = len(self._collection.project_collections)
        export_count = 0
        try:
            export_count = sum(
                1
                for pc in self._collection.project_collections
                if pc.project and hasattr(pc.project, "exports") and pc.project.exports
            )
        except Exception:
            # If relationships are detached, skip export count
            pass
        self.stats_label.setText(f"{track_count} tracks • {export_count} exported")

        # Track list
        self._populate_tracks()

    def _populate_tracks(self) -> None:
        """Populate the track list table."""
        if not self._collection:
            return

        # Refresh collection to ensure we have fresh data
        self._refresh_collection_from_db()

        if not self._collection:
            return

        # Disconnect cellChanged to prevent triggering during population
        try:
            self.track_table.cellChanged.disconnect()
        except TypeError:
            # Already disconnected or never connected
            pass

        # Ensure we're working with fresh project_collections
        pcs = sorted(
            self._collection.project_collections,
            key=lambda x: (x.disc_number or 1, x.track_number or 999),
        )

        self.track_table.setRowCount(len(pcs))

        for row, pc in enumerate(pcs):
            # Track number (editable for reordering)
            track_num = str(pc.track_number) if pc.track_number else str(row + 1)
            track_num_item = QTableWidgetItem(track_num)
            track_num_item.setData(Qt.ItemDataRole.UserRole, pc.id)  # Store ProjectCollection ID
            track_num_item.setFlags(track_num_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.track_table.setItem(row, 0, track_num_item)

            # Artwork column
            artwork_item = QTableWidgetItem()
            if pc.track_artwork_path and Path(pc.track_artwork_path).exists():
                pixmap = QPixmap(pc.track_artwork_path)
                if not pixmap.isNull():
                    icon = QIcon(
                        pixmap.scaled(
                            40,
                            40,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
                    artwork_item.setIcon(icon)
            else:
                artwork_item.setText("📷")
            artwork_item.setData(Qt.ItemDataRole.UserRole, pc.id)
            artwork_item.setFlags(artwork_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.track_table.setItem(row, 1, artwork_item)

            # Track name (editable - priority: track_name > selected_export.export_name > export_song_name > project.name)
            if pc.project:
                if pc.track_name:
                    track_name = pc.track_name
                elif pc.export_id:
                    # Check if export still exists
                    try:
                        if pc.export and pc.export.export_name:
                            track_name = pc.export.export_name
                        else:
                            # Export was deleted, fall back (don't modify DB here, just display)
                            if pc.project.export_song_name:
                                track_name = pc.project.export_song_name
                            else:
                                track_name = pc.project.name
                    except Exception:
                        # Export relationship issue, fall back
                        if pc.project.export_song_name:
                            track_name = pc.project.export_song_name
                        else:
                            track_name = pc.project.name
                elif pc.project.export_song_name:
                    track_name = pc.project.export_song_name
                else:
                    track_name = pc.project.name

                name_item = QTableWidgetItem(track_name)
                name_item.setData(Qt.ItemDataRole.UserRole, pc.id)  # Store ProjectCollection ID
                name_item.setFlags(name_item.flags() | Qt.ItemFlag.ItemIsEditable)
                self.track_table.setItem(row, 2, name_item)

                # Project
                project_item = QTableWidgetItem(pc.project.name)
                project_item.setData(Qt.ItemDataRole.UserRole, pc.project.id)
                project_item.setFlags(project_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.track_table.setItem(row, 3, project_item)

                # Export status
                try:
                    has_export = (
                        bool(pc.project.exports) if hasattr(pc.project, "exports") else False
                    )
                except Exception:
                    has_export = False
                export_item = QTableWidgetItem("✓" if has_export else "")
                export_item.setFlags(export_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.track_table.setItem(row, 4, export_item)
            else:
                name_item = QTableWidgetItem("[Missing]")
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.track_table.setItem(row, 2, name_item)
                self.track_table.setItem(row, 3, QTableWidgetItem(""))
                self.track_table.setItem(row, 4, QTableWidgetItem(""))

            # Actions column with buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(6)
            actions_layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # Align buttons to top
            actions_layout.addStretch()  # Push buttons to the right

            # Play button - same behavior as Find Audio Exports
            play_path = self._get_playable_path_for_track(pc)
            play_btn = QPushButton()
            play_icon = QApplication.instance().style().standardIcon(
                QStyle.StandardPixmap.SP_MediaPlay
            )
            play_btn.setIcon(play_icon)
            play_btn.setIconSize(QSize(18, 18))
            play_btn.setFlat(True)
            play_btn.setFixedSize(40, 40)
            play_btn.setToolTip("Play / Stop")
            play_btn.setStyleSheet(
                "QPushButton { padding: 0px; margin: 0px; border: none; text-align: center; }"
            )
            play_btn.setProperty("file_path", play_path or "")
            play_btn.setEnabled(bool(play_path))
            if play_path:
                play_btn.clicked.connect(
                    lambda checked, fp=play_path: self._on_play_clicked(fp)
                )
            actions_layout.addWidget(play_btn)

            # Export selection button
            export_select_btn = QPushButton("🎞️")
            export_select_btn.setFixedSize(40, 40)
            export_select_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            font = QFont()
            font.setPointSize(24)
            export_select_btn.setFont(font)
            export_select_btn.setStyleSheet(
                "QPushButton { padding: 0px; margin: 0px; border: none; text-align: center; padding-top: 0px; padding-bottom: 0px; }"
            )
            export_select_btn.setToolTip(
                '<div style="font-size: 10px;">Select export for track name</div>'
            )
            # Check if project has exports
            has_exports = False
            try:
                if pc.project:
                    # Check if exports are loaded in the relationship
                    if hasattr(pc.project, "exports"):
                        has_exports = bool(pc.project.exports)
                    else:
                        # If not loaded, query from database
                        from ...database import Export, get_session

                        temp_session = get_session()
                        try:
                            export_count = (
                                temp_session.query(Export)
                                .filter(Export.project_id == pc.project.id)
                                .count()
                            )
                            has_exports = export_count > 0
                        finally:
                            temp_session.close()
            except Exception:
                pass
            export_select_btn.setEnabled(has_exports)
            export_select_btn.clicked.connect(
                lambda checked, pc_id=pc.id: self._on_select_export(pc_id)
            )
            actions_layout.addWidget(export_select_btn)

            # Move up button
            move_up_btn = QPushButton("↑")
            move_up_btn.setFixedSize(40, 40)
            move_up_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            font_up = QFont()
            font_up.setPointSize(26)
            move_up_btn.setFont(font_up)
            move_up_btn.setStyleSheet(
                "QPushButton { padding: 0px; margin: 0px; border: none; text-align: center; padding-top: 0px; padding-bottom: 0px; }"
            )
            move_up_btn.setToolTip('<div style="font-size: 10px;">Move up</div>')
            move_up_btn.setEnabled(row > 0)
            move_up_btn.clicked.connect(lambda checked, pc_id=pc.id: self._move_track(pc_id, -1))
            actions_layout.addWidget(move_up_btn)

            # Move down button
            move_down_btn = QPushButton("↓")
            move_down_btn.setFixedSize(40, 40)
            move_down_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            font_down = QFont()
            font_down.setPointSize(26)
            move_down_btn.setFont(font_down)
            move_down_btn.setStyleSheet(
                "QPushButton { padding: 0px; margin: 0px; border: none; text-align: center; padding-top: 0px; padding-bottom: 0px; }"
            )
            move_down_btn.setToolTip('<div style="font-size: 10px;">Move down</div>')
            move_down_btn.setEnabled(row < len(pcs) - 1)
            move_down_btn.clicked.connect(lambda checked, pc_id=pc.id: self._move_track(pc_id, 1))
            actions_layout.addWidget(move_down_btn)

            # Artwork button
            artwork_btn = QPushButton("🖼️")
            artwork_btn.setFixedSize(40, 40)
            artwork_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            font_art = QFont()
            font_art.setPointSize(24)
            artwork_btn.setFont(font_art)
            artwork_btn.setStyleSheet(
                "QPushButton { padding: 0px; margin: 0px; border: none; text-align: center; padding-top: 0px; padding-bottom: 0px; }"
            )
            artwork_btn.setToolTip('<div style="font-size: 10px;">Set track artwork</div>')
            artwork_btn.clicked.connect(lambda checked, pc_id=pc.id: self._set_track_artwork(pc_id))
            actions_layout.addWidget(artwork_btn)

            # Remove button
            remove_btn = QPushButton("✕")
            remove_btn.setFixedSize(40, 40)
            remove_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            font_remove = QFont()
            font_remove.setPointSize(26)
            remove_btn.setFont(font_remove)
            remove_btn.setStyleSheet(
                "QPushButton { padding: 0px; margin: 0px; border: none; text-align: center; padding-top: 0px; padding-bottom: 0px; }"
            )
            remove_btn.setToolTip('<div style="font-size: 10px;">Remove from collection</div>')
            remove_btn.clicked.connect(lambda checked, pc_id=pc.id: self._remove_track(pc_id))
            actions_layout.addWidget(remove_btn)

            self.track_table.setCellWidget(row, 5, actions_widget)

        # Reconnect cellChanged
        self.track_table.cellChanged.connect(self._on_track_name_changed)

    def _on_track_double_click(self, row: int, col: int) -> None:
        """Handle track double click."""
        if col == 3:  # Project column (renamed from "Project File")
            item = self.track_table.item(row, 3)
            if item:
                project_id = item.data(Qt.ItemDataRole.UserRole)
                if project_id:
                    self.project_selected.emit(project_id)
        elif col == 2:  # Track name column - start editing
            self.track_table.editItem(self.track_table.item(row, 2))

    def _on_track_name_changed(self, row: int, col: int) -> None:
        """Handle track name edit."""
        if col == 2:  # Track name column
            item = self.track_table.item(row, 2)
            if item:
                pc_id = item.data(Qt.ItemDataRole.UserRole)
                new_name = item.text().strip()

                from ...database import ProjectCollection, get_session

                session = get_session()
                try:
                    pc = session.query(ProjectCollection).get(pc_id)
                    if pc:
                        # If user edits track name, clear export_id to use custom name
                        if new_name:
                            pc.track_name = new_name
                            pc.export_id = None  # Clear export selection when using custom name
                        else:
                            pc.track_name = None
                        session.commit()
                finally:
                    session.close()

    def _on_track_context_menu(self, pos) -> None:
        """Show context menu for track."""
        item = self.track_table.itemAt(pos)
        if not item:
            return

        row = item.row()
        pc_id_item = self.track_table.item(row, 0)
        if not pc_id_item:
            return

        pc_id = pc_id_item.data(Qt.ItemDataRole.UserRole)

        menu = QMenu(self)

        edit_name_action = menu.addAction("Edit Track Name")
        edit_name_action.triggered.connect(
            lambda: self.track_table.editItem(self.track_table.item(row, 2))
        )

        artwork_action = menu.addAction("Set Track Artwork...")
        artwork_action.triggered.connect(lambda: self._set_track_artwork(pc_id))

        remove_artwork_action = menu.addAction("Remove Track Artwork")
        remove_artwork_action.triggered.connect(lambda: self._remove_track_artwork(pc_id))

        menu.addSeparator()

        move_up_action = menu.addAction("Move Up")
        move_up_action.triggered.connect(lambda: self._move_track(pc_id, -1))
        move_up_action.setEnabled(row > 0)

        move_down_action = menu.addAction("Move Down")
        move_down_action.triggered.connect(lambda: self._move_track(pc_id, 1))
        move_down_action.setEnabled(row < self.track_table.rowCount() - 1)

        menu.addSeparator()

        remove_action = menu.addAction("Remove from Collection")
        remove_action.triggered.connect(lambda: self._remove_track(pc_id))

        menu.exec(self.track_table.viewport().mapToGlobal(pos))

    def _get_playable_path_for_track(self, pc: ProjectCollection) -> str | None:
        """Resolve the playable audio path for a track. Uses pc.export or most recent project export."""
        if not pc.project:
            return None
        if pc.export and Path(pc.export.export_path).exists():
            return pc.export.export_path
        exports = getattr(pc.project, "exports", None) or []
        if not exports:
            return None
        # Prefer most recent by export_date; fall back to first existing
        sorted_exports = sorted(
            exports,
            key=lambda e: (e.export_date is not None, e.export_date or datetime.min),
            reverse=True,
        )
        for exp in sorted_exports:
            if exp.export_path and Path(exp.export_path).exists():
                return exp.export_path
        return None

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

    def _get_play_button(self, row: int) -> QPushButton | None:
        """Get the play button for a row (first button in Actions cell)."""
        cell = self.track_table.cellWidget(row, 5)
        if cell:
            btn = cell.findChild(QPushButton)
            return btn if isinstance(btn, QPushButton) else None
        return None

    def _find_row_for_path(self, path: str) -> int | None:
        """Find table row containing the given file path (stored in play button property)."""
        for row in range(self.track_table.rowCount()):
            play_btn = self._get_play_button(row)
            if play_btn and play_btn.property("file_path") == path:
                return row
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
        """Update all play buttons to the given icon state."""
        icon = (
            QApplication.instance()
            .style()
            .standardIcon(
                QStyle.StandardPixmap.SP_MediaStop
                if is_playing
                else QStyle.StandardPixmap.SP_MediaPlay
            )
        )
        for row in range(self.track_table.rowCount()):
            play_btn = self._get_play_button(row)
            if play_btn:
                play_btn.setIcon(icon)

    def _on_playback_stopped(self) -> None:
        """Handle playback stopped - update play button."""
        if self._audio_player.current_file:
            self._update_play_button_for_path(self._audio_player.current_file, False)

    def _set_track_artwork(self, pc_id: int) -> None:
        """Set artwork for a track."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Track Artwork",
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.webp *.gif)",
        )
        if path:
            from ...database import ProjectCollection, get_session

            session = get_session()
            try:
                pc = session.query(ProjectCollection).get(pc_id)
                if pc:
                    pc.track_artwork_path = path
                    session.commit()
                    self._populate_tracks()  # Refresh to show new artwork
            finally:
                session.close()

    def _remove_track_artwork(self, pc_id: int) -> None:
        """Remove artwork from a track."""
        from ...database import ProjectCollection, get_session

        session = get_session()
        try:
            pc = session.query(ProjectCollection).get(pc_id)
            if pc:
                pc.track_artwork_path = None
                session.commit()
                self._populate_tracks()
        finally:
            session.close()

    def _move_track(self, pc_id: int, direction: int) -> None:
        """Move a track up or down in the collection."""
        # Refresh collection from database to ensure fresh data
        self._refresh_collection_from_db()

        if not self._collection:
            return

        from ...database import ProjectCollection, get_session

        session = get_session()
        try:
            # Query fresh data from database
            pc = session.query(ProjectCollection).get(pc_id)
            if not pc or pc.collection_id != self._collection.id:
                return

            # Get all tracks for this collection from database, sorted
            all_pcs = (
                session.query(ProjectCollection)
                .filter(ProjectCollection.collection_id == self._collection.id)
                .order_by(ProjectCollection.disc_number, ProjectCollection.track_number)
                .all()
            )

            # Sort by disc_number and track_number
            all_pcs = sorted(all_pcs, key=lambda x: (x.disc_number or 1, x.track_number or 999))

            current_index = next((i for i, p in enumerate(all_pcs) if p.id == pc_id), None)
            if current_index is None:
                return

            new_index = current_index + direction
            if new_index < 0 or new_index >= len(all_pcs):
                return

            # Swap track numbers
            other_pc = all_pcs[new_index]
            pc_track = pc.track_number or (current_index + 1)
            other_track = other_pc.track_number or (new_index + 1)

            pc.track_number = other_track
            other_pc.track_number = pc_track

            session.commit()

            # Refresh collection and repopulate table
            self._refresh_collection_from_db()
            self._populate_tracks()

        finally:
            session.close()

    def _on_select_export(self, pc_id: int) -> None:
        """Show menu to select which export to use for track name."""
        from ...database import Export, ProjectCollection, get_session

        session = get_session()
        try:
            pc = session.query(ProjectCollection).get(pc_id)
            if not pc or not pc.project:
                return

            # Get all exports for this project
            exports = (
                session.query(Export)
                .filter(Export.project_id == pc.project.id)
                .order_by(Export.export_date.desc())
                .all()
            )

            if not exports:
                return

            # Create menu
            menu = QMenu(self)

            # Option: Use custom name
            custom_action = menu.addAction("Use custom name")
            custom_action.triggered.connect(
                lambda: self._set_export_selection(pc_id, None, use_custom=True)
            )

            # Option: Use project name
            project_action = menu.addAction(f"Use project name: {pc.project.name}")
            project_action.triggered.connect(
                lambda: self._set_export_selection(pc_id, None, use_project=True)
            )

            # Option: Use export song name
            if pc.project.export_song_name:
                export_song_action = menu.addAction(
                    f"Use export song name: {pc.project.export_song_name}"
                )
                export_song_action.triggered.connect(
                    lambda: self._set_export_selection(pc_id, None, use_export_song=True)
                )

            if exports:
                menu.addSeparator()

                # List of exports
                for export in exports:
                    export_action = menu.addAction(f"Use export: {export.export_name}")
                    export_action.triggered.connect(
                        lambda checked, e_id=export.id: self._set_export_selection(pc_id, e_id)
                    )

            # Show menu at button position
            button = self.sender()
            if button:
                # Get the global position of the button
                global_pos = button.mapToGlobal(button.rect().bottomLeft())
                menu.exec(global_pos)
            else:
                # Fallback: show at cursor position
                from PyQt6.QtGui import QCursor

                menu.exec(QCursor.pos())

        finally:
            session.close()

    def _set_export_selection(
        self,
        pc_id: int,
        export_id: int | None,
        use_custom: bool = False,
        use_project: bool = False,
        use_export_song: bool = False,
    ) -> None:
        """Set the export selection for a track."""
        from ...database import ProjectCollection, get_session

        session = get_session()
        try:
            pc = session.query(ProjectCollection).get(pc_id)
            if not pc:
                return

            if use_custom:
                # Clear export_id, keep track_name if set
                pc.export_id = None
            elif use_project:
                # Clear export_id and track_name, use project.name
                pc.export_id = None
                pc.track_name = None
            elif use_export_song:
                # Clear export_id and track_name, use export_song_name
                pc.export_id = None
                pc.track_name = None
            else:
                # Set export_id
                pc.export_id = export_id
                # Optionally clear track_name to use export name
                pc.track_name = None

            session.commit()

            # Refresh collection and repopulate table
            self._refresh_collection_from_db()
            self._populate_tracks()

        finally:
            session.close()

    def _remove_track(self, pc_id: int) -> None:
        """Remove a track from the collection."""
        from ...database import ProjectCollection, get_session

        result = QMessageBox.question(
            self,
            "Remove Track",
            "Are you sure you want to remove this track from the collection?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if result == QMessageBox.StandardButton.Yes:
            session = get_session()
            try:
                pc = session.query(ProjectCollection).get(pc_id)
                if pc:
                    session.delete(pc)
                    session.commit()
                    # Refresh collection and repopulate table
                    self._refresh_collection_from_db()
                    self._populate_tracks()
            finally:
                session.close()

    def _on_edit(self) -> None:
        """Show edit collection dialog."""
        if self._collection:
            session = get_session()
            try:
                # Reload collection to check if it's smart
                collection = session.query(Collection).get(self._collection.id)
                if collection:
                    if collection.is_smart:
                        # Edit smart collection
                        from ..dialogs.smart_collection import SmartCollectionDialog

                        dialog = SmartCollectionDialog(self, collection_id=collection.id)
                    else:
                        # Edit regular collection
                        from ..dialogs.create_collection import CreateCollectionDialog

                        dialog = CreateCollectionDialog(self, collection_id=collection.id)

                    if dialog.exec():
                        self.set_collection(collection.id)
                        # Refresh parent view if available
                        if hasattr(self.parent(), "refresh"):
                            self.parent().refresh()
            finally:
                session.close()


class CollectionView(QWidget):
    """Main collection view with grid and detail views."""

    collection_selected = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._collections: list[Collection] = []
        self._cards: dict = {}

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the collection view UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Stack for grid vs detail view
        self.stack = QStackedWidget()

        # Grid view
        grid_widget = QWidget()
        grid_layout = QVBoxLayout(grid_widget)
        grid_layout.setContentsMargins(16, 16, 16, 16)
        grid_layout.setSpacing(16)

        # Header
        header = QHBoxLayout()

        title = QLabel("Collections")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        header.addWidget(title)

        header.addStretch()

        new_btn = QPushButton("+ New Collection")
        new_btn.setObjectName("primary")
        new_btn.clicked.connect(self._on_new_collection)
        header.addWidget(new_btn)

        grid_layout.addLayout(header)

        # Grid scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        scroll.setWidget(self.grid_container)
        grid_layout.addWidget(scroll)

        self.stack.addWidget(grid_widget)

        # Detail view
        self.detail_view = CollectionDetailView()
        self.detail_view.back_requested.connect(lambda: self.stack.setCurrentIndex(0))
        self.detail_view.project_selected.connect(self.collection_selected.emit)
        self.stack.addWidget(self.detail_view)

        layout.addWidget(self.stack)

    def set_collection(self, collection_id: int) -> None:
        """Switch to detail view and load a specific collection."""
        self.detail_view.set_collection(collection_id)
        self.stack.setCurrentIndex(1)  # Switch to detail view

    def refresh(self) -> None:
        """Refresh collections from database."""
        session = get_session()
        try:
            self._collections = (
                session.query(Collection)
                .options(joinedload(Collection.project_collections))
                .order_by(Collection.sort_order, Collection.name)
                .all()
            )
            self._populate_grid()
        finally:
            session.close()

    def _populate_grid(self) -> None:
        """Populate the grid with collection cards."""
        # Clear existing
        for card in self._cards.values():
            card.deleteLater()
        self._cards.clear()

        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add cards
        columns = 4
        for idx, coll in enumerate(self._collections):
            card = CollectionCard(coll)
            card.clicked.connect(self._on_collection_clicked)

            row = idx // columns
            col = idx % columns
            self.grid_layout.addWidget(card, row, col)
            self._cards[coll.id] = card

    def _on_collection_clicked(self, collection_id: int) -> None:
        """Handle collection card click."""
        self.detail_view.set_collection(collection_id)
        self.stack.setCurrentIndex(1)

    def _on_edit_collection(self, collection_id: int) -> None:
        """Edit a collection from context menu."""
        session = get_session()
        try:
            collection = session.query(Collection).get(collection_id)
            if collection:
                if collection.is_smart:
                    # Edit smart collection
                    from ..dialogs.smart_collection import SmartCollectionDialog

                    dialog = SmartCollectionDialog(self, collection_id=collection_id)
                else:
                    # Edit regular collection
                    from ..dialogs.create_collection import CreateCollectionDialog

                    dialog = CreateCollectionDialog(self, collection_id=collection_id)

                if dialog.exec():
                    self.refresh()
                    # If we're viewing this collection, refresh the detail view
                    if (
                        hasattr(self.detail_view, "_collection")
                        and self.detail_view._collection
                        and self.detail_view._collection.id == collection_id
                    ):
                        self.detail_view.set_collection(collection_id)
        finally:
            session.close()

    def _on_new_collection(self) -> None:
        """Show new collection dialog."""
        from ..dialogs.create_collection import CreateCollectionDialog

        dialog = CreateCollectionDialog(self)
        if dialog.exec():
            self.refresh()
