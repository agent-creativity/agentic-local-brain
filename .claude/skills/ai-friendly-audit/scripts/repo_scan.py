#!/usr/bin/env python3
"""
AI Friendly Audit - Repository Scanner

自动扫描代码仓库，收集 AI 亲和度评估所需的基础信息。
支持前端（Node.js/TypeScript）、后端（Go/Java/Python/Rust）和全栈项目。

用法:
    python3 repo_scan.py <repo_path>
    python3 repo_scan.py <repo_path> --json
    python3 repo_scan.py <repo_path> --json --output scan_result.json
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def run_command(cmd: str, cwd: str = None) -> tuple[int, str]:
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd,
            capture_output=True, text=True, timeout=30
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return -1, "Command timed out"
    except Exception as e:
        return -1, str(e)


IGNORE_DIRS = {'node_modules', 'vendor', 'target', 'dist', 'build', '.git', '__pycache__', '.cache', '.next'}


def check_file_exists(repo_path: str, patterns: list[str]) -> list[str]:
    """Check for file existence using glob patterns, skipping ignored directories.

    For recursive patterns (**), uses os.walk with pruning for much better
    performance on repos with large vendor/node_modules directories.
    """
    found = []
    repo = Path(repo_path)

    for pattern in patterns:
        if '**' in pattern:
            parts = pattern.split('**/')
            tail = parts[-1] if len(parts) > 1 else pattern.lstrip('**/')
            for root, dirs, files in os.walk(repo_path):
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                current = Path(root)
                for match in current.glob(tail):
                    rel = str(match.relative_to(repo))
                    if rel not in found:
                        found.append(rel)
        else:
            for m in repo.glob(pattern):
                if IGNORE_DIRS.isdisjoint(set(m.relative_to(repo).parts)):
                    rel = str(m.relative_to(repo))
                    if rel not in found:
                        found.append(rel)
    return found


def find_src_dirs(repo_path: str) -> list[str]:
    """查找源代码目录"""
    repo = Path(repo_path)
    candidates = [
        "src", "pkg", "internal", "cmd", "app", "lib",
        "src/main/java", "src/main/kotlin", "src/main/scala",
    ]
    found = []
    for c in candidates:
        p = repo / c
        if p.exists() and p.is_dir():
            found.append(str(p.relative_to(repo)))
    if not found:
        for subdir in repo.iterdir():
            if subdir.is_dir() and not subdir.name.startswith('.'):
                for c in candidates:
                    p = subdir / c
                    if p.exists() and p.is_dir():
                        found.append(str(p.relative_to(repo)))
    return found


# ---------------------------------------------------------------------------
# Project type detection
# ---------------------------------------------------------------------------

PKG_FILES = {
    "package.json": ("npm/yarn/pnpm", "javascript/typescript"),
    "requirements.txt": ("pip", "python"),
    "pyproject.toml": ("poetry/pip", "python"),
    "setup.py": ("pip", "python"),
    "Cargo.toml": ("cargo", "rust"),
    "go.mod": ("go mod", "go"),
    "pom.xml": ("maven", "java"),
    "build.gradle": ("gradle", "java"),
    "build.gradle.kts": ("gradle-kts", "kotlin"),
    "Gemfile": ("bundler", "ruby"),
    "composer.json": ("composer", "php"),
    "mix.exs": ("mix", "elixir"),
    "Package.swift": ("spm", "swift"),
}

FRAMEWORK_DETECTORS = {
    "javascript/typescript": {
        "react": "React", "vue": "Vue", "angular": "Angular",
        "next": "Next.js", "nuxt": "Nuxt.js", "svelte": "Svelte",
        "express": "Express", "fastify": "Fastify", "@nestjs": "NestJS",
        "koa": "Koa", "hapi": "Hapi",
    },
    "java": {
        "spring-boot": "Spring Boot", "spring-cloud": "Spring Cloud",
        "quarkus": "Quarkus", "micronaut": "Micronaut",
        "mybatis": "MyBatis", "hibernate": "Hibernate",
    },
    "python": {
        "django": "Django", "flask": "Flask", "fastapi": "FastAPI",
        "tornado": "Tornado", "aiohttp": "aiohttp",
    },
    "go": {
        "gin-gonic/gin": "Gin", "gorilla/mux": "Gorilla Mux",
        "labstack/echo": "Echo", "gofiber/fiber": "Fiber",
        "grpc": "gRPC",
    },
    "rust": {
        "actix-web": "Actix Web", "axum": "Axum", "rocket": "Rocket",
        "warp": "Warp",
    },
}

FRONTEND_FRAMEWORKS = {"React", "Vue", "Angular", "Next.js", "Nuxt.js", "Svelte"}
BACKEND_FRAMEWORKS = {
    "Express", "Fastify", "NestJS", "Koa", "Hapi",
    "Spring Boot", "Spring Cloud", "Quarkus", "Micronaut",
    "Django", "Flask", "FastAPI",
    "Gin", "Gorilla Mux", "Echo", "Fiber", "gRPC",
    "Actix Web", "Axum", "Rocket", "Warp",
}


def _detect_js_frameworks(pkg_path: Path) -> list[str]:
    frameworks = []
    try:
        with open(pkg_path) as f:
            pkg = json.load(f)
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        for key, name in FRAMEWORK_DETECTORS.get("javascript/typescript", {}).items():
            if any(key in d.lower() for d in deps):
                frameworks.append(name)
    except Exception:
        pass
    return frameworks


def _detect_go_frameworks(repo_path: str) -> list[str]:
    frameworks = []
    go_mod = Path(repo_path) / "go.mod"
    if not go_mod.exists():
        for sub in Path(repo_path).iterdir():
            if sub.is_dir() and (sub / "go.mod").exists():
                go_mod = sub / "go.mod"
                break
    if go_mod.exists():
        try:
            content = go_mod.read_text()
            for key, name in FRAMEWORK_DETECTORS.get("go", {}).items():
                if key in content:
                    frameworks.append(name)
        except Exception:
            pass
    return frameworks


def _detect_java_frameworks(repo_path: str) -> list[str]:
    frameworks = []
    for pom in Path(repo_path).rglob("pom.xml"):
        try:
            content = pom.read_text()
            for key, name in FRAMEWORK_DETECTORS.get("java", {}).items():
                if key in content:
                    if name not in frameworks:
                        frameworks.append(name)
        except Exception:
            pass
        break
    for gradle in list(Path(repo_path).glob("build.gradle*"))[:1]:
        try:
            content = gradle.read_text()
            for key, name in FRAMEWORK_DETECTORS.get("java", {}).items():
                if key in content:
                    if name not in frameworks:
                        frameworks.append(name)
        except Exception:
            pass
    return frameworks


def _detect_python_frameworks(repo_path: str) -> list[str]:
    frameworks = []
    for req_file in ["requirements.txt", "pyproject.toml", "setup.py"]:
        p = Path(repo_path) / req_file
        if p.exists():
            try:
                content = p.read_text()
                for key, name in FRAMEWORK_DETECTORS.get("python", {}).items():
                    if key in content.lower():
                        if name not in frameworks:
                            frameworks.append(name)
            except Exception:
                pass
    return frameworks


def detect_project_type(repo_path: str) -> dict:
    result = {
        "type": "unknown",
        "languages": [],
        "frameworks": [],
        "package_managers": [],
        "src_dirs": find_src_dirs(repo_path),
    }

    repo = Path(repo_path)

    search_dirs = [repo] + [
        d for d in repo.iterdir()
        if d.is_dir() and not d.name.startswith('.')
        and d.name not in ('node_modules', 'vendor', 'target', 'dist', 'build', '.git')
    ]

    for search_dir in search_dirs:
        for file, (pkg_mgr, lang) in PKG_FILES.items():
            if (search_dir / file).exists():
                if pkg_mgr not in result["package_managers"]:
                    result["package_managers"].append(pkg_mgr)
                if lang not in result["languages"]:
                    result["languages"].append(lang)

    if "javascript/typescript" in result["languages"]:
        for sd in search_dirs:
            pkg_json = sd / "package.json"
            if pkg_json.exists():
                result["frameworks"].extend(
                    f for f in _detect_js_frameworks(pkg_json) if f not in result["frameworks"]
                )
    if "go" in result["languages"]:
        result["frameworks"].extend(
            f for f in _detect_go_frameworks(repo_path) if f not in result["frameworks"]
        )
    if "java" in result["languages"] or "kotlin" in result["languages"]:
        result["frameworks"].extend(
            f for f in _detect_java_frameworks(repo_path) if f not in result["frameworks"]
        )
    if "python" in result["languages"]:
        result["frameworks"].extend(
            f for f in _detect_python_frameworks(repo_path) if f not in result["frameworks"]
        )

    has_fe = bool(set(result["frameworks"]) & FRONTEND_FRAMEWORKS)
    has_be = bool(set(result["frameworks"]) & BACKEND_FRAMEWORKS)
    be_langs = {"go", "java", "kotlin", "rust", "python"}
    has_be_lang = bool(set(result["languages"]) & be_langs)

    if has_fe and (has_be or has_be_lang):
        result["type"] = "fullstack"
    elif has_fe:
        result["type"] = "frontend"
    elif has_be or has_be_lang:
        result["type"] = "backend"
    elif result["languages"]:
        result["type"] = "library"

    return result


# ---------------------------------------------------------------------------
# Dimension checks
# ---------------------------------------------------------------------------

def check_dimensions(repo_path: str, project: dict) -> dict:
    dims = {}
    repo = Path(repo_path)

    # --- 1. 最小可运行环境 ---
    env_data = {
        "env_template": check_file_exists(repo_path, [
            "**/.env.example", "**/.env.local.example", "**/.env.sample",
            "**/application-local.properties", "**/application-local.yml",
            "**/config/local.yaml", "**/config/local.toml",
        ]),
        "lock_file": check_file_exists(repo_path, [
            "**/package-lock.json", "**/yarn.lock", "**/pnpm-lock.yaml",
            "**/go.sum", "**/Cargo.lock", "**/poetry.lock", "**/Pipfile.lock",
            "**/Gemfile.lock", "**/composer.lock",
        ]),
        "vendor_dir": check_file_exists(repo_path, ["**/vendor/"]),
        "mock_config": check_file_exists(repo_path, [
            "**/msw*", "**/mocks/**", "**/__mocks__/**",
            "**/mock*.ts", "**/mock*.js", "**/mock*.go",
            "**/testdata/**", "**/fixtures/**",
            "**/mockData/**", "**/mock_data/**",
        ]),
        "docker": check_file_exists(repo_path, [
            "**/Dockerfile", "**/docker-compose*.yml", "**/docker-compose*.yaml",
        ]),
        "makefile": check_file_exists(repo_path, ["**/Makefile", "**/makefile"]),
        "dev_script": False,
        "build_wrapper": check_file_exists(repo_path, ["**/mvnw", "**/gradlew"]),
    }

    pkg_json = repo / "package.json"
    if not pkg_json.exists():
        for sub in repo.iterdir():
            if sub.is_dir() and (sub / "package.json").exists():
                pkg_json = sub / "package.json"
                break
    if pkg_json.exists():
        try:
            with open(pkg_json) as f:
                scripts = json.load(f).get("scripts", {})
            env_data["dev_script"] = any(
                k in scripts for k in ["dev", "start", "serve"]
            )
        except Exception:
            pass
    if env_data["makefile"]:
        for mf_rel in env_data["makefile"]:
            mf = repo / mf_rel
            if mf.exists():
                try:
                    content = mf.read_text()
                    if any(t in content for t in ["run:", "dev:", "start:", "serve:", "build:"]):
                        env_data["dev_script"] = True
                except Exception:
                    pass

    dims["minimal_env"] = env_data

    # --- 2. 类型系统与静态分析 ---
    type_data = {
        "typescript_config": check_file_exists(repo_path, ["**/tsconfig.json", "**/tsconfig.*.json"]),
        "strict_mode": False,
        "go_vet": "go" in project.get("languages", []),
        "static_analysis_config": check_file_exists(repo_path, [
            "**/.golangci.yml", "**/.golangci.yaml",
            "**/mypy.ini", "**/.mypy.ini", "**/pyrightconfig.json",
            "**/checkstyle.xml", "**/checkstyle*.xml",
            "**/clippy.toml", "**/.clippy.toml",
            "**/errorprone*",
        ]),
        "type_annotations": False,
    }
    for tsconfig_path in repo.rglob("tsconfig.json"):
        if "node_modules" in tsconfig_path.parts:
            continue
        try:
            content = tsconfig_path.read_text()
            if '"strict": true' in content or '"strict":true' in content:
                type_data["strict_mode"] = True
                break
        except Exception:
            pass
    if any(lang in project.get("languages", []) for lang in ["go", "java", "kotlin", "rust"]):
        type_data["type_annotations"] = True

    dims["type_system"] = type_data

    # --- 3. 测试体系 ---
    test_data = {
        "test_config": check_file_exists(repo_path, [
            "**/jest.config.*", "**/vitest.config.*",
            "**/pytest.ini", "**/setup.cfg",
            "**/testng.xml",
        ]),
        "test_files": check_file_exists(repo_path, [
            "**/*_test.go", "**/*_test.py", "**/test_*.py",
            "**/*.test.ts", "**/*.test.tsx", "**/*.test.js",
            "**/*.spec.ts", "**/*.spec.tsx", "**/*.spec.js",
            "**/Test*.java", "**/*Test.java", "**/*Tests.java",
            "**/tests/**/*.rs",
        ]),
        "e2e_config": check_file_exists(repo_path, [
            "**/cypress.config.*", "**/playwright.config.*",
            "**/e2e/", "**/tests/e2e/",
        ]),
        "coverage_config": check_file_exists(repo_path, [
            "**/.nycrc*",
            "**/.coveragerc", "**/coverage.xml",
            "**/jacoco*",
        ]),
        "mock_fixtures": check_file_exists(repo_path, [
            "**/testdata/**", "**/fixtures/**", "**/mocks/**",
            "**/__mocks__/**", "**/mockData/**", "**/mock_data/**",
            "**/testcontainers*",
        ]),
    }
    test_data["test_file_count"] = len(test_data["test_files"])
    dims["test_system"] = test_data

    # --- 4. 文档完备性 ---
    dims["documentation"] = {
        "readme": check_file_exists(repo_path, ["README.md", "readme.md", "README.rst"]),
        "architecture": check_file_exists(repo_path, [
            "docs/*rchitecture*", "docs/*DESIGN*", "ARCHITECTURE.md",
            "docs/backend*", "docs/frontend*",
            "**/design/*.md", "**/design/*.adoc",
        ]),
        "api_docs": check_file_exists(repo_path, [
            "docs/api*", "**/openapi*", "**/swagger*",
            "openapi.yaml", "openapi.json",
            "**/openapi/*.md",
        ]),
        "dev_guide": check_file_exists(repo_path, [
            "CONTRIBUTING.md", "DEVELOPMENT.md",
            "docs/*rule*", "docs/*convention*", "docs/*guide*",
            "*_dev_rule*", "CONVENTIONS.md",
        ]),
        "ai_guide": check_file_exists(repo_path, [
            "AGENTS.md", ".cursor/rules/*", ".cursorrules",
            ".github/copilot-instructions.md",
            "**/Memory Bank/**", ".lingma/**",
            ".aider*", ".continue/", "cline_docs/", ".clinerules",
            ".windsurfrules",
        ]),
    }

    # --- 5. 代码规范与自动化 ---
    dims["code_standards"] = {
        "linting": check_file_exists(repo_path, [
            "**/.eslintrc*", "**/eslint.config.*", "**/biome.json",
            "**/.pylintrc", "**/ruff.toml", "**/.ruff.toml",
            "**/.golangci.yml", "**/.golangci.yaml",
            "**/checkstyle.xml",
            "**/clippy.toml",
        ]),
        "formatting": check_file_exists(repo_path, [
            "**/.prettierrc*", "**/prettier.config.*",
            "**/.editorconfig",
            "**/rustfmt.toml", "**/.rustfmt.toml",
        ]),
        "git_hooks": check_file_exists(repo_path, [
            ".husky/*", ".pre-commit-config.yaml",
            ".git/hooks/pre-commit",
        ]),
        "commit_lint": check_file_exists(repo_path, [
            "**/.commitlintrc*", "**/commitlint.config.*",
        ]),
    }

    # --- 6. 模块化架构 (basic structural check) ---
    dims["modularity"] = {
        "src_dirs": project.get("src_dirs", []),
        "has_layers": False,
        "directory_depth": 0,
    }
    layer_patterns_fe = ["components", "services", "utils", "hooks", "stores", "api", "pages", "views"]
    layer_patterns_be_go = ["cmd", "pkg", "internal", "api", "handler", "service", "repository", "model"]
    layer_patterns_be_java = ["controller", "service", "dao", "mapper", "entity", "config", "dto", "repository"]
    layer_patterns_be_py = ["api", "services", "models", "schemas", "routers", "core"]

    all_patterns = set(layer_patterns_fe + layer_patterns_be_go + layer_patterns_be_java + layer_patterns_be_py)
    found_layers = []
    for p in all_patterns:
        if check_file_exists(repo_path, [f"**/{p}"]):
            found_layers.append(p)
    dims["modularity"]["found_layers"] = found_layers
    dims["modularity"]["has_layers"] = len(found_layers) >= 3

    # --- 7. 上下文窗口友好性 (file size check) ---
    file_size_data = _check_file_sizes(repo_path)
    dims["context_window"] = file_size_data

    # --- 8. 代码自述性 (sample check) ---
    dims["code_readability"] = {
        "note": "Requires manual sampling of 3-5 core files"
    }

    # --- 9. AI 工具与 SDD 支持 ---
    dims["ai_sdd"] = {
        "ai_config": check_file_exists(repo_path, [
            ".cursorrules", ".cursor/rules/*",
            "AGENTS.md",
            ".github/copilot-instructions.md",
            ".aider*", ".continue/", "cline_docs/", ".clinerules",
            ".windsurfrules",
            "**/Memory Bank/**", ".lingma/**",
        ]),
        "api_spec": check_file_exists(repo_path, [
            "openapi.yaml", "openapi.json", "swagger.yaml", "swagger.json",
            "asyncapi.yaml", "asyncapi.json",
            "**/openapi/*.md",
        ]),
        "conventions": check_file_exists(repo_path, [
            "CONVENTIONS.md", "*_dev_rule*",
            "docs/*convention*", "docs/*rule*",
            ".speckit/", "speckit.config.*",
        ]),
    }

    # --- 10. 依赖隔离与可复现性 ---
    dims["dependency_isolation"] = {
        "lock_files": dims["minimal_env"]["lock_file"],
        "vendor": dims["minimal_env"]["vendor_dir"],
        "docker": dims["minimal_env"]["docker"],
        "version_manager": check_file_exists(repo_path, [
            "**/.nvmrc", "**/.node-version", "**/.python-version",
            "**/.tool-versions", "**/.sdkmanrc",
            "**/mvnw", "**/gradlew",
        ]),
        "mock_or_isolation": bool(dims["test_system"]["mock_fixtures"]),
    }

    # --- 11. Outer Loop & 反馈闭环 (v3.0) ---
    dims["outer_loop"] = {
        "structural_tests": check_file_exists(repo_path, [
            "**/architecture.test.*",
            "**/structural.test.*",
            "**/arch-test*",
            "**/ArchTest*",
            "**/archunit*",
            "**/import-boundaries*",
        ]),
        "quality_scripts": check_file_exists(repo_path, [
            "**/ai:check*",
            "**/quality_check*",
            "**/quality-check*",
            "**/.github/workflows/ci*",
            "**/Makefile",
            "**/tox.ini",
            "**/noxfile.py",
        ]),
        "coverage_thresholds": False,
        "regression_tracking": check_file_exists(repo_path, [
            "**/IHS.md",
            "**/ihs*",
            "**/.sonarcloud.properties",
            "**/sonar-project.properties",
        ]),
        "ihs_or_health_script": check_file_exists(repo_path, [
            "**/generate_ihs_report*",
            "**/health_check*",
            "**/repo_health*",
        ]),
    }

    for vconf in repo.rglob("vitest.config.*"):
        if "node_modules" in vconf.parts:
            continue
        try:
            content = vconf.read_text()
            if "thresholds" in content:
                dims["outer_loop"]["coverage_thresholds"] = True
                break
        except Exception:
            pass
    if not dims["outer_loop"]["coverage_thresholds"]:
        for jconf in repo.rglob("jest.config.*"):
            if "node_modules" in jconf.parts:
                continue
            try:
                content = jconf.read_text()
                if "coverageThreshold" in content:
                    dims["outer_loop"]["coverage_thresholds"] = True
                    break
            except Exception:
                pass

    return dims


def _check_file_sizes(repo_path: str) -> dict:
    """Inline file size check to avoid spawning a subprocess."""
    EXTENSIONS = {
        'ts', 'tsx', 'js', 'jsx',
        'go', 'py', 'rs',
        'java', 'kt', 'scala',
        'rb', 'php', 'swift',
    }
    IGNORE = {
        'node_modules', 'dist', 'build', '.git', '__pycache__',
        'vendor', 'target', '.next', 'coverage', '.cache',
        'generated', 'gen', 'pb.go',
    }
    WARN = 500
    ERROR = 1000

    ok = warn = error = 0
    error_files = []
    warn_files = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE]
        for fname in files:
            ext = fname.rsplit('.', 1)[-1] if '.' in fname else ''
            if ext not in EXTENSIONS:
                continue
            fpath = os.path.join(root, fname)
            if any(ig in fpath for ig in ['pb.go', '.gen.', '_generated', '/generated/']):
                continue
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = sum(1 for _ in f)
            except Exception:
                continue

            rel = os.path.relpath(fpath, repo_path)
            if lines > ERROR:
                error += 1
                error_files.append({"path": rel, "lines": lines})
            elif lines > WARN:
                warn += 1
                warn_files.append({"path": rel, "lines": lines})
            else:
                ok += 1

    total = ok + warn + error
    if total == 0:
        score = 4
    else:
        ok_ratio = ok / total
        has_giant = any(f["lines"] > ERROR * 2 for f in error_files)
        if ok_ratio >= 0.9 and error == 0:
            score = 4
        elif ok_ratio >= 0.8 and error <= 2:
            score = 3
        elif error <= 5:
            score = 2
        elif not has_giant:
            score = 1
        else:
            score = 0

    error_files.sort(key=lambda x: x["lines"], reverse=True)
    warn_files.sort(key=lambda x: x["lines"], reverse=True)

    return {
        "total_files": total,
        "ok_count": ok,
        "warn_count": warn,
        "error_count": error,
        "score": score,
        "error_files": error_files[:20],
        "warn_files": warn_files[:20],
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_report(project: dict, dimensions: dict, repo_path: str):
    print(f"\n🔍 Scanning repository: {repo_path}")
    print(f"📅 Scan date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    print(f"\n📦 Project Type: {project['type']}")
    print(f"🔧 Languages: {', '.join(project['languages']) or 'Unknown'}")
    print(f"🏗️  Frameworks: {', '.join(project['frameworks']) or 'None detected'}")
    print(f"📋 Package Managers: {', '.join(project['package_managers']) or 'None detected'}")
    print(f"📂 Source Dirs: {', '.join(project['src_dirs']) or 'None detected'}")

    dim_labels = {
        "minimal_env": "1. 最小可运行环境",
        "type_system": "2. 类型系统与静态分析",
        "test_system": "3. 测试体系",
        "documentation": "4. 文档完备性",
        "code_standards": "5. 代码规范与自动化",
        "modularity": "6. 模块化架构",
        "context_window": "7. 上下文窗口友好性",
        "code_readability": "8. 代码自述性",
        "ai_sdd": "9. AI 工具与 SDD 支持",
        "dependency_isolation": "10. 依赖隔离与可复现性",
        "outer_loop": "11. Outer Loop & 反馈闭环",
    }

    print("\n" + "=" * 60)
    print("📊 Dimension Check Results")
    print("=" * 60)

    for key, label in dim_labels.items():
        data = dimensions.get(key, {})
        print(f"\n{label}:")
        for subkey, value in data.items():
            if subkey in ("error_files", "warn_files"):
                if value:
                    tag = "❌" if subkey == "error_files" else "⚠️"
                    print(f"  {tag} {subkey}: ({len(value)} files)")
                    for item in value[:5]:
                        print(f"      - {item['path']}: {item['lines']} lines")
                    if len(value) > 5:
                        print(f"      ... and {len(value) - 5} more")
                continue
            if isinstance(value, list):
                status = "✅" if value else "❌"
                count = f"({len(value)} found)" if value else "(none)"
                print(f"  {status} {subkey}: {count}")
                if value and len(value) <= 5:
                    for item in value:
                        print(f"      - {item}")
            elif isinstance(value, bool):
                print(f"  {'✅' if value else '❌'} {subkey}")
            elif isinstance(value, int):
                print(f"  📊 {subkey}: {value}")
            else:
                print(f"  ℹ️  {subkey}: {value}")

    cw = dimensions.get("context_window", {})
    if cw.get("total_files"):
        print(f"\n📏 File Size Summary:")
        print(f"   Total: {cw['total_files']} | OK: {cw['ok_count']} | Warn: {cw['warn_count']} | Error: {cw['error_count']}")
        print(f"   Score: {cw['score']}/4")

    print("\n" + "=" * 60)
    print("📝 Note: This is an automated scan. Manual review is recommended")
    print("   for code quality dimensions (readability, error handling, etc.)")
    print("=" * 60)


def output_json(project: dict, dimensions: dict, repo_path: str, output_path: str = None):
    data = {
        "repo_path": repo_path,
        "scan_date": datetime.now().isoformat(),
        "project": project,
        "dimensions": dimensions,
    }
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    if output_path:
        with open(output_path, "w") as f:
            f.write(json_str)
        print(f"📄 JSON report saved to: {output_path}", file=sys.stderr)
    else:
        print(json_str)


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Scan a repository for AI-friendliness indicators.'
    )
    parser.add_argument('repo_path', help='Path to the repository')
    parser.add_argument('--json', action='store_true', help='Output JSON format')
    parser.add_argument('--output', '-o', type=str, help='Write JSON to file instead of stdout')

    args = parser.parse_args()
    repo_path = os.path.abspath(args.repo_path)

    if not os.path.isdir(repo_path):
        print(f"Error: {repo_path} is not a valid directory", file=sys.stderr)
        sys.exit(1)

    project = detect_project_type(repo_path)
    dimensions = check_dimensions(repo_path, project)

    if args.json or args.output:
        output_json(project, dimensions, repo_path, args.output)
    else:
        print_report(project, dimensions, repo_path)


if __name__ == "__main__":
    main()
