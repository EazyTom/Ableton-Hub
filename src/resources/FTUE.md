# Getting Started with Ableton Hub

A comprehensive cross-platform desktop application for organizing, managing, and discovering Ableton Live projects.

---

## Key Workflows

### 1. Adding Project Locations

- **File → Add Location** (or click "+ Add Location" in the sidebar)
- Select a folder containing your `.als` project files
- Choose location type: **Local**, **Network**, **Cloud**, or **USB**
- Click **Scan All** to discover projects in your locations
- Once projects are loaded, **audio preview** lets you audition exports directly—click the 🔊 icon on project cards to play linked exports, or use the play button in Find Audio Exports when mapping files

### 2. Defining Collections and Tagging Projects

**Collections** help you group related projects—perfect for preparing albums, EPs, or session compilations. Create a collection, give it a name and type (Album, EP, Session, etc.), then drag projects from the grid into it. Reorder tracks with drag-and-drop to define your album sequence. Add artwork and track names for a polished overview.

**Tags** let you categorize projects across your library. Right-click a project → **Edit Tags** to add labels like "WIP", "Finished", "Remix", or "Mastered". Filter by tags in search to quickly find projects in a given state. Use tags and collections together: tag candidates for an album, then build a collection from the filtered results.

*For artists preparing releases:* Create an **Album** or **EP** collection, add your chosen tracks in order, and use the collection view to review the flow before exporting. Smart Collections can auto-update based on rules (e.g., "projects tagged Finished from the last 6 months") so your release candidates stay current.

### 3. Adding Audio Export Locations

- Use the same **Add Location** flow for folders that contain exported audio
- Export folders can be separate from project roots (e.g., a shared "Exports" folder)
- Add each export location as its own location for discovery

### 4. Finding Audio Exports & Mapping to Projects

- Go to **Locations** in the sidebar
- Select a location and click **Find Audio Exports**
- Scans for `.wav`, `.mp3`, `.flac`, `.aiff`, etc.
- **Preview before mapping:** Click the ▶ play button next to any file to audition it. Click again to stop. Preview helps you confirm you're linking the right export to the right project.
- Map unmapped files to projects via the **Associate to Project** dropdown—select a project to link the export. Use fuzzy matching when filenames resemble project names.

### 5. Finding Project Similarities

- Click **Similarities** in the sidebar (between Recent and Favorites)
- Select a project to see similar projects by plugins, devices, tempo, and structure
- Or right-click any project → **Find Similar Projects** for a detailed dialog

### 6. Adding Live Installs

- **Settings → Live** tab, or sidebar **Add Live Installation**
- Use **Auto-Detect** to find installed Ableton Live versions, or browse to the executable
- Required for **double-click to open** projects from the grid

### 7. Documentation Hub

The **Learning** section in the sidebar is your hub for Ableton docs and community links. No need to leave the app—click any item to open in your browser:

- **Getting Started:** Learning Music, Making Music, Ableton Help, Learn Live, Official YouTube
- **Community:** Ableton Discord, Certified Trainers, Ableton User Groups
- **Reference:** Live Manual, Move Manual, Live API Overview, Live Object Model
- **Max for Live:** Learn Max, Max Documentation, Building Max Devices, M4L Production Guidelines

Use the Documentation Hub when you need a quick reference or want to share resources with collaborators.

---

## Backup & Project Backups

### Backup Location (Sidebar → BACKUPS)

- **Set Backup Location** — Choose a folder where Ableton Hub will store project archives (ZIP backups). Use this for long-term storage or moving projects off your main drive.
- **Open Backup Folder** — Quickly open the backup folder in your file manager.

### Project Backups (Ableton's Backup Folder)

Ableton Live saves versioned backups of your projects in a `Backup` subfolder. Ableton Hub:

- **Excludes** Backup-folder projects from the main grid by default (keeps the grid focused on current projects)
- **Shows** all backup versions in **Project Properties** — click a project, then scroll to "Available Project Backups"
- **Launch** any backup — double-click a backup in the list to open it in Live (useful for recovering an older version)
- **Clean up** — Tools → Remove Backup Projects from Database to remove Backup-folder entries from the database if desired

### Archive to ZIP

Configure a backup location, then archive projects to create compressed ZIP backups. Useful for backing up finished work or moving projects to cold storage.

---

## Feature Highlights

- **Project Discovery** — Multi-location scanning, file watching, rich metadata (plugins, tempo, tracks), **audio preview** (click-to-play exports on project cards and in Find Audio Exports)
- **Collections** — Static collections (albums, EPs) and Smart Collections with dynamic rules
- **Search** — Full-text search across names, exports, notes, plugins, devices
- **Export Tracking** — Automatic detection, fuzzy matching, click-to-play on project cards, preview in Find Audio Exports
- **Live Integration** — Version auto-detection, project launcher, preferences folder access
- **Backup** — Backup location, project backup viewing and launch, archive to ZIP
- **Documentation Hub** — Quick access to Ableton docs, learning resources, and community links

---

## Tips for New Users

1. **Add locations first** — The app needs at least one project location before it can show projects.
2. **Scan after adding** — Click Scan All (or use the toolbar) to discover projects in your locations.
3. **Double-click to open** — Ensure a Live installation is added (Settings → Live) so double-click works.
4. **Use the User Guide** — Help → User Guide to reopen this guide anytime.

---

## Disclaimer

*This application is not affiliated with or endorsed by Ableton AG. Ableton Live is a trademark of Ableton AG.*
