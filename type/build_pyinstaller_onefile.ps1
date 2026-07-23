# PROTOTYPE - PyInstaller One-File Build Script
# ============================================
# One-file = easier for distribution to end-users
# Slower startup = extracts everything to temp on every launch

Write-Host "=== Building WhisperGUGUGAGA - PyInstaller One-File Mode ===" -ForegroundColor Cyan

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Error: uv not found. Please install uv first." -ForegroundColor Red
    exit 1
}

uv pip install pyinstaller

Write-Host "`nStarting build..." -ForegroundColor Yellow

uv run pyinstaller `
    --onefile `
    --windowed `
    --name WhisperGUGUGAGA `
    --add-data "config.yaml;." `
    --clean `
    main.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Build completed!" -ForegroundColor Green
    Write-Host "Output: dist\WhisperGUGUGAGA.exe" -ForegroundColor Gray
    Write-Host "Size: ~50MB expected" -ForegroundColor Gray
    Write-Host "`nStartup: Slower than directory mode - needs to extract everything first" -ForegroundColor Gray
} else {
    Write-Host "`n❌ Build failed" -ForegroundColor Red
}
