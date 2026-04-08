#!/usr/bin/env python3
"""
Cross-platform build script for localbrain.

Usage:
    python scripts/build.py --version 0.1.0
    python scripts/build.py --version 0.1.0 --platform macos-arm64
"""

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent


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


def build_binary(version: str, platform_key: str = None) -> Path:
    """Build binary using PyInstaller."""
    project_root = get_project_root()
    dist_dir = project_root / "dist"
    
    # Clean dist directory
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)
    
    # Update VERSION file
    version_file = project_root / "VERSION"
    version_file.write_text(version)
    
    # Run PyInstaller
    env = os.environ.copy()
    env["VERSION"] = version
    
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "localbrain.spec", "--clean", "--noconfirm"],
        cwd=project_root,
        env=env,
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"PyInstaller failed with exit code {result.returncode}")
    
    # Find the built binary
    if platform_key is None:
        platform_key = get_platform_key()
    
    binary_name = f"localbrain-{platform_key}"
    if platform.system() == "Windows":
        binary_name += ".exe"
    
    binary_path = dist_dir / binary_name
    
    if not binary_path.exists():
        # PyInstaller might use different naming
        binaries = list(dist_dir.glob("localbrain*"))
        if binaries:
            binary_path = binaries[0]
            # Rename to canonical name
            binary_path = binary_path.rename(dist_dir / binary_name)
        else:
            raise FileNotFoundError(f"Binary not found in {dist_dir}")
    
    return binary_path


def generate_checksum(binary_path: Path) -> Path:
    """Generate SHA256 checksum file."""
    checksum = calculate_sha256(binary_path)
    checksum_file = binary_path.with_suffix(".sha256")
    checksum_file.write_text(f"sha256:{checksum}  {binary_path.name}\n")
    return checksum_file


def main():
    parser = argparse.ArgumentParser(description="Build localbrain binary")
    parser.add_argument("--version", required=True, help="Version to build (e.g., 0.1.0)")
    parser.add_argument("--platform", help="Target platform (e.g., macos-arm64)")
    parser.add_argument("--no-checksum", action="store_true", help="Skip checksum generation")
    
    args = parser.parse_args()
    
    platform_key = args.platform or get_platform_key()
    
    print(f"Building localbrain v{args.version} for {platform_key}")
    
    # Build
    binary_path = build_binary(args.version, platform_key)
    print(f"Binary built: {binary_path}")
    
    # Generate checksum
    if not args.no_checksum:
        checksum_file = generate_checksum(binary_path)
        print(f"Checksum file: {checksum_file}")
    
    # Print summary
    binary_size = binary_path.stat().st_size / (1024 * 1024)
    print(f"\nBuild complete!")
    print(f"  Binary: {binary_path}")
    print(f"  Size: {binary_size:.1f} MB")
    print(f"  Platform: {platform_key}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
