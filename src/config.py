"""Configuration manager for Ableton Hub."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .utils.logging import get_logger
from .utils.paths import get_config_path


@dataclass
class WindowConfig:
    """Window geometry and state configuration."""

    width: int = 1400
    height: int = 900
    x: int | None = None
    y: int | None = None
    maximized: bool = False
    sidebar_width: int = 250
    sidebar_collapsed: bool = False


@dataclass
class ScanConfig:
    """File scanning configuration."""

    recursive_depth: int = 10
    auto_scan_on_startup: bool = False  # Changed to False - scan only on button press
    scan_frequency_hours: int = 24
    exclude_patterns: list[str] = field(
        default_factory=lambda: [
            "**/Backup/**",
            "**/Ableton Project Info/**",
            "**/.git/**",
            "**/node_modules/**",
        ]
    )
    include_hidden: bool = False


@dataclass
class ExportConfig:
    """Export tracking configuration."""

    export_folders: list[str] = field(default_factory=list)
    auto_detect_exports: bool = True
    export_formats: list[str] = field(
        default_factory=lambda: [".wav", ".mp3", ".flac", ".aiff", ".aif"]
    )
    fuzzy_match_threshold: float = 65.0


@dataclass
class LinkConfig:
    """Ableton Link configuration."""

    enabled: bool = False
    scan_interval_seconds: int = 5
    show_offline_devices: bool = True
    device_history_days: int = 30


@dataclass
class LoggingConfig:
    """Logging configuration."""

    enabled: bool = True  # File logging enabled by default
    level: str = "ERROR"  # Default: ERROR for production
    log_dir: str | None = None  # None = use default (%APPDATA%/AbletonHub/logs)
    max_bytes: int = 10 * 1024 * 1024  # 10MB per file
    backup_count: int = 5  # Keep 5 rotated files


@dataclass
class UIConfig:
    """User interface configuration."""

    theme: str = "orange"  # "orange", "blue", "green", "pink"
    default_view: str = "grid"  # "grid" or "list"
    grid_card_size: int = 200
    show_status_bar: bool = True
    confirm_delete: bool = True
    date_format: str = "%Y-%m-%d %H:%M"
    # Gradient modes only: "rainbow", "random", or gradient options (solid colors disabled)
    waveform_color_mode: str = "random"


@dataclass
class Config:
    """Main configuration container."""

    window: WindowConfig = field(default_factory=WindowConfig)
    scan: ScanConfig = field(default_factory=ScanConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    link: LinkConfig = field(default_factory=LinkConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    first_run: bool = True
    version: str = "1.0.7"


class ConfigManager:
    """Manages application configuration persistence."""

    def __init__(self, config_path: Path | None = None):
        """Initialize the configuration manager.

        Args:
            config_path: Optional custom path for config file.
        """
        self.config_path = config_path or get_config_path()
        self._config: Config | None = None

    @property
    def config(self) -> Config:
        """Get the current configuration, loading from disk if needed."""
        if self._config is None:
            self._config = self.load()
        return self._config

    def load(self) -> Config:
        """Load configuration from disk.

        Returns:
            Config object (defaults if file doesn't exist).
        """
        if not self.config_path.exists():
            return Config()

        try:
            with open(self.config_path, encoding="utf-8") as f:
                data = json.load(f)
            return self._dict_to_config(data)
        except (OSError, json.JSONDecodeError) as e:
            logger = get_logger(__name__)
            logger.warning(f"Failed to load config: {e}")
            return Config()

    def save(self) -> None:
        """Save current configuration to disk."""
        if self._config is None:
            return

        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._config_to_dict(self._config), f, indent=2)
        except OSError as e:
            logger = get_logger(__name__)
            logger.warning(f"Failed to save config: {e}")

    def reset(self) -> Config:
        """Reset configuration to defaults.

        Returns:
            New default Config object.
        """
        self._config = Config()
        self.save()
        return self._config

    def update(self, **kwargs: Any) -> None:
        """Update configuration values.

        Args:
            **kwargs: Configuration keys and values to update.
        """
        config = self.config
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        self.save()

    def _config_to_dict(self, config: Config) -> dict:
        """Convert Config dataclass to dictionary for JSON serialization."""
        return {
            "window": asdict(config.window),
            "scan": asdict(config.scan),
            "export": asdict(config.export),
            "link": asdict(config.link),
            "logging": asdict(config.logging),
            "ui": asdict(config.ui),
            "first_run": config.first_run,
            "version": config.version,
        }

    def _dict_to_config(self, data: dict) -> Config:
        """Convert dictionary to Config dataclass."""
        return Config(
            window=WindowConfig(**data.get("window", {})),
            scan=ScanConfig(**data.get("scan", {})),
            export=ExportConfig(**data.get("export", {})),
            link=LinkConfig(**data.get("link", {})),
            logging=LoggingConfig(**data.get("logging", {})),
            ui=UIConfig(**data.get("ui", {})),
            first_run=data.get("first_run", True),
            version=data.get("version", "1.0.1"),
        )


# Global configuration manager instance
_config_manager: ConfigManager | None = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> Config:
    """Get the current configuration."""
    return get_config_manager().config


def save_config() -> None:
    """Save the current configuration."""
    get_config_manager().save()
