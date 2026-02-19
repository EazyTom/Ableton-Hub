"""Ableton Hub - Cross-platform Ableton project organizer."""

# Single source of truth for version - reads from pyproject.toml via importlib.metadata
# When installed via pip, this reads from package metadata
# When running from source, falls back to the hardcoded version below
_FALLBACK_VERSION = "1.0.8"

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
        (
            "FTUE Startup Guide",
            (
                "First-time user experience guide walks you through setup: "
                "adding locations, detecting Live versions, and key features"
            ),
        ),
        (
            "Auto-Add Location",
            (
                "Automatically add default Ableton project folders as locations "
                "when starting fresh or from the sidebar"
            ),
        ),
        (
            "Find Audio Export Tool",
            (
                "Map exports to projects in a dedicated list view; "
                "find orphaned exports and link them to the right .als files"
            ),
        ),
        (
            "Random Song Name Generator",
            (
                "Generate creative project names for new ideas; "
                "handy tool when starting blank sessions"
            ),
        ),
        (
            "Dependency Upgrades",
            (
                "Updated dependencies for macOS and Windows installers; "
                "improved compatibility and security"
            ),
        ),
        (
            "Stability Fixes",
            (
                "Code cleanup and stability improvements across the app; "
                "more reliable scanning, watcher, and UI"
            ),
        ),
    ],
}

# Previous release highlights (for reference in About dialog)
PREVIOUS_FEATURES = [
    (
        "Bugfixes (thx PAG!)",
        (
            "Various bugfixes submitted by PAG; "
            "improved handling when no Live installation is configured, "
            "add Live installs and Locations from Settings menu"
        ),
    ),
    (
        "Jaccard Similarity Fixed",
        (
            "Plugin and device similarity matching now works correctly; "
            "fixed double-serialization bug that caused set comparisons on individual "
            "characters instead of plugin/device names"
        ),
    ),
    (
        "Plugin Detection Working",
        (
            "Fixed VST2/VST3/AU plugin detection that was reading XML attributes "
            "instead of child elements; added VST3 support via Vst3PluginInfo"
        ),
    ),
    (
        "Device Detection Rewritten",
        (
            "Replaced broken hardcoded device list with dynamic detection from "
            "XML Devices containers; catches all native Ableton devices including "
            "Drift, Meld, Echo, Hybrid Reverb, and any future devices"
        ),
    ),
    (
        "Arrangement vs Session Clips",
        (
            "Arrangement length now only counts clips on the arrangement timeline; "
            "session clip lengths (recorded samples) tracked separately and shown "
            "in tooltip and Project Information"
        ),
    ),
    (
        "More Project Metadata",
        (
            "Project Information now shows time signature, track type breakdown "
            "(Audio/MIDI/Return), timeline markers, annotation, and session clip length"
        ),
    ),
    (
        "JSON Storage Fix",
        (
            "Fixed double-encoding of all JSON fields (plugins, devices, samples, "
            "markers, export filenames) in scanner and watcher; "
            "all dict builders now use safe deserialization helpers"
        ),
    ),
    (
        "Faster UI Navigation",
        (
            "Navigating between project views is now near-instant; "
            "background workers are properly cancelled when leaving views"
        ),
    ),
    (
        "Persistent Metadata in Database",
        (
            "Export filenames, annotations, master track names, and ML feature vectors "
            "are now stored in the database during scanning, eliminating redundant ALS parsing"
        ),
    ),
    (
        "Optimized Similarity Analysis",
        (
            "Similar project lookups use pre-computed feature vectors from the database "
            "instead of re-parsing ALS files on demand"
        ),
    ),
    (
        "Automatic Export Detection",
        (
            "Scans for exported audio files during project scanning with "
            "smart fuzzy matching (exact → normalized → fuzzy)"
        ),
    ),
    (
        "Click-to-Play Exports",
        (
            "Single-click project cards with exports to instantly play audio; "
            "click again to cycle through multiple exports"
        ),
    ),
    (
        "In-App Audio Playback",
        (
            "Play exported audio files from project details with full transport controls "
            "(WAV, AIFF, MP3, FLAC, OGG, M4A)"
        ),
    ),
    (
        "Backup Project Management",
        (
            "Backup .als files automatically excluded from grid; "
            "view and launch backups from Project Properties dialog"
        ),
    ),
    (
        "Missing Project Detection",
        (
            "Automatically marks missing projects; toggle View Missing Projects in View menu; "
            "cleanup tools in Tools menu"
        ),
    ),
    (
        "Duplicate Detection",
        (
            "Find duplicate projects using SHA256 hash comparison, "
            "name similarity, and location-based detection"
        ),
    ),
    (
        "Tempo Filtering & Sorting",
        (
            "Filter projects by tempo range (60-90, 90-120, 120-150, 150+ BPM or custom range) "
            "with always-visible controls"
        ),
    ),
    (
        "Enhanced List View",
        "Click column headers to sort by Name, Location, Tempo, Modified date, and more",
    ),
    ("Backup & Archive", "Configure a backup location and archive projects with one click"),
    (
        "Live Preferences Access",
        ("Right-click installed Live versions to open Preferences folder " "or edit Options.txt"),
    ),
    (
        "MCP Agents Links",
        ("Sidebar section with links to popular Ableton MCP server projects " "for AI integration"),
    ),
    (
        "Comprehensive Testing Framework",
        (
            "Release validation test harness (test_release.py) with code quality checks, "
            "essential feature testing, and ML integration verification"
        ),
    ),
    ("Smart Collection Tempo Rules", "Create dynamic collections filtered by tempo range"),
    ("Visual Export Indicators", "Distinct icons for projects with/without exports"),
    (
        "Rainbow Tempo Colors",
        (
            "Visual BPM indicator on project cards with color-coded tempo display "
            "(purple=60 BPM → red=200+ BPM)"
        ),
    ),
]


def get_whats_new_html() -> str:
    """Generate HTML for What's New section (used in About dialog)."""
    items = "\n".join(f"<li><b>{title}</b> - {desc}</li>" for title, desc in WHATS_NEW["features"])
    return f"""
    <h2 style="color: #FF764D;">🆕 What's New (v{__version__})</h2>
    <ul>
        {items}
    </ul>
    """


def get_whats_new_markdown() -> str:
    """Generate Markdown for What's New section (useful for README updates)."""
    items = "\n".join(f"- **{title}**: {desc}" for title, desc in WHATS_NEW["features"])
    return f"## 🆕 What's New (v{__version__})\n\n{items}"
