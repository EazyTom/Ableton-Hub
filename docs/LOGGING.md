# Logging Documentation

## Overview

Ableton Hub uses Python's standard logging framework with file-based logging for troubleshooting and debugging. Logs are automatically rotated to prevent disk space issues.

## Log File Locations

### Default Locations

**Windows:**
- `%APPDATA%\AbletonHub\logs\ableton_hub.log` (all logs)
- `%APPDATA%\AbletonHub\logs\ableton_hub_errors.log` (errors only)

**macOS:**
- `~/Library/Application Support/AbletonHub/logs/ableton_hub.log`
- `~/Library/Application Support/AbletonHub/logs/ableton_hub_errors.log`

**Linux:**
- `~/.local/share/AbletonHub/logs/ableton_hub.log`
- `~/.local/share/AbletonHub/logs/ableton_hub_errors.log`

### Custom Locations

You can change the log directory in Settings → Logging tab.

## Log Files

### Main Log (`ableton_hub.log`)
Contains all log messages at the configured level (default: ERROR).

### Error Log (`ableton_hub_errors.log`)
Contains only ERROR and CRITICAL level messages. Useful for quickly finding problems.

## Log Levels

- **DEBUG**: Detailed information for debugging (development only)
- **INFO**: General informational messages
- **WARNING**: Warning messages (recoverable issues)
- **ERROR**: Error messages (operations failed)
- **CRITICAL**: Critical errors (application may be unstable)

### Default Behavior

- **Production**: ERROR level (only errors logged)
- **Development**: DEBUG level (all messages logged)
  - Detected automatically when running with `python -m src.main`
  - Or set `ABLETON_HUB_DEBUG=1` environment variable

## Log Rotation

Logs are automatically rotated when they reach the maximum file size:
- **Default max size**: 10 MB per file
- **Default backups**: 5 rotated files
- **Total max size**: ~50 MB per log type (100 MB total)

These settings can be changed in Settings → Logging tab.

## Viewing Logs

### In Application
1. Go to **Help → View Logs**
2. Use the dialog to:
   - View recent log entries (last 1000 lines)
   - Filter to errors only
   - Refresh to see latest entries
   - Open log folder in file explorer
   - Copy selected text to clipboard

### Manual Access
Navigate to the log directory (see locations above) and open the log files in any text editor.

## Configuring Logging

### Via Settings Dialog
1. Go to **File → Settings**
2. Open the **Logging** tab
3. Configure:
   - Enable/disable file logging
   - Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
   - Log directory location
   - Max file size (MB)
   - Number of backup files
4. **Restart the application** for changes to take effect

### Via Configuration File
Edit `config.json` in the app data directory:
```json
{
  "logging": {
    "enabled": true,
    "level": "ERROR",
    "log_dir": null,
    "max_bytes": 10485760,
    "backup_count": 5
  }
}
```

## Development Mode

When running in development mode, logging automatically switches to DEBUG level:

**Automatic detection:**
- Running with `python -m src.main` (not optimized)
- `__debug__` flag is True

**Manual override:**
- Set environment variable: `ABLETON_HUB_DEBUG=1`

## Log Format

Each log entry includes:
```
YYYY-MM-DD HH:MM:SS [LEVEL] module.name:thread_name: message
```

Example:
```
2026-02-02 14:30:15 [ERROR] src.ui.workers.als_parser_worker:MainThread: ALSParserWorker error: File not found
  Cancelled: False
  file_path: C:\Projects\project.als
```

## Troubleshooting

### Logs Not Created
- Check that file logging is enabled in Settings
- Verify write permissions to the log directory
- Check disk space availability

### Logs Too Large
- Reduce max file size in Settings
- Reduce number of backup files
- Change log level to ERROR to reduce log volume

### Can't Find Logs
- Use **Help → View Logs** → **Open Log Folder**
- Check Settings → Logging tab for current log directory
- Default location is shown in the Settings dialog

### Development Logging
- Ensure you're running with `python -m src.main` (not `python -O`)
- Or set `ABLETON_HUB_DEBUG=1` environment variable
- Check that log level is set to DEBUG in Settings

## Best Practices

1. **For Users**: Keep log level at ERROR (default) unless troubleshooting
2. **For Developers**: Use DEBUG level during development
3. **For Bug Reports**: Include relevant log entries from `ableton_hub_errors.log`
4. **Disk Space**: Monitor log directory size, adjust rotation settings if needed

## Related Files

- Configuration: `src/config.py` - `LoggingConfig` class
- Logging Setup: `src/utils/logging.py` - `setup_logging()` function
- Settings UI: `src/ui/dialogs/settings_dialog.py` - Logging tab
- Log Viewer: `src/ui/dialogs/log_viewer_dialog.py` - Log viewer dialog
