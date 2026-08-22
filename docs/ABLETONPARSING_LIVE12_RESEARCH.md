# AbletonParsing Live 12 Compatibility Research

**Date:** February 2, 2026  
**Repository:** [DBraun/AbletonParsing](https://github.com/DBraun/AbletonParsing)  
**Latest Version:** v0.1.3 (released June 2, 2025)  
**Status:** ❌ **Live 12 NOT Supported**

---

## Executive Summary

**AbletonParsing does NOT support Ableton Live 12.** The library explicitly states that "Ableton Live 12 uses a different binary format that is not yet supported by this library." No forks have been found that add Live 12 support.

---

## Repository Information

### Primary Repository
- **GitHub:** https://github.com/DBraun/AbletonParsing
- **PyPI Package:** `abletonparsing`
- **Installation:** `pip install abletonparsing`
- **Stars:** 75 ⭐
- **Forks:** 8 🍴
- **License:** MIT
- **Latest Release:** v0.1.3 (June 2, 2025)

### Note on Repository Name
⚠️ **Important:** The repository is `DBraun/AbletonParsing`, NOT `mattypie/AbletonParsing`. Our existing documentation (`EXTERNAL_PROJECTS_ANALYSIS.md`) incorrectly references `mattypie/AbletonParsing`. This appears to be a documentation error.

---

## Live 12 Compatibility Status

### Official Statement
From the repository README:
> **Note:** Ableton Live 12 uses a different binary format that is not yet supported by this library.

### Tested Versions
- ✅ **Ableton Live 9** - Supported and tested
- ✅ **Ableton Live 10** - Supported and tested
- ❌ **Ableton Live 11** - Not explicitly mentioned (likely unsupported)
- ❌ **Ableton Live 12** - **Explicitly NOT supported**

---

## Why Live 12 Doesn't Work

### Binary Format Changes
AbletonParsing uses **version-specific byte offsets** to parse ASD files:

1. **Live 9 Format:**
   - Searches for `'SampleData'` marker
   - Uses specific byte offsets for Live 9 structure

2. **Live 10 Format:**
   - Searches for `'SampleOverViewLevel'` marker
   - Uses different byte offsets for Live 10 structure

3. **Live 12 Format:**
   - Uses a **completely different binary format**
   - Existing byte offset patterns no longer work
   - Would require reverse engineering the new format

### Known Issues Even with Live 10
There's a documented issue ([Issue #1](https://github.com/DBraun/AbletonParsing/issues/1)) where ASD files saved on **macOS Ableton 10.1.30** produce incorrect parsed values:
- `start_marker` and `end_marker` return extremely large numbers (e.g., `5.742306885616792e+72`)
- Suggests even minor version differences can break parsing
- Indicates the binary format is fragile and version-specific

---

## Fork Analysis

### Search Results
- **No forks found** that add Live 12 support
- **8 forks total** exist, but none appear to address Live 12 compatibility
- No pull requests or issues related to Live 12 support

### Alternative Projects
Several other Ableton parsing projects exist, but they focus on `.als` (project) files, not `.asd` (clip analysis) files:

1. **pyableton** - Parses `.als` files (Python, requires Python ≥3.10)
2. **GinoLucianoRojo/ableton** - Parses `.als` files (CoffeeScript)
3. **R9295/ableton-parser** - Parses `.als` files
4. **nicorobo/als2js** - Parses `.als` files to JavaScript

**None of these alternatives parse `.asd` files.**

---

## Technical Details

### ASD File Format Evolution
ASD (Analysis) files are binary format files that store:
- Warp marker positions (seconds and beats)
- Loop start/end markers
- Hidden loop markers
- Warp on/off state
- Sample rate information
- Default clip settings

The format has evolved significantly:
- **Live 9:** One binary structure
- **Live 10:** Modified binary structure (different markers)
- **Live 11:** Likely further changes (not documented)
- **Live 12:** **Completely different binary format** (breaking change)

### Implementation Approach
AbletonParsing uses a **hardcoded offset approach**:
1. Searches for version-specific markers in the binary file
2. Uses fixed byte offsets relative to those markers
3. Reads binary data structures (floats, integers, booleans)

This approach is **fragile** because:
- Any format change breaks parsing
- Byte alignment differences between versions cause failures
- Platform-specific differences (macOS vs Windows) can cause issues

---

## What Would Be Needed for Live 12 Support

### Reverse Engineering Required
To add Live 12 support, someone would need to:

1. **Analyze Live 12 ASD files:**
   - Hex dump analysis
   - Compare structure with Live 9/10 files
   - Identify new markers/headers
   - Map new byte offsets

2. **Test across platforms:**
   - Windows ASD files
   - macOS ASD files
   - Different Live 12 versions (12.0, 12.1, etc.)

3. **Update the parser:**
   - Add Live 12 detection logic
   - Implement new offset patterns
   - Handle format differences

### Estimated Effort
- **Reverse Engineering:** 2-4 weeks (for experienced developer)
- **Implementation:** 1-2 weeks
- **Testing:** 1-2 weeks
- **Total:** 1-2 months of dedicated work

---

## Recommendations for Ableton Hub

### Current Status
- ✅ **dawtool** integrated - Supports Live 8-12 for `.als` timeline markers
- ⚠️ **AbletonParsing** - Only supports Live 9/10 for `.asd` files
- ✅ **Our own ASD parser** - Experimental, best-effort approach

### Options

#### Option 1: Keep Current Approach (Recommended)
- Continue using our experimental `asd_parser.py`
- Use AbletonParsing as optional fallback for Live 9/10 projects
- Accept that Live 11/12 ASD parsing may be incomplete

**Pros:**
- No dependency on unmaintained library
- Works with all Live versions (best-effort)
- No breaking changes

**Cons:**
- Less accurate parsing for Live 9/10
- Missing some advanced features (time map generation)

#### Option 2: Hybrid Approach
- Use AbletonParsing for Live 9/10 projects (when available)
- Fall back to our parser for Live 11/12
- Detect Live version from `.als` file to choose parser

**Pros:**
- Best accuracy for Live 9/10
- Still works for Live 11/12

**Cons:**
- Adds external dependency
- More complex code paths
- Still no Live 12 support

#### Option 3: Wait for Community Solution
- Monitor AbletonParsing repository for Live 12 support
- Check forks periodically
- Consider contributing if we reverse engineer the format

**Pros:**
- Could get full Live 12 support eventually

**Cons:**
- May never happen (low activity repository)
- Unpredictable timeline

#### Option 4: Reverse Engineer Live 12 Format (Future)
- If ASD parsing becomes critical feature
- Dedicate resources to reverse engineering
- Contribute back to AbletonParsing or create our own solution

**Pros:**
- Full control over implementation
- Could support all versions

**Cons:**
- Significant time investment
- Requires expertise in binary format analysis
- May break with future Live updates

---

## Conclusion

**AbletonParsing does NOT and will NOT work with Live 12** without significant reverse engineering work. The library is actively maintained (latest release June 2025) but explicitly excludes Live 12 support.

**For Ableton Hub:**
- ✅ Continue using `dawtool` for `.als` timeline markers (supports Live 8-12)
- ⚠️ Keep AbletonParsing as optional dependency for Live 9/10 ASD parsing
- ✅ Maintain our experimental ASD parser for Live 11/12 (best-effort)
- 📝 Document Live 12 ASD parsing limitations clearly

**Priority:** Low - ASD parsing is not critical for core functionality. Timeline markers (via dawtool) are more valuable and already working with Live 12.

---

## References

- [DBraun/AbletonParsing GitHub](https://github.com/DBraun/AbletonParsing)
- [AbletonParsing PyPI](https://pypi.org/project/abletonparsing/)
- [Issue #1: macOS 10.1.30 Parsing Bug](https://github.com/DBraun/AbletonParsing/issues/1)
- [Ableton Live 12 Manual - Managing Files](https://www.ableton.com/en/live-manual/12/managing-files-and-sets/)
- [Ableton Hub External Projects Analysis](./EXTERNAL_PROJECTS_ANALYSIS.md)
