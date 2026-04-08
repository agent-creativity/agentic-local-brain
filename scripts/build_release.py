#!/usr/bin/env python3
"""
Build release package for localbrain.

This script builds the complete release structure ready for deployment:
- Python wheel package with install scripts
- Binary packages with install scripts
- version.json for update checking

Usage:
    python scripts/build_release.py --version 0.5.0
    python scripts/build_release.py --version 0.5.0 --wheel-only
    python scripts/build_release.py --version 0.5.0 --binary-only --platform macos-arm64

The output structure in dist/:
    dist/
    ├── version.json
    ├── python_installer/
    │   ├── install.sh
    │   ├── install.ps1
    │   └── packages/
    │       ├── localbrain-{version}-py3-none-any.whl
    │       └── localbrain-{version}-py3-none-any.whl.sha256
    └── binary_installer/
        ├── install.sh
        ├── install.ps1
        └── releases/
            └── v{version}/
                ├── localbrain-macos-arm64
                ├── localbrain-macos-arm64.sha256
                └── ...
"""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# Build dependencies for binary builds
BUILD_DEPENDENCIES = ["pyinstaller>=5.0", "pyinstaller-hooks-contrib>=2023.0"]


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent


def get_venv_python(venv_path: Path) -> Path:
    """Get Python executable path in virtual environment."""
    if platform.system() == "Windows":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def setup_build_venv(project_root: Path, for_binary: bool = True) -> tuple[Path, Path]:
    """
    Setup or reuse virtual environment for building.
    
    Returns:
        tuple: (venv_path, python_executable_path)
    """
    # Check for existing venv
    venv_candidates = [project_root / ".venv", project_root / "venv"]
    existing_venv = None
    
    for candidate in venv_candidates:
        python_path = get_venv_python(candidate)
        if candidate.exists() and python_path.exists():
            # Verify venv has pip
            result = subprocess.run(
                [str(python_path), "-m", "pip", "--version"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                existing_venv = candidate
                break
            else:
                print(f"  Warning: {candidate} exists but pip is not available, recreating...")
    
    if existing_venv:
        print(f"\nUsing existing virtual environment: {existing_venv}")
        venv_path = existing_venv
    else:
        # Create new venv
        venv_path = project_root / ".venv"
        print(f"\nCreating virtual environment: {venv_path}")
        
        # Remove old broken venv if exists
        if venv_path.exists():
            shutil.rmtree(venv_path)
        
        # Create venv using subprocess for better compatibility
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_path), "--clear"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"  Warning: venv creation output: {result.stderr}")
        
        print("  Virtual environment created")
    
    python_exe = get_venv_python(venv_path)
    
    # Ensure pip is available
    result = subprocess.run(
        [str(python_exe), "-m", "pip", "--version"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # Install pip manually
        print("  Installing pip in virtual environment...")
        subprocess.run([str(python_exe), "-m", "ensurepip", "--upgrade"], capture_output=True)
    
    # Upgrade pip
    subprocess.run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], capture_output=True)
    
    # Install project dependencies for binary build
    if for_binary:
        print("\nInstalling project dependencies...")
        result = subprocess.run(
            [str(python_exe), "-m", "pip", "install", "-r", str(project_root / "requirements.txt")],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        if result.returncode != 0:
            print(f"  Warning: Some dependencies may not have installed: {result.stderr[:200]}")
        else:
            print("  Project dependencies installed")
    
    # Install build dependencies if building binary
    if for_binary:
        print("\nChecking build dependencies...")
        result = subprocess.run(
            [str(python_exe), "-m", "pip", "list", "--format=json"],
            capture_output=True,
            text=True,
        )
        
        installed_packages = set()
        if result.returncode == 0:
            import json as json_mod
            try:
                packages = json_mod.loads(result.stdout)
                installed_packages = {p["name"].lower() for p in packages}
            except json_mod.JSONDecodeError:
                pass
        
        # Check if pyinstaller is installed
        needs_install = "pyinstaller" not in installed_packages
        
        if needs_install:
            print(f"  Installing build dependencies: {', '.join(BUILD_DEPENDENCIES)}")
            result = subprocess.run(
                [str(python_exe), "-m", "pip", "install"] + BUILD_DEPENDENCIES,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(f"  STDERR: {result.stderr}")
                raise RuntimeError("Failed to install build dependencies")
            print("  Build dependencies installed")
        else:
            print("  Build dependencies already installed")
    
    return venv_path, python_exe


def get_platform_key() -> str:
    """Get current platform key."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if machine in ("x86_64", "amd64"):
        arch = "x64"
    elif machine in ("arm64", "aarch64"):
        arch = "arm64"
    else:
        arch = machine
    
    return f"{system}-{arch}"


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def clean_dist(dist_dir: Path) -> None:
    """Clean dist directory."""
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True)


def build_wheel(project_root: Path, dist_dir: Path, version: str, python_exe: Path = None) -> Path:
    """Build wheel and return path to wheel file."""
    print("\n[1/2] Building Python wheel...")
    
    # Use provided python or fall back to current
    if python_exe is None:
        python_exe = Path(sys.executable)
    
    # Ensure packages directory exists
    packages_dir = dist_dir / "python_installer" / "packages"
    packages_dir.mkdir(parents=True, exist_ok=True)
    
    # Update VERSION file
    version_file = project_root / "VERSION"
    version_file.write_text(version)
    print(f"  Updated VERSION file to {version}")
    
    # Build wheel
    print(f"  Building wheel for localbrain v{version}...")
    result = subprocess.run(
        [str(python_exe), "-m", "pip", "wheel", ".", "--no-deps", "-w", str(packages_dir)],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        print(f"  STDOUT: {result.stdout}")
        print(f"  STDERR: {result.stderr}")
        raise RuntimeError(f"Wheel build failed with exit code {result.returncode}")
    
    # Find the wheel (package name is now 'localbrain', so wheel is already correctly named)
    wheels = list(packages_dir.glob("*.whl"))
    if not wheels:
        raise FileNotFoundError("No wheel found")
    
    wheel_path = wheels[0]
    expected_name = f"localbrain-{version}-py3-none-any.whl"
    
    if wheel_path.name != expected_name:
        print(f"  Warning: wheel name '{wheel_path.name}' doesn't match expected '{expected_name}'")
    
    print(f"  Built: {wheel_path.name}")
    
    # Generate checksum
    checksum = calculate_sha256(wheel_path)
    checksum_file = wheel_path.with_suffix(".whl.sha256")
    checksum_file.write_text(f"sha256:{checksum}  {wheel_path.name}\n")
    print(f"  Checksum: {checksum_file.name}")
    
    return wheel_path


def build_binary(project_root: Path, dist_dir: Path, version: str, platform_key: str = None, python_exe: Path = None) -> Path:
    """Build binary using PyInstaller."""
    print(f"\n[2/2] Building binary for {platform_key}...")
    
    # Use provided python or fall back to current
    if python_exe is None:
        python_exe = Path(sys.executable)
    
    # Ensure releases directory exists
    releases_dir = dist_dir / "binary_installer" / "releases" / f"v{version}"
    releases_dir.mkdir(parents=True, exist_ok=True)
    
    # Update VERSION file
    version_file = project_root / "VERSION"
    version_file.write_text(version)
    
    # Run PyInstaller
    env = os.environ.copy()
    env["VERSION"] = version
    
    result = subprocess.run(
        [str(python_exe), "-m", "PyInstaller", "localbrain.spec", "--clean", "--noconfirm"],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        print(f"  STDOUT: {result.stdout}")
        print(f"  STDERR: {result.stderr}")
        raise RuntimeError(f"PyInstaller failed with exit code {result.returncode}")
    
    # Find and rename binary
    build_dir = project_root / "dist"
    binary_name = f"localbrain-{platform_key}"
    if platform.system() == "Windows":
        binary_name += ".exe"
    
    # Find built binary
    binaries = [f for f in build_dir.iterdir() if f.is_file() and f.name.startswith("localbrain")]
    if not binaries:
        raise FileNotFoundError(f"No binary found in {build_dir}")
    
    source_binary = binaries[0]
    target_binary = releases_dir / binary_name
    shutil.move(str(source_binary), str(target_binary))
    
    print(f"  Built: {target_binary.name}")
    
    # Generate checksum
    checksum = calculate_sha256(target_binary)
    checksum_file = target_binary.with_suffix(".sha256")
    checksum_file.write_text(f"sha256:{checksum}  {target_binary.name}\n")
    print(f"  Checksum: {checksum_file.name}")
    
    # Cleanup PyInstaller build artifacts
    build_cache = project_root / "build"
    if build_cache.exists():
        shutil.rmtree(build_cache)
    
    return target_binary


def copy_install_scripts(project_root: Path, dist_dir: Path, wheel_only: bool, binary_only: bool) -> None:
    """Copy install scripts to dist."""
    scripts_dir = project_root / "scripts"
    
    if not binary_only:
        # Copy Python installer scripts
        print("\nCopying Python installer scripts...")
        python_installer_src = scripts_dir / "python_installer"
        python_installer_dst = dist_dir / "python_installer"
        
        for script in ["install.sh", "install.ps1"]:
            src = python_installer_src / script
            if src.exists():
                dst = python_installer_dst / script
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, dst)
                print(f"  Copied: {script}")
    
    if not wheel_only:
        # Copy binary installer scripts
        print("\nCopying binary installer scripts...")
        binary_installer_src = scripts_dir / "binary_installer"
        binary_installer_dst = dist_dir / "binary_installer"
        
        for script in ["install.sh", "install.ps1"]:
            src = binary_installer_src / script
            if src.exists():
                dst = binary_installer_dst / script
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, dst)
                print(f"  Copied: {script}")


def get_sha256(file_path: Path) -> Optional[str]:
    """Read SHA256 from .sha256 file or compute it."""
    sha256_file = Path(str(file_path) + ".sha256")
    if sha256_file.exists():
        # Parse the sha256 file: "sha256:<hash>  <filename>"
        content = sha256_file.read_text().strip()
        # Format: "sha256:<hash>  <filename>" or just "<hash>  <filename>"
        parts = content.split()
        for part in parts:
            if part.startswith("sha256:"):
                return part.replace("sha256:", "")
            elif len(part) == 64:  # SHA256 hex string length
                return part
    return None


def generate_version_json(dist_dir: Path, version: str) -> None:
    """Generate version.json file with SHA256 hashes."""
    print("\nGenerating version.json...")
    
    # Platform names must match actual binary names from get_platform_key()
    # which uses platform.system().lower(): darwin, linux, windows
    platforms = {}
    platform_specs = [
        ("darwin-arm64", f"localbrain-darwin-arm64"),
        ("darwin-x64", f"localbrain-darwin-x64"),
        ("linux-arm64", f"localbrain-linux-arm64"),
        ("linux-x64", f"localbrain-linux-x64"),
        ("windows-x64", f"localbrain-windows-x64.exe"),
    ]
    
    for platform_key, binary_name in platform_specs:
        binary_path = dist_dir / "binary_installer" / "releases" / f"v{version}" / binary_name
        rel_path = f"binary_installer/releases/v{version}/{binary_name}"
        sha256 = get_sha256(binary_path) if binary_path.exists() else None
        
        platforms[platform_key] = {
            "path": rel_path,
        }
        if sha256:
            platforms[platform_key]["sha256"] = sha256
    
    # Python wheel
    wheel_name = f"localbrain-{version}-py3-none-any.whl"
    wheel_path = dist_dir / "python_installer" / "packages" / wheel_name
    wheel_rel_path = f"python_installer/packages/{wheel_name}"
    wheel_sha256 = get_sha256(wheel_path) if wheel_path.exists() else None
    
    python_package = {"path": wheel_rel_path}
    if wheel_sha256:
        python_package["sha256"] = wheel_sha256
    
    version_data = {
        "version": version,
        "release_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "python_package": python_package,
        "platforms": platforms
    }
    
    version_file = dist_dir / "version.json"
    version_file.write_text(json.dumps(version_data, indent=2) + "\n")
    print(f"  Created: {version_file}")


def print_summary(dist_dir: Path, version: str) -> None:
    """Print build summary."""
    print("\n" + "=" * 60)
    print("Build Complete!")
    print("=" * 60)
    print(f"\nVersion: {version}")
    print(f"Output:  {dist_dir}")
    print("\nRelease structure:")
    
    # Print directory tree
    for item in sorted(dist_dir.rglob("*")):
        if item.is_file():
            rel_path = item.relative_to(dist_dir)
            size = item.stat().st_size
            if size > 1024 * 1024:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{size / 1024:.1f} KB"
            print(f"  {rel_path} ({size_str})")
    
    print("\nDeployment:")
    print("  1. Copy the entire dist/ directory to your web server")
    print("  2. Ensure version.json is at the root")
    print("  3. Installers reference files relative to the server root")


def main():
    parser = argparse.ArgumentParser(
        description="Build localbrain release package",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/build_release.py --version 0.5.0
    python scripts/build_release.py --version 0.5.0 --wheel-only
    python scripts/build_release.py --version 0.5.0 --binary-only --platform macos-arm64
        """,
    )
    parser.add_argument(
        "--version",
        required=True,
        help="Version number (e.g., 0.5.0)",
    )
    parser.add_argument(
        "--wheel-only",
        action="store_true",
        help="Build only Python wheel package",
    )
    parser.add_argument(
        "--binary-only",
        action="store_true",
        help="Build only binary package",
    )
    parser.add_argument(
        "--platform",
        help="Target platform for binary (e.g., macos-arm64)",
    )
    parser.add_argument(
        "--no-venv",
        action="store_true",
        help="Do not use virtual environment (use current Python)",
    )
    
    args = parser.parse_args()
    
    project_root = get_project_root()
    dist_dir = project_root / "dist"
    
    print("=" * 60)
    print(f"Building LocalBrain v{args.version} Release")
    print("=" * 60)
    
    # Setup virtual environment if building binary or not explicitly disabled
    python_exe = None
    if not args.no_venv:
        # Setup venv for binary builds (installs pyinstaller)
        # For wheel-only, we can use the venv if it exists but don't require it
        for_binary = not args.wheel_only
        _, python_exe = setup_build_venv(project_root, for_binary=for_binary)
    else:
        python_exe = Path(sys.executable)
        print(f"\nUsing system Python: {python_exe}")
    
    # Clean dist directory
    clean_dist(dist_dir)
    
    # Build packages
    if not args.binary_only:
        build_wheel(project_root, dist_dir, args.version, python_exe)
    
    if not args.wheel_only:
        platform_key = args.platform or get_platform_key()
        build_binary(project_root, dist_dir, args.version, platform_key, python_exe)
    
    # Copy install scripts
    copy_install_scripts(project_root, dist_dir, args.wheel_only, args.binary_only)
    
    # Generate version.json
    generate_version_json(dist_dir, args.version)
    
    # Print summary
    print_summary(dist_dir, args.version)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
