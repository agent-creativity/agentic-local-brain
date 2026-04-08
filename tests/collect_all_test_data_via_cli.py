#!/usr/bin/env python
"""
使用 kb CLI 收集所有类型的测试数据

确保测试数据的完整性和CLI功能的正确性。
"""

import subprocess
import sys
from pathlib import Path


def run_cli_command(command: list, description: str) -> bool:
    """
    执行CLI命令并返回结果
    
    Args:
        command: 命令列表
        description: 命令描述
        
    Returns:
        bool: 是否成功
    """
    print(f"\n{'=' * 70}")
    print(f"[执行] {description}")
    print(f"命令: {' '.join(command)}")
    print('=' * 70)
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # 输出结果
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        success = result.returncode == 0
        if success:
            print(f"✓ {description} - 成功")
        else:
            print(f"✗ {description} - 失败 (exit code: {result.returncode})")
        
        return success
        
    except subprocess.TimeoutExpired:
        print(f"✗ {description} - 超时")
        return False
    except Exception as e:
        print(f"✗ {description} - 异常: {e}")
        return False


def collect_all_test_data():
    """收集所有类型的测试数据"""
    print("=" * 70)
    print("使用 kb CLI 收集所有测试类型数据")
    print("=" * 70)
    
    # 获取项目根目录
    project_root = Path(__file__).parent.parent
    test_data_dir = project_root / "tests" / "test_data"
    
    # 确保测试数据目录存在
    test_data_dir.mkdir(parents=True, exist_ok=True)
    
    # CLI可执行文件路径
    cli_path = str(project_root / ".venv" / "bin" / "python")
    cli_module = "-m"
    cli_name = "kb.cli"
    
    results = []
    
    # 1. 收集TXT文件
    print("\n" + "=" * 70)
    print("1. 收集本地文件 - TXT文档")
    print("=" * 70)
    txt_file = test_data_dir / "sample_python.txt"
    if txt_file.exists():
        success = run_cli_command(
            [cli_path, cli_module, cli_name, "file", "collect", str(txt_file),
             "-t", "Python", "-t", "编程", "-t", "最佳实践",
             "--title", "Python编程最佳实践示例"],
            "收集TXT文件"
        )
        results.append(("TXT文件", success))
    else:
        print(f"✗ 文件不存在: {txt_file}")
        results.append(("TXT文件", False))
    
    # 2. 收集Markdown文件
    print("\n" + "=" * 70)
    print("2. 收集本地文件 - Markdown文档")
    print("=" * 70)
    md_file = test_data_dir / "sample_markdown.md"
    if md_file.exists():
        success = run_cli_command(
            [cli_path, cli_module, cli_name, "file", "collect", str(md_file),
             "-t", "数据库", "-t", "设计", "-t", "最佳实践",
             "--title", "数据库设计最佳实践"],
            "收集Markdown文件"
        )
        results.append(("Markdown文件", success))
    else:
        print(f"✗ 文件不存在: {md_file}")
        results.append(("Markdown文件", False))
    
    # 3. 收集网页
    print("\n" + "=" * 70)
    print("3. 收集网页内容")
    print("=" * 70)
    success = run_cli_command(
        [cli_path, cli_module, cli_name, "webpage", "collect",
         "https://httpbin.org/html",
         "-t", "测试", "-t", "HTML",
         "--title", "HTTPBin测试页面"],
        "收集网页"
    )
    results.append(("网页", success))
    
    # 4. 收集邮件 (MBOX格式)
    print("\n" + "=" * 70)
    print("4. 收集邮件 - MBOX格式")
    print("=" * 70)
    mbox_file = test_data_dir / "sample_emails.mbox"
    if mbox_file.exists():
        success = run_cli_command(
            [cli_path, cli_module, cli_name, "email", "collect", str(mbox_file),
             "-t", "邮件", "-t", "项目", "-t", "沟通",
             "--max-emails", "10"],
            "收集MBOX邮件"
        )
        results.append(("邮件MBOX", success))
    else:
        print(f"✗ 文件不存在: {mbox_file}")
        results.append(("邮件MBOX", False))
    
    # 5. 收集笔记
    print("\n" + "=" * 70)
    print("5. 创建笔记")
    print("=" * 70)
    note_content = """系统设计面试核心要点：

1. 需求澄清
   - 功能性需求
   - 非功能性需求（性能、可用性）
   - 约束条件

2. 容量估算
   - QPS计算
   - 存储需求
   - 带宽估算

3. 高层设计
   - 核心组件
   - 数据流
   - API设计

4. 详细设计
   - 数据库设计
   - 缓存策略
   - 负载均衡

5. 扩展性
   - 水平扩展
   - 垂直扩展
   - 分片策略"""
    
    success = run_cli_command(
        [cli_path, cli_module, cli_name, "note", "add", note_content,
         "-t", "系统设计", "-t", "面试", "-t", "架构",
         "--title", "系统设计面试要点"],
        "创建笔记"
    )
    results.append(("笔记", success))
    
    # 6. 收集论文 (arXiv) - 使用HTTPS URL
    print("\n" + "=" * 70)
    print("6. 收集学术论文 - arXiv")
    print("=" * 70)
    success = run_cli_command(
        [cli_path, cli_module, cli_name, "paper", "collect",
         "https://arxiv.org/abs/1706.03762",
         "-t", "深度学习", "-t", "Transformer", "-t", "NLP"],
        "收集arXiv论文 (Attention Is All You Need)"
    )
    results.append(("论文arXiv", success))
    
    # 7. 查看统计信息
    print("\n" + "=" * 70)
    print("7. 查看知识库统计")
    print("=" * 70)
    success = run_cli_command(
        [cli_path, cli_module, cli_name, "stats"],
        "查看统计信息"
    )
    results.append(("统计信息", success))
    
    # 8. 查看标签列表
    print("\n" + "=" * 70)
    print("8. 查看标签列表")
    print("=" * 70)
    success = run_cli_command(
        [cli_path, cli_module, cli_name, "tag", "list"],
        "查看标签列表"
    )
    results.append(("标签列表", success))
    
    # 汇总结果
    print("\n" + "=" * 70)
    print("收集结果汇总")
    print("=" * 70)
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for name, success in results:
        status = "✓ 成功" if success else "✗ 失败"
        print(f"  {status} - {name}")
    
    print(f"\n总计: {success_count}/{total_count} 成功")
    
    if success_count == total_count:
        print("\n✓ 所有测试数据收集完成！")
        return True
    else:
        print(f"\n⚠ 部分收集失败: {total_count - success_count} 项")
        return False


if __name__ == "__main__":
    try:
        success = collect_all_test_data()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
