# UniVibe PyInstaller build script
# Run from project root: .\build.ps1

Set-Location $PSScriptRoot

Write-Host "[build] Installing PyInstaller..."
.\.venv\Scripts\pip install pyinstaller

Write-Host "[build] Running PyInstaller..."
.\.venv\Scripts\pyinstaller univibe.spec --clean

Write-Host "[build] Done. Output: dist\UniVibe.exe"
