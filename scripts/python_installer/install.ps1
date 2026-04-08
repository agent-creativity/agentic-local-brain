#
# LocalBrain Python Installer for Windows
#
# Usage:
#   irm https://localbrain.io.alibaba-inc.com/python_installer/install.ps1 | iex
#
# Environment variables:
#   $env:LOCALBRAIN_SERVER  - Server URL
#   $env:LOCALBRAIN_VERSION - Version to install

param()

$ErrorActionPreference = "Stop"

# Configuration
$ServerUrl = if ($env:LOCALBRAIN_SERVER) { $env:LOCALBRAIN_SERVER } else { "https://localbrain.io.alibaba-inc.com" }
$Version = if ($env:LOCALBRAIN_VERSION) { $env:LOCALBRAIN_VERSION } else { "latest" }
$InstallDir = "$env:USERPROFILE\.localbrain"
$VenvDir = "$InstallDir\venv"
$BinDir = "$InstallDir\bin"

# Colors
function Write-Info($message) { Write-Host "[INFO] $message" -ForegroundColor Green }
function Write-Warn($message) { Write-Host "[WARN] $message" -ForegroundColor Yellow }
function Write-Err($message) { Write-Host "[ERROR] $message" -ForegroundColor Red; exit 1 }

# Check Python
function Check-Python {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Err "Python 3.8+ is required. Please install Python first."
    }
    
    $versionOutput = python --version 2>&1
    $pythonVersion = $versionOutput.ToString().Split()[1]
    Write-Info "Python $pythonVersion detected"
}

# Check existing
function Check-Existing {
    if (Test-Path $VenvDir) {
        Write-Warn "Virtual environment already exists at $VenvDir"
        Write-Info "Removing existing venv for clean install"
        Remove-Item -Recurse -Force $VenvDir
    }
}

# Fetch version info
function Fetch-VersionInfo {
    $url = "$ServerUrl/version.json"
    Write-Info "Fetching version info from $url"
    
    try {
        $response = Invoke-RestMethod -Uri $url -Method Get
        if ($Version -eq "latest") {
            $script:Version = $response.version
            Write-Info "Latest version: $Version"
        }
    }
    catch {
        Write-Err "Failed to fetch version info: $_"
    }
}

# Create venv
function Create-Venv {
    Write-Info "Creating virtual environment at $VenvDir"
    python -m venv $VenvDir
    Write-Info "Virtual environment created"
}

# Install wheel
function Install-Wheel {
    $wheelUrl = "$ServerUrl/python_installer/packages/localbrain-$Version-py3-none-any.whl"
    
    Write-Info "Downloading and installing wheel from $wheelUrl"
    
    & "$VenvDir\Scripts\Activate.ps1"
    pip install --upgrade pip --quiet
    pip install $wheelUrl
    deactivate
    
    Write-Info "Wheel installed successfully"
}

# Create bin link (Windows: copy)
function Create-BinLink {
    New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
    Copy-Item "$VenvDir\Scripts\localbrain.exe" "$BinDir\localbrain.exe" -Force
    Write-Info "Binary ready at $BinDir\localbrain.exe"
}

# Add to PATH
function Add-ToPath {
    $path = [Environment]::GetEnvironmentVariable("PATH", "User")
    
    if ($path -like "*$BinDir*") {
        Write-Info "Already in PATH"
        return
    }
    
    [Environment]::SetEnvironmentVariable("PATH", "$BinDir;$path", "User")
    Write-Info "Added to PATH"
}

# Write install info
function Write-InstallInfo {
    $installInfo = @{
        version = $Version
        install_time = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        install_path = "$BinDir\localbrain.exe"
        install_type = "python"
        source_url = "$ServerUrl/python_installer/packages/localbrain-$Version-py3-none-any.whl"
        venv_path = $VenvDir
    }
    
    $infoPath = "$InstallDir\.install-info"
    $installInfo | ConvertTo-Json | Set-Content -Path $infoPath
    
    Write-Info "Install info written to $infoPath"
}

# Print success
function Print-Success {
    Write-Host ""
    Write-Host "✓ LocalBrain installed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Version: $Version"
    Write-Host "Type:    Python (venv)"
    Write-Host "Binary:  $BinDir\localbrain.exe"
    Write-Host "Venv:    $VenvDir"
    Write-Host ""
    Write-Host "Next steps:"
    Write-Host "  1. Restart your terminal or run 'refreshenv'"
    Write-Host "  2. Run 'localbrain init setup' to initialize"
    Write-Host "  3. Run 'localbrain doctor' to verify installation"
    Write-Host ""
}

# Main
Write-Info "Installing LocalBrain (Python method)..."

Check-Python
Check-Existing
Fetch-VersionInfo
Create-Venv
Install-Wheel
Create-BinLink
Write-InstallInfo
Add-ToPath
Print-Success
