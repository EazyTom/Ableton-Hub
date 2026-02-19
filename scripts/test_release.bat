@echo off
REM Release Validation Runner for Ableton Hub
REM Runs comprehensive pre-release validation

cd /d "%~dp0.."
python tests\test_release.py %*
