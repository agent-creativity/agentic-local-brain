#!/usr/bin/env python
"""
示例Python文件 - 用于测试文件收集功能
演示Python编程最佳实践
"""

from typing import List, Optional
from dataclasses import dataclass


@dataclass
class User:
    """用户数据类"""
    name: str
    email: str
    age: Optional[int] = None


def process_users(users: List[User]) -> List[str]:
    """
    处理用户列表
    
    Args:
        users: 用户对象列表
        
    Returns:
        处理后的用户名列表
    """
    # 使用列表推导式
    active_users = [
        user.name 
        for user in users 
        if user.age and user.age >= 18
    ]
    
    # 排序并返回
    return sorted(active_users)


def main():
    """主函数"""
    # 创建测试数据
    users = [
        User("Alice", "alice@example.com", 25),
        User("Bob", "bob@example.com", 17),
        User("Charlie", "charlie@example.com", 30),
    ]
    
    # 处理用户
    result = process_users(users)
    print(f"成年用户: {result}")


if __name__ == "__main__":
    main()
