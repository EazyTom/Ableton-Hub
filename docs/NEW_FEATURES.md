## ✅ COMPLETED FEATURES

- ✅ Use resources/icons/AProject.ico for project icons with no audio export
- ✅ Add new sidebar Section at bottom for managing Ableton MCP servers (GitHub links to projects like https://github.com/ahujasid/ableton-mcp)
- ✅ Add ability to Create Collections from filtered groupings e.g. date range, recent projects, tempo range
  - Smart Collections support tempo range, relative date filters (last X days), absolute date ranges, and more
  - "Create Collection from Current Filter" option in search bar advanced menu
- ✅ Add ability to Filter projects by Tempo range, Sort by Tempo
- ✅ ALS Project deep analysis to find tempo, export locations
- ✅ Saving Song tempo with Hub project metadata when projects are scanned
- ✅ Map project name to export file name - Project -> Song name (in Hub project view)
  - Export Name field in project details with auto-suggest from project name and linked exports
  - Fuzzy matching to link exports to projects
  - "Suggest" button to auto-populate export name
- ✅ Preview/Play project audio wav/aiff/mp3 if ALS project export exists, project icon should be highlighted/colorized
- ✅ Link to version Release notes for each install in the Installs area
- ✅ Determine way to find the Prefs folder for each install in the Installs area - provide a link to open that folder in os file browser
- ✅ Provide button to edit (create if does not exist) Options.txt add to Live prefs folder
- ✅ Add new Ableton Packs section to sidebar to show all the found Packs
- ✅ Create Backups section in sidebar to define Backup Location (only one)
- ✅ Show recent project backups in Hub Project view, they are located in the Backups folder within the Ableton Project folder
- ✅ What is the best method to archive project (copy and zip) into Backup location, allow for update of backup
- ✅ Allow User to Archive Live Project to a defined Backup location
- ✅ ML/AI Project Analysis Infrastructure (Phase 5)
  - Enhanced ALS parser with extended metadata extraction (device chains, clips, routing, automation)
  - ASD clip file parser for warp markers, transients, and timing data
  - ML Feature Extraction service combining ALS metadata with audio analysis (librosa)
  - Project Similarity Analyzer using cosine similarity, Jaccard similarity, and weighted metrics
  - ML Clustering Service (K-means, DBSCAN, Hierarchical) for project grouping
  - Recommendation Engine for similar projects, plugin suggestions, and auto-tagging
  - New dependencies: scikit-learn, librosa, soundfile, lxml, numpy, pandas

## ❌ NOT YET DEVELOPED
- ❌ Research Ableton Live native lesson format and how to load lessons from their location in the Ableton install (find location for Win and Mac)
- ❌ Add browser to view Ableton lessons in the native installed location (link to them from the Lesson table of contents)
- ❌ Add Lessons area in Learning section that goes to the Lesson TOC (Currently hidden per user request until paths and display methods are resolved)
- ❌ Locate or allow user to define Ableton pack location (Basic pack browsing exists, but user-defined location configuration not yet implemented)
- ❌ Load the official Pack TOC (it seems like a lesson also?)
- ❌ Determine best way to keep Stats on Pack usage, find unused/never used Packs (does this have to come from scanning projects?)
