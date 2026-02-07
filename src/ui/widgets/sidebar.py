"""Sidebar navigation widget."""

import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QPoint, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QMouseEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...database import Collection, Location, Tag, get_session
from ...utils.logging import get_logger
from ..theme import AbletonTheme


class SidebarSection(QWidget):
    """Collapsible sidebar section."""

    header_clicked = pyqtSignal()
    context_menu_requested = pyqtSignal(QPoint)  # Position for context menu

    def __init__(
        self,
        title: str,
        parent: QWidget | None = None,
        clickable_header: bool = False,
        enable_context_menu: bool = False,
        start_collapsed: bool = False,
    ):
        super().__init__(parent)
        self._collapsed = start_collapsed
        self._clickable_header = clickable_header
        self._enable_context_menu = enable_context_menu

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        if clickable_header:
            header.setCursor(Qt.CursorShape.PointingHandCursor)
        if enable_context_menu:
            header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            header.customContextMenuRequested.connect(
                lambda pos: self.context_menu_requested.emit(header.mapToGlobal(pos))
            )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("secondary")
        font = self.title_label.font()
        font.setBold(True)
        if font.pointSize() > 0:
            font.setPointSize(10)
        else:
            font.setPixelSize(13)  # Fallback if point size is invalid
        self.title_label.setFont(font)
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        self.toggle_btn = QPushButton("▶" if start_collapsed else "▼")
        self.toggle_btn.setFixedSize(20, 20)
        self.toggle_btn.setFlat(True)
        self.toggle_btn.clicked.connect(self._toggle)
        header_layout.addWidget(self.toggle_btn)

        if clickable_header:
            # Make entire header clickable (except toggle button)
            def header_click(e):
                if e.button() == Qt.MouseButton.LeftButton:
                    self.header_clicked.emit()

            header.mousePressEvent = header_click

        layout.addWidget(header)

        # Content area
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 8)
        self.content_layout.setSpacing(2)
        self.content.setVisible(not start_collapsed)  # Set initial visibility
        layout.addWidget(self.content)

    def _toggle(self) -> None:
        """Toggle section collapsed state."""
        self._collapsed = not self._collapsed
        self.content.setVisible(not self._collapsed)
        self.toggle_btn.setText("▶" if self._collapsed else "▼")

    def add_item(self, widget: QWidget) -> None:
        """Add an item to the section content."""
        self.content_layout.addWidget(widget)


class SidebarItem(QPushButton):
    """Clickable sidebar item."""

    edit_requested = pyqtSignal(int)  # Item ID
    delete_requested = pyqtSignal(int)  # Item ID
    double_clicked = pyqtSignal()  # Double-click signal

    def __init__(
        self,
        text: str,
        icon: str = "",
        color: str | None = None,
        count: int | None = None,
        parent: QWidget | None = None,
        item_type: str = "default",
    ):
        super().__init__(parent)

        self.item_id: int | None = None
        self._selected = False
        self.item_type = item_type  # "collection", "location", "tag", "default"

        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda pos: self._on_context_menu(pos))

        # Build display text
        display = ""
        if icon:
            display += f"{icon} "
        display += text
        if count is not None:
            display += f"  ({count})"

        self.setText(display)
        self.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                padding: 8px 12px;
                border: none;
                border-radius: 6px;
                color: {AbletonTheme.COLORS['text_primary']};
            }}
            QPushButton:hover {{
                background-color: {AbletonTheme.COLORS['surface_hover']};
            }}
            QPushButton:checked {{
                background-color: {AbletonTheme.COLORS['accent']};
                color: {AbletonTheme.COLORS['text_on_accent']};
            }}
            QPushButton::tooltip {{
                background-color: {AbletonTheme.COLORS['background']};
                color: {AbletonTheme.COLORS['text_primary']};
                border: 1px solid {AbletonTheme.COLORS['border']};
                padding: 4px 8px;
            }}
        """)

        self.setCheckable(True)

        # Add color indicator if provided
        if color:
            self.setStyleSheet(self.styleSheet() + f"""
                QPushButton::before {{
                    content: '';
                    width: 4px;
                    height: 4px;
                    background-color: {color};
                    border-radius: 2px;
                }}
            """)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Handle double-click events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)

    def _on_context_menu(self, pos: QPoint) -> None:
        """Show context menu for item."""
        if self.item_type == "collection" and self.item_id:
            menu = QMenu(self)
            edit_action = menu.addAction("Edit Collection...")
            delete_action = menu.addAction("Delete Collection")

            action = menu.exec(self.mapToGlobal(pos))
            if action == edit_action:
                self.edit_requested.emit(self.item_id)
            elif action == delete_action:
                self.delete_requested.emit(self.item_id)
        elif self.item_type == "location" and self.item_id:
            menu = QMenu(self)
            remove_action = menu.addAction("Remove Location")

            action = menu.exec(self.mapToGlobal(pos))
            if action == remove_action:
                self.delete_requested.emit(self.item_id)


class Sidebar(QWidget):
    """Main sidebar with navigation and filters."""

    # Signals
    navigation_changed = pyqtSignal(str)  # View name
    location_selected = pyqtSignal(int)  # Location ID
    location_delete_requested = pyqtSignal(int)  # Location ID
    cleanup_orphaned_projects_requested = pyqtSignal()
    auto_detect_live_versions_requested = pyqtSignal()
    add_manual_installation_requested = pyqtSignal()
    set_favorite_installation_requested = pyqtSignal(int)  # Installation ID
    remove_installation_requested = pyqtSignal(
        int
    )  # Installation ID  # Request to clean up projects not in locations
    collection_selected = pyqtSignal(int)  # Collection ID
    collection_edit_requested = pyqtSignal(int)  # Collection ID
    collection_delete_requested = pyqtSignal(int)  # Collection ID
    tag_selected = pyqtSignal(int)  # Tag ID
    manage_tags_requested = pyqtSignal()  # Request to open tag management dialog

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.logger = get_logger(__name__)
        self._current_item: SidebarItem | None = None
        self._nav_items: dict = {}
        self._live_version_items: list = []
        self._location_items: list = []
        self._collection_items: list = []
        self._tag_items: list = []

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the sidebar UI."""
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {AbletonTheme.COLORS['background_alt']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(8, 12, 8, 12)
        content_layout.setSpacing(16)

        # Navigation section
        nav_section = SidebarSection("LIBRARY")

        all_projects = SidebarItem("All Projects", "📁")
        all_projects.clicked.connect(lambda: self._on_nav_click("projects"))
        self._nav_items["projects"] = all_projects
        nav_section.add_item(all_projects)

        recent = SidebarItem("Recent", "🕐")
        recent.clicked.connect(lambda: self._on_nav_click("recent"))
        self._nav_items["recent"] = recent
        nav_section.add_item(recent)

        similarities = SidebarItem("Similarities", "🔗")
        similarities.clicked.connect(lambda: self._on_nav_click("similarities"))
        self._nav_items["similarities"] = similarities
        nav_section.add_item(similarities)

        favorites = SidebarItem("Favorites", "💎")
        favorites.clicked.connect(lambda: self._on_nav_click("favorites"))
        self._nav_items["favorites"] = favorites
        nav_section.add_item(favorites)

        content_layout.addWidget(nav_section)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet(f"background-color: {AbletonTheme.COLORS['border']};")
        sep1.setFixedHeight(1)
        content_layout.addWidget(sep1)

        # Collections section
        self.collections_section = SidebarSection("COLLECTIONS", clickable_header=True)
        self.collections_section.header_clicked.connect(
            lambda: self.navigation_changed.emit("collections")
        )
        self.collections_container = QWidget()
        self.collections_layout = QVBoxLayout(self.collections_container)
        self.collections_layout.setContentsMargins(0, 0, 0, 0)
        self.collections_layout.setSpacing(2)
        self.collections_section.add_item(self.collections_container)

        # Add collection buttons
        add_collection_btn = SidebarItem("New Collection", "+")
        add_collection_btn.clicked.connect(lambda: self.navigation_changed.emit("new_collection"))
        self.collections_section.add_item(add_collection_btn)

        add_smart_btn = SidebarItem("New Smart Collection", "⚡")
        add_smart_btn.clicked.connect(lambda: self.navigation_changed.emit("new_smart_collection"))
        self.collections_section.add_item(add_smart_btn)

        content_layout.addWidget(self.collections_section)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"background-color: {AbletonTheme.COLORS['border']};")
        sep2.setFixedHeight(1)
        content_layout.addWidget(sep2)

        # Tags section
        self.tags_section = SidebarSection("TAGS", start_collapsed=True, enable_context_menu=True)
        self.tags_section.context_menu_requested.connect(self._on_tags_context_menu)
        self.tags_container = QWidget()
        self.tags_layout = QVBoxLayout(self.tags_container)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setSpacing(2)
        self.tags_section.add_item(self.tags_container)
        content_layout.addWidget(self.tags_section)

        # Separator
        sep_tags = QFrame()
        sep_tags.setFrameShape(QFrame.Shape.HLine)
        sep_tags.setStyleSheet(f"background-color: {AbletonTheme.COLORS['border']};")
        sep_tags.setFixedHeight(1)
        content_layout.addWidget(sep_tags)

        # Locations section
        self.locations_section = SidebarSection("LOCATIONS", enable_context_menu=True)
        self.locations_section.context_menu_requested.connect(self._on_locations_context_menu)
        self.locations_container = QWidget()
        self.locations_layout = QVBoxLayout(self.locations_container)
        self.locations_layout.setContentsMargins(0, 0, 0, 0)
        self.locations_layout.setSpacing(2)
        self.locations_section.add_item(self.locations_container)

        # Add location button
        add_location_btn = SidebarItem("Add Location", "+")
        add_location_btn.clicked.connect(lambda: self.navigation_changed.emit("locations"))
        self.locations_section.add_item(add_location_btn)

        content_layout.addWidget(self.locations_section)

        # Separator
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.HLine)
        sep3.setStyleSheet(f"background-color: {AbletonTheme.COLORS['border']};")
        sep3.setFixedHeight(1)
        content_layout.addWidget(sep3)

        # Ableton Live Installs section (moved above Learning)
        self.live_versions_section = SidebarSection("INSTALLS")
        self.live_versions_container = QWidget()
        self.live_versions_layout = QVBoxLayout(self.live_versions_container)
        self.live_versions_layout.setContentsMargins(0, 0, 0, 0)
        self.live_versions_layout.setSpacing(2)
        self.live_versions_section.add_item(self.live_versions_container)

        # Add button to manually add installation
        add_install_btn = SidebarItem("Add Installation", "+")
        add_install_btn.setCheckable(False)
        add_install_btn.setToolTip("Add a Live installation manually")
        add_install_btn.clicked.connect(lambda: self.add_manual_installation_requested.emit())
        self.live_versions_section.add_item(add_install_btn)

        self._live_version_items = []
        self._load_live_versions()
        content_layout.addWidget(self.live_versions_section)

        # Separator
        sep_live = QFrame()
        sep_live.setFrameShape(QFrame.Shape.HLine)
        sep_live.setStyleSheet(f"background-color: {AbletonTheme.COLORS['border']};")
        sep_live.setFixedHeight(1)
        content_layout.addWidget(sep_live)

        # Learning section
        learning_section = SidebarSection("LEARNING")

        # TODO: Built-in Lessons (hidden until paths and display are resolved)
        # lessons_sep = QLabel("Built-in Lessons:")
        # lessons_sep.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 10px; padding: 4px 12px;")
        # learning_section.add_item(lessons_sep)
        #
        # live_lessons = SidebarItem("Live Lessons", "📖")
        # live_lessons.setCheckable(False)
        # live_lessons.setToolTip("Open Ableton Live built-in lessons folder")
        # live_lessons.clicked.connect(self._open_live_lessons)
        # learning_section.add_item(live_lessons)
        #
        # lessons_toc = SidebarItem("Lessons Index", "📋")
        # lessons_toc.setCheckable(False)
        # lessons_toc.setToolTip("View Lessons Table of Contents")
        # lessons_toc.clicked.connect(self._open_lessons_toc)
        # learning_section.add_item(lessons_toc)

        # Getting Started
        getting_started_sep = QLabel("Getting Started:")
        getting_started_sep.setStyleSheet(
            f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 10px; padding: 4px 12px;"
        )
        learning_section.add_item(getting_started_sep)

        learning_music = SidebarItem("Learning Music", "🎵")
        learning_music.setCheckable(False)  # Don't toggle, just click
        learning_music.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://learningmusic.ableton.com/"))
        )
        learning_section.add_item(learning_music)

        making_music = SidebarItem("Making Music", "📝")
        making_music.setCheckable(False)  # Don't toggle, just click
        making_music.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://makingmusic.ableton.com/"))
        )
        learning_section.add_item(making_music)

        ableton_official = SidebarItem("Ableton.com", "🌐")
        ableton_official.setCheckable(False)  # Don't toggle, just click
        ableton_official.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://www.ableton.com"))
        )
        learning_section.add_item(ableton_official)

        ableton_help = SidebarItem("Ableton Help", "🛟")
        ableton_help.setCheckable(False)  # Don't toggle, just click
        ableton_help.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://www.ableton.com/en/help/"))
        )
        learning_section.add_item(ableton_help)

        learn_live = SidebarItem("Learn Live", "📚")
        learn_live.setCheckable(False)  # Don't toggle, just click
        learn_live.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://www.ableton.com/en/live/learn-live/"))
        )
        learning_section.add_item(learn_live)

        youtube_link = SidebarItem("Official YouTube", "▶️")
        youtube_link.setCheckable(False)  # Don't toggle, just click
        youtube_link.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://youtube.com/ableton"))
        )
        learning_section.add_item(youtube_link)

        # Community
        community_sep = QLabel("Community:")
        community_sep.setStyleSheet(
            f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 10px; padding: 4px 12px; margin-top: 8px;"
        )
        learning_section.add_item(community_sep)

        # Discord (moved to top)
        discord_link = SidebarItem("Ableton Discord", "💬")
        discord_link.setCheckable(False)  # Don't toggle, just click

        # Try to launch Discord app first, fallback to web
        def _launch_discord():
            # Try discord:// protocol first (launches Discord app)
            discord_url = QUrl("discord://discord.gg/ableton")
            if not QDesktopServices.openUrl(discord_url):
                # Fallback to web URL
                QDesktopServices.openUrl(QUrl("https://discord.gg/ableton"))

        discord_link.clicked.connect(_launch_discord)
        learning_section.add_item(discord_link)

        # Certified Trainers (moved to top)
        certified_trainers = SidebarItem("Certified Trainers", "🎓")
        certified_trainers.setCheckable(False)  # Don't toggle, just click
        certified_trainers.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://www.ableton.com/en/certified-training/"))
        )
        learning_section.add_item(certified_trainers)

        # User Groups
        user_groups = SidebarItem("Ableton User Groups", "👥")
        user_groups.setCheckable(False)  # Don't toggle, just click
        user_groups.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://www.ableton.com/en/community/user-groups")
            )
        )
        learning_section.add_item(user_groups)

        # Reference Documentation
        reference_sep = QLabel("Reference:")
        reference_sep.setStyleSheet(
            f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 10px; padding: 4px 12px; margin-top: 8px;"
        )
        learning_section.add_item(reference_sep)

        live12_ref = SidebarItem("Live Manual", "📖")
        live12_ref.setCheckable(False)  # Don't toggle, just click
        live12_ref.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://www.ableton.com/en/live-manual/12/"))
        )
        learning_section.add_item(live12_ref)

        move_manual = SidebarItem("Move Manual", "🎛️")
        move_manual.setCheckable(False)  # Don't toggle, just click
        move_manual.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://www.ableton.com/en/move/manual/"))
        )
        learning_section.add_item(move_manual)

        live_api = SidebarItem("Live API Overview", "📘")
        live_api.setCheckable(False)  # Don't toggle, just click
        live_api.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://docs.cycling74.com/legacy/max8/vignettes/live_api_overview")
            )
        )
        learning_section.add_item(live_api)

        lom_api = SidebarItem("Live Object Model", "🔧")
        lom_api.setCheckable(False)  # Don't toggle, just click
        lom_api.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://docs.cycling74.com/legacy/max8/vignettes/live_object_model")
            )
        )
        learning_section.add_item(lom_api)

        content_layout.addWidget(learning_section)

        # Separator
        sep_learning = QFrame()
        sep_learning.setFrameShape(QFrame.Shape.HLine)
        sep_learning.setStyleSheet(f"background-color: {AbletonTheme.COLORS['border']};")
        sep_learning.setFixedHeight(1)
        content_layout.addWidget(sep_learning)

        # Max for Live section
        max_for_live_section = SidebarSection("MAX for LIVE", start_collapsed=True)

        learn_max = SidebarItem("Learn Max", "📚")
        learn_max.setCheckable(False)  # Don't toggle, just click
        learn_max.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://cycling74.com/learn"))
        )
        max_for_live_section.add_item(learn_max)

        max_docs = SidebarItem("Max Documentation", "📖")
        max_docs.setCheckable(False)  # Don't toggle, just click
        max_docs.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://docs.cycling74.com/"))
        )
        max_for_live_section.add_item(max_docs)

        building_max_devices = SidebarItem("Building Max Devices", "🔨")
        building_max_devices.setCheckable(False)  # Don't toggle, just click
        building_max_devices.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://www.ableton.com/en/packs/building-max-devices/")
            )
        )
        max_for_live_section.add_item(building_max_devices)

        m4l_guidelines = SidebarItem("M4L Production Guidelines", "📋")
        m4l_guidelines.setCheckable(False)  # Don't toggle, just click
        m4l_guidelines.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl(
                    "https://github.com/Ableton/maxdevtools/blob/main/m4l-production-guidelines/m4l-production-guidelines.md"
                )
            )
        )
        max_for_live_section.add_item(m4l_guidelines)

        content_layout.addWidget(max_for_live_section)

        # Separator
        sep_max = QFrame()
        sep_max.setFrameShape(QFrame.Shape.HLine)
        sep_max.setStyleSheet(f"background-color: {AbletonTheme.COLORS['border']};")
        sep_max.setFixedHeight(1)
        content_layout.addWidget(sep_max)

        # Backups section
        backups_section = SidebarSection("BACKUPS", start_collapsed=True)

        self.backup_location_label = QLabel("No backup location set")
        self.backup_location_label.setStyleSheet(
            f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 10px; padding: 4px 12px;"
        )
        self.backup_location_label.setWordWrap(True)
        backups_section.add_item(self.backup_location_label)

        set_backup_btn = SidebarItem("Set Backup Location", "📁")
        set_backup_btn.setCheckable(False)
        set_backup_btn.setToolTip("Choose a folder for project backups")
        set_backup_btn.clicked.connect(self._on_set_backup_location)
        backups_section.add_item(set_backup_btn)

        open_backup_btn = SidebarItem("Open Backup Folder", "📂")
        open_backup_btn.setCheckable(False)
        open_backup_btn.setToolTip("Open the backup folder in file manager")
        open_backup_btn.clicked.connect(self._on_open_backup_folder)
        backups_section.add_item(open_backup_btn)

        content_layout.addWidget(backups_section)

        # Load backup location
        self._load_backup_location()

        # Separator
        sep_backups = QFrame()
        sep_backups.setFrameShape(QFrame.Shape.HLine)
        sep_backups.setStyleSheet(f"background-color: {AbletonTheme.COLORS['border']};")
        sep_backups.setFixedHeight(1)
        content_layout.addWidget(sep_backups)

        # MCP Servers section (Ableton MCP integrations)
        mcp_section = SidebarSection("MCP AGENTS", start_collapsed=True)

        mcp_intro = QLabel("AI Integration Tools:")
        mcp_intro.setStyleSheet(
            f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 10px; padding: 4px 12px;"
        )
        mcp_section.add_item(mcp_intro)

        # Producer Pal - AI-powered assistant for Ableton Live
        producer_pal = SidebarItem("Producer Pal", "🎹")
        producer_pal.setCheckable(False)
        producer_pal.setToolTip(
            "AI-powered assistant for music production. Control Ableton Live with words."
        )
        producer_pal.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://producer-pal.org/"))
        )
        mcp_section.add_item(producer_pal)

        ableton_mcp = SidebarItem("Ableton MCP", "🤖")
        ableton_mcp.setCheckable(False)
        ableton_mcp.setToolTip("Control Ableton Live via AI assistants (Claude, etc.)")
        ableton_mcp.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/ahujasid/ableton-mcp"))
        )
        mcp_section.add_item(ableton_mcp)

        live_api_mcp = SidebarItem("Live API MCP", "🔌")
        live_api_mcp.setCheckable(False)
        live_api_mcp.setToolTip("MCP server for Ableton Live API access")
        live_api_mcp.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://github.com/Simon-Kansara/ableton-live-mcp-server")
            )
        )
        mcp_section.add_item(live_api_mcp)

        mcp_docs = SidebarItem("MCP Documentation", "📖")
        mcp_docs.setCheckable(False)
        mcp_docs.setToolTip("Model Context Protocol documentation")
        mcp_docs.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://modelcontextprotocol.io/"))
        )
        mcp_section.add_item(mcp_docs)

        content_layout.addWidget(mcp_section)

        # Separator
        # Add stretch at bottom
        content_layout.addStretch()

        # Link section at bottom
        sep5 = QFrame()
        sep5.setFrameShape(QFrame.Shape.HLine)
        sep5.setStyleSheet(f"background-color: {AbletonTheme.COLORS['border']};")
        sep5.setFixedHeight(1)
        content_layout.addWidget(sep5)

        # Bottom links container (with consistent spacing)
        bottom_links_container = QWidget()
        bottom_links_layout = QVBoxLayout(bottom_links_container)
        bottom_links_layout.setContentsMargins(0, 0, 0, 0)
        bottom_links_layout.setSpacing(2)  # Match section spacing

        # Move.local link
        move_local_item = SidebarItem("Move.local", "🌐")
        move_local_item.setCheckable(False)
        move_local_item.setToolTip("Open http://move.local in browser")
        move_local_item.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("http://move.local")))
        bottom_links_layout.addWidget(move_local_item)

        link_item = SidebarItem("Ableton Link WiFi", "📡")
        link_item.clicked.connect(lambda: self._on_nav_click("link"))
        self._nav_items["link"] = link_item
        bottom_links_layout.addWidget(link_item)

        health_item = SidebarItem("Health Dashboard", "🏥")
        health_item.clicked.connect(lambda: self._on_nav_click("health"))
        self._nav_items["health"] = health_item
        bottom_links_layout.addWidget(health_item)

        content_layout.addWidget(bottom_links_container)

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _on_nav_click(self, view: str) -> None:
        """Handle navigation item click."""
        self._select_item(self._nav_items.get(view))
        self.navigation_changed.emit(view)

    def _on_location_click(self, location_id: int, item: SidebarItem) -> None:
        """Handle location item click."""
        self._select_item(item)
        self.location_selected.emit(location_id)

    def _on_collection_click(self, collection_id: int, item: SidebarItem) -> None:
        """Handle collection item click."""
        self._select_item(item)
        self.collection_selected.emit(collection_id)

    def _on_tag_click(self, tag_id: int, item: SidebarItem) -> None:
        """Handle tag item click."""
        self._select_item(item)
        self.tag_selected.emit(tag_id)

    def _select_item(self, item: SidebarItem | None) -> None:
        """Select a sidebar item."""
        # Deselect current (check if still valid)
        if self._current_item:
            try:
                # Check if widget still exists
                if hasattr(self._current_item, "setChecked"):
                    self._current_item.setChecked(False)
            except RuntimeError:
                # Widget was deleted, just clear the reference
                pass
            self._current_item = None

        # Select new
        self._current_item = item
        if item:
            try:
                item.setChecked(True)
            except RuntimeError:
                # Widget was deleted, clear reference
                self._current_item = None

    def clear_selection(self) -> None:
        """Clear the current selection."""
        self._select_item(None)

    def _on_locations_context_menu(self, pos: QPoint) -> None:
        """Show context menu for Locations section."""
        menu = QMenu(self)
        cleanup_action = menu.addAction("Remove Projects Not in Locations...")

        action = menu.exec(self.mapToGlobal(pos))
        if action == cleanup_action:
            self.cleanup_orphaned_projects_requested.emit()

    def _on_tags_context_menu(self, pos: QPoint) -> None:
        """Show context menu for Tags section."""
        menu = QMenu(self)
        manage_action = menu.addAction("Manage Tags...")

        action = menu.exec(pos)
        if action == manage_action:
            self.manage_tags_requested.emit()

    def refresh(self) -> None:
        """Refresh sidebar data from database."""
        # Clear current selection before refreshing
        self._current_item = None
        self._load_live_versions()
        self._load_locations()
        self._load_collections()
        self._load_tags()

    def _load_live_versions(self) -> None:
        """Load Ableton Live installations from database."""
        # Clear existing
        for item in self._live_version_items:
            if self._current_item == item:
                self._current_item = None
            item.deleteLater()
        self._live_version_items.clear()

        try:
            from ...database import LiveInstallation, get_session

            session = get_session()
            try:
                installations = (
                    session.query(LiveInstallation)
                    .order_by(LiveInstallation.is_favorite.desc(), LiveInstallation.version.desc())
                    .all()
                )

                if not installations:
                    # Show clickable message if no installations found
                    no_versions = SidebarItem("No Live installations - Click to Detect", "🔍")
                    no_versions.setToolTip(
                        "Click to auto-detect Live installations or add manually"
                    )
                    no_versions.clicked.connect(
                        lambda: self.auto_detect_live_versions_requested.emit()
                    )
                    self.live_versions_layout.addWidget(no_versions)
                    self._live_version_items.append(no_versions)
                    return

                for install in installations:
                    # Create display text
                    favorite_marker = "💎 " if install.is_favorite else ""
                    display_text = f"{favorite_marker}{install.name}"
                    icon = "🎧" if install.is_suite else "🎧"

                    item = SidebarItem(display_text, icon)
                    item.item_id = install.id
                    item.item_type = "live_install"
                    # Set tooltip with installation details
                    tooltip_text = (
                        f"Path: {install.executable_path}\n"
                        f"Version: {install.version}\n"
                        f"{'Favorite' if install.is_favorite else 'Not favorite'}\n"
                        f"Double-click to launch Live"
                    )
                    item.setToolTip(tooltip_text)
                    # Ensure tooltip is enabled (QPushButton should have this by default, but be explicit)
                    item.setToolTipDuration(0)  # 0 = show until mouse leaves
                    item.setCheckable(False)  # Don't allow single-click toggling

                    # Right-click context menu for each installation
                    item.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                    item.customContextMenuRequested.connect(
                        lambda pos, iid=install.id: self._on_install_item_context_menu(pos, iid)
                    )

                    # Double-click to launch Live (without a project)
                    item.double_clicked.connect(lambda v=install: self._launch_live_version(v))

                    self.live_versions_layout.addWidget(item)
                    self._live_version_items.append(item)
            finally:
                session.close()
        except Exception as e:
            self.logger.error(f"Failed to load Live installations: {e}", exc_info=True)
            error_item = SidebarItem("Error loading Live installations", "⚠️")
            error_item.setEnabled(False)
            self.live_versions_layout.addWidget(error_item)
            self._live_version_items.append(error_item)

    def _on_install_item_context_menu(self, pos: QPoint, install_id: int) -> None:
        """Show context menu for a Live installation item."""
        from PyQt6.QtGui import QCursor

        from ...database import LiveInstallation, get_session

        session = get_session()
        try:
            install = session.query(LiveInstallation).get(install_id)
            if not install:
                return

            menu = QMenu(self)

            if not install.is_favorite:
                favorite_action = menu.addAction("Set as Favorite")
                favorite_action.triggered.connect(
                    lambda: self.set_favorite_installation_requested.emit(install_id)
                )
            else:
                unfavorite_action = menu.addAction("Remove Favorite")
                unfavorite_action.triggered.connect(
                    lambda: self.set_favorite_installation_requested.emit(install_id)
                )

            menu.addSeparator()

            # Store version in local variable to ensure it's captured correctly
            # Validate that version is a valid string
            install_version = str(install.version) if install.version else None
            if not install_version or install_version.lower() in ("none", "false", ""):
                self.logger.error(
                    f"Invalid version for installation {install_id}: {install.version}"
                )
                # Try to extract version from name or path as fallback
                import re

                version_match = re.search(r"Live\s+(\d+(?:\.\d+)*(?:[a-zA-Z]+\d+)?)", install.name)
                if version_match:
                    install_version = version_match.group(1)
                    self.logger.info(f"Extracted version from name: {install_version}")
                else:
                    # Last resort: try to get from executable path
                    path_match = re.search(
                        r"Live\s+(\d+(?:\.\d+)*(?:[a-zA-Z]+\d+)?)", install.executable_path
                    )
                    if path_match:
                        install_version = path_match.group(1)
                        self.logger.info(f"Extracted version from path: {install_version}")

            # Release Notes link
            if install_version:
                version_parts = install_version.split(".")
                major_version = version_parts[0] if version_parts else "12"
                release_notes_action = menu.addAction("View Release Notes")
                release_notes_action.triggered.connect(
                    lambda: QDesktopServices.openUrl(
                        QUrl(f"https://www.ableton.com/en/release-notes/live-{major_version}/")
                    )
                )

            menu.addSeparator()

            # Open Preferences folder
            # Use the full version string from the database (should include major.minor.hotfix)
            prefs_action = menu.addAction("Open Preferences Folder")
            if install_version:
                # Capture version in closure properly
                version_str = install_version
                prefs_action.triggered.connect(
                    lambda checked=False, v=version_str: self._open_prefs_folder(v)
                )
            else:
                prefs_action.setEnabled(False)
                prefs_action.setToolTip("Version information not available")

            # View Live Log.txt
            # Use the full version string from the database (should include major.minor.hotfix)
            log_action = menu.addAction("View Live Log.txt")
            if install_version:
                # Capture version in closure properly
                version_str = install_version
                log_action.triggered.connect(
                    lambda checked=False, v=version_str: self._view_live_log(v)
                )
            else:
                log_action.setEnabled(False)
                log_action.setToolTip("Version information not available")

            # Edit Options.txt
            # Use the full version string from the database (should include major.minor.hotfix)
            options_action = menu.addAction("Edit Options.txt")
            if install_version:
                # Capture version in closure properly
                version_str = install_version
                options_action.triggered.connect(
                    lambda checked=False, v=version_str: self._edit_options_txt(v)
                )
            else:
                options_action.setEnabled(False)
                options_action.setToolTip("Version information not available")

            menu.addSeparator()
            remove_action = menu.addAction("Remove Installation")
            remove_action.triggered.connect(
                lambda: self.remove_installation_requested.emit(install_id)
            )

            # Use QCursor.pos() to get the actual global cursor position
            menu.exec(QCursor.pos())
        finally:
            session.close()

    def _get_prefs_folder(self, version: str) -> Path | None:
        """Get the preferences folder path for a Live version.

        Uses the full version string (major.minor.hotfix) including beta versions
        to correctly locate the Preferences folder.

        If only a major version is provided (e.g., "12"), attempts to find the
        actual preferences folder by scanning for folders matching "Live 12.*".

        Args:
            version: Full version string (e.g., "12.3.5", "11.3.13", "12.0.5b1")
                    or major version only (e.g., "12")

        Returns:
            Path to Preferences folder or None if version is invalid.
        """
        if not version:
            self.logger.warning("_get_prefs_folder called with empty version")
            return None

        # Convert to string and validate
        version_str = str(version).strip()

        # Check for invalid values
        if version_str.lower() in ("none", "false", "null", ""):
            self.logger.error(f"Invalid version string: '{version}' (converted to '{version_str}')")
            return None

        # Use the full version string as stored (e.g., "12.3.5", "11.3.13", "12.0.5b1")
        # Live's preferences folder uses the full version including hotfix
        version_clean = version_str

        # Check if version looks like only major version (e.g., "12" without dots)
        # If so, try to find the actual folder by scanning
        if "." not in version_clean and version_clean.isdigit():
            self.logger.warning(
                f"Version '{version_clean}' appears to be major version only. "
                f"Attempting to find actual preferences folder..."
            )
            # Try to find the actual preferences folder
            prefs_path = self._find_prefs_folder_by_major_version(version_clean)
            if prefs_path:
                return prefs_path
            # Fall through to use major version only as last resort

        if sys.platform == "win32":
            # Windows: %APPDATA%\Ableton\Live <full_version>\Preferences
            # Example: %APPDATA%\Ableton\Live 12.3.5\Preferences
            appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
            prefs_path = appdata / "Ableton" / f"Live {version_clean}" / "Preferences"
        elif sys.platform == "darwin":
            # macOS: ~/Library/Preferences/Ableton/Live <full_version>
            # Example: ~/Library/Preferences/Ableton/Live 12.3.5
            prefs_path = (
                Path.home() / "Library" / "Preferences" / "Ableton" / f"Live {version_clean}"
            )
        else:
            # Linux: ~/.ableton/Live <full_version>/Preferences (if using Wine)
            prefs_path = Path.home() / ".ableton" / f"Live {version_clean}" / "Preferences"

        return prefs_path

    def _find_prefs_folder_by_major_version(self, major_version: str) -> Path | None:
        """Try to find the preferences folder by scanning for folders matching the major version.

        Finds the most recent version folder (e.g., if major is "12", finds "Live 12.3.5"
        instead of "Live 12.2.5").

        Args:
            major_version: Major version number (e.g., "12")

        Returns:
            Path to Preferences folder (most recent version) or None if not found.
        """
        try:
            if sys.platform == "win32":
                appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
                ableton_folder = appdata / "Ableton"
            elif sys.platform == "darwin":
                ableton_folder = Path.home() / "Library" / "Preferences" / "Ableton"
            else:
                ableton_folder = Path.home() / ".ableton"

            if not ableton_folder.exists():
                return None

            # Look for folders matching "Live {major_version}.*"
            import re

            pattern = re.compile(rf"^Live\s+{re.escape(major_version)}\.")

            matching_folders = []
            for item in ableton_folder.iterdir():
                if item.is_dir() and pattern.match(item.name):
                    # Extract version number from folder name (e.g., "Live 12.3.5" -> "12.3.5")
                    version_match = re.search(
                        rf"{re.escape(major_version)}\.(\d+(?:\.\d+)*(?:[a-zA-Z]+\d+)?)", item.name
                    )
                    if version_match:
                        full_version = f"{major_version}.{version_match.group(1)}"
                        # Parse version for sorting
                        try:
                            version_parts = [int(x) for x in full_version.split(".")[:3]]
                            while len(version_parts) < 3:
                                version_parts.append(0)
                            matching_folders.append((tuple(version_parts), item))
                        except ValueError:
                            # If parsing fails, still add it but with low priority
                            matching_folders.append(((0, 0, 0), item))

            if not matching_folders:
                return None

            # Sort by version (most recent first) and get the latest
            matching_folders.sort(key=lambda x: x[0], reverse=True)
            latest_folder = matching_folders[0][1]

            # Check for Preferences subfolder
            prefs_path = latest_folder / "Preferences" if sys.platform == "win32" else latest_folder
            if prefs_path.exists():
                self.logger.info(
                    f"Found most recent preferences folder for major version {major_version}: {prefs_path} "
                    f"(from folder: {latest_folder.name})"
                )
                return prefs_path

            return None
        except Exception as e:
            self.logger.debug(f"Error scanning for preferences folder: {e}")
            return None

    def _open_prefs_folder(self, version: str) -> None:
        """Open the preferences folder for a Live version."""
        from PyQt6.QtWidgets import QMessageBox

        # Log the version being used for debugging
        self.logger.debug(f"Opening preferences folder for Live version: '{version}'")

        prefs_path = self._get_prefs_folder(version)

        # Log the constructed path
        self.logger.debug(f"Constructed preferences path: {prefs_path}")

        if not prefs_path or not prefs_path.exists():
            QMessageBox.warning(
                self,
                "Preferences Not Found",
                f"Could not find preferences folder for Live {version}.\n\n"
                f"Expected location:\n{prefs_path}\n\n"
                "The folder may not exist if Live hasn't been run yet.",
            )
            return

        try:
            if sys.platform == "win32":
                subprocess.run(["explorer", str(prefs_path)])
            elif sys.platform == "darwin":
                subprocess.run(["open", str(prefs_path)])
            else:
                subprocess.run(["xdg-open", str(prefs_path)])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open preferences folder:\n{str(e)}")

    def _view_live_log(self, version: str) -> None:
        """View Live's Log.txt file for a specific version."""
        from PyQt6.QtWidgets import QMessageBox

        # Log the version being used for debugging
        self.logger.debug(f"Viewing Live log for version: '{version}'")

        prefs_path = self._get_prefs_folder(version)

        # Log the constructed path
        self.logger.debug(f"Constructed preferences path: {prefs_path}")

        if not prefs_path:
            QMessageBox.warning(
                self, "Error", f"Could not determine preferences folder for Live {version}."
            )
            return

        log_path = prefs_path / "Log.txt"

        if not log_path.exists():
            QMessageBox.warning(
                self,
                "Log File Not Found",
                f"Log.txt not found for Live {version}.\n\n"
                f"Expected location:\n{log_path}\n\n"
                "The log file may not exist if Live hasn't been run yet or logging is disabled.",
            )
            return

        # Open log viewer dialog with the Live Log.txt file
        try:
            from ..dialogs.log_viewer_dialog import LogViewerDialog

            dialog = LogViewerDialog(self, log_file_path=log_path)
            # Center dialog on parent window
            if self.parent():
                parent_geometry = self.parent().geometry()
                dialog_geometry = dialog.geometry()
                x = parent_geometry.x() + (parent_geometry.width() - dialog_geometry.width()) // 2
                y = parent_geometry.y() + (parent_geometry.height() - dialog_geometry.height()) // 2
                dialog.move(x, y)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open log viewer:\n{str(e)}")

    def _edit_options_txt(self, version: str) -> None:
        """Edit or create Options.txt for a Live version."""
        from PyQt6.QtWidgets import QMessageBox

        prefs_path = self._get_prefs_folder(version)

        if not prefs_path:
            QMessageBox.warning(
                self, "Error", f"Could not determine preferences folder for Live {version}."
            )
            return

        options_path = prefs_path / "Options.txt"

        # Create prefs folder if it doesn't exist
        if not prefs_path.exists():
            reply = QMessageBox.question(
                self,
                "Create Preferences Folder",
                f"The preferences folder doesn't exist:\n{prefs_path}\n\n"
                "Would you like to create it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    prefs_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    QMessageBox.critical(
                        self, "Error", f"Failed to create preferences folder:\n{str(e)}"
                    )
                    return
            else:
                return

        # Create Options.txt if it doesn't exist
        if not options_path.exists():
            reply = QMessageBox.question(
                self,
                "Create Options.txt",
                f"Options.txt doesn't exist at:\n{options_path}\n\n"
                "Would you like to create it with common options?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    # Create with common options as comments
                    default_content = """# Ableton Live Options.txt
# Uncomment options by removing the # at the start of the line
# See: https://help.ableton.com/hc/en-us/articles/209772865-Options-txt-file

# Enable high-resolution waveforms
# -EnableHighResolutionWaveforms

# Disable splash screen
# -NoSplash

# Enable ASIO4ALL on Windows
# -_EnableAsio4All

# Set maximum audio buffer size
# -MaxAudioBufferSize=2048

# Enable APC40 MkII emulation mode
# -_APC40MkIIEmulationMode

# Enable Push 2 display mirroring
# -EnablePush2DisplayMirroring

# Disable GPU acceleration
# -DisableGPUAcceleration

# Enable legacy browser database
# -EnableLegacyBrowserDatabase
"""
                    options_path.write_text(default_content, encoding="utf-8")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to create Options.txt:\n{str(e)}")
                    return

        # Open Options.txt in default text editor
        try:
            if sys.platform == "win32":
                os.startfile(str(options_path))
            elif sys.platform == "darwin":
                subprocess.run(["open", "-t", str(options_path)])
            else:
                subprocess.run(["xdg-open", str(options_path)])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open Options.txt:\n{str(e)}")

    def _launch_live_version(self, install) -> None:
        """Launch a specific Live installation."""
        try:
            from pathlib import Path

            exe_path = Path(install.executable_path)
            if not exe_path.exists():
                from PyQt6.QtWidgets import QMessageBox

                QMessageBox.warning(
                    self,
                    "Installation Not Found",
                    f"The Live installation at:\n{exe_path}\n\ncould not be found.\n\nPlease remove and re-add this installation.",
                )
                return

            # Launch Live without a project (just open Live)
            if sys.platform == "win32":
                subprocess.Popen([str(exe_path)], cwd=exe_path.parent)
            elif sys.platform == "darwin":
                # On macOS, launch the .app bundle
                app_path = exe_path.parent.parent.parent  # Go up from MacOS/Live to .app
                subprocess.Popen(["open", str(app_path)])
            else:
                subprocess.Popen([str(exe_path)], cwd=exe_path.parent)
            self.logger.info(f"Launched {install.name}")
        except Exception as e:
            self.logger.error(f"Failed to launch {install.name}: {e}", exc_info=True)

    # === Resource Path Helper ===

    def _get_live_resources_path(self) -> Path | None:
        """Get the Resources path from the most recent Live installation."""
        from ...database import LiveInstallation, get_session

        session = get_session()
        try:
            # Get the most recent (favorite or first) installation
            install = (
                session.query(LiveInstallation).filter(LiveInstallation.is_favorite == True).first()
            )

            if not install:
                install = session.query(LiveInstallation).first()

            if not install:
                return None

            exe_path = Path(install.executable_path)

            # Navigate to Resources folder
            # Windows: C:\ProgramData\Ableton\Live XX\Resources
            # macOS: /Applications/Ableton Live XX.app/Contents/App-Resources
            if sys.platform == "win32":
                # Try ProgramData location first
                version_parts = install.version.split(".")
                major = version_parts[0] if version_parts else "12"
                program_data = Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData"))
                resources = program_data / "Ableton" / f"Live {major}" / "Resources"
                if resources.exists():
                    return resources
                # Fallback to installation directory
                resources = exe_path.parent / "Resources"
            elif sys.platform == "darwin":
                resources = exe_path.parent.parent / "App-Resources"
            else:
                resources = exe_path.parent / "Resources"

            return resources if resources.exists() else None
        finally:
            session.close()

    # === Lessons Methods ===

    def _open_live_lessons(self) -> None:
        """Open the Ableton Live built-in lessons folder."""
        from PyQt6.QtWidgets import QMessageBox

        resources = self._get_live_resources_path()
        if resources:
            lessons = resources / "Lessons"
            if lessons.exists():
                try:
                    if sys.platform == "win32":
                        subprocess.run(["explorer", str(lessons)])
                    elif sys.platform == "darwin":
                        subprocess.run(["open", str(lessons)])
                    else:
                        subprocess.run(["xdg-open", str(lessons)])
                    return
                except Exception:
                    pass

        QMessageBox.information(
            self,
            "Lessons Not Found",
            "Could not find the Ableton Live lessons folder.\n\n"
            "Lessons are located in:\n"
            "Windows: C:\\ProgramData\\Ableton\\Live XX\\Resources\\Lessons\n"
            "macOS: /Applications/Ableton Live XX.app/Contents/App-Resources/Lessons\n\n"
            "Make sure you have at least one Live installation registered.",
        )

    def _open_lessons_toc(self) -> None:
        """Open the lessons table of contents / index."""

        resources = self._get_live_resources_path()
        if resources:
            lessons = resources / "Lessons"
            # Look for an index file
            index_files = [
                lessons / "TOC.txt",
                lessons / "index.html",
                lessons / "Contents.txt",
                lessons / "Lessons.txt",
            ]
            for index_file in index_files:
                if index_file.exists():
                    try:
                        if sys.platform == "win32":
                            os.startfile(str(index_file))
                        elif sys.platform == "darwin":
                            subprocess.run(["open", str(index_file)])
                        else:
                            subprocess.run(["xdg-open", str(index_file)])
                        return
                    except Exception:
                        pass

            # If no index found, just open the lessons folder
            if lessons.exists():
                try:
                    if sys.platform == "win32":
                        subprocess.run(["explorer", str(lessons)])
                    elif sys.platform == "darwin":
                        subprocess.run(["open", str(lessons)])
                    else:
                        subprocess.run(["xdg-open", str(lessons)])
                    return
                except Exception:
                    pass

        # Fallback to online lessons
        QDesktopServices.openUrl(QUrl("https://www.ableton.com/en/live/learn-live/"))

    def _load_locations(self) -> None:
        """Load locations from database."""
        # Clear existing
        for item in self._location_items:
            # Clear current item if it's being deleted
            if self._current_item == item:
                self._current_item = None
            item.deleteLater()
        self._location_items.clear()

        session = get_session()
        try:
            locations = (
                session.query(Location)
                .filter(Location.is_active == True)
                .order_by(Location.sort_order, Location.name)
                .all()
            )

            for loc in locations:
                # Choose icon based on type
                icon_map = {
                    "local": "📁",
                    "network": "🌐",
                    "dropbox": "☁️",
                    "cloud": "☁️",
                    "usb": "💾",
                    "collab": "👥",
                }
                icon = icon_map.get(loc.location_type.value, "📁")

                # Count projects
                project_count = len(loc.projects)

                item = SidebarItem(loc.name, icon, loc.color, project_count, item_type="location")
                item.item_id = loc.id
                item.clicked.connect(
                    lambda checked, lid=loc.id, i=item: self._on_location_click(lid, i)
                )
                item.delete_requested.connect(
                    lambda lid=loc.id: self.location_delete_requested.emit(lid)
                )

                self.locations_layout.addWidget(item)
                self._location_items.append(item)
        finally:
            session.close()

    def _load_collections(self) -> None:
        """Load collections from database."""
        # Clear existing
        for item in self._collection_items:
            # Clear current item if it's being deleted
            if self._current_item == item:
                self._current_item = None
            item.deleteLater()
        self._collection_items.clear()

        session = get_session()
        try:
            collections = (
                session.query(Collection).order_by(Collection.sort_order, Collection.name).all()
            )

            for coll in collections:
                # Choose icon based on type and smart status
                if coll.is_smart:
                    icon = "⚡"  # Smart collection icon
                else:
                    icon_map = {
                        "album": "💿",
                        "ep": "📀",
                        "single": "🎵",
                        "compilation": "📚",
                        "session": "🎤",
                        "client": "💼",
                        "custom": "📁",
                    }
                    icon = icon_map.get(coll.collection_type.value, "📁")

                # Count projects (for smart collections, show dynamic count)
                if coll.is_smart:
                    from ...services.smart_collections import SmartCollectionService

                    matching_ids = SmartCollectionService.evaluate_smart_collection(coll.id)
                    project_count = len(matching_ids) + len(coll.project_collections)
                else:
                    project_count = len(coll.project_collections)

                item = SidebarItem(
                    coll.name, icon, coll.color, project_count, item_type="collection"
                )
                item.item_id = coll.id
                item.clicked.connect(
                    lambda checked, cid=coll.id, i=item: self._on_collection_click(cid, i)
                )
                item.edit_requested.connect(self.collection_edit_requested.emit)
                item.delete_requested.connect(self.collection_delete_requested.emit)

                self.collections_layout.addWidget(item)
                self._collection_items.append(item)
        finally:
            session.close()

    def _load_tags(self) -> None:
        """Load tags from database."""
        # Clear existing
        for item in self._tag_items:
            # Clear current item if it's being deleted
            if self._current_item == item:
                self._current_item = None
            item.deleteLater()
        self._tag_items.clear()

        session = get_session()
        try:
            tags = session.query(Tag).order_by(Tag.category, Tag.name).all()

            for tag in tags:
                item = SidebarItem(tag.name, "●", tag.color)
                item.item_id = tag.id
                item.clicked.connect(lambda checked, tid=tag.id, i=item: self._on_tag_click(tid, i))

                self.tags_layout.addWidget(item)
                self._tag_items.append(item)
        finally:
            session.close()

    def _load_backup_location(self) -> None:
        """Load and display the backup location from settings."""
        from ...database import AppSettings, get_session

        session = get_session()
        try:
            backup_path = AppSettings.get_value(session, "backup_location", None)
            if backup_path and Path(backup_path).exists():
                # Truncate long paths
                display_path = backup_path
                if len(display_path) > 40:
                    display_path = "..." + display_path[-37:]
                self.backup_location_label.setText(f"📍 {display_path}")
                self.backup_location_label.setToolTip(backup_path)
            else:
                self.backup_location_label.setText("No backup location set")
                self.backup_location_label.setToolTip("Click 'Set Backup Location' to configure")
        finally:
            session.close()

    def _on_set_backup_location(self) -> None:
        """Show dialog to set backup location."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox

        from ...database import AppSettings, get_session

        # Get current backup location
        session = get_session()
        try:
            current_path = AppSettings.get_value(session, "backup_location", "")
        finally:
            session.close()

        # Show folder picker
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Backup Location",
            current_path or str(Path.home()),
            QFileDialog.Option.ShowDirsOnly,
        )

        if folder:
            # Verify folder is writable
            test_file = Path(folder) / ".ableton_hub_test"
            try:
                test_file.touch()
                test_file.unlink()
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Invalid Location",
                    f"Cannot write to the selected folder:\n{folder}\n\n"
                    f"Error: {str(e)}\n\n"
                    "Please choose a different location.",
                )
                return

            # Save to settings
            session = get_session()
            try:
                AppSettings.set_value(
                    session, "backup_location", folder, description="Location for project backups"
                )

                # Update display
                self._load_backup_location()

                QMessageBox.information(
                    self, "Backup Location Set", f"Backup location has been set to:\n{folder}"
                )
            finally:
                session.close()

    def _on_open_backup_folder(self) -> None:
        """Open the backup folder in file manager."""
        from PyQt6.QtWidgets import QMessageBox

        from ...database import AppSettings, get_session

        session = get_session()
        try:
            backup_path = AppSettings.get_value(session, "backup_location", None)
        finally:
            session.close()

        if not backup_path:
            QMessageBox.information(
                self,
                "No Backup Location",
                "No backup location has been set.\n\n"
                "Click 'Set Backup Location' to configure one.",
            )
            return

        path = Path(backup_path)
        if not path.exists():
            reply = QMessageBox.question(
                self,
                "Folder Not Found",
                f"The backup folder doesn't exist:\n{backup_path}\n\n"
                "Would you like to create it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    QMessageBox.critical(
                        self, "Error", f"Failed to create backup folder:\n{str(e)}"
                    )
                    return
            else:
                return

        try:
            if sys.platform == "win32":
                subprocess.run(["explorer", str(path)])
            elif sys.platform == "darwin":
                subprocess.run(["open", str(path)])
            else:
                subprocess.run(["xdg-open", str(path)])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open backup folder:\n{str(e)}")
