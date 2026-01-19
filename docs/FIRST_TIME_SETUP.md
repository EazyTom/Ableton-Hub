# First Time Setup Guide

Welcome to Ableton Hub! This guide will walk you through what to expect when you first launch the application and how to get started.

## What to Expect on First Launch

When you first open Ableton Hub, you'll see:

1. **An empty project grid** - This is normal! You haven't added any project locations yet.
2. **A sidebar on the left** - This is where you'll manage locations, collections, and settings.
3. **A toolbar at the top** - Contains buttons for scanning, searching, and other actions.
4. **A status bar at the bottom** - Shows messages and progress information.

Don't worry if it looks empty - we'll add your projects in the next steps!

## Step 1: Add Your First Location

A "location" is a folder on your computer (or network drive) that contains Ableton Live projects.

1. **Click "Add Location"** in the sidebar (or go to File → Add Location)

2. **Select a folder** that contains your Ableton projects:
   - Common locations:
     - `~/Music/Ableton/` (macOS)
     - `~/Documents/Ableton/` (macOS)
     - `C:\Users\YourName\Documents\Ableton\` (Windows)
     - `C:\Users\YourName\Music\Ableton\` (Windows)
   - You can also browse to any folder where you keep `.als` files

3. **Choose a location type**:
   - **Local** - Projects on your computer's hard drive
   - **Network** - Projects on a network share or NAS
   - **Cloud** - Projects in cloud storage (Dropbox, OneDrive, etc.)
   - **USB** - Projects on an external drive

4. **Click "OK"** to add the location

The location will now appear in your sidebar under "Locations". You can add multiple locations if your projects are spread across different folders or drives.

## Step 2: Scan for Projects

Now that you've added a location, you need to scan it to find all your Ableton projects.

1. **Click the "Scan" button** in the toolbar (or go to File → Scan All Locations)

2. **Wait for the scan to complete**:
   - You'll see progress in the status bar at the bottom
   - The scan may take a few minutes depending on:
     - How many projects you have
     - How many subfolders need to be searched
     - Whether the projects are on a network drive (slower)
   - You can continue using the app while scanning, but it's best to wait until it finishes

3. **What happens during scanning**:
   - Ableton Hub finds all `.als` files in your location(s)
   - It reads metadata from each project file (tempo, plugins, tracks, etc.)
   - It looks for exported audio files and links them to projects
   - It creates a searchable index of all your projects

4. **When scanning completes**:
   - Projects will appear in the main grid view
   - You'll see project cards with names, tempo, and other info
   - Projects with exports will show a 🔊 icon

## Step 3: Understanding the Interface

### Project Grid View

The main area shows your projects as cards:
- **Project name** - The name of your `.als` file
- **Tempo** - Shows the BPM (beats per minute) with a color-coded indicator
- **Location** - Which folder/drive the project is on
- **Export indicator** - 🔊 icon means the project has linked exports
- **Favorite indicator** - 💎 icon means you've marked it as a favorite

**Double-click any project** to open it in Ableton Live!

### Sidebar

The left sidebar contains:
- **Locations** - Folders you're scanning for projects
- **Collections** - Groups of related projects (albums, EPs, etc.)
- **Live Installations** - Detected Ableton Live versions
- **Learning & Reference** - Links to Ableton resources
- **Tools** - Backup location, Link network, etc.

### Search Bar

At the top, you'll find:
- **Search box** - Type to search project names, exports, tags, plugins
- **Date filters** - Filter by when projects were created/modified
- **Tempo filters** - Quick buttons for tempo ranges (60-90, 90-120, etc.)
- **View toggle** - Switch between grid and list view

### Menu Bar

- **File** - Add locations, scan, settings
- **View** - Change view mode, show/hide missing projects
- **Tools** - Advanced tools and utilities
- **Help** - Documentation and about

## Step 4: Next Steps After First Scan

Once your projects are loaded, here are some things to try:

### Explore Your Projects

- **Click a project card** to see details in the right panel
- **Double-click a project** to open it in Ableton Live
- **Right-click a project** for more options (favorite, add to collection, etc.)

### Search and Filter

- **Type in the search bar** to find projects by name
- **Use tempo filters** to find projects in a specific BPM range
- **Use date filters** to find recent projects
- **Switch to list view** to see more details and sort by different columns

### Create a Collection

Collections let you group related projects together:

1. Click "New Collection" in the sidebar
2. Give it a name (e.g., "My Album", "WIP Tracks")
3. Choose a type (Album, EP, Session, etc.)
4. Drag projects from the grid into the collection

### Add Tags

Tags help you categorize projects:

1. Right-click a project → "Edit Tags"
2. Create or select tags
3. Use tags to filter projects later

### Check Out Exports

If you see projects with a 🔊 icon:
- **Click the project card** to play the export
- **Click again** to cycle through multiple exports
- **View in project details** for full playback controls

## Common First-Time Questions

### Why don't I see all my projects?

- Make sure you've added all the folders where your projects are stored
- Click "Scan All Locations" to rescan
- Check that `.als` files are actually in those folders
- Some projects might be in Backup folders (these are hidden by default)

### How do I change which Live version opens projects?

- Right-click a Live installation in the sidebar → "Set as Favorite"
- Or right-click a project → "Open With" → select a Live version

### Can I scan network drives or cloud storage?

Yes! When adding a location, choose "Network" or "Cloud" as the type. Note that scanning network drives may be slower than local drives.

### What if I move or delete a project file?

- Ableton Hub will mark it as "MISSING" on the next scan
- You can view missing projects: View → Show Missing Projects
- Clean them up: Tools → Clean Up Missing Projects

### How do I organize projects better?

- **Collections** - Group related projects (albums, EPs)
- **Tags** - Add categories (WIP, Finished, Remix, etc.)
- **Favorites** - Mark important projects with 💎
- **Smart Collections** - Auto-updating collections based on rules

## Getting More Help

- **[Quick Reference](QUICK_REFERENCE.md)** - Common tasks and shortcuts
- **[FAQ](FAQ.md)** - Answers to frequently asked questions
- **Help menu** - Access documentation from within the app
- **GitHub Issues** - Report bugs or request features

## Tips for Success

1. **Be patient on first scan** - It may take several minutes if you have many projects
2. **Add all your project locations** - Don't forget external drives or network shares
3. **Use collections** - They make it much easier to find related projects
4. **Tag as you go** - Add tags when you create or finish projects
5. **Regular scans** - The app watches for changes, but you can manually scan anytime

Enjoy organizing your Ableton projects! 🎵
