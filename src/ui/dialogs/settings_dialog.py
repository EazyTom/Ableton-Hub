"""Settings dialog for Ableton Hub."""

from pathlib import Path

from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...config import Config, save_config
from ...database import LiveInstallation, Location, get_session
from ...utils.logging import get_logs_directory
from ..theme import AbletonTheme


class SettingsDialog(QDialog):
    """Settings dialog for application configuration."""

    def __init__(
        self,
        config: Config,
        parent: QWidget | None = None,
        initial_tab: str | None = None,
    ):
        """Initialize the settings dialog.

        Args:
            config: Application configuration object.
            parent: Parent widget (typically MainWindow).
            initial_tab: Optional tab to open to ("live", "locations", etc.).
        """
        super().__init__(parent)
        self.config = config
        self._initial_tab = initial_tab
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Settings")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Tab widget for different settings categories
        self.tabs = QTabWidget()

        # General tab
        general_tab = self._create_general_tab()
        self.tabs.addTab(general_tab, "General")

        # Scanning tab
        scanning_tab = self._create_scanning_tab()
        self.tabs.addTab(scanning_tab, "Scanning")

        # Live tab
        live_tab = self._create_live_tab()
        self.tabs.addTab(live_tab, "Live")

        # Locations tab
        locations_tab = self._create_locations_tab()
        self.tabs.addTab(locations_tab, "Locations")

        # Export tab
        export_tab = self._create_export_tab()
        self.tabs.addTab(export_tab, "Exports")

        # Link tab
        link_tab = self._create_link_tab()
        self.tabs.addTab(link_tab, "Link")

        # Logging tab
        logging_tab = self._create_logging_tab()
        self.tabs.addTab(logging_tab, "Logging")

        layout.addWidget(self.tabs)

        # Switch to initial tab if requested
        if self._initial_tab == "live":
            self.tabs.setCurrentWidget(live_tab)
        elif self._initial_tab == "locations":
            self.tabs.setCurrentWidget(locations_tab)

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
        current_theme = getattr(self.config.ui, "theme", "orange")
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
        waveform_group = QGroupBox("Waveform Color Gradient")
        waveform_layout = QVBoxLayout(waveform_group)

        self.waveform_group = QButtonGroup(self)

        # Get current waveform color mode
        current_waveform_mode = getattr(self.config.ui, "waveform_color_mode", "rainbow")

        # Waveform color mode options (gradients only, solid colors disabled)
        waveform_modes = {
            "rainbow": "Rainbow",
            "dark_blue_cyan": "Dark Blue → Cyan",
            "orange_red": "Orange → Red",
            "purple_cyan": "Purple → Cyan",
            "green_red": "Green → Red",
            "pink_orange": "Pink → Orange",
            "teal_blue": "Teal → Blue",
            "yellow_green": "Yellow → Green",
            "magenta_pink": "Magenta → Pink",
            "cyan_green": "Cyan → Green",
            "random": "Random (Per Project, Changes on Rescan)",
        }

        self.waveform_radios = {}
        for idx, (mode_id, mode_name) in enumerate(waveform_modes.items()):
            radio = QRadioButton(mode_name)
            radio.setChecked(current_waveform_mode == mode_id)
            self.waveform_group.addButton(radio, idx)
            self.waveform_radios[mode_id] = radio
            waveform_layout.addWidget(radio)

        # Info label
        info_text = (
            "Note: Existing thumbnails will keep their current colors.\n"
            "Use 'Clear Thumbnail Cache' in Tools menu to regenerate.\n\n"
            "Random mode: Each project gets a random color gradient, which changes when you rescan."
        )
        info_label = QLabel(info_text)
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

    def _create_live_tab(self) -> QWidget:
        """Create the Live installations tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        live_group = QGroupBox("Ableton Live Installations")
        live_layout = QVBoxLayout(live_group)

        # List of current installations
        self.live_list = QListWidget()
        self.live_list.setMaximumHeight(180)
        live_layout.addWidget(QLabel("Configured installations:"))
        live_layout.addWidget(self.live_list)
        self._refresh_live_list()

        # Buttons
        live_btn_layout = QHBoxLayout()
        add_live_btn = QPushButton("Add Live Installation...")
        add_live_btn.clicked.connect(self._on_add_live_installation)
        live_btn_layout.addWidget(add_live_btn)

        auto_detect_btn = QPushButton("Auto-Detect")
        auto_detect_btn.clicked.connect(self._on_auto_detect_live)
        live_btn_layout.addWidget(auto_detect_btn)

        live_btn_layout.addStretch()
        live_layout.addLayout(live_btn_layout)

        info_label = QLabel(
            "Add Ableton Live installations to open projects by double-clicking. "
            "Use Auto-Detect to find installations in default locations."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #888; font-size: 10px;")
        live_layout.addWidget(info_label)

        layout.addWidget(live_group)
        layout.addStretch()
        return widget

    def _create_locations_tab(self) -> QWidget:
        """Create the Locations tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        loc_group = QGroupBox("Project Locations")
        loc_layout = QVBoxLayout(loc_group)

        # List of current locations
        self.locations_list = QListWidget()
        self.locations_list.setMaximumHeight(180)
        loc_layout.addWidget(QLabel("Configured locations:"))
        loc_layout.addWidget(self.locations_list)
        self._refresh_locations_list()

        # Add button
        add_loc_btn = QPushButton("Add Location...")
        add_loc_btn.clicked.connect(self._on_add_location)
        loc_layout.addWidget(add_loc_btn)

        info_label = QLabel(
            "Locations are folders that contain Ableton projects. "
            "Add folders to scan and index your projects."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #888; font-size: 10px;")
        loc_layout.addWidget(info_label)

        layout.addWidget(loc_group)
        layout.addStretch()
        return widget

    def _refresh_live_list(self) -> None:
        """Refresh the Live installations list."""
        self.live_list.clear()
        with get_session() as session:
            installations = (
                session.query(LiveInstallation)
                .order_by(LiveInstallation.version.desc())
                .all()
            )
            for install in installations:
                fav = " ★" if install.is_favorite else ""
                path_short = install.executable_path
                if len(path_short) > 50:
                    path_short = "..." + path_short[-47:]
                text = f"{install.name} (v{install.version}){fav}\n  {path_short}"
                item = QListWidgetItem(text)
                item.setData(100, install.id)
                self.live_list.addItem(item)

    def _refresh_locations_list(self) -> None:
        """Refresh the locations list."""
        self.locations_list.clear()
        with get_session() as session:
            locations = session.query(Location).order_by(Location.name).all()
            for loc in locations:
                path_short = loc.path
                if len(path_short) > 50:
                    path_short = "..." + path_short[-47:]
                active = "✓" if loc.is_active else "○"
                text = f"{loc.name} [{active}]\n  {path_short}"
                item = QListWidgetItem(text)
                item.setData(100, loc.id)
                self.locations_list.addItem(item)

    def _on_add_live_installation(self) -> None:
        """Open Add Live Installation dialog."""
        from .add_live_installation import AddLiveInstallationDialog

        main_window = self.parent()
        dialog = AddLiveInstallationDialog(main_window)
        if dialog.exec():
            self._refresh_live_list()
            if main_window and hasattr(main_window, "_refresh_sidebar"):
                main_window._refresh_sidebar()

    def _on_auto_detect_live(self) -> None:
        """Run auto-detect for Live installations."""
        from ...services.live_detector import LiveDetector

        detector = LiveDetector()
        detected_versions = detector.get_versions()

        if not detected_versions:
            QMessageBox.information(
                self,
                "No Versions Found",
                "No Ableton Live installations were detected in default locations.\n\n"
                "You can manually add an installation using 'Add Live Installation...'",
            )
            return

        with get_session() as session:
            added_count = 0
            skipped_count = 0

            for version in detected_versions:
                existing = (
                    session.query(LiveInstallation)
                    .filter(LiveInstallation.executable_path == str(version.path))
                    .first()
                )
                if existing:
                    skipped_count += 1
                    continue

                install = LiveInstallation(
                    name=str(version),
                    version=version.version,
                    executable_path=str(version.path),
                    build=version.build,
                    is_suite=version.is_suite,
                    is_auto_detected=True,
                )
                session.add(install)
                added_count += 1

            session.commit()

        self._refresh_live_list()
        main_window = self.parent()
        if main_window and hasattr(main_window, "_refresh_sidebar"):
            main_window._refresh_sidebar()

        if added_count > 0:
            msg = f"Added {added_count} installation(s)."
            if skipped_count:
                msg += f" {skipped_count} already configured."
            QMessageBox.information(self, "Auto-Detect Complete", msg)
        elif skipped_count > 0:
            QMessageBox.information(
                self,
                "Auto-Detect Complete",
                "All detected installations are already configured.",
            )

    def _on_add_location(self) -> None:
        """Open Add Location dialog."""
        from .add_location import AddLocationDialog

        main_window = self.parent()
        dialog = AddLocationDialog(main_window)
        if dialog.exec():
            self._refresh_locations_list()
            if main_window and hasattr(main_window, "_refresh_sidebar"):
                main_window._refresh_sidebar()
            if main_window and hasattr(main_window, "location_panel"):
                main_window.location_panel.refresh()

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

    def _create_logging_tab(self) -> QWidget:
        """Create the logging settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        # File logging settings
        file_group = QGroupBox("File Logging")
        file_layout = QVBoxLayout(file_group)

        self.logging_enabled = QCheckBox("Enable file logging")
        self.logging_enabled.setChecked(self.config.logging.enabled)
        file_layout.addWidget(self.logging_enabled)

        # Log level
        level_layout = QHBoxLayout()
        level_layout.addWidget(QLabel("Log level:"))
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        current_level = self.config.logging.level.upper()
        index = self.log_level_combo.findText(current_level)
        if index >= 0:
            self.log_level_combo.setCurrentIndex(index)
        else:
            self.log_level_combo.setCurrentText("ERROR")
        level_layout.addWidget(self.log_level_combo)
        level_layout.addStretch()
        file_layout.addLayout(level_layout)

        layout.addWidget(file_group)

        # Log file settings
        file_settings_group = QGroupBox("Log File Settings")
        file_settings_layout = QVBoxLayout(file_settings_group)

        # Log directory
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Log directory:"))
        self.log_dir_edit = QLineEdit()
        if self.config.logging.log_dir:
            self.log_dir_edit.setText(self.config.logging.log_dir)
        else:
            # Show default location
            default_dir = get_logs_directory()
            self.log_dir_edit.setText(str(default_dir))
            self.log_dir_edit.setPlaceholderText(f"Default: {default_dir}")
        dir_layout.addWidget(self.log_dir_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_log_directory)
        dir_layout.addWidget(browse_btn)
        file_settings_layout.addLayout(dir_layout)

        # Current log file location (read-only)
        current_log_label = QLabel()
        current_log_path = get_logs_directory(self.config.logging) / "ableton_hub.log"
        current_log_label.setText(f"Current log file: {current_log_path}")
        current_log_label.setWordWrap(True)
        current_log_label.setStyleSheet("color: #888; font-size: 10px;")
        file_settings_layout.addWidget(current_log_label)

        # Max file size
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Max file size (MB):"))
        self.max_file_size = QSpinBox()
        self.max_file_size.setRange(1, 100)
        self.max_file_size.setValue(self.config.logging.max_bytes // (1024 * 1024))
        size_layout.addWidget(self.max_file_size)
        size_layout.addStretch()
        file_settings_layout.addLayout(size_layout)

        # Backup count
        backup_layout = QHBoxLayout()
        backup_layout.addWidget(QLabel("Number of backup files:"))
        self.backup_count = QSpinBox()
        self.backup_count.setRange(1, 20)
        self.backup_count.setValue(self.config.logging.backup_count)
        backup_layout.addWidget(self.backup_count)
        backup_layout.addStretch()
        file_settings_layout.addLayout(backup_layout)

        # Info label
        info_label = QLabel(
            "Note: Changes to logging settings require restarting the application to take effect.\n\n"
            "Log files are automatically rotated when they reach the maximum size. "
            "The error log (ableton_hub_errors.log) contains only ERROR and CRITICAL messages."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #888; font-size: 10px;")
        file_settings_layout.addWidget(info_label)

        layout.addWidget(file_settings_group)

        layout.addStretch()
        return widget

    def _browse_log_directory(self) -> None:
        """Browse for log directory."""
        current_dir = self.log_dir_edit.text() or str(get_logs_directory())
        directory = QFileDialog.getExistingDirectory(
            self, "Select Log Directory", current_dir, QFileDialog.Option.ShowDirsOnly
        )
        if directory:
            self.log_dir_edit.setText(directory)

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
            patterns = [p.strip() for p in patterns_text.replace("\n", ",").split(",") if p.strip()]
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

        # Logging settings
        self.config.logging.enabled = self.logging_enabled.isChecked()
        self.config.logging.level = self.log_level_combo.currentText()
        log_dir_text = self.log_dir_edit.text().strip()
        if log_dir_text and Path(log_dir_text).is_dir():
            self.config.logging.log_dir = log_dir_text
        else:
            # Reset to default if invalid
            self.config.logging.log_dir = None
        self.config.logging.max_bytes = self.max_file_size.value() * 1024 * 1024
        self.config.logging.backup_count = self.backup_count.value()

        # Check if logging settings changed
        logging_changed = (
            self.logging_enabled.isChecked() != self.config.logging.enabled
            or self.log_level_combo.currentText() != self.config.logging.level
            or (log_dir_text and log_dir_text != str(get_logs_directory(self.config.logging)))
        )

        # Save configuration
        save_config()

        # Warn if logging settings changed
        if logging_changed:
            QMessageBox.information(
                self,
                "Restart Required",
                "Logging settings have been saved.\n\n"
                "Please restart the application for the changes to take effect.",
            )

        self.accept()
