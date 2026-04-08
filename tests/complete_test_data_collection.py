#!/usr/bin/env python
"""
完整的测试数据生成脚本

使用CLI收集数据后，自动注册到SQLite数据库中。
确保所有类型数据的完整性和可查询性。
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime
import uuid

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kb.storage.sqlite_storage import SQLiteStorage
from kb.config import Config


def run_cli_collect(command: list) -> tuple:
    """
    执行CLI收集命令
    
    Returns:
        (success: bool, file_path: str, title: str, word_count: int)
    """
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            # Parse output to extract info
            output = result.stdout
            title = ""
            file_path = ""
            word_count = 0
            
            for line in output.split('\n'):
                if '标题:' in line:
                    title = line.split('标题:')[1].strip()
                elif '保存路径:' in line:
                    file_path = line.split('保存路径:')[1].strip()
                elif '字数:' in line:
                    word_count = int(line.split('字数:')[1].strip())
            
            return True, file_path, title, word_count
        else:
            return False, "", "", 0
            
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False, "", "", 0


def register_in_database(storage: SQLiteStorage, content_type: str, title: str, 
                        source: str, file_path: str, word_count: int, tags: list) -> bool:
    """
    将收集的知识注册到数据库中
    
    Returns:
        bool: 是否成功
    """
    try:
        # Generate unique ID
        item_id = f"{content_type}_{uuid.uuid4().hex[:12]}"
        
        # Read content from file
        content = ""
        if Path(file_path).exists():
            content = Path(file_path).read_text(encoding='utf-8')
        
        # Add to database
        success = storage.add_knowledge(
            id=item_id,
            title=title,
            content_type=content_type,
            source=source,
            collected_at=datetime.now().isoformat(),
            summary=content[:200] if content else "",
            word_count=word_count,
            file_path=file_path
        )
        
        if success and tags:
            storage.add_tags(item_id, tags)
            print(f"  ✓ 已注册到数据库: {title}")
            return True
        elif success:
            print(f"  ✓ 已注册到数据库: {title}")
            return True
        else:
            print(f"  ✗ 注册失败: {title}")
            return False
            
    except Exception as e:
        print(f"  ✗ 注册异常: {e}")
        return False


def collect_and_register_all():
    """收集并注册所有类型的测试数据"""
    print("=" * 70)
    print("完整测试数据生成 - CLI收集 + 数据库注册")
    print("=" * 70)
    
    # Initialize database
    config = Config()
    data_dir = Path(config.get("data_dir", "~/knowledge-base")).expanduser()
    db_path = str(data_dir / "metadata.db")
    storage = SQLiteStorage(db_path=db_path)
    
    print(f"\n数据库路径: {db_path}")
    
    # CLI paths
    cli_path = str(project_root / ".venv" / "bin" / "python")
    cli_module = "-m"
    cli_name = "kb.cli"
    test_data_dir = project_root / "tests" / "test_data"
    
    results = []
    
    # 1. Collect TXT file
    print("\n" + "=" * 70)
    print("1. 收集TXT文件")
    print("=" * 70)
    txt_file = test_data_dir / "sample_python.txt"
    if txt_file.exists():
        print(f"执行CLI收集...")
        success, file_path, title, word_count = run_cli_collect([
            cli_path, cli_module, cli_name, "file", "collect", str(txt_file),
            "-t", "Python", "-t", "编程", "-t", "最佳实践",
            "--title", "Python编程最佳实践示例"
        ])
        
        if success:
            print(f"注册到数据库...")
            db_success = register_in_database(
                storage, "file", title, str(txt_file), file_path, word_count,
                ["Python", "编程", "最佳实践"]
            )
            results.append(("TXT文件", db_success))
        else:
            results.append(("TXT文件", False))
    
    # 2. Collect Markdown file
    print("\n" + "=" * 70)
    print("2. 收集Markdown文件")
    print("=" * 70)
    md_file = test_data_dir / "sample_markdown.md"
    if md_file.exists():
        print(f"执行CLI收集...")
        success, file_path, title, word_count = run_cli_collect([
            cli_path, cli_module, cli_name, "file", "collect", str(md_file),
            "-t", "数据库", "-t", "设计", "-t", "最佳实践",
            "--title", "数据库设计最佳实践"
        ])
        
        if success:
            print(f"注册到数据库...")
            db_success = register_in_database(
                storage, "file", title, str(md_file), file_path, word_count,
                ["数据库", "设计", "最佳实践"]
            )
            results.append(("Markdown文件", db_success))
        else:
            results.append(("Markdown文件", False))
    
    # 3. Collect Webpage
    print("\n" + "=" * 70)
    print("3. 收集网页")
    print("=" * 70)
    print(f"执行CLI收集...")
    success, file_path, title, word_count = run_cli_collect([
        cli_path, cli_module, cli_name, "webpage", "collect",
        "https://httpbin.org/html",
        "-t", "测试", "-t", "HTML",
        "--title", "HTTPBin测试页面"
    ])
    
    if success:
        print(f"注册到数据库...")
        db_success = register_in_database(
            storage, "webpage", title, "https://httpbin.org/html", 
            file_path, word_count, ["测试", "HTML"]
        )
        results.append(("网页", db_success))
    else:
        results.append(("网页", False))
    
    # 4. Collect Email (MBOX)
    print("\n" + "=" * 70)
    print("4. 收集邮件 (MBOX)")
    print("=" * 70)
    mbox_file = test_data_dir / "sample_emails.mbox"
    if mbox_file.exists():
        print(f"执行CLI收集...")
        success, file_path, title, word_count = run_cli_collect([
            cli_path, cli_module, cli_name, "email", "collect", str(mbox_file),
            "-t", "邮件", "-t", "项目", "-t", "沟通",
            "--max-emails", "10"
        ])
        
        # Email collection returns multiple items, we'll register the first one
        if success:
            print(f"注册到数据库...")
            # For MBOX, we need to handle multiple emails
            # For simplicity, register as one entry
            db_success = register_in_database(
                storage, "email", "MBOX邮件集合", str(mbox_file),
                file_path if file_path else str(mbox_file), word_count,
                ["邮件", "项目", "沟通"]
            )
            results.append(("邮件MBOX", db_success))
        else:
            results.append(("邮件MBOX", False))
    
    # 5. Create Note
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
    
    print(f"执行CLI创建...")
    success, file_path, title, word_count = run_cli_collect([
        cli_path, cli_module, cli_name, "note", "add", note_content,
        "-t", "系统设计", "-t", "面试", "-t", "架构",
        "--title", "系统设计面试要点"
    ])
    
    if success:
        print(f"注册到数据库...")
        db_success = register_in_database(
            storage, "note", title, "manual", file_path, word_count,
            ["系统设计", "面试", "架构"]
        )
        results.append(("笔记", db_success))
    else:
        results.append(("笔记", False))
    
    # 6. Collect Paper (arXiv)
    print("\n" + "=" * 70)
    print("6. 收集论文 (arXiv)")
    print("=" * 70)
    print(f"执行CLI收集...")
    success, file_path, title, word_count = run_cli_collect([
        cli_path, cli_module, cli_name, "paper", "collect",
        "https://arxiv.org/abs/1706.03762",
        "-t", "深度学习", "-t", "Transformer", "-t", "NLP"
    ])
    
    if success:
        print(f"注册到数据库...")
        db_success = register_in_database(
            storage, "paper", title, "https://arxiv.org/abs/1706.03762",
            file_path, word_count, ["深度学习", "Transformer", "NLP"]
        )
        results.append(("论文arXiv", db_success))
    else:
        results.append(("论文arXiv", False))
    
    # Summary
    print("\n" + "=" * 70)
    print("收集结果汇总")
    print("=" * 70)
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for name, success in results:
        status = "✓ 成功" if success else "✗ 失败"
        print(f"  {status} - {name}")
    
    print(f"\n总计: {success_count}/{total_count} 成功")
    
    # Final statistics
    print("\n" + "=" * 70)
    print("最终数据库统计")
    print("=" * 70)
    stats = storage.get_stats()
    print(f"\n总知识项: {stats['total_items']}")
    print(f"\n按类型分布:")
    for ctype, count in stats['items_by_type'].items():
        print(f"  - {ctype}: {count}")
    print(f"\n总标签数: {stats['total_tags']}")
    
    if success_count == total_count:
        print("\n✓ 所有测试数据收集并注册完成！")
        return True
    else:
        print(f"\n⚠ 部分失败: {total_count - success_count} 项")
        return False


if __name__ == "__main__":
    try:
        success = collect_and_register_all()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
