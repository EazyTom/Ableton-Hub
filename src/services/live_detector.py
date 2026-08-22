"""Service for detecting installed Ableton Live versions."""

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from ..utils.logging import get_logger


@dataclass
class LiveVersion:
    """Represents an installed Ableton Live version."""

    version: str  # e.g., "11.3.13", "12.4a1", "13.0.1"
    path: Path  # Path to Live executable
    build: str | None = None  # Build number if available
    is_suite: bool = False  # True if Live Suite, False if Standard/Intro
    is_prerelease: bool = False  # True for alpha/beta/rc builds

    def __post_init__(self) -> None:
        from ..utils.live_version import is_prerelease_version

        if not self.is_prerelease:
            self.is_prerelease = is_prerelease_version(self.version)

    def __str__(self) -> str:
        suite_str = " Suite" if self.is_suite else ""
        pre_str = " (Pre-release)" if self.is_prerelease else ""
        return f"Live {self.version}{suite_str}{pre_str}"


class LiveDetector:
    """Detects installed Ableton Live versions on the system."""

    def __init__(
        self,
        *,
        scan_default_locations: bool = True,
        scan_extended_locations: bool = True,
    ):
        self.logger = get_logger(__name__)
        self._scan_default_locations = scan_default_locations
        self._scan_extended_locations = scan_extended_locations
        self._versions: list[LiveVersion] = []
        self._scan()

    @classmethod
    def from_config(cls, config=None) -> "LiveDetector":
        """Build a detector using application Live detection settings."""
        if config is None:
            from ..config import get_config

            config = get_config()
        return cls(
            scan_default_locations=config.live.scan_default_install_locations,
            scan_extended_locations=config.live.scan_extended_install_locations,
        )

    @staticmethod
    def get_default_windows_base_paths() -> list[Path]:
        """Standard Windows folders that contain ``Ableton\\Live *`` installs."""
        return [
            Path(os.environ.get("ProgramData", "C:\\ProgramData")),
            Path(os.environ.get("ProgramFiles", "C:\\Program Files")),
            Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")),
        ]

    @staticmethod
    def get_extended_windows_base_paths() -> list[Path]:
        """Additional Windows folders that may contain Ableton installs."""
        return [
            Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")),
            Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")),
        ]

    @staticmethod
    def get_default_macos_app_paths() -> list[Path]:
        """Standard macOS application folders for ``Live *.app`` bundles."""
        return [Path("/Applications"), Path.home() / "Applications"]

    @staticmethod
    def get_extended_macos_paths() -> list[Path]:
        """Additional macOS Ableton support folders."""
        return [Path.home() / "Library" / "Application Support" / "Ableton"]

    @classmethod
    def describe_default_install_locations(cls) -> str:
        """Human-readable summary of default scan paths for the current OS."""
        if sys.platform == "win32":
            lines = [
                f"{base / 'Ableton'}" for base in cls.get_default_windows_base_paths()
            ]
            return "Windows default folders:\n" + "\n".join(f"  • {line}" for line in lines)
        if sys.platform == "darwin":
            lines = [str(path) for path in cls.get_default_macos_app_paths()]
            return "macOS default folders:\n" + "\n".join(f"  • {line}" for line in lines)
        return "Default Ableton install folders for this platform."

    def _windows_base_search_paths(self) -> list[Path]:
        paths: list[Path] = []
        if self._scan_default_locations:
            paths.extend(self.get_default_windows_base_paths())
        if self._scan_extended_locations:
            paths.extend(self.get_extended_windows_base_paths())
        # Preserve order while removing duplicates
        seen: set[str] = set()
        unique_paths: list[Path] = []
        for path in paths:
            key = str(path).lower()
            if key not in seen:
                seen.add(key)
                unique_paths.append(path)
        return unique_paths

    def get_versions(self) -> list[LiveVersion]:
        """Get all detected Live versions, sorted by version (newest first)."""
        return sorted(
            self._versions,
            key=lambda v: self._parse_version(v.version),
            reverse=True,
        )

    def detect_all(self) -> list[LiveVersion]:
        """Alias for get_versions() used by LiveController."""
        self.refresh()
        return self.get_versions()

    def get_version_by_path(self, path: Path) -> LiveVersion | None:
        """Get Live version by executable path."""
        for version in self._versions:
            if version.path == path:
                return version
        return None

    def _scan(self) -> None:
        """Scan for installed Live versions."""
        self._versions.clear()

        if sys.platform == "win32":
            self._scan_windows()
        elif sys.platform == "darwin":
            self._scan_macos()
        else:
            self._scan_linux()

    def _windows_live_exe_candidates(
        self, install_dir: Path, version_num: str, major_version: int
    ) -> list[Path]:
        """Build candidate Live executables for a Windows install folder."""
        candidates: list[Path] = [
            install_dir / "Live.exe",
            install_dir / "Program" / "Ableton Live.exe",
            install_dir / "Program" / f"Ableton Live {version_num}.exe",
            install_dir / "Program" / f"Ableton Live {install_dir.name}.exe",
            install_dir / "Program" / f"Ableton {install_dir.name}.exe",
            install_dir / "Program" / f"Ableton Live {version_num} Suite.exe",
            install_dir / "Program" / f"Ableton Live {version_num} Standard.exe",
            install_dir / f"Live {major_version}.exe",
            install_dir / "Program" / f"Live {major_version}.exe",
        ]

        program_dir = install_dir / "Program"
        if program_dir.is_dir():
            for pattern in ("Ableton Live*.exe", "Live*.exe"):
                for exe_path in sorted(program_dir.glob(pattern)):
                    if exe_path not in candidates:
                        candidates.append(exe_path)

        return candidates

    def _find_windows_live_exe(
        self, install_dir: Path, version_num: str, major_version: int
    ) -> Path | None:
        """Return the first existing Live executable for an install folder."""
        for exe_path in self._windows_live_exe_candidates(
            install_dir, version_num, major_version
        ):
            self.logger.debug(f"Checking for Live.exe at: {exe_path}")
            if exe_path.exists():
                self.logger.debug(f"Found Live.exe: {exe_path}")
                return exe_path
        return None

    def _resolve_install_version_label(
        self, install_dir: Path, version_num: str, live_exe: Path
    ) -> str:
        """Resolve a display/install version string from PE metadata and folder name."""
        from ..utils.live_version import parse_live_folder_label

        version_str = self._get_exe_version(live_exe)
        _, folder_label, _ = parse_live_folder_label(install_dir.name)

        if version_str and version_str != version_num:
            return version_str
        if folder_label:
            return folder_label
        return version_num

    def _is_prerelease_install(self, install_dir: Path, version_str: str) -> bool:
        from ..utils.live_version import is_prerelease_version, parse_live_folder_label

        _, _, folder_prerelease = parse_live_folder_label(install_dir.name)
        return folder_prerelease or is_prerelease_version(version_str)

    def _scan_windows(self) -> None:
        """Scan for Live on Windows."""
        base_search_paths = self._windows_base_search_paths()
        if not base_search_paths:
            self.logger.debug("Windows Live scan skipped: no search paths enabled")
            return

        import re

        # Scan enabled base paths for "Ableton" folders
        for base_path in base_search_paths:
            self.logger.debug(f"Checking base path: {base_path}")
            if not base_path.exists():
                self.logger.debug(f"Base path does not exist: {base_path}")
                continue

            try:
                # Look for "Ableton" folder in this base path
                ableton_folder = base_path / "Ableton"
                self.logger.debug(f"Checking for Ableton folder: {ableton_folder}")
                if not ableton_folder.exists():
                    self.logger.debug(f"Ableton folder does not exist: {ableton_folder}")
                    # Also check if there are any folders starting with "Ableton" or containing "Live"
                    try:
                        for item in base_path.iterdir():
                            if item.is_dir() and ("Ableton" in item.name or "Live" in item.name):
                                self.logger.debug(f"Found potential Ableton/Live folder: {item}")
                    except (PermissionError, OSError):
                        pass
                    continue

                if not ableton_folder.is_dir():
                    self.logger.debug(f"Path exists but is not a directory: {ableton_folder}")
                    continue

                self.logger.debug(f"Found Ableton folder: {ableton_folder}, scanning contents...")

                # Now scan inside the Ableton folder for Live installations
                # Support Live 10, Live 11, Live 12, and future versions
                found_items = []
                for item in ableton_folder.iterdir():
                    found_items.append(item.name)
                    if not item.is_dir():
                        continue

                    self.logger.debug(f"Checking item in Ableton folder: {item.name}")

                    # Match patterns like:
                    # - "Live 10", "Live 11", "Live 12"
                    # - "Live 10 Suite", "Live 11 Standard", "Live 12 Suite"
                    # - "Live 10.1.30", "Live 11.3.13", "Live 12.0.5"
                    # - "Live 10 Suite 10.1.30", "Live 11 Standard 11.3.13", etc.
                    # Regex matches Live followed by version number (10, 11, 12, or any future version)
                    # Captures full version including hotfix and beta (e.g., "12.3.5", "12.0.5b1", "11.3.13rc2")
                    live_match = re.match(
                        r"^Live\s+(\d+(?:\.\d+)*(?:[a-zA-Z]+\d+)?)", item.name, re.IGNORECASE
                    )
                    if live_match:
                        version_num = live_match.group(1)
                        # Extract major version (10, 11, or 12) for validation
                        major_version = int(version_num.split(".")[0])

                        # Only process Live 10, 11, 12 (and future versions >= 10)
                        if major_version >= 10:
                            self.logger.debug(
                                f"Matched Live pattern: {item.name} -> version {version_num} (major: {major_version})"
                            )

                            live_exe = self._find_windows_live_exe(item, version_num, major_version)

                            if live_exe:
                                version_str = self._resolve_install_version_label(
                                    item, version_num, live_exe
                                )
                                self.logger.debug(f"Resolved install version label: {version_str}")

                                # Check if it's Suite (Standard is default if not Suite)
                                # Check both folder name and executable name
                                is_suite = (
                                    "Suite" in item.name
                                    or "Suite" in live_exe.name
                                    or self._check_suite_windows(item)
                                )
                                is_prerelease = self._is_prerelease_install(item, version_str)

                                # Avoid duplicates (check if we already have this path)
                                if not any(v.path == live_exe for v in self._versions):
                                    self.logger.info(
                                        f"Adding Live version: {version_str} {'Suite' if is_suite else 'Standard'} at {live_exe}"
                                    )
                                    self._versions.append(
                                        LiveVersion(
                                            version=version_str,
                                            path=live_exe,
                                            is_suite=is_suite,
                                            is_prerelease=is_prerelease,
                                        )
                                    )
                            else:
                                self.logger.debug(
                                    f"Live.exe not found in any expected location for: {item.name}"
                                )
                        else:
                            self.logger.debug(
                                f"Skipping Live version {major_version} (only supporting Live 10+)"
                            )
                            continue
                    else:
                        self.logger.debug(f"Item does not match Live pattern: {item.name}")

                if found_items:
                    self.logger.debug(f"All items in {ableton_folder}: {', '.join(found_items)}")
            except (PermissionError, OSError) as e:
                self.logger.warning(f"Error accessing {base_path}: {e}")
                # Skip paths we can't access
                continue

    def _scan_macos(self) -> None:
        """Scan for Live on macOS."""
        app_search_paths: list[Path] = []
        if self._scan_default_locations:
            app_search_paths.extend(self.get_default_macos_app_paths())
        if not app_search_paths and not self._scan_extended_locations:
            self.logger.debug("macOS Live scan skipped: no search paths enabled")
            return

        library_app_support = None
        if self._scan_extended_locations:
            library_app_support = self.get_extended_macos_paths()[0]

        for base_path in app_search_paths:
            if not base_path.exists():
                continue

            try:
                # Look for Live X.X.app bundles
                # Support Live 10, Live 11, Live 12, and future versions
                for item in base_path.iterdir():
                    if not item.is_dir() or item.suffix != ".app":
                        continue

                    # Match patterns like:
                    # - "Live 10.app", "Live 11.app", "Live 12.app"
                    # - "Live 10 Suite.app", "Live 11 Standard.app", "Live 12 Suite.app"
                    # - "Live 10.1.30.app", "Live 11.3.13.app", "Live 12.0.5.app"
                    import re

                    from ..utils.live_version import parse_live_folder_label

                    # Captures full version including hotfix and beta (e.g., "12.3.5", "12.0.5b1")
                    live_match = re.match(
                        r"^Live\s+(\d+(?:\.\d+)*(?:[a-zA-Z]+\d+)?)", item.stem, re.IGNORECASE
                    )
                    if live_match:
                        version_num = live_match.group(1)
                        major_version_str = re.sub(r"[a-zA-Z].*$", "", version_num.split(".")[0])
                        major_version = int(major_version_str)

                        if major_version >= 10:
                            live_exe = item / "Contents" / "MacOS" / "Live"
                            if live_exe.exists():
                                version_str = self._get_exe_version(live_exe)
                                _, folder_label, folder_prerelease = parse_live_folder_label(
                                    item.stem
                                )

                                if not version_str or version_str == version_num:
                                    version_str = folder_label or version_num
                                is_suite = "Suite" in item.stem or self._check_suite_macos(item)
                                is_prerelease = folder_prerelease or self._is_prerelease_install(
                                    item, version_str
                                )

                                if not any(v.path == live_exe for v in self._versions):
                                    self.logger.info(
                                        f"Adding Live version: {version_str} {'Suite' if is_suite else 'Standard'} at {live_exe}"
                                    )
                                    self._versions.append(
                                        LiveVersion(
                                            version=version_str,
                                            path=live_exe,
                                            is_suite=is_suite,
                                            is_prerelease=is_prerelease,
                                        )
                                    )
            except (PermissionError, OSError):
                # Skip paths we can't access
                continue

        # Also check Application Support for additional installations
        if library_app_support and library_app_support.exists():
            try:
                for item in library_app_support.iterdir():
                    if not item.is_dir():
                        continue

                    # Look for Live folders in Application Support
                    import re

                    # Captures full version including hotfix and beta (e.g., "12.3.5", "12.0.5b1", "11.3.13rc2")
                    live_match = re.match(
                        r"^Live\s+(\d+(?:\.\d+)*(?:[a-zA-Z]+\d+)?)", item.name, re.IGNORECASE
                    )
                    if live_match:
                        version_num = live_match.group(1)
                        # Extract major version (10, 11, or 12) for validation
                        # Remove beta suffix for major version extraction
                        major_version_str = re.sub(r"[a-zA-Z].*$", "", version_num.split(".")[0])
                        major_version = int(major_version_str)

                        # Only process Live 10, 11, 12 (and future versions >= 10)
                        if major_version >= 10:
                            # Some installations might have Live executable here
                            live_exe = item / "Live"
                            if live_exe.exists() and live_exe.is_file():
                                # Try to extract version from executable or nearby files
                                version_str = self._get_exe_version(live_exe)

                                # Fallback to folder name version if extraction fails
                                if not version_str or version_str == version_num:
                                    version_str = version_num
                                    self.logger.debug(
                                        f"Using version from folder name: {version_str}"
                                    )

                                is_suite = "Suite" in item.name or self._check_suite_macos(item)

                                if not any(v.path == live_exe for v in self._versions):
                                    self.logger.info(
                                        f"Adding Live version from Application Support: {version_str} {'Suite' if is_suite else 'Standard'} at {live_exe}"
                                    )
                                    self._versions.append(
                                        LiveVersion(
                                            version=version_str, path=live_exe, is_suite=is_suite
                                        )
                                    )
            except (PermissionError, OSError):
                pass

    def _scan_linux(self) -> None:
        """Scan for Live on Linux (if running via Wine or native)."""
        # Linux paths (less common, but possible)
        home = Path.home()
        search_paths = [
            home / ".wine" / "drive_c" / "Program Files" / "Ableton",
            home / ".local" / "bin",
            Path("/usr/local/bin"),
            Path("/opt/ableton"),
        ]

        for base_path in search_paths:
            if not base_path.exists():
                continue

            if base_path.is_file() and "live" in base_path.name.lower():
                # Single executable
                version_str = self._extract_version_from_path(base_path)
                if version_str:
                    self._versions.append(
                        LiveVersion(
                            version=version_str,
                            path=base_path,
                            is_suite=False,  # Hard to determine on Linux
                        )
                    )
            elif base_path.is_dir():
                # Look for Live folders
                for item in base_path.iterdir():
                    if item.is_dir() and "live" in item.name.lower():
                        live_exe = item / "Live"
                        if live_exe.exists():
                            version_str = self._extract_version_from_path(item)
                            if version_str:
                                self._versions.append(
                                    LiveVersion(version=version_str, path=live_exe, is_suite=False)
                                )

    def _check_suite_windows(self, live_dir: Path) -> bool:
        """Check if this is Live Suite on Windows."""
        # Suite typically has more content or different structure
        # Check for Suite-specific files or folders
        suite_indicators = [
            live_dir / "Max" / "Max.exe",  # Max for Live
            live_dir / "Max.app",  # Max for Live (if bundled)
        ]
        return any(indicator.exists() for indicator in suite_indicators)

    def _check_suite_macos(self, live_app: Path) -> bool:
        """Check if this is Live Suite on macOS."""
        # Check for Max for Live in Contents
        max_path = live_app / "Contents" / "Max"
        return max_path.exists()

    def _get_exe_version(self, exe_path: Path) -> str | None:
        """Extract version from executable file (cross-platform).

        Attempts to extract the full version string from the executable file
        using platform-specific methods:
        - Windows: Reads PE file version info (using win32api if available)
        - macOS: Reads Info.plist from .app bundle
        - Linux: Attempts to read version metadata or falls back to None

        Args:
            exe_path: Path to the executable file (or .app bundle on macOS).

        Returns:
            Version string (e.g., "12.3.5") or None if extraction fails.
        """
        import re

        if sys.platform == "win32":
            return self._get_exe_version_windows(exe_path)
        elif sys.platform == "darwin":
            return self._get_exe_version_macos(exe_path)
        else:
            # Linux: Try to read version from executable metadata
            # This is less reliable, so we'll mainly rely on path parsing
            return None

    def _get_exe_version_windows(self, exe_path: Path) -> str | None:
        """Extract version from Windows executable file properties.

        Uses Windows API via ctypes (standard library, no external dependencies).
        First tries to read the string FileVersion, then falls back to binary version.

        Args:
            exe_path: Path to the executable file.

        Returns:
            Version string (e.g., "12.3.5") or None if extraction fails.
        """
        try:
            import ctypes
            from ctypes import wintypes

            # Load version.dll which contains the version info functions
            version_dll = ctypes.windll.version

            # Get the size needed for version info buffer
            file_path = str(exe_path.resolve())
            size = version_dll.GetFileVersionInfoSizeW(file_path, None)
            if size == 0:
                self.logger.debug(f"GetFileVersionInfoSizeW returned 0 for {file_path}")
                return None

            # Allocate buffer for version info
            buffer = ctypes.create_string_buffer(size)

            # Get version info
            if not version_dll.GetFileVersionInfoW(file_path, 0, size, buffer):
                self.logger.debug(f"GetFileVersionInfoW failed for {file_path}")
                return None

            # First, try to get the language and codepage to read string version
            # Query for translation info
            p_trans = ctypes.POINTER(wintypes.DWORD)()
            u_len = wintypes.UINT()

            if version_dll.VerQueryValueW(
                buffer, "\\VarFileInfo\\Translation", ctypes.byref(p_trans), ctypes.byref(u_len)
            ):
                # Get language and codepage
                lang_codepage = p_trans[0]
                lang = lang_codepage & 0xFFFF
                codepage = (lang_codepage >> 16) & 0xFFFF

                # Format as hex string (e.g., "040904B0" for English/Unicode)
                lang_codepage_str = f"{lang:04X}{codepage:04X}"

                # Try to read FileVersion string
                file_version_key = f"\\StringFileInfo\\{lang_codepage_str}\\FileVersion"
                p_value = ctypes.POINTER(wintypes.LPWSTR)()
                u_len = wintypes.UINT()

                if version_dll.VerQueryValueW(
                    buffer, file_version_key, ctypes.byref(p_value), ctypes.byref(u_len)
                ):
                    version_str = ctypes.wstring_at(p_value)
                    if version_str:
                        # Clean up the version string (remove trailing .0 if present)
                        version_str = version_str.strip()
                        if version_str.endswith(".0"):
                            version_str = version_str[:-2]

                        # Validate it looks like a version string
                        import re

                        if re.match(r"^\d+(?:\.\d+)*(?:[a-zA-Z]+\d+)?$", version_str):
                            self.logger.debug(
                                f"Extracted version from executable (string): {version_str}"
                            )
                            return version_str

            # Fallback: Try to read binary version from VS_FIXEDFILEINFO
            class VS_FIXEDFILEINFO(ctypes.Structure):  # noqa: N801
                _fields_ = [
                    ("dwSignature", wintypes.DWORD),
                    ("dwStrucVersion", wintypes.DWORD),
                    ("dwFileVersionMS", wintypes.DWORD),
                    ("dwFileVersionLS", wintypes.DWORD),
                    ("dwProductVersionMS", wintypes.DWORD),
                    ("dwProductVersionLS", wintypes.DWORD),
                    ("dwFileFlagsMask", wintypes.DWORD),
                    ("dwFileFlags", wintypes.DWORD),
                    ("dwFileOS", wintypes.DWORD),
                    ("dwFileType", wintypes.DWORD),
                    ("dwFileSubtype", wintypes.DWORD),
                    ("dwFileDateMS", wintypes.DWORD),
                    ("dwFileDateLS", wintypes.DWORD),
                ]

            # Query VS_FIXEDFILEINFO (binary version info)
            p_block = ctypes.POINTER(wintypes.DWORD)()
            u_len = wintypes.UINT()

            if version_dll.VerQueryValueW(buffer, "\\", ctypes.byref(p_block), ctypes.byref(u_len)):
                # Cast to VS_FIXEDFILEINFO structure
                p_ffi = ctypes.cast(p_block, ctypes.POINTER(VS_FIXEDFILEINFO))
                ffi = p_ffi.contents

                # Extract version parts (MS = major.minor, LS = build.revision)
                # dwFileVersionMS: high word = major, low word = minor
                # dwFileVersionLS: high word = build, low word = revision
                major = (ffi.dwFileVersionMS >> 16) & 0xFFFF
                minor = ffi.dwFileVersionMS & 0xFFFF
                build = (ffi.dwFileVersionLS >> 16) & 0xFFFF
                revision = ffi.dwFileVersionLS & 0xFFFF

                # Only use if values look reasonable (major version should be >= 9 for Live)
                if major >= 9:
                    version_parts = [major, minor, build]
                    if revision > 0:
                        version_parts.append(revision)

                    # Convert to version string, removing trailing .0 if present
                    version_str = ".".join(str(p) for p in version_parts)
                    if version_str.endswith(".0"):
                        version_str = version_str[:-2]

                    # Validate it looks like a version string
                    import re

                    if re.match(r"^\d+(?:\.\d+)*(?:[a-zA-Z]+\d+)?$", version_str):
                        self.logger.debug(
                            f"Extracted version from executable (binary): {version_str}"
                        )
                        return version_str

        except Exception as e:
            self.logger.debug(
                f"Could not extract version from Windows executable: {e}", exc_info=True
            )

        return None

    def _get_exe_version_macos(self, exe_path: Path) -> str | None:
        """Extract version from macOS .app bundle Info.plist.

        Reads CFBundleShortVersionString or CFBundleVersion from Info.plist
        in the .app bundle.

        Args:
            exe_path: Path to the executable (may be inside .app bundle).

        Returns:
            Version string (e.g., "12.3.5") or None if extraction fails.
        """
        try:
            import plistlib

            # If exe_path is inside an .app bundle, find the .app bundle
            app_bundle = exe_path
            while app_bundle.parent != app_bundle:  # Not at root
                if app_bundle.suffix == ".app":
                    break
                app_bundle = app_bundle.parent
            else:
                # Didn't find .app bundle, try parent directories
                # Check if exe_path is Contents/MacOS/Live inside an .app
                if "Contents" in exe_path.parts and "MacOS" in exe_path.parts:
                    # Go up to find .app bundle
                    parts = list(exe_path.parts)
                    app_idx = None
                    for i, part in enumerate(parts):
                        if part.endswith(".app"):
                            app_idx = i
                            break
                    if app_idx is not None:
                        app_bundle = Path(*parts[: app_idx + 1])
                    else:
                        return None
                else:
                    return None

            # Read Info.plist
            info_plist = app_bundle / "Contents" / "Info.plist"
            if not info_plist.exists():
                return None

            with open(info_plist, "rb") as f:
                plist_data = plistlib.load(f)

            # Try CFBundleShortVersionString first (e.g., "12.3.5")
            version_str = plist_data.get("CFBundleShortVersionString")
            if not version_str:
                # Fallback to CFBundleVersion
                version_str = plist_data.get("CFBundleVersion")

            if version_str:
                # Validate it looks like a version string
                import re

                version_str = str(version_str).strip()
                if re.match(r"^\d+(?:\.\d+)*(?:[a-zA-Z]+\d+)?$", version_str):
                    self.logger.debug(f"Extracted version from Info.plist: {version_str}")
                    return version_str

        except Exception as e:
            self.logger.debug(f"Could not extract version from macOS bundle: {e}")

        return None

    def _extract_version_from_path(self, path: Path) -> str | None:
        """Extract version string from path."""
        name = path.name
        # Try to find version pattern like "11.3" or "11.3.13"
        import re

        # Capture full version including hotfix and beta (e.g., "12.3.5", "12.0.5b1", "11.3.13rc2")
        match = re.search(r"(\d+(?:\.\d+)*(?:[a-zA-Z]+\d+)?)", name)
        if match:
            return match.group(1)
        return None

    def _parse_version(self, version_str: str) -> tuple:
        """Parse version string to tuple for sorting (supports alpha/beta/rc)."""
        from ..utils.live_version import parse_version_sort_key

        return parse_version_sort_key(version_str)

    def refresh(self) -> None:
        """Rescan for Live versions."""
        self._scan()
