# macOS Installation Guide

This guide will walk you through installing Ableton Hub on macOS step by step.

## Prerequisites

Most Macs come with Python (programming language) already installed. We'll check this first.

## Step 1: Check if Python is Installed

1. **Open Terminal**:
   - Press `Cmd + Space` to open Spotlight
   - Type "Terminal" and press Enter

2. **Check Python version**:
   Type this command and press Enter:
   ```bash
   python3 --version
   ```

   **Expected output:**
   ```
   Python 3.11.x
   ```
   or
   ```
   Python 3.12.x
   ```

   ✅ **If you see Python 3.11 or higher**, you're all set! Skip to Step 2.

   ❌ **If you see an error** or Python 2.x, you'll need to install Python (see below).

### Installing Python (if needed)

**Option A: Official Python Installer (Recommended)**
1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download the latest Python 3.11 or 3.12 installer for macOS
3. Run the installer and follow the prompts
4. Make sure to check "Add Python to PATH" if that option appears
5. After installation, close and reopen Terminal, then verify with `python3 --version`

**Option B: Using Homebrew (if you have it)**
```bash
brew install python3
```

## Step 2: Choose Installation Method

You have two options:

### Method 1: Install from GitHub (Recommended - Easiest)

This method uses pip (Python package installer) to automatically download and install everything.

1. **Open Terminal** (if not already open)

2. **Install Ableton Hub**:
   ```bash
   pip install git+https://github.com/EazyTom/ableton-hub.git
   ```

   **Expected output:**
   ```
   Collecting git+https://github.com/EazyTom/ableton-hub.git
   Installing collected packages: ...
   Successfully installed ableton-hub-0.3.0
   ```

3. **Run Ableton Hub**:
   ```bash
   ableton-hub
   ```

   The application should launch! If you see any errors, see the Troubleshooting section below.

### Method 2: Download Source and Install

If you prefer to download the source code and install manually:

1. **Download the source code**:
   - Go to the GitHub repository: https://github.com/EazyTom/ableton-hub
   - Click the green "Code" button
   - Click "Download ZIP"
   - Extract the ZIP file (usually goes to your Downloads folder)
   - **Note**: The extracted folder will be named `Ableton-Hub-main`

2. **Open Terminal** and navigate to the extracted folder:
   ```bash
   cd ~/Downloads/Ableton-Hub-main
   ```
   (Adjust the path if you extracted it to a different location. The folder name will be `Ableton-Hub-main` when you download the ZIP from GitHub.)

3. **Set up a virtual environment** (recommended - keeps dependencies isolated):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   **Expected output:**
   You should see `(.venv)` appear at the beginning of your Terminal prompt, like:
   ```
   (.venv) yourname@yourmac Ableton-Hub-main %
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   **Expected output:**
   ```
   Collecting PyQt6>=6.6.0
   Collecting SQLAlchemy>=2.0.0
   ...
   Successfully installed ...
   ```

   This may take a few minutes as it downloads and installs all required packages.

5. **Run the application**:
   ```bash
   python -m src.main
   ```

   The application should launch!

## Step 3: Verify Installation

After installation, you should see the Ableton Hub window open. If it doesn't appear:

1. Check Terminal for any error messages
2. Make sure you activated the virtual environment (if using Method 2) - you should see `(.venv)` in your prompt
3. Try running the command again

## Troubleshooting

### "pip: command not found"

This means pip (Python package installer) isn't available. Try:
```bash
python3 -m pip install git+https://github.com/EazyTom/ableton-hub.git
```

### "Permission denied" errors

You may need to use `sudo` (superuser do - administrator privileges), but this is not recommended. Instead, try:
```bash
pip install --user git+https://github.com/EazyTom/ableton-hub.git
```

### "Command 'ableton-hub' not found"

If you installed using Method 1 but can't run `ableton-hub`:
- Make sure the installation completed successfully
- Try using the full path: `python3 -m ableton_hub.main`
- Or reinstall: `pip install --upgrade git+https://github.com/EazyTom/ableton-hub.git`

### Virtual environment not activating

If `source .venv/bin/activate` doesn't work:
- Make sure you're in the correct directory (where you ran `python3 -m venv .venv`)
- Try: `. .venv/bin/activate` (with a dot and space before the path)
- On some shells, you might need: `source .venv/bin/activate.sh`

### "ModuleNotFoundError" or missing dependencies

If you see errors about missing modules:
- Make sure you ran `pip install -r requirements.txt` (Method 2)
- Make sure your virtual environment is activated (you should see `(.venv)` in your prompt)
- Try reinstalling: `pip install --upgrade -r requirements.txt`

### The app won't start

- Check Terminal for error messages - they usually tell you what's wrong
- Make sure Python 3.11+ is installed: `python3 --version`
- Try running with verbose output: `python -m src.main --verbose`

## Next Steps

Once Ableton Hub is installed and running:

1. Check out the [First Time Setup Guide](FIRST_TIME_SETUP.md) to learn what to expect on first launch
2. Add your first project location
3. Start scanning for projects!

## Updating Ableton Hub

**If you used Method 1 (pip install):**
```bash
pip install --upgrade git+https://github.com/EazyTom/ableton-hub.git
```

**If you used Method 2 (source installation):**
1. Download the latest source code ZIP from GitHub
2. Extract it (creates `Ableton-Hub-main` folder)
3. Navigate to the folder in Terminal: `cd ~/Downloads/Ableton-Hub-main`
4. Activate your virtual environment: `source .venv/bin/activate`
5. Update dependencies: `pip install --upgrade -r requirements.txt`

## Getting Help

If you're still having trouble:
- Check the [FAQ](FAQ.md) for common questions
- Review the [Troubleshooting section](../README.md#-troubleshooting) in the main README
- Open an issue on GitHub with details about your problem
