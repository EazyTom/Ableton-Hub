# Dependency Audit Report
**Date:** January 31, 2026  
**Python Version Requirement:** >=3.11 (from pyproject.toml)

## Summary

Most packages can be safely upgraded. However, **two major version upgrades require careful testing**:
- **numpy**: 1.24.0 → 2.4.1 (major version change)
- **pandas**: 2.0.0 → 3.0.0 (major version change)

## Package Upgrade Recommendations

### ✅ Safe Upgrades (Minor/Patch Versions)

| Package | Current | Latest | Status | Notes |
|---------|---------|--------|--------|-------|
| **PyQt6** | >=6.6.0 | 6.10.2 | ✅ Safe | Minor version upgrade |
| **SQLAlchemy** | >=2.0.0 | 2.0.46 | ✅ Safe | Patch version upgrade (constraint already allows) |
| **aiosqlite** | >=0.19.0 | 0.22.1 | ✅ Safe | Minor version upgrade |
| **watchdog** | >=3.0.0 | 6.0.0 | ✅ Safe | Major version but backward compatible |
| **zeroconf** | >=0.131.0 | 0.148.0 | ✅ Safe | Minor version upgrade |
| **qasync** | >=0.27.0 | 0.28.0 | ✅ Safe | Minor version upgrade |
| **Pillow** | >=10.0.0 | 12.1.0 | ✅ Safe | Major version but backward compatible (requires Python 3.10+) |
| **rapidfuzz** | >=3.0.0 | 3.14.3 | ✅ Safe | Minor version upgrade |
| **scikit-learn** | >=1.3.0 | 1.8.0 | ✅ Safe | Minor version upgrade |
| **librosa** | >=0.10.0 | 0.11.0 | ✅ Safe | Minor version upgrade |
| **soundfile** | >=0.12.0 | 0.13.1 | ✅ Safe | Minor version upgrade |
| **lxml** | >=4.9.0 | 6.0.2 | ✅ Safe | Major version but backward compatible |

### ⚠️ Major Upgrades Requiring Testing

| Package | Current | Latest | Status | Notes |
|---------|---------|--------|--------|-------|
| **numpy** | >=1.24.0 | 2.4.1 | ⚠️ Test Required | Major version change - may have breaking changes. Requires Python 3.11+ |
| **pandas** | >=2.0.0 | 3.0.0 | ⚠️ Test Required | Major version change - removed deprecated functionality. Requires Python 3.11+ |

### 📋 Recommended Action Plan

#### Phase 1: Safe Upgrades (Immediate)
Update these packages immediately as they are backward compatible:

```txt
PyQt6>=6.10.0
SQLAlchemy>=2.0.0  # Already allows latest
aiosqlite>=0.22.0
watchdog>=6.0.0
zeroconf>=0.148.0
qasync>=0.28.0
Pillow>=12.0.0
rapidfuzz>=3.14.0
scikit-learn>=1.8.0
librosa>=0.11.0
soundfile>=0.13.0
lxml>=6.0.0
```

#### Phase 2: Major Upgrades (After Testing)
Test these upgrades carefully:

1. **numpy 2.x**: 
   - Check compatibility with scikit-learn, librosa, pandas
   - Review numpy 2.0 migration guide: https://numpy.org/devdocs/numpy_2_0_migration_guide.html
   - Test ML features thoroughly (ml_clustering, similarity_analyzer, ml_feature_extractor)

2. **pandas 3.x**:
   - Review pandas 3.0 migration guide: https://pandas.pydata.org/docs/whatsnew/v3.0.0.html
   - Test any code using pandas (currently marked as "Future: Statistics & Analytics Dashboard")
   - Note: pandas 3.0 requires upgrading to pandas 2.3 first

## Compatibility Notes

### Python Version Compatibility
- All packages support Python 3.11+ ✅
- numpy 2.x requires Python 3.11+ ✅
- pandas 3.0 requires Python 3.11+ ✅
- Pillow 12.x requires Python 3.10+ ✅

### Inter-Package Dependencies
- **scikit-learn** depends on numpy - ensure numpy 2.x compatibility
- **librosa** depends on numpy and soundfile - test audio analysis features
- **pandas** depends on numpy - ensure numpy 2.x compatibility
- **qasync** works with PyQt6 - ensure async features still work

## Testing Checklist

Before upgrading numpy and pandas:

- [ ] Run full test suite (if available)
- [ ] Test ML clustering features
- [ ] Test similarity analyzer
- [ ] Test ML feature extractor
- [ ] Test audio analysis (librosa)
- [ ] Test any pandas-dependent code (currently minimal)
- [ ] Verify UI responsiveness (PyQt6 upgrade)
- [ ] Test file watching (watchdog upgrade)
- [ ] Test network discovery (zeroconf upgrade)

## Updated Requirements.txt (Recommended)

See `requirements-updated.txt` for the recommended updated version.

## References

- PyQt6: https://pypi.org/project/PyQt6/
- SQLAlchemy: https://pypi.org/project/SQLAlchemy/
- numpy 2.0 Migration: https://numpy.org/devdocs/numpy_2_0_migration_guide.html
- pandas 3.0 Migration: https://pandas.pydata.org/docs/whatsnew/v3.0.0.html
