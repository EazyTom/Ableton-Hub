"""Tag editor widget for creating and managing tags."""

from typing import Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QColorDialog, QListWidget, QListWidgetItem,
    QDialog, QFormLayout, QDialogButtonBox, QMessageBox, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPixmap, QPainter, QBrush

from ...database import get_session, Tag
from ..theme import AbletonTheme


class TagChip(QWidget):
    """Small tag display widget."""
    
    clicked = pyqtSignal(int)   # Tag ID
    remove = pyqtSignal(int)    # Tag ID
    
    def __init__(self, tag: Tag, removable: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.tag = tag
        self.removable = removable
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the chip UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        
        # Color dot
        color_label = QLabel("●")
        color_label.setStyleSheet(f"color: {self.tag.color}; font-size: 8px;")
        layout.addWidget(color_label)
        
        # Tag name
        name_label = QLabel(self.tag.name)
        name_label.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(name_label)
        
        # Remove button
        if self.removable:
            remove_btn = QPushButton("×")
            remove_btn.setFixedSize(16, 16)
            remove_btn.setFlat(True)
            remove_btn.clicked.connect(lambda: self.remove.emit(self.tag.id))
            layout.addWidget(remove_btn)
        
        self.setStyleSheet(f"""
            TagChip {{
                background-color: {AbletonTheme.COLORS['surface_light']};
                border-radius: 12px;
            }}
            TagChip:hover {{
                background-color: {AbletonTheme.COLORS['surface_hover']};
            }}
        """)
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def mousePressEvent(self, event) -> None:
        """Handle mouse press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.tag.id)
        super().mousePressEvent(event)


class CreateTagDialog(QDialog):
    """Dialog for creating a new tag."""
    
    def __init__(self, parent: Optional[QWidget] = None, tag_id: Optional[int] = None):
        super().__init__(parent)
        
        self.tag_id = tag_id
        self._color = AbletonTheme.COLORS['accent']
        
        self.setWindowTitle("Edit Tag" if tag_id else "Create Tag")
        self.setMinimumWidth(300)
        
        self._setup_ui()
        
        if tag_id:
            self._load_tag()
    
    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Tag name")
        form.addRow("Name:", self.name_input)
        
        # Category
        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("Optional category")
        form.addRow("Category:", self.category_input)
        
        # Color
        color_row = QHBoxLayout()
        
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(24, 24)
        self._update_color_preview()
        color_row.addWidget(self.color_preview)
        
        color_btn = QPushButton("Choose Color...")
        color_btn.clicked.connect(self._choose_color)
        color_row.addWidget(color_btn)
        
        color_row.addStretch()
        
        form.addRow("Color:", color_row)
        
        layout.addLayout(form)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _load_tag(self) -> None:
        """Load existing tag data."""
        session = get_session()
        try:
            tag = session.query(Tag).get(self.tag_id)
            if tag:
                self.name_input.setText(tag.name)
                self.category_input.setText(tag.category or "")
                self._color = tag.color
                self._update_color_preview()
        finally:
            session.close()
    
    def _choose_color(self) -> None:
        """Show color picker dialog."""
        color = QColorDialog.getColor(QColor(self._color), self)
        if color.isValid():
            self._color = color.name()
            self._update_color_preview()
    
    def _update_color_preview(self) -> None:
        """Update the color preview widget."""
        pixmap = QPixmap(24, 24)
        pixmap.fill(QColor(self._color))
        self.color_preview.setPixmap(pixmap)
    
    def _on_accept(self) -> None:
        """Handle accept button."""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a tag name.")
            return
        
        session = get_session()
        try:
            if self.tag_id:
                # Update existing
                tag = session.query(Tag).get(self.tag_id)
                if tag:
                    tag.name = name
                    tag.category = self.category_input.text().strip() or None
                    tag.color = self._color
            else:
                # Check for duplicate
                existing = session.query(Tag).filter(Tag.name == name).first()
                if existing:
                    QMessageBox.warning(self, "Error", f"Tag '{name}' already exists.")
                    return
                
                # Create new
                tag = Tag(
                    name=name,
                    category=self.category_input.text().strip() or None,
                    color=self._color
                )
                session.add(tag)
            
            session.commit()
            self.accept()
        finally:
            session.close()


class TagEditor(QWidget):
    """Widget for managing all tags."""
    
    tag_selected = pyqtSignal(int)
    tags_changed = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._tags: List[Tag] = []
        
        self._setup_ui()
        self.refresh()
    
    def _setup_ui(self) -> None:
        """Set up the editor UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("Tags")
        title.setStyleSheet("font-weight: bold;")
        header.addWidget(title)
        
        header.addStretch()
        
        add_btn = QPushButton("+")
        add_btn.setFixedSize(24, 24)
        add_btn.setToolTip("Create new tag")
        add_btn.clicked.connect(self._on_create_tag)
        header.addWidget(add_btn)
        
        layout.addLayout(header)
        
        # Tag list
        self.tag_list = QListWidget()
        self.tag_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tag_list.customContextMenuRequested.connect(self._on_context_menu)
        self.tag_list.itemDoubleClicked.connect(self._on_item_double_click)
        
        layout.addWidget(self.tag_list)
    
    def refresh(self) -> None:
        """Refresh tags from database."""
        self.tag_list.clear()
        
        session = get_session()
        try:
            self._tags = session.query(Tag).order_by(Tag.category, Tag.name).all()
            
            current_category = None
            for tag in self._tags:
                # Add category header
                if tag.category != current_category:
                    if tag.category:
                        header_item = QListWidgetItem(tag.category)
                        header_item.setFlags(Qt.ItemFlag.NoItemFlags)
                        header_item.setForeground(AbletonTheme.get_qcolor("text_secondary"))
                        font = AbletonTheme.safe_font_modify(header_item.font(), bold=True, pixel_size=12)
                        header_item.setFont(font)
                        self.tag_list.addItem(header_item)
                    current_category = tag.category
                
                # Add tag item
                item = QListWidgetItem(f"  ● {tag.name}")
                item.setData(Qt.ItemDataRole.UserRole, tag.id)
                item.setForeground(QColor(tag.color))
                self.tag_list.addItem(item)
        finally:
            session.close()
    
    def _on_create_tag(self) -> None:
        """Show create tag dialog."""
        dialog = CreateTagDialog(self)
        if dialog.exec():
            self.refresh()
            self.tags_changed.emit()
    
    def _on_item_double_click(self, item: QListWidgetItem) -> None:
        """Handle tag double click."""
        tag_id = item.data(Qt.ItemDataRole.UserRole)
        if tag_id:
            self.tag_selected.emit(tag_id)
    
    def _on_context_menu(self, pos) -> None:
        """Show context menu for tag."""
        item = self.tag_list.itemAt(pos)
        if not item:
            return
        
        tag_id = item.data(Qt.ItemDataRole.UserRole)
        if not tag_id:
            return
        
        menu = QMenu(self)
        
        edit_action = menu.addAction("Edit")
        edit_action.triggered.connect(lambda: self._edit_tag(tag_id))
        
        menu.addSeparator()
        
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda: self._delete_tag(tag_id))
        
        menu.exec(self.tag_list.viewport().mapToGlobal(pos))
    
    def _edit_tag(self, tag_id: int) -> None:
        """Show edit tag dialog."""
        dialog = CreateTagDialog(self, tag_id=tag_id)
        if dialog.exec():
            self.refresh()
            self.tags_changed.emit()
    
    def _delete_tag(self, tag_id: int) -> None:
        """Delete a tag."""
        tag = next((t for t in self._tags if t.id == tag_id), None)
        if not tag:
            return
        
        result = QMessageBox.question(
            self,
            "Delete Tag",
            f"Are you sure you want to delete the tag '{tag.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            session = get_session()
            try:
                tag = session.query(Tag).get(tag_id)
                if tag:
                    session.delete(tag)
                    session.commit()
                    self.refresh()
                    self.tags_changed.emit()
            finally:
                session.close()
    
    def get_selected_tag_id(self) -> Optional[int]:
        """Get the currently selected tag ID."""
        item = self.tag_list.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None


class ManageTagsDialog(QDialog):
    """Dialog for managing all tags with full CRUD operations."""
    
    tags_changed = pyqtSignal()  # Emitted when tags are modified
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.setWindowTitle("Manage Tags")
        self.setMinimumSize(400, 500)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Instructions
        instructions = QLabel(
            "Create, edit, and delete tags. Right-click a tag for options, "
            "or double-click to edit."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet(f"color: {AbletonTheme.COLORS['text_secondary']};")
        layout.addWidget(instructions)
        
        # Tag editor widget
        self.tag_editor = TagEditor(self)
        self.tag_editor.tags_changed.connect(self._on_tags_changed)
        layout.addWidget(self.tag_editor, 1)  # stretch factor 1
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.accept)
        layout.addWidget(button_box)
    
    def _on_tags_changed(self) -> None:
        """Handle tags changed in the editor."""
        self.tags_changed.emit()
    
    def refresh(self) -> None:
        """Refresh the tag list."""
        self.tag_editor.refresh()


class ProjectTagSelector(QWidget):
    """Widget for selecting tags for a project."""
    
    tags_changed = pyqtSignal(list)  # List of tag IDs
    tag_created = pyqtSignal()       # Emitted when a new tag is created
    
    def __init__(self, project_id: Optional[int] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.project_id = project_id
        self._selected_tags: List[int] = []
        
        self._setup_ui()
        
        if project_id:
            self._load_project_tags()
    
    def _setup_ui(self) -> None:
        """Set up the selector UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Selected tags display
        self.selected_container = QWidget()
        self.selected_layout = QHBoxLayout(self.selected_container)
        self.selected_layout.setContentsMargins(0, 0, 0, 0)
        self.selected_layout.setSpacing(4)
        layout.addWidget(self.selected_container)
        
        # Add tag button
        add_row = QHBoxLayout()
        
        self.add_btn = QPushButton("+ Add Tag")
        self.add_btn.clicked.connect(self._show_tag_menu)
        add_row.addWidget(self.add_btn)
        
        add_row.addStretch()
        
        layout.addLayout(add_row)
    
    def _load_project_tags(self) -> None:
        """Load tags for the current project."""
        from ...database import Project
        
        session = get_session()
        try:
            project = session.query(Project).get(self.project_id)
            if project and project.tags:
                self._selected_tags = list(project.tags)
                self._update_display()
        finally:
            session.close()
    
    def _update_display(self) -> None:
        """Update the selected tags display."""
        # Clear existing
        while self.selected_layout.count():
            item = self.selected_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self._selected_tags:
            placeholder = QLabel("No tags")
            placeholder.setStyleSheet(f"color: {AbletonTheme.COLORS['text_disabled']};")
            self.selected_layout.addWidget(placeholder)
            return
        
        session = get_session()
        try:
            for tag_id in self._selected_tags:
                tag = session.query(Tag).get(tag_id)
                if tag:
                    chip = TagChip(tag, removable=True)
                    chip.remove.connect(self._remove_tag)
                    self.selected_layout.addWidget(chip)
        finally:
            session.close()
        
        self.selected_layout.addStretch()
    
    def _show_tag_menu(self) -> None:
        """Show menu of available tags."""
        menu = QMenu(self)
        
        session = get_session()
        try:
            tags = session.query(Tag).order_by(Tag.name).all()
            
            if not tags:
                action = menu.addAction("No tags available")
                action.setEnabled(False)
            else:
                for tag in tags:
                    if tag.id not in self._selected_tags:
                        action = menu.addAction(f"● {tag.name}")
                        action.setData(tag.id)
                        action.triggered.connect(
                            lambda checked, tid=tag.id: self._add_tag(tid)
                        )
            
            menu.addSeparator()
            
            create_action = menu.addAction("+ Create New Tag...")
            create_action.triggered.connect(self._create_tag)
        finally:
            session.close()
        
        menu.exec(self.add_btn.mapToGlobal(self.add_btn.rect().bottomLeft()))
    
    def _add_tag(self, tag_id: int) -> None:
        """Add a tag to the selection."""
        if tag_id not in self._selected_tags:
            self._selected_tags.append(tag_id)
            self._update_display()
            self.tags_changed.emit(self._selected_tags)
    
    def _remove_tag(self, tag_id: int) -> None:
        """Remove a tag from the selection."""
        if tag_id in self._selected_tags:
            self._selected_tags.remove(tag_id)
            self._update_display()
            self.tags_changed.emit(self._selected_tags)
    
    def _create_tag(self) -> None:
        """Show create tag dialog."""
        dialog = CreateTagDialog(self)
        if dialog.exec():
            # Notify that a new tag was created so sidebar can refresh
            self.tag_created.emit()
    
    def get_selected_tags(self) -> List[int]:
        """Get the list of selected tag IDs."""
        return list(self._selected_tags)
    
    def set_selected_tags(self, tag_ids: List[int]) -> None:
        """Set the selected tags."""
        self._selected_tags = list(tag_ids)
        self._update_display()
