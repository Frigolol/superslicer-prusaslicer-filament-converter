@echo off
cd /d "%~dp0"
where pyw >nul 2>nul && (start "" pyw converter_gui.py & exit /b)
where pythonw >nul 2>nul && (start "" pythonw converter_gui.py & exit /b)
echo Python is not installed. Download it from python.org (tick "Add Python to PATH").
pause
