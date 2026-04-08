#!/usr/bin/env python3
"""
FileCollector 使用示例

演示如何使用 FileCollector 收集不同类型的文件。
"""

import tempfile
from pathlib import Path

from kb.collectors import FileCollector


def example_collect_txt():
    """示例 1: 收集 TXT 文件"""
    print("=" * 60)
    print("示例 1: 收集 TXT 文件")
    print("=" * 60)

    # 创建测试文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("这是一个测试 TXT 文件。\n")
        f.write("包含多行内容用于测试文件收集功能。\n")
        f.write("FileCollector 会自动提取内容并生成元数据。")
        txt_file = Path(f.name)

    try:
        # 创建收集器
        collector = FileCollector()

        # 收集文件
        result = collector.collect(
            source=txt_file,
            tags=["测试", "TXT", "示例"],
            title="TXT 文件测试"
        )

        # 显示结果
        if result.success:
            print(f"成功收集")
            print(f"  标题: {result.title}")
            print(f"  字数: {result.word_count}")
            print(f"  标签: {', '.join(result.tags)}")
            print(f"  保存路径: {result.file_path}")

            # 显示保存的文件内容
            print(f"\n保存的文件内容:")
            print("-" * 60)
            content = result.file_path.read_text(encoding="utf-8")
            print(content[:500] + "..." if len(content) > 500 else content)
        else:
            print(f"收集失败: {result.error}")

    finally:
        # 清理测试文件
        txt_file.unlink(missing_ok=True)


def example_collect_markdown():
    """示例 2: 收集 Markdown 文件"""
    print("\n" + "=" * 60)
    print("示例 2: 收集 Markdown 文件")
    print("=" * 60)

    # 创建测试 Markdown 文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("---\n")
        f.write("title: 原始标题\n")
        f.write("author: Test Author\n")
        f.write("---\n\n")
        f.write("# Markdown 测试文档\n\n")
        f.write("这是一个 Markdown 格式的测试文档。\n\n")
        f.write("## 特性\n\n")
        f.write("- 支持 YAML Front Matter\n")
        f.write("- 自动提取纯文本内容\n")
        f.write("- 生成标准化元数据")
        md_file = Path(f.name)

    try:
        collector = FileCollector()

        result = collector.collect(
            source=md_file,
            tags=["Markdown", "文档"],
            title="Markdown 文件示例"
        )

        if result.success:
            print(f"成功收集")
            print(f"  标题: {result.title}")
            print(f"  字数: {result.word_count}")
            print(f"  保存路径: {result.file_path}")
        else:
            print(f"收集失败: {result.error}")

    finally:
        md_file.unlink(missing_ok=True)


def example_collect_pdf():
    """示例 3: 收集 PDF 文件"""
    print("\n" + "=" * 60)
    print("示例 3: 收集 PDF 文件")
    print("=" * 60)

    # 注意：这里需要一个真实的 PDF 文件
    # 如果 PyPDF2 未安装，会提示安装
    print("提示: 收集 PDF 文件需要安装 PyPDF2")
    print("运行: pip install PyPDF2")

    # 示例代码（需要真实 PDF 文件才能运行）
    # pdf_file = Path("/path/to/your/document.pdf")
    # collector = FileCollector()
    # result = collector.collect(pdf_file, tags=["PDF", "论文"])


def example_programmatic_usage():
    """示例 4: 编程方式使用"""
    print("\n" + "=" * 60)
    print("示例 4: 编程方式使用 FileCollector")
    print("=" * 60)

    # 批量收集文件
    files_to_collect = []

    # 创建一些测试文件
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # 创建测试文件
        for i in range(3):
            test_file = tmpdir / f"document_{i}.txt"
            test_file.write_text(f"这是第 {i+1} 个测试文档的内容。" * 10)
            files_to_collect.append(test_file)

        # 批量收集
        collector = FileCollector()
        results = []

        for file_path in files_to_collect:
            result = collector.collect(
                source=file_path,
                tags=["批量", f"文档{i+1}"]
            )
            results.append(result)

        # 显示批量收集结果
        print(f"批量收集完成，共处理 {len(results)} 个文件")
        for i, result in enumerate(results, 1):
            if result.success:
                print(f"  [成功] 文件 {i}: {result.title} ({result.word_count} 字)")
            else:
                print(f"  [失败] 文件 {i}: {result.error}")


def example_error_handling():
    """示例 5: 错误处理"""
    print("\n" + "=" * 60)
    print("示例 5: 错误处理")
    print("=" * 60)

    collector = FileCollector()

    # 测试不存在的文件
    result = collector.collect("/nonexistent/file.txt")
    print(f"不存在的文件: {result.error}")

    # 测试不支持的格式
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        f.write(b"fake content")
        docx_file = Path(f.name)

    try:
        result = collector.collect(docx_file)
        print(f"不支持的格式: {result.error}")
    finally:
        docx_file.unlink(missing_ok=True)


def main():
    """主函数：运行所有示例"""
    print("\n" + "=" * 60)
    print("FileCollector 使用示例集合")
    print("=" * 60 + "\n")

    example_collect_txt()
    example_collect_markdown()
    example_collect_pdf()
    example_programmatic_usage()
    example_error_handling()

    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
