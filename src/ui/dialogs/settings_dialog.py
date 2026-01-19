"""Settings dialog for Ableton Hub."""

from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QSpinBox, QCheckBox, QGroupBox,
    QFileDialog, QLineEdit, QMessageBox, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt

from ...config import Config, save_config
from ..theme import AbletonTheme


class SettingsDialog(QDialog):
    """Settings dialog for application configuration."""
    
    def __init__(self, config: Config, parent: Optional[QWidget] = None):
        """Initialize the settings dialog.
        
        Args:
            config: Application configuration object.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.config = config
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Settings")
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Tab widget for different settings categories
        tabs = QTabWidget()
        
        # General tab
        general_tab = self._create_general_tab()
        tabs.addTab(general_tab, "General")
        
        # Scanning tab
        scanning_tab = self._create_scanning_tab()
        tabs.addTab(scanning_tab, "Scanning")
        
        # Export tab
        export_tab = self._create_export_tab()
        tabs.addTab(export_tab, "Exports")
        
        # Link tab
        link_tab = self._create_link_tab()
        tabs.addTab(link_tab, "Link")
        
        layout.addWidget(tabs)
        
        # Buttons
        buttons = QHBoxLayout()
        buttons.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_ok)
        buttons.addWidget(ok_btn)
        
        layout.addLayout(buttons)
    
    def _create_general_tab(self) -> QWidget:
        """Create the general settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        
        # Theme selection
        theme_group = QGroupBox("Color Theme")
        theme_layout = QVBoxLayout(theme_group)
        
        self.theme_group = QButtonGroup(self)
        available_themes = AbletonTheme.get_available_themes()
        
        # Get current theme (handle legacy "dark" theme)
        current_theme = getattr(self.config.ui, 'theme', 'orange')
        if current_theme == "dark":
            current_theme = "orange"
        
        # Map theme IDs to radio buttons
        self.theme_radios = {}
        for idx, (theme_id, theme_name) in enumerate(available_themes.items()):
            radio = QRadioButton(theme_name)
            radio.setChecked(current_theme == theme_id)
            self.theme_group.addButton(radio, idx)
            self.theme_radios[theme_id] = radio
            theme_layout.addWidget(radio)
        
        layout.addWidget(theme_group)
        
        # Waveform color mode selection
        waveform_group = QGroupBox("Waveform Color")
        waveform_layout = QVBoxLayout(waveform_group)
        
        self.waveform_group = QButtonGroup(self)
        
        # Get current waveform color mode
        current_waveform_mode = getattr(self.config.ui, 'waveform_color_mode', 'rainbow')
        
        # Waveform color mode options
        waveform_modes = {
            "rainbow": "Rainbow (Gradient)",
            "random": "Random (Per Project)",
            "accent": "Accent (Green)"
        }
        
        self.waveform_radios = {}
        for idx, (mode_id, mode_name) in enumerate(waveform_modes.items()):
            radio = QRadioButton(mode_name)
            radio.setChecked(current_waveform_mode == mode_id)
            self.waveform_group.addButton(radio, idx)
            self.waveform_radios[mode_id] = radio
            waveform_layout.addWidget(radio)
        
        # Info label
        info_label = QLabel("Note: Existing thumbnails will keep their current colors.\nUse 'Clear Thumbnail Cache' in Tools menu to regenerate.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #888; font-size: 10px;")
        waveform_layout.addWidget(info_label)
        
        layout.addWidget(waveform_group)
        
        # View settings
        view_group = QGroupBox("Default View")
        view_layout = QVBoxLayout(view_group)
        
        self.view_group = QButtonGroup(self)
        self.grid_radio = QRadioButton("Grid View")
        self.grid_radio.setChecked(self.config.ui.default_view == "grid")
        self.view_group.addButton(self.grid_radio, 0)
        view_layout.addWidget(self.grid_radio)
        
        self.list_radio = QRadioButton("List View")
        self.list_radio.setChecked(self.config.ui.default_view == "list")
        self.view_group.addButton(self.list_radio, 1)
        view_layout.addWidget(self.list_radio)
        
        layout.addWidget(view_group)
        
        # Other settings
        other_group = QGroupBox("Other")
        other_layout = QVBoxLayout(other_group)
        
        self.confirm_delete = QCheckBox("Confirm before deleting")
        self.confirm_delete.setChecked(self.config.ui.confirm_delete)
        other_layout.addWidget(self.confirm_delete)
        
        self.show_status_bar = QCheckBox("Show status bar")
        self.show_status_bar.setChecked(self.config.ui.show_status_bar)
        other_layout.addWidget(self.show_status_bar)
        
        layout.addWidget(other_group)
        
        layout.addStretch()
        return widget
    
    def _create_scanning_tab(self) -> QWidget:
        """Create the scanning settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        
        # Auto-scan settings
        auto_group = QGroupBox("Auto-Scanning")
        auto_layout = QVBoxLayout(auto_group)
        
        self.auto_scan_startup = QCheckBox("Scan on startup")
        self.auto_scan_startup.setChecked(self.config.scan.auto_scan_on_startup)
        auto_layout.addWidget(self.auto_scan_startup)
        
        # Scan frequency
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Scan frequency (hours):"))
        self.scan_frequency = QSpinBox()
        self.scan_frequency.setRange(1, 168)  # 1 hour to 1 week
        self.scan_frequency.setValue(self.config.scan.scan_frequency_hours)
        freq_layout.addWidget(self.scan_frequency)
        freq_layout.addStretch()
        auto_layout.addLayout(freq_layout)
        
        # Recursive depth
        depth_layout = QHBoxLayout()
        depth_layout.addWidget(QLabel("Recursive depth:"))
        self.recursive_depth = QSpinBox()
        self.recursive_depth.setRange(1, 50)
        self.recursive_depth.setValue(self.config.scan.recursive_depth)
        depth_layout.addWidget(self.recursive_depth)
        depth_layout.addStretch()
        auto_layout.addLayout(depth_layout)
        
        layout.addWidget(auto_group)
        
        # Exclude patterns
        exclude_group = QGroupBox("Exclude Patterns")
        exclude_layout = QVBoxLayout(exclude_group)
        
        exclude_info = QLabel("Patterns to exclude from scanning (one per line):")
        exclude_info.setWordWrap(True)
        exclude_layout.addWidget(exclude_info)
        
        self.exclude_patterns = QLineEdit()
        self.exclude_patterns.setPlaceholderText("**/Backup/**, **/.git/**, etc.")
        if self.config.scan.exclude_patterns:
            self.exclude_patterns.setText(", ".join(self.config.scan.exclude_patterns))
        exclude_layout.addWidget(self.exclude_patterns)
        
        layout.addWidget(exclude_group)
        
        layout.addStretch()
        return widget
    
    def _create_export_tab(self) -> QWidget:
        """Create the export settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        
        # Auto-detect
        detect_group = QGroupBox("Export Detection")
        detect_layout = QVBoxLayout(detect_group)
        
        self.auto_detect_exports = QCheckBox("Automatically detect exports")
        self.auto_detect_exports.setChecked(self.config.export.auto_detect_exports)
        detect_layout.addWidget(self.auto_detect_exports)
        
        # Fuzzy match threshold
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Fuzzy match threshold:"))
        self.fuzzy_threshold = QSpinBox()
        self.fuzzy_threshold.setRange(0, 100)
        self.fuzzy_threshold.setSuffix("%")
        self.fuzzy_threshold.setValue(int(self.config.export.fuzzy_match_threshold))
        threshold_layout.addWidget(self.fuzzy_threshold)
        threshold_layout.addStretch()
        detect_layout.addLayout(threshold_layout)
        
        layout.addWidget(detect_group)
        
        layout.addStretch()
        return widget
    
    def _create_link_tab(self) -> QWidget:
        """Create the Link settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        
        # Link settings
        link_group = QGroupBox("Ableton Link")
        link_layout = QVBoxLayout(link_group)
        
        self.link_enabled = QCheckBox("Enable Ableton Link")
        self.link_enabled.setChecked(self.config.link.enabled)
        link_layout.addWidget(self.link_enabled)
        
        # Scan interval
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Scan interval (seconds):"))
        self.scan_interval = QSpinBox()
        self.scan_interval.setRange(1, 60)
        self.scan_interval.setValue(self.config.link.scan_interval_seconds)
        interval_layout.addWidget(self.scan_interval)
        interval_layout.addStretch()
        link_layout.addLayout(interval_layout)
        
        # Show offline devices
        self.show_offline = QCheckBox("Show offline devices")
        self.show_offline.setChecked(self.config.link.show_offline_devices)
        link_layout.addWidget(self.show_offline)
        
        layout.addWidget(link_group)
        
        layout.addStretch()
        return widget
    
    def _on_ok(self) -> None:
        """Handle OK button click - save settings."""
        # Theme selection
        for theme_id, radio in self.theme_radios.items():
            if radio.isChecked():
                self.config.ui.theme = theme_id
                break
        
        # Waveform color mode selection
        for mode_id, radio in self.waveform_radios.items():
            if radio.isChecked():
                self.config.ui.waveform_color_mode = mode_id
                break
        
        # General settings
        if self.grid_radio.isChecked():
            self.config.ui.default_view = "grid"
        elif self.list_radio.isChecked():
            self.config.ui.default_view = "list"
        
        self.config.ui.confirm_delete = self.confirm_delete.isChecked()
        self.config.ui.show_status_bar = self.show_status_bar.isChecked()
        
        # Scanning settings
        self.config.scan.auto_scan_on_startup = self.auto_scan_startup.isChecked()
        self.config.scan.scan_frequency_hours = self.scan_frequency.value()
        self.config.scan.recursive_depth = self.recursive_depth.value()
        
        # Parse exclude patterns
        patterns_text = self.exclude_patterns.text().strip()
        if patterns_text:
            # Split by comma or newline
            patterns = [p.strip() for p in patterns_text.replace('\n', ',').split(',') if p.strip()]
            self.config.scan.exclude_patterns = patterns
        else:
            self.config.scan.exclude_patterns = []
        
        # Export settings
        self.config.export.auto_detect_exports = self.auto_detect_exports.isChecked()
        self.config.export.fuzzy_match_threshold = float(self.fuzzy_threshold.value())
        
        # Link settings
        self.config.link.enabled = self.link_enabled.isChecked()
        self.config.link.scan_interval_seconds = self.scan_interval.value()
        self.config.link.show_offline_devices = self.show_offline.isChecked()
        
        # Save configuration
        save_config()
        
        self.accept()
