#
# LocalBrain Installer for Windows
#
# Usage:
#   irm https://localbrain.io.alibaba-inc.com/binary_installer/install.ps1 | iex
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
$BinDir = "$InstallDir\bin"

# Colors
function Write-Info($message) { Write-Host "[INFO] $message" -ForegroundColor Green }
function Write-Warn($message) { Write-Host "[WARN] $message" -ForegroundColor Yellow }
function Write-Err($message) { Write-Host "[ERROR] $message" -ForegroundColor Red; exit 1 }

# Detect platform
function Detect-Platform {
    $OS = "win"
    # Detect architecture including ARM64 support
    $Arch = if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") {
        "arm64"
    } elseif ([Environment]::Is64BitOperatingSystem) {
        "x64"
    } else {
        "x86"
    }
    $script:Platform = "$OS-$Arch"
    Write-Info "Detected platform: $Platform"
}

# Check if already installed
function Check-Existing {
    if (Test-Path "$BinDir\localbrain.exe") {
        Write-Warn "LocalBrain is already installed at $BinDir\localbrain.exe"
        Write-Info "Run 'localbrain self-update' to update to the latest version"
        exit 0
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

# Download binary
function Download-Binary {
    $filename = "localbrain-$Platform.exe"
    $url = "$ServerUrl/binary_installer/releases/v$Version/$filename"
    $tempFile = "$env:TEMP\localbrain.exe"
    
    Write-Info "Downloading binary from $url"
    
    try {
        Invoke-WebRequest -Uri $url -OutFile $tempFile -UseBasicParsing
    }
    catch {
        Write-Err "Failed to download: $_"
    }
    
    # Create directory and move
    New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
    Move-Item -Path $tempFile -Destination "$BinDir\localbrain.exe" -Force
    
    Write-Info "Binary installed to $BinDir\localbrain.exe"
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
    Write-Info "Restart your terminal or run 'refreshenv' to update PATH"
}

# Write install info
function Write-InstallInfo {
    $installInfo = @{
        version = $Version
        install_time = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        install_path = "$BinDir\localbrain.exe"
        source_url = "$ServerUrl/releases/v$Version/localbrain-$Platform.exe"
        platform = "windows"
        architecture = $Platform.Split("-")[1]
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
    Write-Host "Binary:  $BinDir\localbrain.exe"
    Write-Host ""
    Write-Host "Next steps:"
    Write-Host "  1. Restart your terminal or run 'refreshenv'"
    Write-Host "  2. Run 'localbrain init setup' to initialize"
    Write-Host "  3. Run 'localbrain doctor' to verify installation"
    Write-Host ""
}

# Main
Write-Info "Installing LocalBrain..."

Detect-Platform
Check-Existing
Fetch-VersionInfo
Download-Binary
Write-InstallInfo
Add-ToPath
Print-Success
