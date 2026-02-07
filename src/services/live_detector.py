"""Service for detecting installed Ableton Live versions."""

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from ..utils.logging import get_logger


@dataclass
class LiveVersion:
    """Represents an installed Ableton Live version."""

    version: str  # e.g., "11.3.13"
    path: Path  # Path to Live executable
    build: str | None = None  # Build number if available
    is_suite: bool = False  # True if Live Suite, False if Standard/Intro

    def __str__(self) -> str:
        suite_str = " Suite" if self.is_suite else ""
        return f"Live {self.version}{suite_str}"


class LiveDetector:
    """Detects installed Ableton Live versions on the system."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self._versions: list[LiveVersion] = []
        self._scan()

    def get_versions(self) -> list[LiveVersion]:
        """Get all detected Live versions, sorted by version (newest first)."""
        return sorted(self._versions, key=lambda v: self._parse_version(v.version), reverse=True)

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

    def _scan_windows(self) -> None:
        """Scan for Live on Windows."""
        # Common installation base paths on Windows
        program_files = Path(os.environ.get("ProgramFiles", "C:\\Program Files"))
        program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"))
        program_data = Path(os.environ.get("ProgramData", "C:\\ProgramData"))
        local_appdata = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))

        # Base paths that might contain an "Ableton" folder
        base_search_paths = [
            program_files,
            program_files_x86,
            program_data,  # C:\ProgramData\Ableton
            local_appdata,
            appdata,
        ]

        import re

        # Scan all base paths for "Ableton" folders
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

                            # Try multiple possible locations for Live.exe
                            possible_paths = [
                                item / "Live.exe",  # Direct in Live folder
                                item / "Program" / "Ableton Live.exe",  # In Program subfolder
                                item
                                / "Program"
                                / f"Ableton Live {version_num}.exe",  # Versioned in Program
                            ]

                            # Also check for Suite/Standard variants in Program folder
                            suite_variants = [
                                item / "Program" / f"Ableton Live {version_num} Suite.exe",
                                item / "Program" / f"Ableton Live {version_num} Standard.exe",
                            ]
                            possible_paths.extend(suite_variants)

                            # For Live 10, 11, 12, also check common alternative naming
                            if major_version in [10, 11, 12]:
                                # Check for "Live X Suite" or "Live X Standard" folder names with executable
                                possible_paths.extend(
                                    [
                                        item / f"Live {major_version}.exe",  # Simple version
                                        item
                                        / "Program"
                                        / f"Live {major_version}.exe",  # In Program
                                    ]
                                )

                            live_exe = None
                            for exe_path in possible_paths:
                                self.logger.debug(f"Checking for Live.exe at: {exe_path}")
                                if exe_path.exists():
                                    live_exe = exe_path
                                    self.logger.debug(f"Found Live.exe: {live_exe}")
                                    break

                            if live_exe:
                                # Try to extract full version from executable file properties first
                                # This gives us the exact version (e.g., 12.3.5) instead of just major (12)
                                version_str = self._get_exe_version(live_exe)

                                # Fallback to folder name version if executable version extraction fails
                                if not version_str or version_str == version_num:
                                    version_str = version_num
                                    self.logger.debug(
                                        f"Using version from folder name: {version_str}"
                                    )
                                else:
                                    self.logger.debug(
                                        f"Extracted version from executable: {version_str} (folder had: {version_num})"
                                    )

                                # Check if it's Suite (Standard is default if not Suite)
                                # Check both folder name and executable name
                                is_suite = (
                                    "Suite" in item.name
                                    or "Suite" in live_exe.name
                                    or self._check_suite_windows(item)
                                )

                                # Avoid duplicates (check if we already have this path)
                                if not any(v.path == live_exe for v in self._versions):
                                    self.logger.info(
                                        f"Adding Live version: {version_str} {'Suite' if is_suite else 'Standard'} at {live_exe}"
                                    )
                                    self._versions.append(
                                        LiveVersion(
                                            version=version_str, path=live_exe, is_suite=is_suite
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
        # Common installation paths on macOS
        applications = Path("/Applications")
        user_applications = Path.home() / "Applications"

        # Also check common user data locations
        library_app_support = Path.home() / "Library" / "Application Support" / "Ableton"

        search_paths = [applications, user_applications]

        for base_path in search_paths:
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
                            # Live executable is inside the .app bundle
                            live_exe = item / "Contents" / "MacOS" / "Live"
                            if live_exe.exists():
                                # Try to extract full version from Info.plist first
                                # This gives us the exact version (e.g., 12.3.5) instead of just major (12)
                                version_str = self._get_exe_version(live_exe)

                                # Fallback to folder name version if Info.plist extraction fails
                                if not version_str or version_str == version_num:
                                    version_str = version_num
                                    self.logger.debug(
                                        f"Using version from folder name: {version_str}"
                                    )
                                else:
                                    self.logger.debug(
                                        f"Extracted version from Info.plist: {version_str} (folder had: {version_num})"
                                    )

                                # Check if it's Suite
                                is_suite = "Suite" in item.name or self._check_suite_macos(item)

                                # Avoid duplicates
                                if not any(v.path == live_exe for v in self._versions):
                                    self.logger.info(
                                        f"Adding Live version: {version_str} {'Suite' if is_suite else 'Standard'} at {live_exe}"
                                    )
                                    self._versions.append(
                                        LiveVersion(
                                            version=version_str, path=live_exe, is_suite=is_suite
                                        )
                                    )
            except (PermissionError, OSError):
                # Skip paths we can't access
                continue

        # Also check Application Support for additional installations
        if library_app_support.exists():
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
        """Parse version string to tuple for sorting (e.g., "11.3.13" -> (11, 3, 13))."""
        try:
            parts = [int(x) for x in version_str.split(".")]
            # Pad with zeros for consistent sorting
            while len(parts) < 3:
                parts.append(0)
            return tuple(parts[:3])
        except ValueError:
            return (0, 0, 0)

    def refresh(self) -> None:
        """Rescan for Live versions."""
        self._scan()
