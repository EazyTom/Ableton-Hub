"""Ableton Hub - Cross-platform Ableton project organizer."""

# Single source of truth for version - reads from pyproject.toml via importlib.metadata
# When installed via pip, this reads from package metadata
# When running from source, falls back to the hardcoded version below
_FALLBACK_VERSION = "0.3.0"

try:
    from importlib.metadata import version as get_version
    __version__ = get_version("ableton-hub")
except Exception:
    # Not installed as package, use fallback
    __version__ = _FALLBACK_VERSION

__author__ = "Tom Carlile"
__email__ = "carlile.tom@gmail.com"

# What's New / Changelog - single source for About dialog and documentation
# Update this when releasing new versions
WHATS_NEW = {
    "version": __version__,
    "features": [
        ("Tempo Filtering & Sorting", "Filter projects by tempo range (60-90, 90-120, 120-150, 150+ BPM or custom range) with always-visible controls in the search bar"),
        ("Enhanced List View", "Click column headers to sort by Name, Location, Tempo, Modified date, and more"),
        ("Audio Playback", "Play exported audio files directly from the project details dialog with full transport controls (WAV, AIFF, MP3, FLAC, OGG, M4A)"),
        ("Backup & Archive", "Configure a backup location and archive projects with one click; view all project backups"),
        ("Live Preferences Access", "Right-click installed Live versions to open Preferences folder or edit Options.txt"),
        ("Packs Browser", "Quick access links to Core Library, User Library, Factory Packs, and Ableton Pack Store"),
        ("MCP Servers Links", "Sidebar section with links to popular Ableton MCP server projects for AI integration"),
        ("Smart Collection Tempo Rules", "Create dynamic collections filtered by tempo range"),
        ("Visual Export Indicators", "Distinct icons for projects with/without exports"),
        ("Rainbow Tempo Colors", "Visual BPM indicator on project cards with color-coded tempo display (purple=60 BPM → red=200+ BPM)"),
    ]
}


def get_whats_new_html() -> str:
    """Generate HTML for What's New section (used in About dialog)."""
    items = "\n".join(
        f"<li><b>{title}</b> - {desc}</li>"
        for title, desc in WHATS_NEW["features"]
    )
    return f"""
    <h2 style="color: #FF764D;">🆕 What's New (v{__version__})</h2>
    <ul>
        {items}
    </ul>
    """


def get_whats_new_markdown() -> str:
    """Generate Markdown for What's New section (useful for README updates)."""
    items = "\n".join(
        f"- **{title}**: {desc}"
        for title, desc in WHATS_NEW["features"]
    )
    return f"## 🆕 What's New (v{__version__})\n\n{items}"
