# Qt Threading Audit & Fixes

**Date:** February 2, 2026  
**Status:** Critical Issues Identified & Fixed  
**Severity:** High - Application Crashes

## Executive Summary

This audit identified **6 critical threading issues** that can cause application crashes, particularly during startup scans and application shutdown. All issues have been addressed with proper Qt threading patterns.

## Critical Issues Found

### 1. **Missing Logger in ProjectScanner** ⚠️ CRITICAL
**Location:** `src/services/scanner.py:582`  
**Issue:** `ProjectScanner._on_complete()` uses `self.logger` but `ProjectScanner` never initializes a logger.  
**Impact:** `AttributeError` when scan completes, causing crashes.  
**Fix:** Initialize logger in `__init__`.

### 2. **Race Condition in ScanController** ⚠️ CRITICAL
**Location:** `src/ui/controllers/scan_controller.py:92`  
**Issue:** `_on_complete()` sets `self._scanner = None` immediately without waiting for thread cleanup.  
**Impact:** Thread may still be running when scanner is set to None, causing crashes on shutdown.  
**Fix:** Wait for thread completion before setting to None.

### 3. **Signal Disconnection Race Condition** ⚠️ CRITICAL
**Location:** `src/services/scanner.py:565-570`  
**Issue:** Signals connected to worker are never disconnected before cleanup. Signals may fire after worker is deleted.  
**Impact:** Crashes when signals are emitted after worker deletion.  
**Fix:** Disconnect all signals before cleanup.

### 4. **Inconsistent Thread Cleanup Patterns** ⚠️ HIGH
**Location:** Multiple files  
**Issue:** Different cleanup approaches across codebase (some wait, some don't, some disconnect signals, some don't).  
**Impact:** Unpredictable behavior, difficult to maintain.  
**Fix:** Standardize cleanup pattern across all workers.

### 5. **Thread Ownership Issues** ⚠️ MEDIUM
**Location:** `src/services/scanner.py:565`  
**Issue:** `ScanWorker` created without parent, but not explicitly managed.  
**Impact:** Potential memory leaks or premature deletion.  
**Fix:** Ensure proper parent/ownership management.

### 6. **Missing Signal Disconnection in Stop Methods** ⚠️ MEDIUM
**Location:** `src/services/scanner.py:590-602`  
**Issue:** `stop()` method doesn't disconnect signals before cleanup.  
**Impact:** Signals may fire during cleanup causing crashes.  
**Fix:** Disconnect signals in stop method.

## Qt Threading Best Practices Applied

### ✅ Proper Thread Lifecycle Management

1. **Signal Disconnection Before Cleanup**
   ```python
   # Disconnect all signals before cleanup
   worker.progress.disconnect()
   worker.finished.disconnect()
   worker.error.disconnect()
   ```

2. **Wait for Thread Completion**
   ```python
   if worker.isRunning():
       worker.quit()  # Request graceful shutdown
       if not worker.wait(timeout_ms):
           worker.terminate()  # Force if needed
           worker.wait(timeout_ms)
   ```

3. **Schedule Deletion Properly**
   ```python
   worker.deleteLater()  # Let Qt event loop handle deletion
   worker = None  # Clear reference AFTER scheduling deletion
   ```

4. **Logger Initialization**
   ```python
   def __init__(self, parent=None):
       super().__init__(parent)
       self.logger = get_logger(__name__)  # Always initialize logger
   ```

### ✅ Standardized Cleanup Pattern

All worker cleanup now follows this pattern:

```python
def _cleanup_worker(self, worker: QThread) -> None:
    """Standardized worker cleanup pattern."""
    if not worker:
        return
    
    # 1. Stop the worker if it has a stop method
    if hasattr(worker, 'stop'):
        worker.stop()
    
    # 2. Disconnect all signals
    try:
        for signal_name in ['progress', 'finished', 'error', 'scan_complete', 
                           'project_found', 'error_occurred']:
            if hasattr(worker, signal_name):
                signal = getattr(worker, signal_name)
                signal.disconnect()
    except (TypeError, RuntimeError):
        pass  # Signals may already be disconnected
    
    # 3. Wait for thread to finish
    if worker.isRunning():
        worker.quit()
        if not worker.wait(2000):  # 2 second timeout
            worker.terminate()
            worker.wait(1000)  # Additional wait after terminate
    
    # 4. Schedule deletion
    worker.deleteLater()
```

## Files Modified

1. **`src/services/scanner.py`**
   - ✅ Added logger initialization to `ProjectScanner.__init__()` (line 521)
   - ✅ Added signal disconnection in `_on_complete()` (lines 580-587)
   - ✅ Added signal disconnection in `stop()` (lines 612-618)
   - ✅ Improved thread cleanup sequence with proper `quit()` before `wait()`
   - ✅ Fixed `GlobalScanner.stop()` with proper signal disconnection and cleanup

2. **`src/ui/controllers/scan_controller.py`**
   - ✅ Fixed race condition in `_on_complete()` (lines 92-111)
   - ✅ Added proper thread waiting before setting scanner to None
   - ✅ Improved error handling in `_on_error()` with forced stop
   - ✅ Fixed `rescan_project()` cleanup with proper signal disconnection (lines 141-186)

3. **`src/services/link_scanner.py`**
   - ✅ Added signal disconnection in `stop()` (lines 180-186)
   - ✅ Improved thread cleanup with proper sequence

## Testing Recommendations

1. **Startup Scan Test**
   - Start application
   - Verify scan completes without crashes
   - Check logs for any threading warnings

2. **Shutdown Test**
   - Start scan
   - Immediately close application
   - Verify no "QThread destroyed while running" errors

3. **Concurrent Operations Test**
   - Start scan
   - While scanning, trigger other operations (rescan, export, etc.)
   - Verify no crashes or race conditions

4. **Signal Disconnection Test**
   - Start scan
   - Stop scan mid-operation
   - Verify no signals fire after stop

## Additional Recommendations

### Future Improvements

1. **Create Base Thread Manager Class**
   - Centralize thread lifecycle management
   - Reduce code duplication
   - Ensure consistent patterns

2. **Add Thread State Monitoring**
   - Log thread state transitions
   - Detect stuck threads
   - Provide diagnostics

3. **Implement Thread Pool**
   - For multiple concurrent operations
   - Better resource management
   - Prevents thread exhaustion

4. **Add Unit Tests for Threading**
   - Test cleanup sequences
   - Test signal disconnection
   - Test race conditions

## Conclusion

All critical threading issues have been identified and fixed. The codebase now follows Qt threading best practices with proper signal disconnection, thread waiting, and cleanup sequences. Application stability should be significantly improved, especially during startup scans and shutdown.
