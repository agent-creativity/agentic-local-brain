# Release v0.6.4

## 🐛 Bug Fixes

- **Fixed Python detection in install scripts** - Replaced bash-specific `&>` syntax with POSIX-compatible `> /dev/null 2>&1` to ensure scripts work correctly when executed with `sh` instead of `bash`
- **Domain migration** - Updated all installation URLs from internal domain to public OSS endpoint (http://localbrain.oss-cn-shanghai.aliyuncs.com)

## 📦 Installation

### Python Package (Recommended)

**macOS / Linux:**
```bash
curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.sh | sh
```

**Windows (PowerShell):**
```powershell
irm http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.ps1 | iex
```

### Binary Install (No Python Required)

**macOS / Linux:**
```bash
curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/binary_installer/install.sh | sh
```

**Windows (PowerShell):**
```powershell
irm http://localbrain.oss-cn-shanghai.aliyuncs.com/binary_installer/install.ps1 | iex
```

## 📝 Full Changelog

https://github.com/agent-creativity/agentic-local-brain/compare/v0.6.0...v0.6.4
