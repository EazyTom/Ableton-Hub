"""Smart collection creation/editing dialog."""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QTextEdit, QCheckBox,
    QSpinBox, QDateEdit, QDialogButtonBox, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt, QDate

from ...database import get_session, Collection, CollectionType, Tag, Location, Project
from ..theme import AbletonTheme
from PyQt6.QtGui import QFont


class SmartCollectionDialog(QDialog):
    """Dialog for creating or editing a smart collection."""
    
    def __init__(self, parent=None, collection_id: Optional[int] = None):
        super().__init__(parent)
        
        self.collection_id = collection_id
        self._rules: Dict[str, Any] = {}
        
        self.setWindowTitle("Edit Smart Collection" if collection_id else "New Smart Collection")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        # Ensure dialog has a valid font
        font = self.font()
        if font.pointSize() <= 0:
            font.setPixelSize(12)
            self.setFont(font)
        
        self._setup_ui()
        
        if collection_id:
            self._load_collection()
    
    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Basic info
        basic_group = QGroupBox("Collection Info")
        basic_layout = QFormLayout(basic_group)
        
        self.name_input = QLineEdit()
        basic_layout.addRow("Name:", self.name_input)
        
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        basic_layout.addRow("Description:", self.description_input)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems([ct.value.title() for ct in CollectionType])
        basic_layout.addRow("Type:", self.type_combo)
        
        layout.addWidget(basic_group)
        
        # Smart rules
        rules_group = QGroupBox("Smart Collection Rules")
        rules_layout = QVBoxLayout(rules_group)
        
        # Tags
        tags_layout = QHBoxLayout()
        tags_layout.addWidget(QLabel("Tags:"))
        self.tags_combo = QComboBox()
        self.tags_combo.setEditable(False)  # Single selection only
        self._populate_tags()
        tags_layout.addWidget(self.tags_combo)
        self.tags_mode_combo = QComboBox()
        self.tags_mode_combo.addItems(["Any", "All"])
        tags_layout.addWidget(self.tags_mode_combo)
        rules_layout.addLayout(tags_layout)
        
        # Locations
        locations_layout = QHBoxLayout()
        locations_layout.addWidget(QLabel("Locations:"))
        self.locations_combo = QComboBox()
        self.locations_combo.setEditable(True)
        self._populate_locations()
        locations_layout.addWidget(self.locations_combo)
        rules_layout.addLayout(locations_layout)
        
        # Date range - relative (last X days)
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Modified in last:"))
        self.days_spin = QSpinBox()
        self.days_spin.setMinimum(1)
        self.days_spin.setMaximum(3650)
        self.days_spin.setValue(30)
        self.days_spin.setSuffix(" days")
        date_layout.addWidget(self.days_spin)
        self.use_date_filter = QCheckBox("Use relative date")
        date_layout.addWidget(self.use_date_filter)
        rules_layout.addLayout(date_layout)
        
        # Quick presets for relative dates
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Quick presets:"))
        for days, label in [(7, "1 Week"), (30, "1 Month"), (90, "3 Months"), (365, "1 Year")]:
            btn = QPushButton(label)
            btn.setFixedWidth(70)
            btn.clicked.connect(lambda checked, d=days: self._set_days_preset(d))
            preset_layout.addWidget(btn)
        preset_layout.addStretch()
        rules_layout.addLayout(preset_layout)
        
        # Date range - absolute (start/end dates)
        abs_date_layout = QHBoxLayout()
        abs_date_layout.addWidget(QLabel("Or date range:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        abs_date_layout.addWidget(self.start_date)
        abs_date_layout.addWidget(QLabel("to"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        abs_date_layout.addWidget(self.end_date)
        self.use_abs_date_filter = QCheckBox("Use date range")
        abs_date_layout.addWidget(self.use_abs_date_filter)
        rules_layout.addLayout(abs_date_layout)
        
        # Export status
        export_layout = QHBoxLayout()
        self.has_export_check = QCheckBox("Has exports")
        export_layout.addWidget(self.has_export_check)
        self.no_export_check = QCheckBox("No exports")
        export_layout.addWidget(self.no_export_check)
        rules_layout.addLayout(export_layout)
        
        # Rating
        rating_layout = QHBoxLayout()
        rating_layout.addWidget(QLabel("Minimum rating:"))
        self.rating_spin = QSpinBox()
        self.rating_spin.setMinimum(0)
        self.rating_spin.setMaximum(5)
        self.rating_spin.setValue(0)
        rating_layout.addWidget(self.rating_spin)
        self.use_rating_filter = QCheckBox("Use rating filter")
        rating_layout.addWidget(self.use_rating_filter)
        rules_layout.addLayout(rating_layout)
        
        # Favorites
        self.favorites_only_check = QCheckBox("Favorites only")
        rules_layout.addWidget(self.favorites_only_check)
        
        # Tempo range
        tempo_layout = QHBoxLayout()
        tempo_layout.addWidget(QLabel("Tempo range:"))
        self.tempo_min_spin = QSpinBox()
        self.tempo_min_spin.setMinimum(0)
        self.tempo_min_spin.setMaximum(999)
        self.tempo_min_spin.setValue(0)
        self.tempo_min_spin.setSuffix(" BPM")
        self.tempo_min_spin.setSpecialValueText("Min")
        tempo_layout.addWidget(self.tempo_min_spin)
        tempo_layout.addWidget(QLabel("to"))
        self.tempo_max_spin = QSpinBox()
        self.tempo_max_spin.setMinimum(0)
        self.tempo_max_spin.setMaximum(999)
        self.tempo_max_spin.setValue(0)
        self.tempo_max_spin.setSuffix(" BPM")
        self.tempo_max_spin.setSpecialValueText("Max")
        tempo_layout.addWidget(self.tempo_max_spin)
        self.use_tempo_filter = QCheckBox("Use tempo filter")
        tempo_layout.addWidget(self.use_tempo_filter)
        rules_layout.addLayout(tempo_layout)
        
        # Similarity filter
        similarity_layout = QHBoxLayout()
        similarity_layout.addWidget(QLabel("Similar to project:"))
        self.similar_project_combo = QComboBox()
        self.similar_project_combo.setEditable(False)
        self._populate_projects()
        similarity_layout.addWidget(self.similar_project_combo)
        similarity_layout.addWidget(QLabel("Min similarity:"))
        self.similarity_min_spin = QSpinBox()
        self.similarity_min_spin.setMinimum(20)
        self.similarity_min_spin.setMaximum(100)
        self.similarity_min_spin.setValue(50)
        self.similarity_min_spin.setSuffix("%")
        similarity_layout.addWidget(self.similarity_min_spin)
        self.use_similarity_filter = QCheckBox("Use similarity filter")
        similarity_layout.addWidget(self.use_similarity_filter)
        rules_layout.addLayout(similarity_layout)
        
        layout.addWidget(rules_group)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _set_days_preset(self, days: int) -> None:
        """Set days preset and enable relative date filter."""
        self.days_spin.setValue(days)
        self.use_date_filter.setChecked(True)
        self.use_abs_date_filter.setChecked(False)
    
    def _populate_tags(self) -> None:
        """Populate tags combo box."""
        session = get_session()
        try:
            tags = session.query(Tag).order_by(Tag.name).all()
            self.tags_combo.addItem("(None)")
            for tag in tags:
                self.tags_combo.addItem(tag.name, tag.id)
        finally:
            session.close()
    
    def _populate_locations(self) -> None:
        """Populate locations combo box."""
        session = get_session()
        try:
            locations = session.query(Location).filter(
                Location.is_active == True
            ).order_by(Location.name).all()
            self.locations_combo.addItem("(All)")
            for location in locations:
                self.locations_combo.addItem(location.name, location.id)
        finally:
            session.close()
    
    def _populate_projects(self) -> None:
        """Populate projects combo box for similarity filter."""
        session = get_session()
        try:
            projects = session.query(Project).order_by(Project.name).all()
            self.similar_project_combo.addItem("(Select project)")
            for project in projects:
                self.similar_project_combo.addItem(project.name, project.id)
        finally:
            session.close()
    
    def _load_collection(self) -> None:
        """Load existing collection data."""
        session = get_session()
        try:
            collection = session.query(Collection).get(self.collection_id)
            if collection:
                self.name_input.setText(collection.name)
                self.description_input.setText(collection.description or "")
                self.type_combo.setCurrentText(collection.collection_type.value.title())
                
                if collection.smart_rules:
                    self._rules = collection.smart_rules
                    self._apply_rules_to_ui()
        finally:
            session.close()
    
    def _apply_rules_to_ui(self) -> None:
        """Apply loaded rules to UI."""
        if 'tags' in self._rules:
            tag_ids = self._rules['tags']
            if tag_ids:
                # Find tag in combo
                for i in range(self.tags_combo.count()):
                    if self.tags_combo.itemData(i) in tag_ids:
                        self.tags_combo.setCurrentIndex(i)
                        break
        
        if 'tags_mode' in self._rules:
            mode = self._rules['tags_mode']
            self.tags_mode_combo.setCurrentText("All" if mode == 'all' else "Any")
        
        if 'days_ago' in self._rules:
            self.days_spin.setValue(self._rules['days_ago'])
            self.use_date_filter.setChecked(True)
        
        if 'has_export' in self._rules:
            self.has_export_check.setChecked(self._rules['has_export'])
        
        if 'min_rating' in self._rules:
            self.rating_spin.setValue(self._rules['min_rating'])
            self.use_rating_filter.setChecked(True)
        
        if 'favorites_only' in self._rules:
            self.favorites_only_check.setChecked(self._rules['favorites_only'])
        
        if 'tempo_min' in self._rules:
            self.tempo_min_spin.setValue(self._rules['tempo_min'])
            self.use_tempo_filter.setChecked(True)
        
        if 'tempo_max' in self._rules:
            self.tempo_max_spin.setValue(self._rules['tempo_max'])
            self.use_tempo_filter.setChecked(True)
        
        if 'similar_to_project' in self._rules:
            project_id = self._rules['similar_to_project']
            for i in range(self.similar_project_combo.count()):
                if self.similar_project_combo.itemData(i) == project_id:
                    self.similar_project_combo.setCurrentIndex(i)
                    break
        
        if 'min_similarity' in self._rules:
            self.similarity_min_spin.setValue(int(self._rules['min_similarity'] * 100))
            self.use_similarity_filter.setChecked(True)
        
        # Absolute date range
        if 'date_range' in self._rules:
            date_range = self._rules['date_range']
            if 'start_date' in date_range:
                self.start_date.setDate(QDate.fromString(date_range['start_date'], "yyyy-MM-dd"))
            if 'end_date' in date_range:
                self.end_date.setDate(QDate.fromString(date_range['end_date'], "yyyy-MM-dd"))
            self.use_abs_date_filter.setChecked(True)
    
    def _build_rules(self) -> Dict[str, Any]:
        """Build rules dictionary from UI."""
        rules = {}
        
        # Tags
        tag_id = self.tags_combo.currentData()
        if tag_id:
            rules['tags'] = [tag_id]
            rules['tags_mode'] = 'all' if self.tags_mode_combo.currentText() == "All" else 'any'
        
        # Locations
        location_id = self.locations_combo.currentData()
        if location_id:
            rules['locations'] = [location_id]
        
        # Date filter
        if self.use_date_filter.isChecked():
            rules['days_ago'] = self.days_spin.value()
        
        # Export status
        if self.has_export_check.isChecked():
            rules['has_export'] = True
        elif self.no_export_check.isChecked():
            rules['has_export'] = False
        
        # Rating
        if self.use_rating_filter.isChecked():
            rules['min_rating'] = self.rating_spin.value()
        
        # Favorites
        if self.favorites_only_check.isChecked():
            rules['favorites_only'] = True
        
        # Tempo range
        if self.use_tempo_filter.isChecked():
            if self.tempo_min_spin.value() > 0:
                rules['tempo_min'] = self.tempo_min_spin.value()
            if self.tempo_max_spin.value() > 0:
                rules['tempo_max'] = self.tempo_max_spin.value()
        
        # Absolute date range (only if relative not used)
        if self.use_abs_date_filter.isChecked() and not self.use_date_filter.isChecked():
            rules['date_range'] = {
                'start_date': self.start_date.date().toString("yyyy-MM-dd"),
                'end_date': self.end_date.date().toString("yyyy-MM-dd")
            }
        
        # Similarity filter
        if self.use_similarity_filter.isChecked():
            project_id = self.similar_project_combo.currentData()
            if project_id:
                rules['similar_to_project'] = project_id
                rules['min_similarity'] = self.similarity_min_spin.value() / 100.0
        
        return rules
    
    def _on_accept(self) -> None:
        """Handle accept button."""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Input", "Collection name is required.")
            return
        
        session = get_session()
        try:
            rules = self._build_rules()
            
            if self.collection_id:
                # Update existing
                collection = session.query(Collection).get(self.collection_id)
                if collection:
                    collection.name = name
                    collection.description = self.description_input.toPlainText().strip() or None
                    collection.collection_type = CollectionType(self.type_combo.currentText().lower())
                    collection.is_smart = True
                    collection.smart_rules = rules
            else:
                # Create new
                collection = Collection(
                    name=name,
                    description=self.description_input.toPlainText().strip() or None,
                    collection_type=CollectionType(self.type_combo.currentText().lower()),
                    is_smart=True,
                    smart_rules=rules
                )
                session.add(collection)
            
            session.commit()
            
            # Update smart collection
            if collection:
                from ...services.smart_collections import SmartCollectionService
                added = SmartCollectionService.update_smart_collection(collection.id)
                if added > 0:
                    QMessageBox.information(
                        self, "Smart Collection Updated",
                        f"Collection created/updated. {added} projects added."
                    )
            
            self.accept()
        finally:
            session.close()
