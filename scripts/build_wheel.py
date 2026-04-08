#!/usr/bin/env python3
"""
Build wheel for localbrain.

Usage:
    python scripts/build_wheel.py --version 0.1.0
    
The script:
1. Updates VERSION file
2. Builds wheel using pip wheel
3. Renames to canonical format: localbrain-{version}-py3-none-any.whl
4. Generates SHA256 checksum file
"""

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def build_wheel(version: str) -> Path:
    """Build wheel and return path to wheel file."""
    project_root = get_project_root()
    dist_dir = project_root / "dist"
    
    # Ensure dist directory exists
    dist_dir.mkdir(exist_ok=True)
    
    # Clean existing wheels
    for f in dist_dir.glob("*.whl"):
        f.unlink()
        print(f"Removed old wheel: {f}")
    
    # Update VERSION file
    version_file = project_root / "VERSION"
    version_file.write_text(version)
    print(f"Updated VERSION file to {version}")
    
    # Build wheel
    print(f"Building wheel for localbrain v{version}...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "-w", "dist"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        raise RuntimeError(f"Wheel build failed with exit code {result.returncode}")
    
    # Find built wheel
    wheels = list(dist_dir.glob("*.whl"))
    if not wheels:
        raise FileNotFoundError("No wheel found in dist/")
    
    wheel_path = wheels[0]
    print(f"Built wheel: {wheel_path.name}")
    
    # Rename to canonical name (handle version normalization)
    canonical_name = f"localbrain-{version}-py3-none-any.whl"
    canonical_path = dist_dir / canonical_name
    
    if wheel_path.name != canonical_name:
        wheel_path = wheel_path.rename(canonical_path)
        print(f"Renamed to: {canonical_name}")
    
    return wheel_path


def generate_checksum(wheel_path: Path) -> Path:
    """Generate SHA256 checksum file for wheel."""
    checksum = calculate_sha256(wheel_path)
    checksum_file = wheel_path.with_suffix(".whl.sha256")
    checksum_file.write_text(f"sha256:{checksum}  {wheel_path.name}\n")
    return checksum_file


def main():
    parser = argparse.ArgumentParser(
        description="Build localbrain wheel for distribution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/build_wheel.py --version 0.1.0
    python scripts/build_wheel.py --version 0.2.0 --output ./release/
        """,
    )
    parser.add_argument(
        "--version",
        required=True,
        help="Version number (e.g., 0.1.0)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output directory (default: dist/)",
    )
    
    args = parser.parse_args()
    
    # Build wheel
    print(f"\n{'='*50}")
    print(f"Building localbrain v{args.version} wheel")
    print(f"{'='*50}\n")
    
    wheel_path = build_wheel(args.version)
    
    # Generate checksum
    checksum_file = generate_checksum(wheel_path)
    print(f"Generated checksum: {checksum_file.name}")
    
    # Copy to output directory if specified
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy(wheel_path, args.output / wheel_path.name)
        shutil.copy(checksum_file, args.output / checksum_file.name)
        print(f"Copied to: {args.output}")
    
    # Print summary
    wheel_size = wheel_path.stat().st_size / 1024
    print(f"\n{'='*50}")
    print("Build complete!")
    print(f"{'='*50}")
    print(f"Wheel:    {wheel_path}")
    print(f"Checksum: {checksum_file}")
    print(f"Size:     {wheel_size:.1f} KB")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
