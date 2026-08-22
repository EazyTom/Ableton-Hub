"""Tests for Live version parsing and sorting helpers."""

from __future__ import annotations

import pytest
from pathlib import Path

from src.database.models import LiveInstallation, Project
from src.services.live_detector import LiveDetector, LiveVersion
from src.utils.live_version import (
    compare_live_versions,
    extract_live_version_token,
    is_prerelease_version,
    parse_live_major_version,
    parse_version_sort_key,
)


class TestLiveVersionUtils:
    def test_extract_live_version_token(self) -> None:
        assert extract_live_version_token("Ableton Live 13.0.1") == "13.0.1"
        assert extract_live_version_token("Ableton Live 12.4a1") == "12.4a1"
        assert extract_live_version_token("Live 11.3.13") == "11.3.13"

    def test_parse_live_major_version(self) -> None:
        assert parse_live_major_version("Ableton Live 13.0.1") == 13
        assert parse_live_major_version("Ableton Live 12.4a1") == 12
        assert parse_live_major_version("Ableton Live 8.0") is None

    def test_is_prerelease_version(self) -> None:
        assert is_prerelease_version("12.4a1") is True
        assert is_prerelease_version("13.1b2") is True
        assert is_prerelease_version("13 Beta") is True
        assert is_prerelease_version("12.3.5") is False

    def test_parse_live_folder_label(self) -> None:
        from src.utils.live_version import parse_live_folder_label

        major, label, is_pre = parse_live_folder_label("Live 13 Beta")
        assert major == 13
        assert label == "13 Beta"
        assert is_pre is True

    def test_parse_version_sort_key_order(self) -> None:
        assert parse_version_sort_key("13.0") > parse_version_sort_key("12.4")
        assert parse_version_sort_key("12.4") > parse_version_sort_key("12.4a1")
        assert parse_version_sort_key("12.4a1") > parse_version_sort_key("12.3")

    def test_compare_live_versions(self) -> None:
        assert compare_live_versions("13.0", "12.4") == 1
        assert compare_live_versions("12.4a1", "12.4") == -1


class TestProjectModelLiveVersion:
    def test_get_live_version_major_live_13(self) -> None:
        project = Project(ableton_version="Ableton Live 13.0.1")
        assert project.get_live_version_major() == 13
        assert project.get_live_version_display() == "v13"

    def test_get_live_version_major_alpha(self) -> None:
        project = Project(ableton_version="Ableton Live 12.4a1")
        assert project.get_live_version_major() == 12
        assert project.get_live_version_full_display() == "v12.4a1"


class TestLiveInstallationModel:
    def test_get_major_version_live_13(self) -> None:
        install = LiveInstallation(
            name="Live 13",
            version="13.0.1",
            executable_path="C:/Program Files/Ableton/Live 13/Live.exe",
        )
        assert install.get_major_version() == 13

    def test_get_major_version_alpha(self) -> None:
        install = LiveInstallation(
            name="Live 12 Alpha",
            version="12.4a1",
            executable_path="C:/Program Files/Ableton/Live 12.4a1/Live.exe",
        )
        assert install.get_major_version() == 12

    def test_get_major_version_live_13_beta(self) -> None:
        install = LiveInstallation(
            name="Live 13 Beta",
            version="13 Beta",
            executable_path="C:/ProgramData/Ableton/Live 13 Beta/Program/Ableton Live 13 Beta.exe",
        )
        assert install.get_major_version() == 13


class TestLiveDetectorSorting:
    def test_parse_version_with_prerelease(self) -> None:
        detector = LiveDetector.__new__(LiveDetector)
        assert detector._parse_version("13.0") > detector._parse_version("12.4a1")
        assert detector._parse_version("12.4") > detector._parse_version("12.4a1")

    def test_windows_exe_candidates_live_13_beta(self, tmp_path: Path) -> None:
        install_dir = tmp_path / "Live 13 Beta"
        program_dir = install_dir / "Program"
        program_dir.mkdir(parents=True)
        exe = program_dir / "Ableton Live 13 Beta.exe"
        exe.write_bytes(b"MZ")

        detector = LiveDetector.__new__(LiveDetector)
        detector.logger = __import__("logging").getLogger("test")

        found = detector._find_windows_live_exe(install_dir, "13", 13)
        assert found == exe

    def test_live_version_str_shows_prerelease(self) -> None:
        version = LiveVersion(version="12.4a1", path=Path("."))
        assert "Pre-release" in str(version)

        beta_version = LiveVersion(version="13 Beta", path=Path("."), is_prerelease=True)
        assert "Pre-release" in str(beta_version)
