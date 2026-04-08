#!/usr/bin/env python3
"""
文件体积检查脚本

检查源代码文件的行数，识别超标文件，生成报告。

用法:
    python3 check_file_size.py <src_path> [options]

示例:
    python3 check_file_size.py ./src --warn 500 --error 1000
    python3 check_file_size.py ./src --extensions ts,tsx,js,jsx --json
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import NamedTuple
from collections import defaultdict


class FileInfo(NamedTuple):
    """文件信息"""
    path: str
    lines: int
    status: str  # 'ok', 'warn', 'error'


class CheckResult(NamedTuple):
    """检查结果"""
    total_files: int
    ok_files: list[FileInfo]
    warn_files: list[FileInfo]
    error_files: list[FileInfo]
    score: int  # 0-4 评分


# 默认配置
DEFAULT_EXTENSIONS = ['ts', 'tsx', 'js', 'jsx', 'py', 'go', 'rs', 'java', 'kt', 'swift']
DEFAULT_WARN_THRESHOLD = 500
DEFAULT_ERROR_THRESHOLD = 1000
DEFAULT_IGNORE_PATTERNS = [
    'node_modules', 'dist', 'build', '.git', '__pycache__',
    'vendor', 'target', '.next', 'coverage', '.cache'
]


def count_lines(file_path: str) -> int:
    """统计文件行数"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def should_ignore(path: str, ignore_patterns: list[str]) -> bool:
    """检查路径是否应该忽略"""
    path_parts = Path(path).parts
    return any(pattern in path_parts for pattern in ignore_patterns)


def scan_files(
    src_path: str,
    extensions: list[str],
    warn_threshold: int,
    error_threshold: int,
    ignore_patterns: list[str]
) -> CheckResult:
    """扫描文件并分类"""
    ok_files = []
    warn_files = []
    error_files = []
    
    src_path = os.path.abspath(src_path)
    
    for root, dirs, files in os.walk(src_path):
        # 过滤忽略的目录
        dirs[:] = [d for d in dirs if d not in ignore_patterns]
        
        for file in files:
            # 检查扩展名
            ext = file.rsplit('.', 1)[-1] if '.' in file else ''
            if ext not in extensions:
                continue
            
            file_path = os.path.join(root, file)
            
            # 检查是否应该忽略
            if should_ignore(file_path, ignore_patterns):
                continue
            
            lines = count_lines(file_path)
            rel_path = os.path.relpath(file_path, src_path)
            
            if lines > error_threshold:
                error_files.append(FileInfo(rel_path, lines, 'error'))
            elif lines > warn_threshold:
                warn_files.append(FileInfo(rel_path, lines, 'warn'))
            else:
                ok_files.append(FileInfo(rel_path, lines, 'ok'))
    
    # 排序：按行数降序
    ok_files.sort(key=lambda x: x.lines, reverse=True)
    warn_files.sort(key=lambda x: x.lines, reverse=True)
    error_files.sort(key=lambda x: x.lines, reverse=True)
    
    total = len(ok_files) + len(warn_files) + len(error_files)
    
    # 计算评分 (0-4)
    if total == 0:
        score = 4
    else:
        ok_ratio = len(ok_files) / total
        has_error = len(error_files) > 0
        has_many_errors = len(error_files) > 5
        has_giant = any(f.lines > error_threshold * 2 for f in error_files)
        
        if ok_ratio >= 0.9 and not has_error:
            score = 4
        elif ok_ratio >= 0.8 and len(error_files) <= 2:
            score = 3
        elif len(error_files) <= 5:
            score = 2
        elif not has_giant:
            score = 1
        else:
            score = 0
    
    return CheckResult(total, ok_files, warn_files, error_files, score)


def print_report(result: CheckResult, warn_threshold: int, error_threshold: int, verbose: bool = False):
    """打印报告"""
    total = result.total_files
    ok_count = len(result.ok_files)
    warn_count = len(result.warn_files)
    error_count = len(result.error_files)
    
    print("\n📊 文件体积检查报告")
    print("=" * 50)
    print(f"总文件数: {total}")
    
    if total > 0:
        print(f"正常 (≤{warn_threshold}行): {ok_count} ({ok_count/total*100:.1f}%)")
        print(f"警告 ({warn_threshold}-{error_threshold}行): {warn_count} ({warn_count/total*100:.1f}%)")
        print(f"严重 (>{error_threshold}行): {error_count} ({error_count/total*100:.1f}%)")
    
    print(f"\n评分: {result.score}/4")
    
    # 打印严重超标文件
    if result.error_files:
        print(f"\n❌ 严重超标文件 (>{error_threshold}行):")
        for f in result.error_files[:20]:  # 最多显示 20 个
            print(f"  - {f.path}: {f.lines} 行")
        if len(result.error_files) > 20:
            print(f"  ... 还有 {len(result.error_files) - 20} 个文件")
    
    # 打印警告文件
    if result.warn_files:
        print(f"\n⚠️  警告文件 ({warn_threshold}-{error_threshold}行):")
        display_count = 10 if not verbose else len(result.warn_files)
        for f in result.warn_files[:display_count]:
            print(f"  - {f.path}: {f.lines} 行")
        if len(result.warn_files) > display_count:
            print(f"  ... 还有 {len(result.warn_files) - display_count} 个文件")
    
    # 打印最大的正常文件（用于参考）
    if verbose and result.ok_files:
        print(f"\n✅ 最大的正常文件 (top 10):")
        for f in result.ok_files[:10]:
            print(f"  - {f.path}: {f.lines} 行")
    
    print("\n" + "=" * 50)


def output_json(result: CheckResult, warn_threshold: int, error_threshold: int):
    """输出 JSON 格式"""
    data = {
        "summary": {
            "total_files": result.total_files,
            "ok_count": len(result.ok_files),
            "warn_count": len(result.warn_files),
            "error_count": len(result.error_files),
            "score": result.score,
            "thresholds": {
                "warn": warn_threshold,
                "error": error_threshold
            }
        },
        "error_files": [{"path": f.path, "lines": f.lines} for f in result.error_files],
        "warn_files": [{"path": f.path, "lines": f.lines} for f in result.warn_files]
    }
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(
        description='检查源代码文件体积，识别超标文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s ./src                           # 使用默认阈值检查
  %(prog)s ./src --warn 500 --error 1000   # 自定义阈值
  %(prog)s ./src --extensions ts,tsx       # 只检查特定扩展名
  %(prog)s ./src --json                    # 输出 JSON 格式
  %(prog)s ./src -v                        # 详细输出
        """
    )
    
    parser.add_argument('src_path', help='源代码目录路径')
    parser.add_argument('--warn', type=int, default=DEFAULT_WARN_THRESHOLD,
                        help=f'警告阈值（行数），默认 {DEFAULT_WARN_THRESHOLD}')
    parser.add_argument('--error', type=int, default=DEFAULT_ERROR_THRESHOLD,
                        help=f'错误阈值（行数），默认 {DEFAULT_ERROR_THRESHOLD}')
    parser.add_argument('--extensions', type=str, default=','.join(DEFAULT_EXTENSIONS),
                        help=f'检查的文件扩展名，逗号分隔，默认 {",".join(DEFAULT_EXTENSIONS[:5])}...')
    parser.add_argument('--ignore', type=str, default=','.join(DEFAULT_IGNORE_PATTERNS[:5]),
                        help='忽略的目录模式，逗号分隔')
    parser.add_argument('--json', action='store_true', help='输出 JSON 格式')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    # 验证路径
    if not os.path.isdir(args.src_path):
        print(f"错误: 路径不存在或不是目录: {args.src_path}", file=sys.stderr)
        sys.exit(1)
    
    # 解析扩展名和忽略模式
    extensions = [ext.strip().lstrip('.') for ext in args.extensions.split(',')]
    ignore_patterns = [p.strip() for p in args.ignore.split(',')]
    ignore_patterns.extend(DEFAULT_IGNORE_PATTERNS)
    ignore_patterns = list(set(ignore_patterns))  # 去重
    
    # 执行扫描
    result = scan_files(
        args.src_path,
        extensions,
        args.warn,
        args.error,
        ignore_patterns
    )
    
    # 输出结果
    if args.json:
        output_json(result, args.warn, args.error)
    else:
        print_report(result, args.warn, args.error, args.verbose)
    
    # 返回码：有严重问题返回 1
    sys.exit(1 if result.error_files else 0)


if __name__ == '__main__':
    main()

