# New User Experience Documentation Improvements

## Problem Analysis

The current README.md is developer-focused and presents barriers for non-technical users:

1. **Technical Jargon**: Terms like "pip", "git clone", "virtual environment", "PyQt6", "SQLAlchemy" are confusing without explanations
2. **Mixed Audiences**: Developer setup and end-user instructions are intermingled
3. **No Platform-Specific Guides**: Installation steps don't differentiate Mac vs Windows clearly
4. **Missing First-Run Guidance**: No explanation of what happens when the app first launches
5. **Assumes Python Knowledge**: Installation assumes users know what Python is and how to install it
6. **Troubleshooting Too Technical**: Error messages reference technical concepts users may not understand

## Proposed Changes

### 1. Restructure README.md

**Current Structure Issues:**

- Installation section mixes source code installation with end-user installation
- Quick Start assumes users already have the app running
- Development section appears before user documentation
- Architecture diagrams are developer-focused

**New Structure:**

```
1. What is Ableton Hub? (Simple explanation)
2. Features (Keep technical terms, explain in parentheses)
3. Installation (Platform-specific, Mac first)
   - Method 1: pip install from GitHub (recommended)
   - Method 2: Download source + pip install -r requirements.txt
     - Include venv setup note: python -m venv .venv
     - Windows: .venv\Scripts\activate.bat
     - Mac: source .venv/bin/activate (or activate.sh)
   - Mac Installation (link to docs/INSTALLATION_MAC.md)
   - Windows Installation (link to docs/INSTALLATION_WINDOWS.md)
4. First Time Setup (NEW - link to docs/FIRST_TIME_SETUP.md)
5. Quick Start Guide (Step-by-step instructions)
6. Troubleshooting (Common issues for non-technical users)
7. For Developers (Move technical content here)
   - Git clone + virtual environment setup
   - Development dependencies
   - Building standalone executable
```

### 2. Create Platform-Specific Installation Guides

**New File: `docs/INSTALLATION_MAC.md`**

- Step-by-step Mac installation for both methods:
  - Method 1: `pip install git+https://github.com/yourusername/ableton-hub.git`
  - Method 2: Download source + `pip install -r requirements.txt` + venv setup
- Assume Python is already installed (most macOS users have it)
- How to check if Python is installed (quick verification)
- How to install Python if needed (for users who don't have it)
- Virtual environment setup: `python -m venv .venv` then `source .venv/bin/activate`
- How to verify installation worked
- Common Mac-specific issues (permissions, PATH, etc.)
- Terminal command examples with expected output

**New File: `docs/INSTALLATION_WINDOWS.md`**

- Step-by-step Windows installation for both methods:
  - Method 1: `pip install git+https://github.com/yourusername/ableton-hub.git`
  - Method 2: Download source + `pip install -r requirements.txt` + venv setup
- How to check if Python is installed
- How to install Python if needed
- How to add Python to PATH
- Virtual environment setup: `python -m venv .venv` then `.venv\Scripts\activate.bat`
- How to verify installation worked
- Common Windows-specific issues
- Command Prompt/PowerShell examples with expected output

### 3. Create First-Time User Guide

**New File: `docs/FIRST_TIME_SETUP.md`**

- What to expect on first launch
- Empty state explanation (no projects yet)
- How to add your first location
- How to scan for projects
- What happens during scanning
- Understanding the interface
- Next steps after first scan

### 4. Keep Technical Terms with Explanations

**Approach:**

- Keep technical jargon (pip, git clone, virtual environment, SQLite, etc.)
- Add brief explanations in parentheses when first introduced
- Example: "pip (Python package installer)" or "SQLite database (local file-based database)"
- Move advanced developer concepts to developer section
- Explain terms contextually rather than removing them

**Add Explanations:**

- What is Python? (Brief explanation in parentheses)
- Why do I need Python? (Brief explanation)
- What is a command line/Terminal? (Brief explanation)
- What happens when I install? (Brief explanation)

### 5. Text-Based Examples (No Screenshots)

**Focus on:**

- Terminal/Command Prompt command examples with expected output
- Code blocks showing what users should type and what they'll see
- Clear step-by-step instructions without visual dependencies
- Text-based workflow descriptions

### 6. Improve Troubleshooting Section

**Current Issues:**

- Too technical
- Assumes knowledge of PATH, dependencies, etc.
- No solutions for common non-technical problems

**New Troubleshooting Categories:**

- "I can't install Python" (with platform-specific help)
- "The app won't start" (with simple diagnostic steps)
- "I don't see my projects" (common scanning issues)
- "I'm confused by the interface" (link to first-time guide)
- "Something went wrong" (how to report issues)

### 7. Create Quick Reference Card

**New File: `docs/QUICK_REFERENCE.md`**

- One-page cheat sheet
- Common tasks
- Keyboard shortcuts
- Where to find things

## Implementation Plan

### Phase 1: Restructure README.md

- [x] Split into user and developer sections
- [x] Add "What is Ableton Hub?" section at top
- [x] Reorganize installation section:
  - Method 1: `pip install git+https://github.com/yourusername/ableton-hub.git` (from GitHub)
  - Method 2: Download GitHub source + `pip install -r requirements.txt`
  - Include venv setup instructions: `python -m venv .venv`
  - Windows activation: `.venv\Scripts\activate.bat`
  - Mac activation: `source .venv/bin/activate` (or `.venv/bin/activate.sh`)
- [x] Link to platform-specific guides (Mac first, then Windows)
- [x] Keep technical terms with explanations in parentheses
- [x] Move git clone + venv setup to Developer Setup section

### Phase 2: Create Platform-Specific Guides

- [x] Create `docs/INSTALLATION_MAC.md` with step-by-step instructions
- [x] Assume Python is already installed for Mac users
- [x] Create `docs/INSTALLATION_WINDOWS.md` with step-by-step instructions
- [x] Add command examples with expected output (text-based)
- [x] Include Python installation instructions for users who need it
- [x] Add verification steps

### Phase 3: Create First-Time User Guide

- [x] Create `docs/FIRST_TIME_SETUP.md`
- [x] Document first launch experience
- [x] Explain empty state (no screenshots)
- [x] Explain each step of initial setup
- [x] Link from README Quick Start section using relative links

### Phase 4: Improve Troubleshooting

- [x] Rewrite troubleshooting section in README
- [x] Add non-technical language
- [x] Create platform-specific troubleshooting
- [x] Add diagnostic steps users can follow

### Phase 5: Create Supporting Documents

- [x] Create `docs/QUICK_REFERENCE.md`
- [x] Create `docs/FAQ.md` for common questions
- [x] Update README to link to all new docs using relative links (e.g., `[Mac Installation](docs/INSTALLATION_MAC.md)`)
- [x] Ensure all links work in GitHub markdown rendering

## Files Created/Modified

### New Files Created:

- `docs/INSTALLATION_MAC.md` - Mac-specific installation guide
- `docs/INSTALLATION_WINDOWS.md` - Windows-specific installation guide  
- `docs/FIRST_TIME_SETUP.md` - First-time user guide
- `docs/QUICK_REFERENCE.md` - Quick reference card
- `docs/FAQ.md` - Frequently asked questions
- `docs/NEW_USER_EXPERIENCE_PLAN.md` - This document

### Files Modified:

- `README.md` - Restructured for non-technical users:
  - Added "What is Ableton Hub?" section
  - Reorganized installation with Method 1 (pip from GitHub) and Method 2 (source + requirements.txt)
  - Included venv setup instructions for Method 2
  - Added links to platform-specific guides
  - Moved git clone + venv to Developer Setup section
  - Improved troubleshooting section
  - Added explanations for technical terms in parentheses
  - Reorganized content to prioritize user documentation over developer documentation

## Key Principles Applied

1. **Mac First**: All platform-specific content prioritizes Mac, then Windows ✅
2. **Progressive Disclosure**: Basic info first, advanced/developer info later ✅
3. **Text-Based Examples**: Used command examples with expected output (no screenshots) ✅
4. **Keep Technical Terms**: Maintained jargon but explained in parentheses when first introduced ✅
5. **Mac Python Assumption**: Assumed most macOS users already have Python installed ✅
6. **Relative Links**: Used GitHub-compatible relative links in README ✅
7. **Action-Oriented**: Focused on "how to do X" rather than "what is X" ✅
8. **Error Prevention**: Anticipated common mistakes and provided prevention ✅
9. **Recovery Paths**: Provided clear next steps when errors occur ✅

## Success Metrics

The documentation improvements should result in:
- Non-technical users can install without asking for help
- Users understand what to do on first launch
- Common questions are answered in documentation
- Installation success rate increases
- Support requests decrease
