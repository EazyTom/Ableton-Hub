# Signal Flow Documentation

This document describes the signal/slot connections in the Ableton Hub application.

## MainWindow Signals

### Outgoing Signals
- `scan_requested()` - Emitted when a scan is requested

### Incoming Signal Connections

#### From Sidebar
- `navigation_changed(str)` → `_on_navigation_changed()` - Handle view navigation
- `location_selected(int)` → `_on_location_filter()` - Filter projects by location
- `collection_selected(int)` → `_on_collection_selected()` - Show collection details
- `location_delete_requested(int)` → `_on_delete_location_from_sidebar()` - Delete location
- `cleanup_orphaned_projects_requested()` → `_on_cleanup_orphaned_projects()` - Clean up orphaned projects
- `collection_edit_requested(int)` → `_on_edit_collection_from_sidebar()` - Edit collection
- `collection_delete_requested(int)` → `_on_delete_collection_from_sidebar()` - Delete collection
- `auto_detect_live_versions_requested()` → `_on_auto_detect_live_versions()` - Auto-detect Live versions
- `add_manual_installation_requested()` → `_on_add_manual_installation()` - Add manual installation
- `set_favorite_installation_requested(int)` → `_on_set_favorite_installation()` - Set favorite installation
- `remove_installation_requested(int)` → `_on_remove_installation()` - Remove installation
- `tag_selected(int)` → `_on_tag_filter()` - Filter projects by tag
- `manage_tags_requested()` → `_on_manage_tags()` - Open tag management dialog

#### From MenuBarManager
- `add_location_requested()` → `_on_add_location()` - Show add location dialog
- `scan_all_requested()` → `_on_scan_all()` - Start scan of all locations
- `settings_requested()` → `_on_settings()` - Show settings dialog
- `exit_requested()` → `close()` - Close application
- `search_projects_requested()` → `_focus_search()` - Focus search bar
- `select_all_requested()` → `_select_all_projects()` - Select all projects
- `grid_view_requested()` → `_set_view_mode("grid")` - Switch to grid view
- `list_view_requested()` → `_set_view_mode("list")` - Switch to list view
- `toggle_sidebar_requested()` → `_toggle_sidebar()` - Toggle sidebar visibility
- `toggle_show_missing_requested()` → `_toggle_show_missing()` - Toggle missing projects filter
- `refresh_requested()` → `_refresh_view()` - Refresh current view
- `new_collection_requested()` → `_on_new_collection()` - Show new collection dialog
- `global_search_requested()` → `_on_global_search()` - Show global search dialog
- `show_link_panel_requested()` → `_show_link_panel()` - Show Link panel
- `force_rescan_metadata_requested()` → `_on_force_rescan_metadata()` - Force metadata rescan
- `clear_thumbnail_cache_requested()` → `_on_clear_thumbnail_cache()` - Clear thumbnail cache
- `cleanup_missing_projects_requested()` → `_on_cleanup_missing_projects()` - Clean up missing projects
- `cleanup_backup_projects_requested()` → `_on_cleanup_backup_projects()` - Clean up backup projects
- `reset_database_requested()` → `_on_reset_database()` - Reset database
- `about_requested()` → `_show_about()` - Show about dialog

#### From ToolBarManager
- `scan_requested()` → `_on_scan_all()` - Start scan
- `grid_view_requested()` → `_set_view_mode("grid")` - Switch to grid view
- `list_view_requested()` → `_set_view_mode("list")` - Switch to list view

#### From SearchBar
- `search_changed(str)` → `_on_search()` - Handle search query change
- `filter_changed(dict)` → `_on_filter_changed()` - Handle filter change
- `tempo_filter_changed(int, int)` → `_on_tempo_filter_changed()` - Handle tempo filter change
- `sort_changed(str, str)` → `_on_sort_changed()` - Handle sort change
- `create_collection_from_filter(dict)` → `_on_create_collection_from_filter()` - Create collection from filter

#### From ProjectGrid
- `project_selected(int)` → `_on_project_selected()` - Handle project selection
- `project_double_clicked(int)` → `_on_project_open()` - Handle project double-click
- `sort_requested(str, str)` → `_on_grid_sort_requested()` - Handle sort request
- `tags_modified()` → `_refresh_sidebar()` - Refresh sidebar after tag modification

#### From ScanController
- `scan_started()` → `_on_scan_started()` - Handle scan start
- `scan_progress(int, int, str)` → `_on_scan_progress()` - Handle scan progress
- `scan_complete(int)` → `_on_scan_complete()` - Handle scan completion
- `scan_error(str)` → `_on_scan_error()` - Handle scan error
- `project_found(str)` → `_on_project_found()` - Handle project found

#### From FileWatcher
- `project_created(str)` → `_on_watcher_project_created()` - Handle project creation
- `project_modified(str)` → `_on_watcher_project_modified()` - Handle project modification
- `project_deleted(str)` → `_on_watcher_project_deleted()` - Handle project deletion
- `project_moved(str, str)` → `_on_watcher_project_moved()` - Handle project move
- `error_occurred(str)` → `_on_watcher_error()` - Handle watcher error

#### From AudioPlayer
- `playback_started()` → `_on_audio_playback_started()` - Handle playback start
- `playback_stopped()` → `_on_audio_playback_stopped()` - Handle playback stop
- `playback_finished()` → `_on_audio_playback_stopped()` - Handle playback finish

#### From ProjectPropertiesView
- `back_requested()` → `_on_properties_back()` - Handle back button
- `project_selected(int)` → `_on_project_selected()` - Handle project selection
- `tags_modified()` → `_refresh_sidebar()` - Refresh sidebar after tag modification
- `project_saved()` → `_on_project_saved()` - Handle project save

## ViewManager Signals

- `view_changed(str)` - Emitted when view is switched

## Controller Signals

### ScanController
- `scan_started()` - Scan operation started
- `scan_progress(int, int, str)` - Scan progress update (current, total, message)
- `scan_complete(int)` - Scan completed (found_count)
- `scan_error(str)` - Scan error occurred
- `project_found(str)` - Project found during scan (path)

### ProjectController
- `projects_loaded(list)` - Projects loaded (list of Project objects)
- `project_count_changed(int)` - Project count changed

### CollectionController
- `collection_created(int)` - Collection created (collection_id)
- `collection_updated(int)` - Collection updated (collection_id)
- `collection_deleted(int)` - Collection deleted (collection_id)

### ViewController
- `view_changed(str)` - View changed (view_name)
- `view_state_changed(str, dict)` - View state changed (view_name, state)

## Worker Signals

### BaseWorker
- `finished(object)` - Worker finished (result)
- `error(str)` - Worker error (error_message)
- `progress(int, int, str)` - Worker progress (current, total, message)

### ALSParserWorker
- `finished(dict)` - Parsing finished (metadata dict)

### BackupScanWorker
- `finished(list)` - Backup scan finished (list of backup file paths)

### SimilarProjectsWorker
- `finished(list)` - Similar projects found (list of similar projects)

## Signal Optimization Notes

### Removed Duplicates
- Removed duplicate sidebar signal connections in MainWindow._create_central_widget()
- All sidebar signals now connected only once

### Connection Timing
- Most signals connected during widget initialization
- Some signals connected lazily (e.g., FileWatcher signals connected when watcher is started)
