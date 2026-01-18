"""Sidebar navigation widget."""

import os
from typing import Optional
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTreeWidget, QTreeWidgetItem, QSizePolicy, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QUrl
from PyQt6.QtGui import QFont, QPixmap, QDesktopServices

from ...database import get_session, Location, Collection, Tag
from ..theme import AbletonTheme


class SidebarSection(QWidget):
    """Collapsible sidebar section."""
    
    header_clicked = pyqtSignal()
    context_menu_requested = pyqtSignal(QPoint)  # Position for context menu
    
    def __init__(self, title: str, parent: Optional[QWidget] = None, clickable_header: bool = False, 
                 enable_context_menu: bool = False):
        super().__init__(parent)
        self._collapsed = False
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
        
        self.toggle_btn = QPushButton("▼")
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
    
    def __init__(self, text: str, icon: str = "", color: Optional[str] = None,
                 count: Optional[int] = None, parent: Optional[QWidget] = None,
                 item_type: str = "default"):
        super().__init__(parent)
        
        self.item_id: Optional[int] = None
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
    location_selected = pyqtSignal(int)   # Location ID
    location_delete_requested = pyqtSignal(int)  # Location ID
    cleanup_orphaned_projects_requested = pyqtSignal()
    auto_detect_live_versions_requested = pyqtSignal()
    add_manual_installation_requested = pyqtSignal()
    set_favorite_installation_requested = pyqtSignal(int)  # Installation ID
    remove_installation_requested = pyqtSignal(int)  # Installation ID  # Request to clean up projects not in locations
    collection_selected = pyqtSignal(int) # Collection ID
    collection_edit_requested = pyqtSignal(int)  # Collection ID
    collection_delete_requested = pyqtSignal(int)  # Collection ID
    tag_selected = pyqtSignal(int)        # Tag ID
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._current_item: Optional[SidebarItem] = None
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
        
        favorites = SidebarItem("Favorites", "⭐")
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
        self.collections_section.header_clicked.connect(lambda: self.navigation_changed.emit("collections"))
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
        self.tags_section = SidebarSection("TAGS")
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
        
        # Backups section
        backups_section = SidebarSection("BACKUPS")
        
        self.backup_location_label = QLabel("No backup location set")
        self.backup_location_label.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 10px; padding: 4px 12px;")
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
        
        # Ableton Live Installs section
        self.live_versions_section = SidebarSection("INSTALLS")
        self.live_versions_container = QWidget()
        self.live_versions_layout = QVBoxLayout(self.live_versions_container)
        self.live_versions_layout.setContentsMargins(0, 0, 0, 0)
        self.live_versions_layout.setSpacing(2)
        self.live_versions_section.add_item(self.live_versions_container)
        self._live_version_items = []
        self._load_live_versions()
        content_layout.addWidget(self.live_versions_section)
        
        # Separator
        sep_live = QFrame()
        sep_live.setFrameShape(QFrame.Shape.HLine)
        sep_live.setStyleSheet(f"background-color: {AbletonTheme.COLORS['border']};")
        sep_live.setFixedHeight(1)
        content_layout.addWidget(sep_live)
        
        # Packs section
        self.packs_section = SidebarSection("PACKS")
        
        # Pack location info
        packs_intro = QLabel("Ableton Packs:")
        packs_intro.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 10px; padding: 4px 12px;")
        self.packs_section.add_item(packs_intro)
        
        # Core Library
        core_library = SidebarItem("Core Library", "📦")
        core_library.setCheckable(False)
        core_library.setToolTip("Open Ableton Core Library folder")
        core_library.clicked.connect(self._open_core_library)
        self.packs_section.add_item(core_library)
        
        # User Library / Packs
        user_packs = SidebarItem("User Library", "📁")
        user_packs.setCheckable(False)
        user_packs.setToolTip("Open User Library folder")
        user_packs.clicked.connect(self._open_user_library)
        self.packs_section.add_item(user_packs)
        
        # Factory Packs location
        factory_packs = SidebarItem("Factory Packs", "🎹")
        factory_packs.setCheckable(False)
        factory_packs.setToolTip("Browse installed Factory Packs")
        factory_packs.clicked.connect(self._open_factory_packs)
        self.packs_section.add_item(factory_packs)
        
        # Ableton Packs Store
        packs_store = SidebarItem("Pack Store", "🛒")
        packs_store.setCheckable(False)
        packs_store.setToolTip("Browse Ableton Packs in store")
        packs_store.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.ableton.com/en/packs/")))
        self.packs_section.add_item(packs_store)
        
        content_layout.addWidget(self.packs_section)
        
        # Separator
        sep_packs = QFrame()
        sep_packs.setFrameShape(QFrame.Shape.HLine)
        sep_packs.setStyleSheet(f"background-color: {AbletonTheme.COLORS['border']};")
        sep_packs.setFixedHeight(1)
        content_layout.addWidget(sep_packs)
        
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
        getting_started_sep.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 10px; padding: 4px 12px;")
        learning_section.add_item(getting_started_sep)
        
        learning_music = SidebarItem("Learning Music", "🎵")
        learning_music.setCheckable(False)  # Don't toggle, just click
        learning_music.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://learningmusic.ableton.com/")))
        learning_section.add_item(learning_music)
        
        ableton_official = SidebarItem("Ableton.com", "🌐")
        ableton_official.setCheckable(False)  # Don't toggle, just click
        ableton_official.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.ableton.com")))
        learning_section.add_item(ableton_official)
        
        learn_live = SidebarItem("Learn Live", "📚")
        learn_live.setCheckable(False)  # Don't toggle, just click
        learn_live.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.ableton.com/en/live/learn-live/")))
        learning_section.add_item(learn_live)
        
        youtube_link = SidebarItem("Official YouTube", "▶️")
        youtube_link.setCheckable(False)  # Don't toggle, just click
        youtube_link.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://youtube.com/ableton")))
        learning_section.add_item(youtube_link)
        
        # Reference Documentation
        reference_sep = QLabel("Reference:")
        reference_sep.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 10px; padding: 4px 12px; margin-top: 8px;")
        learning_section.add_item(reference_sep)
        
        live12_ref = SidebarItem("Live 12 Reference", "📖")
        live12_ref.setCheckable(False)  # Don't toggle, just click
        live12_ref.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.ableton.com/en/live-manual/12/")))
        learning_section.add_item(live12_ref)
        
        live_api = SidebarItem("Live API Overview", "📘")
        live_api.setCheckable(False)  # Don't toggle, just click
        live_api.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://docs.cycling74.com/legacy/max8/vignettes/live_api_overview")))
        learning_section.add_item(live_api)
        
        lom_api = SidebarItem("LOM API Reference", "🔧")
        lom_api.setCheckable(False)  # Don't toggle, just click
        lom_api.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://docs.cycling74.com/legacy/max8/vignettes/live_object_model")))
        learning_section.add_item(lom_api)
        
        # Training
        training_sep = QLabel("Training:")
        training_sep.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 10px; padding: 4px 12px; margin-top: 8px;")
        learning_section.add_item(training_sep)
        
        certified_trainers = SidebarItem("Certified Trainers", "🎓")
        certified_trainers.setCheckable(False)  # Don't toggle, just click
        certified_trainers.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.ableton.com/en/certified-training/")))
        learning_section.add_item(certified_trainers)
        
        # User Groups
        user_groups_sep = QLabel("User Groups:")
        user_groups_sep.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 10px; padding: 4px 12px;")
        learning_section.add_item(user_groups_sep)
        
        austin_group = SidebarItem("Austin User Group", "🤠")
        austin_group.setCheckable(False)  # Don't toggle, just click
        austin_group.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.facebook.com/groups/abletonATX")))
        learning_section.add_item(austin_group)
        
        chicago_group = SidebarItem("Chicago User Group", "🏙️")
        chicago_group.setCheckable(False)  # Don't toggle, just click
        chicago_group.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.facebook.com/groups/chicagoableton")))
        learning_section.add_item(chicago_group)
        
        sf_group = SidebarItem("San Francisco User Group", "🌉")
        sf_group.setCheckable(False)  # Don't toggle, just click
        sf_group.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.facebook.com/groups/sfableton")))
        learning_section.add_item(sf_group)
        
        # Discord
        discord_sep = QLabel("Community:")
        discord_sep.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 10px; padding: 4px 12px; margin-top: 8px;")
        learning_section.add_item(discord_sep)
        
        discord_link = SidebarItem("Ableton Discord", "💬")
        discord_link.setCheckable(False)  # Don't toggle, just click
        # Try to launch Discord app first, fallback to web
        def _launch_discord():
            import subprocess
            import sys
            # Try discord:// protocol first (launches Discord app)
            discord_url = QUrl("discord://discord.gg/ableton")
            if not QDesktopServices.openUrl(discord_url):
                # Fallback to web URL
                QDesktopServices.openUrl(QUrl("https://discord.gg/ableton"))
        discord_link.clicked.connect(_launch_discord)
        learning_section.add_item(discord_link)
        
        content_layout.addWidget(learning_section)
        
        # Separator
        sep_mcp = QFrame()
        sep_mcp.setFrameShape(QFrame.Shape.HLine)
        sep_mcp.setStyleSheet(f"background-color: {AbletonTheme.COLORS['border']};")
        sep_mcp.setFixedHeight(1)
        content_layout.addWidget(sep_mcp)
        
        # MCP Servers section (Ableton MCP integrations)
        mcp_section = SidebarSection("MCP SERVERS")
        
        mcp_intro = QLabel("AI Integration Tools:")
        mcp_intro.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']}; font-size: 10px; padding: 4px 12px;")
        mcp_section.add_item(mcp_intro)
        
        # Producer Pal - AI-powered assistant for Ableton Live
        producer_pal = SidebarItem("Producer Pal", "🎹")
        producer_pal.setCheckable(False)
        producer_pal.setToolTip("AI-powered assistant for music production. Control Ableton Live with words.")
        producer_pal.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://producer-pal.org/")))
        mcp_section.add_item(producer_pal)
        
        ableton_mcp = SidebarItem("Ableton MCP", "🤖")
        ableton_mcp.setCheckable(False)
        ableton_mcp.setToolTip("Control Ableton Live via AI assistants (Claude, etc.)")
        ableton_mcp.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/ahujasid/ableton-mcp")))
        mcp_section.add_item(ableton_mcp)
        
        live_api_mcp = SidebarItem("Live API MCP", "🔌")
        live_api_mcp.setCheckable(False)
        live_api_mcp.setToolTip("MCP server for Ableton Live API access")
        live_api_mcp.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/Simon-Kansara/ableton-live-mcp")))
        mcp_section.add_item(live_api_mcp)
        
        mcp_docs = SidebarItem("MCP Documentation", "📖")
        mcp_docs.setCheckable(False)
        mcp_docs.setToolTip("Model Context Protocol documentation")
        mcp_docs.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://modelcontextprotocol.io/")))
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
        
        link_item = SidebarItem("Link Network", "📡")
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
    
    def _select_item(self, item: Optional[SidebarItem]) -> None:
        """Select a sidebar item."""
        # Deselect current (check if still valid)
        if self._current_item:
            try:
                # Check if widget still exists
                if hasattr(self._current_item, 'setChecked'):
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
            from ...database import get_session, LiveInstallation
            session = get_session()
            try:
                installations = session.query(LiveInstallation).order_by(
                    LiveInstallation.is_favorite.desc(),
                    LiveInstallation.version.desc()
                ).all()
                
                if not installations:
                    # Show clickable message if no installations found
                    no_versions = SidebarItem("No Live installations - Click to Detect", "🔍")
                    no_versions.setToolTip("Click to auto-detect Live installations or add manually")
                    no_versions.clicked.connect(
                        lambda: self.auto_detect_live_versions_requested.emit()
                    )
                    self.live_versions_layout.addWidget(no_versions)
                    self._live_version_items.append(no_versions)
                    return
                
                for install in installations:
                    # Create display text
                    favorite_marker = "⭐ " if install.is_favorite else ""
                    display_text = f"{favorite_marker}{install.name}"
                    icon = "🎵" if install.is_suite else "🎶"
                    
                    item = SidebarItem(display_text, icon)
                    item.item_id = install.id
                    item.item_type = "live_install"
                    item.setToolTip(f"Path: {install.executable_path}\nVersion: {install.version}\n{'Favorite' if install.is_favorite else 'Not favorite'}")
                    
                    # Right-click context menu for each installation
                    item.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                    item.customContextMenuRequested.connect(
                        lambda pos, iid=install.id: self._on_install_item_context_menu(pos, iid)
                    )
                    
                    # Click to launch Live (without a project)
                    item.clicked.connect(
                        lambda checked, v=install: self._launch_live_version(v)
                    )
                    
                    self.live_versions_layout.addWidget(item)
                    self._live_version_items.append(item)
            finally:
                session.close()
        except Exception as e:
            print(f"[SIDEBAR] ERROR: Failed to load Live installations: {e}")
            import traceback
            traceback.print_exc()
            error_item = SidebarItem("Error loading Live installations", "⚠️")
            error_item.setEnabled(False)
            self.live_versions_layout.addWidget(error_item)
            self._live_version_items.append(error_item)
    
    def _on_install_item_context_menu(self, pos: QPoint, install_id: int) -> None:
        """Show context menu for a Live installation item."""
        from ...database import get_session, LiveInstallation
        from PyQt6.QtGui import QCursor
        import sys
        import os
        import subprocess
        
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
            
            # Release Notes link
            version_parts = install.version.split('.')
            major_version = version_parts[0] if version_parts else "12"
            release_notes_action = menu.addAction("View Release Notes")
            release_notes_action.triggered.connect(
                lambda: QDesktopServices.openUrl(QUrl(f"https://www.ableton.com/en/release-notes/live-{major_version}/"))
            )
            
            menu.addSeparator()
            
            # Open Preferences folder
            prefs_action = menu.addAction("Open Preferences Folder")
            prefs_action.triggered.connect(
                lambda: self._open_prefs_folder(install.version)
            )
            
            # Edit Options.txt
            options_action = menu.addAction("Edit Options.txt")
            options_action.triggered.connect(
                lambda: self._edit_options_txt(install.version)
            )
            
            menu.addSeparator()
            remove_action = menu.addAction("Remove Installation")
            remove_action.triggered.connect(
                lambda: self.remove_installation_requested.emit(install_id)
            )
            
            # Use QCursor.pos() to get the actual global cursor position
            menu.exec(QCursor.pos())
        finally:
            session.close()
    
    def _get_prefs_folder(self, version: str) -> Optional[Path]:
        """Get the preferences folder path for a Live version."""
        import sys
        
        # Extract major.minor version (e.g., "11.3" from "11.3.13")
        version_parts = version.split('.')
        if len(version_parts) >= 2:
            major_minor = f"{version_parts[0]}.{version_parts[1]}"
        else:
            major_minor = version_parts[0]
        
        if sys.platform == "win32":
            # Windows: %APPDATA%\Ableton\Live x.x\Preferences
            appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
            prefs_path = appdata / "Ableton" / f"Live {major_minor}" / "Preferences"
        elif sys.platform == "darwin":
            # macOS: ~/Library/Preferences/Ableton/Live x.x
            prefs_path = Path.home() / "Library" / "Preferences" / "Ableton" / f"Live {major_minor}"
        else:
            # Linux: ~/.ableton/Live x.x/Preferences (if using Wine)
            prefs_path = Path.home() / ".ableton" / f"Live {major_minor}" / "Preferences"
        
        return prefs_path
    
    def _open_prefs_folder(self, version: str) -> None:
        """Open the preferences folder for a Live version."""
        import sys
        import subprocess
        from PyQt6.QtWidgets import QMessageBox
        
        prefs_path = self._get_prefs_folder(version)
        
        if not prefs_path or not prefs_path.exists():
            QMessageBox.warning(
                self,
                "Preferences Not Found",
                f"Could not find preferences folder for Live {version}.\n\n"
                f"Expected location:\n{prefs_path}\n\n"
                "The folder may not exist if Live hasn't been run yet."
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
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open preferences folder:\n{str(e)}"
            )
    
    def _edit_options_txt(self, version: str) -> None:
        """Edit or create Options.txt for a Live version."""
        import sys
        import subprocess
        from PyQt6.QtWidgets import QMessageBox, QInputDialog
        
        prefs_path = self._get_prefs_folder(version)
        
        if not prefs_path:
            QMessageBox.warning(
                self,
                "Error",
                f"Could not determine preferences folder for Live {version}."
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
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    prefs_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Failed to create preferences folder:\n{str(e)}"
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
                QMessageBox.StandardButton.Yes
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
                    options_path.write_text(default_content, encoding='utf-8')
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Failed to create Options.txt:\n{str(e)}"
                    )
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
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open Options.txt:\n{str(e)}"
            )
    
    def _launch_live_version(self, install) -> None:
        """Launch a specific Live installation."""
        try:
            from pathlib import Path
            import subprocess
            import sys
            
            exe_path = Path(install.executable_path)
            if not exe_path.exists():
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Installation Not Found",
                    f"The Live installation at:\n{exe_path}\n\ncould not be found.\n\nPlease remove and re-add this installation."
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
            print(f"[SIDEBAR] Launched {install.name}")
        except Exception as e:
            print(f"[SIDEBAR] ERROR: Failed to launch {install.name}: {e}")
            import traceback
            traceback.print_exc()
    
    # === Packs Methods ===
    
    def _get_live_resources_path(self) -> Optional[Path]:
        """Get the Resources path from the most recent Live installation."""
        from ...database import get_session, LiveInstallation
        
        session = get_session()
        try:
            # Get the most recent (favorite or first) installation
            install = session.query(LiveInstallation).filter(
                LiveInstallation.is_favorite == True
            ).first()
            
            if not install:
                install = session.query(LiveInstallation).first()
            
            if not install:
                return None
            
            exe_path = Path(install.executable_path)
            
            # Navigate to Resources folder
            # Windows: C:\ProgramData\Ableton\Live XX\Resources
            # macOS: /Applications/Ableton Live XX.app/Contents/App-Resources
            import sys
            if sys.platform == "win32":
                # Try ProgramData location first
                version_parts = install.version.split('.')
                major = version_parts[0] if version_parts else "12"
                program_data = Path(os.environ.get('PROGRAMDATA', 'C:\\ProgramData'))
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
    
    def _open_core_library(self) -> None:
        """Open the Ableton Core Library folder."""
        import subprocess
        import sys
        from PyQt6.QtWidgets import QMessageBox
        
        resources = self._get_live_resources_path()
        if resources:
            core_lib = resources / "Core Library"
            if core_lib.exists():
                try:
                    if sys.platform == "win32":
                        subprocess.run(["explorer", str(core_lib)])
                    elif sys.platform == "darwin":
                        subprocess.run(["open", str(core_lib)])
                    else:
                        subprocess.run(["xdg-open", str(core_lib)])
                    return
                except Exception as e:
                    pass
        
        QMessageBox.information(
            self,
            "Core Library Not Found",
            "Could not find the Ableton Core Library.\n\n"
            "Make sure you have at least one Live installation registered."
        )
    
    def _open_user_library(self) -> None:
        """Open the User Library folder."""
        import subprocess
        import sys
        from PyQt6.QtWidgets import QMessageBox
        
        # Default user library locations
        if sys.platform == "win32":
            user_lib = Path.home() / "Documents" / "Ableton" / "User Library"
        elif sys.platform == "darwin":
            user_lib = Path.home() / "Music" / "Ableton" / "User Library"
        else:
            user_lib = Path.home() / "Ableton" / "User Library"
        
        if user_lib.exists():
            try:
                if sys.platform == "win32":
                    subprocess.run(["explorer", str(user_lib)])
                elif sys.platform == "darwin":
                    subprocess.run(["open", str(user_lib)])
                else:
                    subprocess.run(["xdg-open", str(user_lib)])
                return
            except Exception as e:
                pass
        
        QMessageBox.information(
            self,
            "User Library Not Found",
            f"Could not find the User Library at:\n{user_lib}\n\n"
            "The folder may not exist if Live hasn't been run yet."
        )
    
    def _open_factory_packs(self) -> None:
        """Open the Factory Packs folder."""
        import subprocess
        import sys
        from PyQt6.QtWidgets import QMessageBox
        
        # Default factory packs location
        if sys.platform == "win32":
            packs_path = Path.home() / "Documents" / "Ableton" / "Factory Packs"
        elif sys.platform == "darwin":
            packs_path = Path.home() / "Music" / "Ableton" / "Factory Packs"
        else:
            packs_path = Path.home() / "Ableton" / "Factory Packs"
        
        if packs_path.exists():
            try:
                if sys.platform == "win32":
                    subprocess.run(["explorer", str(packs_path)])
                elif sys.platform == "darwin":
                    subprocess.run(["open", str(packs_path)])
                else:
                    subprocess.run(["xdg-open", str(packs_path)])
                return
            except Exception as e:
                pass
        
        QMessageBox.information(
            self,
            "Factory Packs Not Found",
            f"Could not find Factory Packs at:\n{packs_path}\n\n"
            "The folder may not exist if no packs have been installed."
        )
    
    # === Lessons Methods ===
    
    def _open_live_lessons(self) -> None:
        """Open the Ableton Live built-in lessons folder."""
        import subprocess
        import sys
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
                except Exception as e:
                    pass
        
        QMessageBox.information(
            self,
            "Lessons Not Found",
            "Could not find the Ableton Live lessons folder.\n\n"
            "Lessons are located in:\n"
            "Windows: C:\\ProgramData\\Ableton\\Live XX\\Resources\\Lessons\n"
            "macOS: /Applications/Ableton Live XX.app/Contents/App-Resources/Lessons\n\n"
            "Make sure you have at least one Live installation registered."
        )
    
    def _open_lessons_toc(self) -> None:
        """Open the lessons table of contents / index."""
        import subprocess
        import sys
        from PyQt6.QtWidgets import QMessageBox
        
        resources = self._get_live_resources_path()
        if resources:
            lessons = resources / "Lessons"
            # Look for an index file
            index_files = [
                lessons / "TOC.txt",
                lessons / "index.html",
                lessons / "Contents.txt",
                lessons / "Lessons.txt"
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
                    except Exception as e:
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
                except Exception as e:
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
            locations = session.query(Location).filter(
                Location.is_active == True
            ).order_by(Location.sort_order, Location.name).all()
            
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
            collections = session.query(Collection).order_by(
                Collection.sort_order, Collection.name
            ).all()
            
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
                
                item = SidebarItem(coll.name, icon, coll.color, project_count, item_type="collection")
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
                item.clicked.connect(
                    lambda checked, tid=tag.id, i=item: self._on_tag_click(tid, i)
                )
                
                self.tags_layout.addWidget(item)
                self._tag_items.append(item)
        finally:
            session.close()
    
    def _load_backup_location(self) -> None:
        """Load and display the backup location from settings."""
        from ...database import get_session, AppSettings
        
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
        from ...database import get_session, AppSettings
        
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
            QFileDialog.Option.ShowDirsOnly
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
                    "Please choose a different location."
                )
                return
            
            # Save to settings
            session = get_session()
            try:
                AppSettings.set_value(
                    session, 
                    "backup_location", 
                    folder,
                    description="Location for project backups"
                )
                
                # Update display
                self._load_backup_location()
                
                QMessageBox.information(
                    self,
                    "Backup Location Set",
                    f"Backup location has been set to:\n{folder}"
                )
            finally:
                session.close()
    
    def _on_open_backup_folder(self) -> None:
        """Open the backup folder in file manager."""
        import sys
        import subprocess
        from PyQt6.QtWidgets import QMessageBox
        from ...database import get_session, AppSettings
        
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
                "Click 'Set Backup Location' to configure one."
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
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Failed to create backup folder:\n{str(e)}"
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
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open backup folder:\n{str(e)}"
            )