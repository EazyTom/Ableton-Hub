# Windows Installation Guide

This guide will walk you through installing Ableton Hub on Windows step by step.

## Prerequisites

You'll need Python (programming language) installed. We'll check this first.

## Step 1: Check if Python is Installed

1. **Open Command Prompt or PowerShell**:
   - Press `Win + R` to open Run dialog
   - Type `cmd` or `powershell` and press Enter
   - Or search for "Command Prompt" or "PowerShell" in the Start menu

2. **Check Python version**:
   Type this command and press Enter:
   ```bash
   python --version
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

1. **Download Python**:
   - Go to [python.org/downloads](https://www.python.org/downloads/)
   - Download the latest Python 3.11 or 3.12 installer for Windows
   - Run the installer

2. **Important during installation**:
   - ✅ **Check the box** "Add Python to PATH" (this is very important!)
   - Click "Install Now"
   - Wait for installation to complete

3. **Verify installation**:
   - Close and reopen Command Prompt/PowerShell
   - Type: `python --version`
   - You should see Python 3.11.x or 3.12.x

   ⚠️ **If Python still isn't found**, you may need to add it to PATH manually:
   - Search for "Environment Variables" in Windows Settings
   - Edit the "Path" variable
   - Add: `C:\Users\YourName\AppData\Local\Programs\Python\Python3XX` (replace XX with your version)
   - Add: `C:\Users\YourName\AppData\Local\Programs\Python\Python3XX\Scripts`

## Step 2: Choose Installation Method

You have two options:

### Method 1: Install from GitHub (Recommended - Easiest)

This method uses pip (Python package installer) to automatically download and install everything.

1. **Open Command Prompt or PowerShell** (if not already open)

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

2. **Open Command Prompt or PowerShell** and navigate to the extracted folder:
   ```bash
   cd C:\Users\YourName\Downloads\Ableton-Hub-main
   ```
   (Adjust the path to match where you extracted the ZIP file. The folder name will be `Ableton-Hub-main` when you download the ZIP from GitHub.)

3. **Set up a virtual environment** (recommended - keeps dependencies isolated):
   ```bash
   python -m venv .venv
   .venv\Scripts\activate.bat
   ```

   **Expected output:**
   You should see `(.venv)` appear at the beginning of your Command Prompt, like:
   ```
   (.venv) C:\Users\YourName\Downloads\Ableton-Hub-main>
   ```

   **Note**: In PowerShell, you might need to use:
   ```powershell
   .venv\Scripts\Activate.ps1
   ```
   If you get an execution policy error, run:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
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
   
   **Option A: Command Line**
   ```bash
   python -m src.main
   ```
   
   **Option B: Launcher Script** (Easier - no command line needed)
   - Double-click `run-ableton-hub.bat` to run the application
   - **Tip**: Create a desktop shortcut to `run-ableton-hub.bat` for easy access:
     1. Right-click `run-ableton-hub.bat`
     2. Select "Create shortcut"
     3. Drag the shortcut to your desktop
     4. You can rename it to "Ableton Hub" if you like

   The application should launch!

## Step 3: Verify Installation

After installation, you should see the Ableton Hub window open. If it doesn't appear:

1. Check Command Prompt/PowerShell for any error messages
2. Make sure you activated the virtual environment (if using Method 2) - you should see `(.venv)` in your prompt
3. Try running the command again

## Troubleshooting

### "pip is not recognized" or "pip: command not found"

This means pip (Python package installer) isn't available. Try:
```bash
python -m pip install git+https://github.com/EazyTom/ableton-hub.git
```

### "Python is not recognized"

This means Python isn't in your PATH (system path). Solutions:
1. Reinstall Python and make sure to check "Add Python to PATH"
2. Or manually add Python to PATH (see Step 1 above)

### "Permission denied" errors

You may see permission errors. Try:
```bash
pip install --user git+https://github.com/EazyTom/ableton-hub.git
```

Or run Command Prompt as Administrator (right-click → "Run as administrator").

### "Command 'ableton-hub' not found"

If you installed using Method 1 but can't run `ableton-hub`:
- Make sure the installation completed successfully
- Try using the full path: `python -m ableton_hub.main`
- Or reinstall: `pip install --upgrade git+https://github.com/EazyTom/ableton-hub.git`

### Virtual environment not activating

If `.venv\Scripts\activate.bat` doesn't work:
- Make sure you're in the correct directory (where you ran `python -m venv .venv`)
- In PowerShell, try: `.venv\Scripts\Activate.ps1`
- Check that the `.venv` folder exists in your current directory

### PowerShell execution policy error

If you see "execution of scripts is disabled" in PowerShell:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Then try activating again: `.venv\Scripts\Activate.ps1`

### "ModuleNotFoundError" or missing dependencies

If you see errors about missing modules:
- Make sure you ran `pip install -r requirements.txt` (Method 2)
- Make sure your virtual environment is activated (you should see `(.venv)` in your prompt)
- Try reinstalling: `pip install --upgrade -r requirements.txt`

### The app won't start

- Check Command Prompt/PowerShell for error messages - they usually tell you what's wrong
- Make sure Python 3.11+ is installed: `python --version`
- Try running with verbose output: `python -m src.main --verbose`

### Antivirus blocking installation

Some antivirus software may flag Python packages. If installation is blocked:
- Temporarily disable antivirus during installation
- Or add Python/pip to your antivirus whitelist
- The application is safe - it's open source and doesn't connect to external servers

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
3. Navigate to the folder in Command Prompt/PowerShell: `cd C:\Users\YourName\Downloads\Ableton-Hub-main`
4. Activate your virtual environment: `.venv\Scripts\activate.bat` (or `.ps1` in PowerShell)
5. Update dependencies: `pip install --upgrade -r requirements.txt`

## Getting Help

If you're still having trouble:
- Check the [FAQ](FAQ.md) for common questions
- Review the [Troubleshooting section](../README.md#-troubleshooting) in the main README
- Open an issue on GitHub with details about your problem
