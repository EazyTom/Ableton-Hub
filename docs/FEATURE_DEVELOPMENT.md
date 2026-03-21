# Ableton Hub - Feature Development Status

This document tracks all features that have been implemented and those planned for future development.

---

## ✅ Completed Features

### Core Functionality

#### Project Discovery & Management
- ✅ Multi-location scanning for `.als` project files (local drives, network shares, cloud storage)
- ✅ Automatic file watching with real-time detection of new, modified, or deleted projects
- ✅ Rich metadata extraction from `.als` files:
  - Plugins and devices used
  - Tempo and time signature
  - Musical key and scale type (C Major, D# Minor, etc.)
  - Track counts (audio, MIDI, return tracks)
  - Arrangement length
  - Ableton Live version
  - Sample references
  - Automation status
- ✅ SHA256 file hash tracking for duplicate detection and integrity verification
- ✅ Project health dashboard with health score metrics
- ✅ Visual export indicators on project cards
- ✅ Missing project detection and cleanup tools

#### Collections & Organization
- ✅ Static collections (albums, EPs, sessions, compilations, custom)
- ✅ Smart collections with rule-based dynamic filtering:
  - Filter by tags, locations, date ranges
  - Filter by plugins, devices, project metadata
  - Filter by rating, favorites, export status
  - Filter by tempo range (min/max BPM)
  - Filter by similarity to reference project
- ✅ Track management within collections (custom names, artwork, drag-and-drop reordering)
- ✅ Collection types with distinct icons

#### Search & Discovery
- ✅ Full-text search (FTS5) across project names, export names, notes, tags, plugins, devices
- ✅ Advanced filtering (date ranges, locations, tags, plugins, tempo)
- ✅ Search modes (name, export name, tags, notes)
- ✅ Real-time debounced search results
- ✅ Always-visible tempo filter with preset ranges

#### Project Similarity & Discovery
- ✅ Jaccard similarity algorithm for plugin and device overlap
- ✅ Multi-metric comparison (plugins, devices, tempo, structure, feature vectors)
- ✅ Weighted similarity scoring (0-100%)
- ✅ Similar projects in Project Details Dialog
- ✅ "Find Similar Projects" context menu option
- ✅ Recommendations Panel with similarity-based suggestions
- ✅ Smart Collections similarity filter rule
- ✅ Visual similarity indicators on project cards

#### ML/AI Infrastructure (Phase 5)
- ✅ Enhanced ALS parser with extended metadata extraction (device chains, clips, routing, automation)
- ✅ ASD clip file parser for warp markers, transients, and timing data
- ✅ ML Feature Extraction service combining ALS metadata with audio analysis (librosa)
- ✅ Project Similarity Analyzer using cosine similarity, Jaccard similarity, weighted metrics
- ✅ ML Clustering Service (K-means, DBSCAN, Hierarchical) for project grouping
- ✅ Recommendation Engine for similar projects, plugin suggestions, auto-tagging

#### Export Tracking
- ✅ Automatic export detection during project scanning
- ✅ Smart fuzzy matching for export-to-project linking (exact → normalized → fuzzy)
- ✅ Export metadata tracking (format, bit depth, sample rate, file size)
- ✅ Export-to-project mapping with confidence scoring
- ✅ Visual export status indicators (green border, 🔊 icon)
- ✅ Custom export song name for improved matching

#### Audio Preview & Playback
- ✅ Waveform thumbnail generation from exported audio
- ✅ Click-to-play on project cards (cycle through multiple exports)
- ✅ Status bar playback display with filename
- ✅ In-app audio playback with full transport controls
- ✅ Support for WAV, AIFF, MP3, FLAC, OGG, M4A formats
- ✅ Volume control and seek slider

#### Duplicate Detection
- ✅ Hash-based duplicate detection (SHA256)
- ✅ Name-based similarity matching (85% threshold)
- ✅ Location-based detection (same name in different locations)
- ✅ Duplicate reports in Health Dashboard

#### Backup & Archive
- ✅ Configurable backup location in sidebar
- ✅ Project backups view in Project Properties dialog
- ✅ Backup project launch (double-click to open in Live)
- ✅ Automatic backup detection in Backup folders
- ✅ Archive service for compressed (ZIP) project backups
- ✅ One-click archive to backup location
- ✅ Backup .als files excluded from main project grid

#### Location Management
- ✅ Multiple location types (local, network, cloud, USB, custom)
- ✅ Favorite locations with color coding
- ✅ Active/inactive status with project counts
- ✅ Last scan timestamp tracking
- ✅ Bulk scan all active locations

#### Tagging System
- ✅ Flexible tagging with categories
- ✅ Color-coded tags for visual organization
- ✅ Full CRUD operations for tags
- ✅ Tag-based filtering

#### Ableton Live Integration
- ✅ Automatic Live version detection (9.x, 10.x, 11.x, 12.x)
- ✅ Live launcher with version selection
- ✅ Quick launch (double-click projects)
- ✅ Preferences folder access per Live version
- ✅ Options.txt editing/creation

#### Ableton Link Network
- ✅ Link device discovery and monitoring
- ✅ Real-time Link network status
- ✅ Device information display (name, IP address)

#### Release Infrastructure & UX (v1.0.3–v1.0.10)
- ✅ Startup Soundcheck service — plays audio on launch to verify output; custom sound file support; 440 Hz sine fallback if no file found
- ✅ Automatic Update Checker — queries GitHub releases API on startup; UpdateDialog with download link; configurable via `check_for_updates_at_startup`
- ✅ FTUE first-launch dialog — renders `FTUE.md` as HTML for new users
- ✅ Song Name Generator — service and dialog for generating random creative project names
- ✅ Select Exports Dialog — two-column UI (DB exports + filesystem browse) for manually linking audio exports to projects

#### User Interface
- ✅ Multiple themes (Orange, Blue, Green, Pink)
- ✅ Grid and list views with toggle
- ✅ Sortable list view (Name, Location, Tempo, Key, Version, Modified, etc.)
- ✅ Rainbow tempo colors on project cards (color-coded BPM display)
- ✅ MCP servers integration links in sidebar
- ✅ Learning resources links (Ableton docs, trainers, user groups)

---

## 🔄 In Progress / Infrastructure Complete

### ML Clustering Visualization
- ✅ ML Clustering service (K-means, DBSCAN, Hierarchical) - **Complete** — includes `ClusterInfo` dataclass with `avg_tempo`, `common_plugins`, `common_devices`, `suggested_label`, `silhouette_score`
- ⏳ Cluster visualization UI widget - **Not started**
- ⏳ Auto-organize by cluster feature - **Not started**

### Plugin Usage Analytics
- ✅ Plugin extraction from ALS files - **Complete**
- ✅ Plugin data in feature vectors - **Complete**
- ⏳ Plugin usage dashboard UI - **Not started**
- ⏳ "Projects using this plugin" filter - **Not started**

### Workflow Analytics
- ✅ Project metadata timestamps (created, modified) - **Complete**
- ✅ Health metrics calculation - **Complete**
- ⏳ Workflow analytics dashboard UI - **Not started**
- ⏳ Productivity trends visualization - **Not started**

---

## ❌ Planned Features (Not Yet Developed)

### High Priority
- **Plugin Usage Dashboard**: Dedicated UI showing most-used plugins, plugin combinations, missing plugin warnings
- **Workflow Analytics Dashboard**: Timeline visualization, productivity charts, project lifecycle metrics
- **ML Cluster Visualization**: Visual grouping of similar projects, cluster labeling, smart collection suggestions

### Medium Priority
- **Project Versioning & History**: Automatic version detection, version timeline, version comparison
- **Project Templates**: Save/load project templates, template library, usage tracking
- **Time Tracking**: Manual/automatic time entry per project, time reports, productivity insights
- **Export Presets & Batch Export**: Save export settings, apply to multiple projects, batch export queue

### Lower Priority
- **Statistics & Analytics Dashboard**: Project creation timeline, tag usage trends, visual charts
- **Project Archiving**: Archive policies, archive location management, restore from archive
- **Custom Metadata Fields**: User-defined fields (text, number, date, dropdown), field templates
- **Workflow Automation**: Custom scripts, bulk operations, scheduled tasks

### Future Consideration
- **Ableton Lesson Integration**: Browse built-in lessons, lesson TOC viewer
- **Cloud Sync Integration**: Sync project metadata across devices
- **Project Sharing**: Export/import metadata and collections


---

## Technical Dependencies

### Currently Installed
- PyQt6 >= 6.10.0 (UI Framework)
- SQLAlchemy >= 2.0.0 (Database ORM)
- watchdog >= 6.0.0 (File System Monitoring)
- zeroconf >= 0.148.0 (Ableton Link Discovery)
- qasync >= 0.28.0 (Async Qt Integration)
- aiosqlite >= 0.22.0 (Async SQLite)
- Pillow >= 12.0.0 (Image Processing)
- rapidfuzz >= 3.14.0 (Fuzzy Matching)
- scikit-learn >= 1.8.0 (ML Clustering)
- numpy >= 2.0.0 (Numerical Computing)
- pandas >= 3.0.0 (Data Analysis)
- librosa >= 0.11.0 (Audio Analysis)
- soundfile >= 0.13.0 (Audio File I/O)
- lxml >= 6.0.0 (XML Parsing)
- markdown >= 3.5.0 (FTUE / User Guide rendering)

---

*Last updated: March 2026 (v1.0.10)*
