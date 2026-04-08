"""
清理重复的Webpage数据

检查并删除重复的Webpage知识项，保留唯一的数据。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kb.storage.sqlite_storage import SQLiteStorage


def cleanup_duplicates():
    """清理重复的Webpage数据"""
    print("=" * 70)
    print("清理重复的Webpage数据")
    print("=" * 70)
    
    storage = SQLiteStorage()
    
    # 获取所有webpage类型的数据
    items = storage.list_knowledge(content_type="webpage", limit=1000)
    
    print(f"\n找到 {len(items)} 条webpage数据")
    
    # 按标题分组
    title_groups = {}
    for item in items:
        title = item['title']
        if title not in title_groups:
            title_groups[title] = []
        title_groups[title].append(item)
    
    # 统计重复项
    duplicates = {title: group for title, group in title_groups.items() if len(group) > 1}
    
    if not duplicates:
        print("\n✓ 没有发现重复数据")
        return
    
    print(f"\n发现 {len(duplicates)} 个重复的标题:")
    
    deleted_count = 0
    for title, group in duplicates.items():
        print(f"\n标题: {title}")
        print(f"  重复次数: {len(group)}")
        
        # 保留第一个，删除其他
        for i, item in enumerate(group):
            if i == 0:
                print(f"  保留: {item['id']}")
            else:
                print(f"  删除: {item['id']}")
                if storage.delete_knowledge(item['id']):
                    deleted_count += 1
    
    print(f"\n✓ 清理完成，共删除 {deleted_count} 条重复数据")
    
    # 显示最终统计
    remaining = storage.list_knowledge(content_type="webpage", limit=1000)
    print(f"\n剩余webpage数据: {len(remaining)} 条")


if __name__ == "__main__":
    cleanup_duplicates()

