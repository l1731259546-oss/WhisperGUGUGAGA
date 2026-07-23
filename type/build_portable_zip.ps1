# PROTOTYPE - Portable Python + ZIP Build Script
# =============================================
# No compilation at all - just bundle portable Python + code
# Fast startup (same as regular Python)
# Easiest builder experience after initial setup

Write-Host "=== Building WhisperGUGUGAGA - Portable Python ZIP ===" -ForegroundColor Cyan

Write-Host "This approach:" -ForegroundColor Yellow
Write-Host "  - No compilation ever - just copy files" -ForegroundColor Gray
Write-Host "  - Fast startup (native Python speed)" -ForegroundColor Gray
Write-Host "  - Needs to bundle portable Python (~50MB)" -ForegroundColor Gray
Write-Host ""

# Step by step instructions
Write-Host "Step 1: Download Python embeddable package" -ForegroundColor Cyan
Write-Host "  Go to: https://www.python.org/downloads/windows/" -ForegroundColor Gray
Write-Host "  Download 'Windows embeddable package (64-bit)' matching your Python version" -ForegroundColor Gray
Write-Host "  Extract it to a folder named 'python'" -ForegroundColor Gray
Write-Host ""

Write-Host "Step 2: Install dependencies to the portable python" -ForegroundColor Cyan
Write-Host "  .\python\python.exe -m pip install -r requirements.txt" -ForegroundColor Gray
Write-Host "  (or use: uv pip install --target .\python\Lib\site-packages -r pyproject.toml)" -ForegroundColor Gray
Write-Host ""

Write-Host "Step 3: Copy your project code" -ForegroundColor Cyan
Write-Host "  mkdir dist\WhisperGUGUGAGA" -ForegroundColor Gray
Write-Host "  xcopy /E /I python dist\WhisperGUGUGAGA\python" -ForegroundColor Gray
Write-Host "  xcopy /E /I src dist\WhisperGUGUGAGA\src" -ForegroundColor Gray
Write-Host "  copy main.py dist\WhisperGUGUGAGA\" -ForegroundColor Gray
Write-Host "  copy config.yaml dist\WhisperGUGUGAGA\" -ForegroundColor Gray
Write-Host ""

Write-Host "Step 4: Create launch script" -ForegroundColor Cyan
@'
@echo off
python\python.exe main.py
'@ | Out-File -FilePath "dist\WhisperGUGUGAGA\run.bat" -Encoding ASCII
Write-Host "  Created run.bat" -ForegroundColor Gray
Write-Host ""

Write-Host "Step 5: ZIP it" -ForegroundColor Cyan
Write-Host "  Compress dist\WhisperGUGUGAGA to WhisperGUGUGAGA.zip" -ForegroundColor Gray
Write-Host "  Done! End-user just extracts and double-clicks run.bat" -ForegroundColor Gray
Write-Host ""

Write-Host "✅ Setup complete after initial download" -ForegroundColor Green
Write-Host "Subsequent rebuilds just need copying changed files - no compilation" -ForegroundColor Gray
Write-Host "Total size: ~120MB expected" -ForegroundColor Gray
Write-Host "Startup: Fast - same as running with regular Python" -ForegroundColor Gray
