
@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
start "" "d:\Programming\Projects\Python\MidiToPad\.venv\Scripts\pythonw.exe" main.py
exit
