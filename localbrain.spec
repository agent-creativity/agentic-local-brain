# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for localbrain.

Build standalone executable with all dependencies bundled.
"""

import os
import sys
from pathlib import Path

# Get the project root
block_cipher = None
# SPECPATH is injected by PyInstaller at build time
project_root = Path(SPECPATH)

# Read version from VERSION file
version_file = project_root / "VERSION"
version = version_file.read_text().strip() if version_file.exists() else "0.0.0"

# Determine platform suffix
import platform
system = platform.system().lower()
machine = platform.machine().lower()
# Handle different platform.machine() values across OS
if machine in ("x86_64", "amd64", "AMD64"):
    arch = "x64"
elif machine in ("arm64", "aarch64", "ARM64"):
    arch = "arm64"
else:
    arch = machine

# Data files to include
datas = [
    (str(project_root / "kb"), "kb"),  # Includes kb/config-template.yaml
    (str(project_root / "VERSION"), "."),
]

# Hidden imports for dynamic loading
hiddenimports = [
    # Core CLI dependencies
    "click",
    "click.core",
    "click.formatting",
    "yaml",
    "tqdm",
    "pypinyin",
    
    # PDF processing
    "PyPDF2",
    "PyPDF2.PdfReader",
    
    # Web scraping
    "httpx",
    "httpx._transports.default",
    "httpx._content",
    "readability",
    "readability.lxml",
    "markdownify",
    "bs4",
    "beautifulsoup4",
    
    # LLM providers
    "dashscope",
    "openai",
    
    # Vector store
    "chromadb",
    "chromadb.config",
    "chromadb.api",
    "chromadb.db",
    
    # Embeddings (optional)
    "sentence_transformers",
    
    # Machine Learning
    "numpy",
    "numpy.core",
    "sklearn",
    "sklearn.cluster",
    "sklearn.cluster._hdbscan",
    
    # Async/networking
    "h11",
    "anyio",
    "anyio._backends._asyncio",
    "sniffio",
    
    # Web API
    "fastapi",
    "uvicorn",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "starlette",
    "starlette.responses",
    "starlette.routing",
    "starlette.middleware",
    "starlette.requests",
    "multipart",
    "python_multipart",
    
    # Standard library modules used dynamically
    "sqlite3",
    "json",
    "hashlib",
    "pathlib",
    "typing",
    "dataclasses",
    "datetime",
    "re",
    "collections",
    "functools",
    "itertools",
    "abc",
]

# Collect all dependencies
from PyInstaller.utils.hooks import collect_all, collect_submodules

binaries = []
for package in ["chromadb", "sentence_transformers", "sklearn"]:
    try:
        pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(package)
        datas.extend(pkg_datas)
        binaries.extend(pkg_binaries)
        hiddenimports.extend(pkg_hiddenimports)
    except Exception:
        pass

a = Analysis(
    ["kb/cli.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=f"localbrain-{system}-{arch}" + (".exe" if system == "windows" else ""),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Disable UPX compression for macOS compatibility
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
