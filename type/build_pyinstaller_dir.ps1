# PROTOTYPE - PyInstaller Directory Mode Build Script
# =================================================
# Recommendation when: Builder Ease = High, Startup Speed = High (your requirements
# No C compiler needed - works immediately
# Directory mode = faster startup than one-file (no extraction every time

Write-Host "=== Building WhisperGUGUGAGA - PyInstaller Directory Mode ===" -ForegroundColor Cyan

# Check if uv is available
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Error: uv not found. Please install uv first." -ForegroundColor Red
    exit 1
}

# Install PyInstaller if not installed
uv add --project .
uv pip install pyinstaller

Write-Host "`nStarting build..." -ForegroundColor Yellow

# Build command
# --directory = output directory, faster startup
# --windowed = no console window for GUI app
# --name = output name
# Add any data files you need to include
uv run pyinstaller `
    --windowed `
    --directory `
    --name WhisperGUGUGAGA `
    --add-data "config.yaml;." `
    --clean `
    main.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Build completed!" -ForegroundColor Green
    Write-Host "Output: dist\WhisperGUGUGAGA\WhisperGUGUGAGA.exe" -ForegroundColor Gray
    Write-Host "Size: ~60MB expected" -ForegroundColor Gray
    Write-Host "`nStartup: Faster than one-file mode because no extraction required" -ForegroundColor Gray
} else {
    Write-Host "`n❌ Build failed" -ForegroundColor Red
}
