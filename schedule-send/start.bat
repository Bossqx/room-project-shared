@echo off
cd /d "%~dp0"
start "" /B sendenv\Scripts\pythonw.exe schedule_service.py
