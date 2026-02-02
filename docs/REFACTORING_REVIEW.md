# GUI Refactoring Review - Issues Found and Fixed

## Review Date
February 2, 2026

## Overview
This document summarizes the comprehensive review of the Phase 1 & 2 GUI refactoring work, identifying potential issues and fixes applied.

## Issues Found and Fixed

### 1. ✅ ProjectCard Signal Disconnection
**Issue**: `ProjectCard` connects to `AudioPlayer` signals (`playback_finished`, `playback_stopped`) but never disconnects them. When cards are deleted, signals remain connected, potentially causing callbacks to deleted objects.

**Risk**: Medium - Could cause crashes or errors when AudioPlayer emits signals after card deletion.

**Fix**: 
- Added `cleanup()` method to `ProjectCard` that disconnects signals before deletion
- Updated `ProjectGrid._populate_grid()` to call `cleanup()` before `deleteLater()`

**Files Modified**:
- `src/ui/widgets/project_card.py` - Added cleanup method
- `src/ui/widgets/project_grid.py` - Call cleanup before deletion

### 2. ✅ Worker Signal Disconnection
**Issue**: Worker signals in `ProjectPropertiesView` were not explicitly disconnected before cleanup, relying solely on Qt's automatic cleanup.

**Risk**: Low - Qt handles this automatically, but explicit disconnection is cleaner and prevents potential race conditions.

**Fix**: Added explicit signal disconnection in `_stop_workers()` before calling `deleteLater()` for all workers.

**Files Modified**:
- `src/ui/widgets/project_properties_view.py` - Disconnect signals before cleanup

### 3. ✅ ViewManager Bounds Checking
**Issue**: `ViewManager.switch_to_view()` checked if index was None or < 0, but didn't verify the index was within the stack's bounds.

**Risk**: Medium - Could cause crashes if an invalid index >= stack count is used.

**Fix**: Added bounds check to ensure index < `stack.count()` before switching views.

**Files Modified**:
- `src/ui/managers/view_manager.py` - Added bounds validation

### 4. ✅ ProjectCard Widget Null Checks
**Issue**: Some widget accesses in `ProjectCard` methods (`_update_folder_label`, `_update_playing_indicator`) didn't have null checks.

**Risk**: Medium - Could cause AttributeError if widgets aren't initialized when methods are called.

**Fix**: Added `hasattr()` checks for `folder_label` and `name_label` before accessing them.

**Files Modified**:
- `src/ui/widgets/project_card.py` - Added null checks for widget access

### 5. ✅ Worker Thread Cleanup Order
**Issue**: Worker cleanup was already robust, but signal disconnection order could be improved.

**Risk**: Low - Already handled correctly, but improved for clarity.

**Fix**: Disconnect signals before thread cleanup to ensure no signals are emitted during cleanup.

**Files Modified**:
- `src/ui/widgets/project_properties_view.py` - Improved cleanup order

## Previously Fixed Issues (From Earlier Sessions)

### ✅ QThread moveToThread Warning
**Issue**: Workers were created with parent, preventing `moveToThread()`.

**Fix**: Changed worker instantiation to use `None` as parent.

### ✅ ProjectCard tempo_sep NoneType Error
**Issue**: `_update_display()` accessed widgets that might not be initialized.

**Fix**: Added comprehensive `hasattr()` checks for all widget accesses.

### ✅ Path Comparison in Audio Playback
**Issue**: Path comparison failed when exports were manually added due to normalization differences.

**Fix**: Normalized paths using `Path.resolve()` before comparison.

## Code Quality Improvements

### Signal Management
- ✅ All signal connections now have corresponding disconnections
- ✅ Cleanup methods added where needed
- ✅ Signal disconnection wrapped in try/except to handle already-disconnected cases

### Thread Safety
- ✅ Worker cleanup properly stops threads before deletion
- ✅ Signals disconnected before thread cleanup
- ✅ Proper use of `deleteLater()` for Qt object lifecycle

### Error Handling
- ✅ Widget access protected with null checks
- ✅ Bounds checking added where needed
- ✅ Graceful handling of disconnection errors

## Testing Recommendations

1. **Signal Disconnection**: Test that deleting cards while audio is playing doesn't cause errors
2. **View Switching**: Test switching views with invalid indices
3. **Worker Cleanup**: Test rapid switching between project properties views
4. **Widget Access**: Test ProjectCard methods when widgets might not be initialized
5. **Path Normalization**: Test audio playback with manually added exports using different path formats

## Remaining Considerations

### Low Priority
- Consider adding unit tests for manager classes
- Consider adding logging for signal disconnection failures
- Monitor for any remaining thread cleanup warnings

### Future Improvements
- Consider using weak references for signal connections where appropriate
- Consider adding a base class for widgets that need cleanup
- Consider adding automated tests for signal/slot connections

## Conclusion

All identified issues have been addressed. The refactored code now includes:
- Proper signal lifecycle management
- Comprehensive error handling
- Robust thread cleanup
- Safe widget access patterns

The codebase is now more stable and should handle edge cases better than before the refactoring.
