"""Tests for Live installation detection helpers."""

from pathlib import Path
from unittest.mock import patch

from src.config import Config, LiveConfig
from src.services.live_detector import LiveDetector


def test_default_windows_base_paths_include_programdata() -> None:
    paths = LiveDetector.get_default_windows_base_paths()
    assert any("ProgramData" in str(path) or path.name == "ProgramData" for path in paths)
    assert len(paths) == 3


def test_default_macos_app_paths() -> None:
    paths = LiveDetector.get_default_macos_app_paths()
    assert paths[0] == Path("/Applications")
    assert paths[1] == Path.home() / "Applications"


def test_describe_default_install_locations_mentions_ableton_on_windows() -> None:
    with patch("src.services.live_detector.sys.platform", "win32"):
        description = LiveDetector.describe_default_install_locations()
    assert "Windows default folders" in description
    assert "Ableton" in description


def test_describe_default_install_locations_on_macos() -> None:
    with patch("src.services.live_detector.sys.platform", "darwin"):
        description = LiveDetector.describe_default_install_locations()
    assert "macOS default folders" in description
    assert "Applications" in description


def test_from_config_respects_live_scan_flags() -> None:
    config = Config(
        live=LiveConfig(
            scan_default_install_locations=False,
            scan_extended_install_locations=True,
        )
    )
    detector = LiveDetector.from_config(config)
    assert detector._scan_default_locations is False
    assert detector._scan_extended_locations is True


def test_windows_base_search_paths_honors_flags() -> None:
    default_only = LiveDetector(scan_default_locations=True, scan_extended_locations=False)
    extended_only = LiveDetector(scan_default_locations=False, scan_extended_locations=True)

    default_paths = default_only._windows_base_search_paths()
    extended_paths = extended_only._windows_base_search_paths()

    assert default_paths
    assert extended_paths
    assert default_paths != extended_paths
