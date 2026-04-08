#!/usr/bin/env python3
"""
WebpageCollector 使用示例

演示如何使用 WebpageCollector 收集网页内容。
"""

import asyncio
from kb.collectors import WebpageCollector


def example_basic_usage():
    """示例 1: 基本使用"""
    print("=" * 60)
    print("示例 1: 基本使用 - 收集单个网页")
    print("=" * 60)

    # 创建收集器
    collector = WebpageCollector()

    # 收集网页
    url = "https://example.com"
    print(f"\n正在收集: {url}")

    result = collector.collect(url)

    if result.success:
        print(f"\n✓ 收集成功！")
        print(f"  标题: {result.title}")
        print(f"  字数: {result.word_count}")
        print(f"  标签: {', '.join(result.tags) if result.tags else '无'}")
        print(f"  保存路径: {result.file_path}")

        # 显示保存的文件内容（前 500 字符）
        content = result.file_path.read_text(encoding="utf-8")
        print(f"\n保存的文件内容（前 500 字符）:")
        print("-" * 60)
        print(content[:500] + "..." if len(content) > 500 else content)
    else:
        print(f"\n✗收集失败: {result.error}")


def example_with_tags():
    """示例 2: 添加标签"""
    print("\n" + "=" * 60)
    print("示例 2: 添加标签")
    print("=" * 60)

    collector = WebpageCollector()

    url = "https://example.com"
    tags = ["AI", "教程", "技术文章"]

    print(f"\n正在收集: {url}")
    print(f"标签: {', '.join(tags)}")

    result = collector.collect(url, tags=tags)

    if result.success:
        print(f"\n✓ 收集成功！")
        print(f"  标题: {result.title}")
        print(f"  标签: {', '.join(result.tags)}")
        print(f"  保存路径: {result.file_path}")
    else:
        print(f"\n✗收集失败: {result.error}")


def example_custom_title():
    """示例 3: 自定义标题"""
    print("\n" + "=" * 60)
    print("示例 3: 自定义标题")
    print("=" * 60)

    collector = WebpageCollector()

    url = "https://example.com"
    custom_title = "我的自定义网页标题"

    print(f"\n正在收集: {url}")
    print(f"自定义标题: {custom_title}")

    result = collector.collect(url, title=custom_title)

    if result.success:
        print(f"\n✓ 收集成功！")
        print(f"  标题: {result.title}")
        print(f"  保存路径: {result.file_path}")
    else:
        print(f"\n✗收集失败: {result.error}")


def example_batch_collection():
    """示例 4: 批量收集（同步）"""
    print("\n" + "=" * 60)
    print("示例 4: 批量收集（同步方式）")
    print("=" * 60)

    collector = WebpageCollector()

    # 定义要收集的 URL 列表
    urls = [
        "https://example.com",
        "https://httpbin.org/html",
    ]

    print(f"\n准备批量收集 {len(urls)} 个网页...")

    # 同步批量收集
    results = []
    for url in urls:
        print(f"\n正在收集: {url}")
        result = collector.collect(url, tags=["批量收集"])
        results.append((url, result))

    # 显示结果
    print(f"\n批量收集完成！")
    print("-" * 60)
    for url, result in results:
        if result.success:
            print(f"  [成功] {result.title} ({result.word_count} 字)")
        else:
            print(f"  [失败] {url}: {result.error}")


def example_async_batch_collection():
    """示例 5: 异步批量收集"""
    print("\n" + "=" * 60)
    print("示例 5: 异步批量收集")
    print("=" * 60)

    async def run_async_collection():
        collector = WebpageCollector()

        urls = [
            "https://example.com",
            "https://httpbin.org/html",
        ]

        print(f"\n准备异步批量收集 {len(urls)} 个网页...")

        # 异步批量收集
        results = await collector.collect_batch(urls, tags=["异步收集"], max_concurrent=2)

        print(f"\n异步批量收集完成！")
        print("-" * 60)
        for result in results:
            if result.success:
                print(f"  [成功] {result.title} ({result.word_count} 字)")
            else:
                print(f"  [失败] {result.error}")

    # 运行异步收集
    asyncio.run(run_async_collection())


def example_custom_configuration():
    """示例 6: 自定义配置"""
    print("\n" + "=" * 60)
    print("示例 6: 自定义配置")
    print("=" * 60)

    # 自定义超时时间和 User-Agent
    collector = WebpageCollector(
        timeout=60,  # 60 秒超时
        user_agent="MyCustomBot/1.0 (+https://mywebsite.com/bot)",
    )

    print(f"\n配置信息:")
    print(f"  超时时间: {collector._timeout} 秒")
    print(f"  User-Agent: {collector._user_agent}")

    url = "https://example.com"
    print(f"\n正在收集: {url}")

    result = collector.collect(url)

    if result.success:
        print(f"\n✓ 收集成功！")
        print(f"  标题: {result.title}")
    else:
        print(f"\n✗收集失败: {result.error}")


def example_error_handling():
    """示例 7: 错误处理"""
    print("\n" + "=" * 60)
    print("示例 7: 错误处理")
    print("=" * 60)

    collector = WebpageCollector(timeout=5)  # 短超时用于测试

    # 测试 1: 无效 URL
    print("\n测试 1: 无效 URL")
    result = collector.collect("not-a-valid-url")
    print(f"  结果: {result.error}")

    # 测试 2: 不存在的网站
    print("\n测试 2: 不存在的网站")
    result = collector.collect("https://this-domain-does-not-exist-12345.com")
    print(f"  结果: {result.error}")

    # 测试 3: 超时错误
    print("\n测试 3: 超时错误（模拟）")
    result = collector.collect("https://httpbin.org/delay/10")
    print(f"  结果: {result.error}")


def example_metadata_inspection():
    """示例 8: 检查元数据"""
    print("\n" + "=" * 60)
    print("示例 8: 检查元数据")
    print("=" * 60)

    collector = WebpageCollector()

    url = "https://example.com"
    print(f"\n正在收集: {url}")

    result = collector.collect(url, tags=["示例", "元数据"])

    if result.success:
        print(f"\n✓ 收集成功！")
        print(f"\n元数据详情:")
        print("-" * 60)
        for key, value in result.metadata.items():
            print(f"  {key}: {value}")
    else:
        print(f"\n✗收集失败: {result.error}")


def example_programmatic_usage():
    """示例 9: 编程方式使用"""
    print("\n" + "=" * 60)
    print("示例 9: 编程方式使用")
    print("=" * 60)

    # 创建收集器
    collector = WebpageCollector()

    # 定义要收集的网页
    urls_to_collect = [
        ("https://example.com", ["示例", "网页1"]),
        ("https://httpbin.org/html", ["示例", "网页2"]),
    ]

    print(f"\n准备收集 {len(urls_to_collect)} 个网页...")

    # 收集并处理结果
    successful_count = 0
    failed_count = 0

    for url, tags in urls_to_collect:
        print(f"\n收集: {url}")
        result = collector.collect(url, tags=tags)

        if result.success:
            successful_count += 1
            print(f"  ✓ 成功: {result.title}")
            # 可以在这里做进一步处理
            # 例如：发送到其他系统、生成索引等
        else:
            failed_count += 1
            print(f" ✗失败: {result.error}")

    print(f"\n收集完成！")
    print(f"  成功: {successful_count}")
    print(f"  失败: {failed_count}")


def main():
    """主函数：运行所有示例"""
    print("\n" + "=" * 60)
    print("WebpageCollector 使用示例集合")
    print("=" * 60 + "\n")

    print("提示: 某些示例可能需要网络连接，如果失败请检查网络状态。")
    print()

    # 运行示例
    try:
        example_basic_usage()
        example_with_tags()
        example_custom_title()
        example_batch_collection()
        example_custom_configuration()
        example_error_handling()
        example_metadata_inspection()
        example_programmatic_usage()

        # 异步示例需要单独运行
        print("\n" + "=" * 60)
        print("运行异步批量收集示例...")
        print("=" * 60)
        example_async_batch_collection()

    except KeyboardInterrupt:
        print("\n\n用户中断执行")
    except Exception as e:
        print(f"\n\n发生错误: {e}")

    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
