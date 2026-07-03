@echo off
title SongSorter - Build Installer
cd /d "%~dp0"
echo ============================================
echo   Building SongSorter Installer...
echo ============================================
python build_installer.py
pause
