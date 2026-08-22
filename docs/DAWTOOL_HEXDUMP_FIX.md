# Remove hexdump from dawtool (EazyTom fork)

Ableton Hub only uses dawtool for Ableton Live (.als) marker extraction, but dawtool loads the FL Studio parser at import time, which currently requires `hexdump`. The hexdump usage is only in commented-out debug code.

**Apply this fix in your EazyTom/dawtool repo** to remove the hexdump dependency:

## File: `dawtool/daw/flstudio_core.py`

### 1. Remove the top-level import (around line 24)

**Delete this line:**
```python
from hexdump import hexdump
```

### 2. Remove the import inside `_handle_event` (around line 361)

**Delete this line:**
```python
from hexdump import hexdump
```

Both occurrences are only used in commented-out `# hexdump(...)` debug calls, so removing the imports is safe.

After pushing these changes to `github.com/EazyTom/dawtool`, reinstall in your venv:

```powershell
.venv\Scripts\pip.exe uninstall dawtool -y
.venv\Scripts\pip.exe install "dawtool @ git+https://github.com/EazyTom/dawtool"
```
