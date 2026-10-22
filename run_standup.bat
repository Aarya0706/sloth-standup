@echo off
REM Used by Windows Task Scheduler. Runs from this folder.
cd /d "%~dp0"
python -m sloth_standup
