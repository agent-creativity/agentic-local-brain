#!/usr/bin/env python3
"""
BookmarkCollector 使用示例

演示如何使用 BookmarkCollector 从浏览器或 HTML 文件收集书签。
"""

import json
import tempfile
from pathlib import Path

from kb.collectors import BookmarkCollector


def example_basic_usage():
    """示例 1: 基本使用 - 从 HTML 文件导入书签"""
    print("=" * 60)
    print("示例 1: 从 HTML 文件导入书签")
    print("=" * 60)

    # 创建示例 HTML 书签文件
    sample_html = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<TITLE>Bookmarks</TITLE>
<H1>Bookmarks</H1>
<DL><p>
    <DT><A HREF="https://example.com" ADD_DATE="1234567890">Example Site</A>
    <DT><H3>技术</H3>
    <DL><p>
        <DT><A HREF="https://python.org" ADD_DATE="1234567891">Python Official</A>
        <DT><A HREF="https://github.com" ADD_DATE="1234567892">GitHub</A>
    </DL><p>
</DL><p>"""

    # 写入临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(sample_html)
        html_file = Path(f.name)

    try:
        # 创建收集器
        collector = BookmarkCollector()

        # 从 HTML 文件收集
        print(f"\n正在从文件收集书签: {html_file}")
        results = collector.collect_from_file(html_file, max_concurrent=3)

        # 显示结果
        success_count = sum(1 for r in results if r.success)
        failed_count = len(results) - success_count

        print(f"\n收集完成！")
        print(f"  成功: {success_count} 个")
        print(f"  失败: {failed_count} 个")

        # 显示成功的书签
        if success_count > 0:
            print(f"\n收集的书签:")
            for result in results:
                if result.success:
                    print(f"  ✓ {result.title} -> {result.file_path.name}")

    finally:
        # 清理临时文件
        html_file.unlink(missing_ok=True)


def example_from_chrome_json():
    """示例 2: 从 Chrome JSON 书签文件收集"""
    print("\n" + "=" * 60)
    print("示例 2: 从 Chrome JSON 书签文件收集")
    print("=" * 60)

    # 创建示例 Chrome 书签 JSON
    sample_bookmarks = {
        "checksum": "abc123",
        "roots": {
            "bookmark_bar": {
                "children": [
                    {
                        "date_added": "13285267200000000",
                        "name": "Example Site",
                        "type": "url",
                        "url": "https://example.com"
                    },
                    {
                        "children": [
                            {
                                "date_added": "13285267300000000",
                                "name": "Python Official",
                                "type": "url",
                                "url": "https://python.org"
                            }
                        ],
                        "name": "Development",
                        "type": "folder"
                    }
                ],
                "name": "书签栏",
                "type": "folder"
            },
            "other": {"children": [], "name": "其他书签", "type": "folder"},
            "synced": {"children": [], "name": "移动设备书签", "type": "folder"}
        },
        "version": 1
    }

    # 写入临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(sample_bookmarks, f)
        json_file = Path(f.name)

    try:
        # 创建收集器
        collector = BookmarkCollector()

        # 从 Chrome JSON 收集
        print(f"\n正在从 Chrome JSON 文件收集书签: {json_file}")
        results = collector.collect_from_chrome_json(json_file, max_concurrent=2)

        # 显示结果
        success_count = sum(1 for r in results if r.success)
        print(f"\n收集完成！成功 {success_count} 个书签")

        for result in results:
            if result.success:
                folder = result.metadata.get('folder_path', [])
                folder_str = " / ".join(folder) if folder else "根目录"
                print(f"  ✓ {result.title} [{folder_str}]")

    finally:
        # 清理临时文件
        json_file.unlink(missing_ok=True)


def example_incremental_update():
    """示例 3: 增量更新 - 跳过已收集的书签"""
    print("\n" + "=" * 60)
    print("示例 3: 增量更新 - 跳过已收集的书签")
    print("=" * 60)

    sample_html = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<TITLE>Bookmarks</TITLE>
<H1>Bookmarks</H1>
<DL><p>
    <DT><A HREF="https://example.com" ADD_DATE="1234567890">Example Site</A>
    <DT><A HREF="https://python.org" ADD_DATE="1234567891">Python Official</A>
</DL><p>"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(sample_html)
        html_file = Path(f.name)

    try:
        collector = BookmarkCollector()

        # 第一次收集
        print("\n第一次收集（所有书签）:")
        results1 = collector.collect_from_file(html_file, skip_existing=True)
        print(f"  收集了 {len(results1)} 个书签")

        # 第二次收集（应该跳过所有）
        print("\n第二次收集（跳过已收集的）:")
        results2 = collector.collect_from_file(html_file, skip_existing=True)
        print(f"  收集了 {len(results2)} 个书签（都已存在）")

        # 如果不跳过
        print("\n第三次收集（不跳过）:")
        results3 = collector.collect_from_file(html_file, skip_existing=False)
        print(f"  收集了 {len(results3)} 个书签（强制重新收集）")

    finally:
        html_file.unlink(missing_ok=True)


def example_custom_configuration():
    """示例 4: 自定义配置"""
    print("\n" + "=" * 60)
    print("示例 4: 自定义配置")
    print("=" * 60)

    # 自定义并发数、重试次数和延迟
    collector = BookmarkCollector(
        max_concurrent=10,  # 10 个并发
        max_retries=5,  # 最多重试 5 次
        retry_delay=2.0,  # 重试延迟 2 秒
    )

    print(f"\n配置信息:")
    print(f"  最大并发数: {collector._max_concurrent}")
    print(f"  最大重试次数: {collector._max_retries}")
    print(f"  重试延迟: {collector._retry_delay} 秒")
    print(f"  支持的浏览器: {', '.join(collector.get_supported_browsers())}")


def example_single_bookmark():
    """示例 5: 收集单个书签"""
    print("\n" + "=" * 60)
    print("示例 5: 收集单个书签")
    print("=" * 60)

    collector = BookmarkCollector()

    # 收集单个书签
    result = collector.collect(
        source="https://python.org",
        title="Python 官方网站",
        tags=["Python", "编程", "官方文档"],
        folder_path=["技术", "编程语言"]
    )

    if result.success:
        print(f"\n✓ 收集成功！")
        print(f"  标题: {result.title}")
        print(f"  字数: {result.word_count}")
        print(f"  标签: {', '.join(result.tags)}")
        print(f"  保存路径: {result.file_path}")

        # 显示保存的文件内容
        content = result.file_path.read_text(encoding="utf-8")
        print(f"\n保存的文件内容:")
        print("-" * 60)
        print(content)
    else:
        print(f"\n✗失败: {result.error}")


def example_metadata_inspection():
    """示例 6: 检查元数据"""
    print("\n" + "=" * 60)
    print("示例 6: 检查元数据")
    print("=" * 60)

    collector = BookmarkCollector()

    result = collector.collect(
        source="https://github.com",
        title="GitHub",
        folder_path=["技术", "开发工具"]
    )

    if result.success:
        print(f"\n✓ 收集成功！")
        print(f"\n元数据详情:")
        print("-" * 60)
        for key, value in result.metadata.items():
            print(f"  {key}: {value}")


def example_error_handling():
    """示例 7: 错误处理"""
    print("\n" + "=" * 60)
    print("示例 7: 错误处理")
    print("=" * 60)

    collector = BookmarkCollector()

    # 测试 1: 无效 URL
    print("\n测试 1: 收集无效 URL")
    result = collector.collect(
        source="not-a-valid-url",
        title="Invalid"
    )
    print(f"  结果: {result.error}")

    # 测试 2: 文件不存在
    print("\n测试 2: 文件不存在")
    try:
        collector.collect_from_file("/nonexistent/path/bookmarks.html")
    except FileNotFoundError as e:
        print(f"  捕获到异常: {e}")


def example_programmatic_usage():
    """示例 8: 编程方式使用"""
    print("\n" + "=" * 60)
    print("示例 8: 编程方式使用")
    print("=" * 60)

    # 创建收集器
    collector = BookmarkCollector()

    # 定义要收集的书签列表
    bookmarks_to_collect = [
        {
            "url": "https://example.com",
            "title": "Example Site",
            "tags": ["示例"],
            "folder": ["测试"]
        },
        {
            "url": "https://httpbin.org/html",
            "title": "HTTPBin HTML Test",
            "tags": ["测试", "HTTP"],
            "folder": ["测试", "HTTP"]
        },
    ]

    print(f"\n准备收集 {len(bookmarks_to_collect)} 个书签...")

    # 收集并处理结果
    successful_count = 0
    failed_count = 0

    for bookmark in bookmarks_to_collect:
        print(f"\n收集: {bookmark['title']}")
        result = collector.collect(
            source=bookmark["url"],
            title=bookmark["title"],
            tags=bookmark["tags"],
            folder_path=bookmark["folder"]
        )

        if result.success:
            successful_count += 1
            print(f"  ✓ 成功: {result.title}")
        else:
            failed_count += 1
            print(f"✗: {result.error}")

    print(f"\n收集完成！")
    print(f"  成功: {successful_count}")
    print(f"  失败: {failed_count}")


def example_from_safari():
    """示例 9: 从 Safari plist 文件收集（macOS）"""
    print("\n" + "=" * 60)
    print("示例 9: 从 Safari plist 文件收集（macOS）")
    print("=" * 60)

    import platform

    if platform.system() != "Darwin":
        print("此示例仅在 macOS 系统上可用")
        return

    collector = BookmarkCollector()

    # Safari 书签文件路径
    safari_bookmarks = Path.home() / "Library" / "Safari" / "Bookmarks.plist"

    if safari_bookmarks.exists():
        print(f"\n找到 Safari 书签文件: {safari_bookmarks}")

        try:
            results = collector.collect_from_safari_plist(
                safari_bookmarks,
                max_concurrent=3
            )

            success_count = sum(1 for r in results if r.success)
            print(f"\n收集完成！成功 {success_count} 个书签")

        except Exception as e:
            print(f"\n收集失败: {e}")
    else:
        print(f"\n未找到 Safari 书签文件: {safari_bookmarks}")
        print("请确保已使用 Safari 浏览器并添加了书签。")


def main():
    """主函数：运行所有示例"""
    print("\n" + "=" * 60)
    print("BookmarkCollector 使用示例集合")
    print("=" * 60 + "\n")

    try:
        example_basic_usage()
        example_from_chrome_json()
        example_incremental_update()
        example_custom_configuration()
        example_single_bookmark()
        example_metadata_inspection()
        example_error_handling()
        example_programmatic_usage()
        example_from_safari()

    except KeyboardInterrupt:
        print("\n\n用户中断执行")
    except Exception as e:
        print(f"\n\n发生错误: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
