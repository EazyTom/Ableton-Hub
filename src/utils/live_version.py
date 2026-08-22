"""Shared helpers for Ableton Live version strings and sorting."""

from __future__ import annotations

import re
from typing import Any

# Matches "Live 12", "Live 12.4a1", "Live 13.1b2", "Live 13 Beta", etc.
LIVE_VERSION_TOKEN_RE = re.compile(
    r"Live\s+(\d+(?:\.\d+)*(?:[a-zA-Z]+\d+)?(?:\s+(?:Beta|Alpha|RC|Pre))*)",
    re.IGNORECASE,
)
LIVE_FOLDER_NAME_RE = re.compile(r"^Live\s+(.+)$", re.IGNORECASE)
PRERELEASE_WORD_RE = re.compile(r"\b(beta|alpha|rc|pre-release|pre)\b", re.IGNORECASE)
# Matches trailing pre-release suffix on a version segment, e.g. "4a1", "0.5b1"
PRERELEASE_SUFFIX_RE = re.compile(r"([a-zA-Z]+)(\d+)$")
# Validates a bare version token like "12.4a1"
VERSION_TOKEN_RE = re.compile(r"^\d+(?:\.\d+)*(?:[a-zA-Z]+\d+)?$")

# Sort pre-releases before release builds at the same numeric level.
PRERELEASE_KIND_ORDER = {
    "a": 0,
    "alpha": 0,
    "b": 1,
    "beta": 1,
    "rc": 2,
    "pre": 2,
}


def extract_live_version_token(text: str | None) -> str | None:
    """Extract version token from Creator or folder names (e.g. '12.4a1')."""
    if not text:
        return None
    match = LIVE_VERSION_TOKEN_RE.search(text)
    if match:
        return match.group(1)
    match = VERSION_TOKEN_RE.match(text.strip())
    if match:
        return match.group(0)
    return None


def parse_live_major_version(text: str | None, *, min_major: int = 9) -> int | None:
    """Return major Live version from a Creator or install version string."""
    if not text:
        return None

    token = extract_live_version_token(text)
    if not token:
        bare_match = re.match(r"^(\d+)", text.strip())
        if bare_match:
            try:
                major = int(bare_match.group(1))
                return major if major >= min_major else None
            except (ValueError, TypeError):
                return None
        return None

    first_part = token.split()[0].split(".")[0]
    major_str = PRERELEASE_SUFFIX_RE.sub("", first_part)
    try:
        major = int(major_str)
    except (ValueError, TypeError):
        return None
    if major < min_major:
        return None
    return major


def is_prerelease_version(version_str: str | None) -> bool:
    """True when version string contains alpha/beta/rc style suffix."""
    if not version_str:
        return False
    if re.search(r"[a-zA-Z]+\d+", version_str):
        return True
    return bool(PRERELEASE_WORD_RE.search(version_str))


def parse_live_folder_label(folder_name: str) -> tuple[int | None, str | None, bool]:
    """Parse install folder names like ``Live 13 Beta``.

    Returns:
        Tuple of (major_version, version_label, is_prerelease).
    """
    match = LIVE_FOLDER_NAME_RE.match(folder_name.strip())
    if not match:
        return None, None, False

    rest = match.group(1).strip()
    major_match = re.match(r"(\d+)", rest)
    if not major_match:
        return None, None, False

    major = int(major_match.group(1))
    is_prerelease = bool(PRERELEASE_WORD_RE.search(rest))
    return major, rest, is_prerelease


def format_live_version_display(version_str: str | None, *, prefix: str = "Live ") -> str:
    """Human-readable version label for UI."""
    if not version_str:
        return "Unknown"
    token = extract_live_version_token(version_str) or version_str.strip()
    return f"{prefix}{token}"


def parse_version_sort_key(version_str: str | None) -> tuple[int, ...]:
    """Sort key for install/project versions; pre-releases sort before release."""
    if not version_str:
        return (0, 0, 0, 99, 0)

    token = extract_live_version_token(version_str) or version_str.strip()

    word_match = re.match(r"^(\d+(?:\.\d+)*)\s+(Beta|Alpha|RC|Pre)\b", token, re.IGNORECASE)
    if word_match:
        numeric_parts = [int(part) for part in word_match.group(1).split(".")]
        while len(numeric_parts) < 3:
            numeric_parts.append(0)
        kind = word_match.group(2).lower()
        return (
            numeric_parts[0],
            numeric_parts[1],
            numeric_parts[2],
            PRERELEASE_KIND_ORDER.get(kind, 3),
            0,
        )

    parts = token.split(".")
    key: list[int] = []

    for index, part in enumerate(parts):
        suffix_match = PRERELEASE_SUFFIX_RE.search(part)
        if suffix_match:
            numeric = part[: suffix_match.start()]
            kind = suffix_match.group(1).lower()
            number = int(suffix_match.group(2))
            key.append(int(numeric) if numeric else 0)
            key.append(PRERELEASE_KIND_ORDER.get(kind, 3))
            key.append(number)
            # Remaining segments treated as zero
            while len(key) < 5:
                key.append(0)
            return tuple(key[:5])

        try:
            key.append(int(part))
        except ValueError:
            key.append(0)

    # Release build: prerelease rank 99 (sorts after alpha/beta/rc)
    while len(key) < 3:
        key.append(0)
    key.extend([99, 0])
    return tuple(key[:5])


def live_version_order_case(column: Any, *, descending: bool = False) -> Any:
    """Build SQLAlchemy CASE ordering for Project.ableton_version-like columns."""
    from sqlalchemy import case

    # Support Live 9 through 20 without hardcoding every future release in sort logic.
    whens: list[tuple[Any, int]] = []
    order = range(20, 8, -1) if descending else range(9, 21)
    for major in order:
        whens.append((column.like(f"%Live {major}%"), major))
    version_order = case(*whens, else_=0)
    return version_order


def compare_live_versions(left: str | None, right: str | None) -> int:
    """Compare two version strings. Returns -1, 0, or 1."""
    lk = parse_version_sort_key(left)
    rk = parse_version_sort_key(right)
    if lk < rk:
        return -1
    if lk > rk:
        return 1
    return 0
