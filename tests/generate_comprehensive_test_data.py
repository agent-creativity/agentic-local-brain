#!/usr/bin/env python
"""
生成综合测试数据
支持多种内容类型：file, webpage, note, bookmark, email, paper
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
import uuid
from kb.storage.sqlite_storage import SQLiteStorage
from kb.config import Config
from kb.processors.chunker import Chunker
from kb.processors.embedder import Embedder


def generate_comprehensive_test_data():
    """生成综合测试数据"""
    print("=" * 70)
    print("生成综合测试数据")
    print("=" * 70)
    
    # 初始化存储
    config = Config()
    data_dir = config.get("data_dir", "~/knowledge-base")
    db_path = Path(data_dir).expanduser() / "metadata.db"
    
    print(f"\n数据库路径: {db_path}")
    storage = SQLiteStorage(db_path=str(db_path))
    
    # 测试数据集合
    test_data = []
    
    # 1. 文件类型 (File)
    print("\n[1/6] 生成文件类型数据...")
    file_items = [
        {
            "title": "Python编程最佳实践",
            "content": """Python编程最佳实践指南

1. 代码风格
   - 遵循PEP 8规范
   - 使用有意义的变量名
   - 保持函数简洁（单一职责原则）

2. 错误处理
   - 使用try-except捕获异常
   - 避免裸except语句
   - 提供有意义的错误信息

3. 性能优化
   - 使用生成器处理大数据
   - 避免不必要的循环
   - 利用内置函数和标准库

4. 测试
   - 编写单元测试
   - 使用pytest框架
   - 保持高代码覆盖率

5. 文档
   - 使用docstring
   - 编写README文件
   - 保持文档更新""",
            "tags": ["Python", "编程", "最佳实践", "代码质量"]
        },
        {
            "title": "数据库设计范式详解",
            "content": """数据库设计范式详解

第一范式（1NF）
- 所有列都是不可再分的原子值
- 消除重复组
- 每个字段只包含单一值

第二范式（2NF）
- 满足1NF
- 消除部分函数依赖
- 非主键列必须完全依赖于主键

第三范式（3NF）
- 满足2NF
- 消除传递函数依赖
- 非主键列之间不能有依赖关系

BC范式（BCNF）
- 满足3NF
- 所有决定因素都是候选键
- 更强的约束条件

第四范式（4NF）
- 满足BCNF
- 消除多值依赖
- 适用于复杂的数据关系

实际应用建议
- 大多数场景使用3NF即可
- 过度规范化可能影响性能
- 根据查询模式适当反规范化""",
            "tags": ["数据库", "设计", "范式", "SQL"]
        },
        {
            "title": "Git工作流实践指南",
            "content": """Git工作流实践指南

1. Git Flow工作流
   - master分支：生产环境代码
   - develop分支：开发主分支
   - feature分支：功能开发
   - release分支：发布准备
   - hotfix分支：紧急修复

2. GitHub Flow
   - 简化的工作流
   - 主分支始终可部署
   - 功能分支开发
   - Pull Request审查
   - 合并后部署

3. GitLab Flow
   - 环境分支
   - 上游优先原则
   - 持续交付支持

4. 最佳实践
   - 提交信息规范
   - 定期rebase
   - 避免大提交
   - 使用tag标记版本""",
            "tags": ["Git", "版本控制", "工作流", "协作"]
        }
    ]
    
    for item in file_items:
        file_id = f"file_{uuid.uuid4().hex[:12]}"
        success = storage.add_knowledge(
            id=file_id,
            title=item['title'],
            content_type="file",
            source=f"/docs/{file_id}.txt",
            collected_at=datetime.now().isoformat(),
            summary=item['content'][:200],
            word_count=len(item['content'])
        )
        if success:
            storage.add_tags(file_id, item['tags'])
            test_data.append(file_id)
            print(f"  ✓ 添加: {item['title']}")
    
    # 2. 网页类型 (Webpage)
    print("\n[2/6] 生成网页类型数据...")
    webpage_items = [
        {
            "title": "2024年AI技术趋势预测",
            "url": "https://tech-insights.com/ai-trends-2024",
            "content": """2024年AI技术趋势预测

1. 多模态大模型
   - 文本、图像、视频统一处理
   - GPT-5、Gemini 2.0等新一代模型
   - 跨模态理解能力大幅提升

2. AI Agent技术
   - 自主决策和执行能力
   - 工具调用和API集成
   - 多Agent协作系统

3. 边缘AI部署
   - 模型压缩和量化技术
   - 端侧推理优化
   - 隐私保护计算

4. AI安全与对齐
   - RLHF技术改进
   - 可解释性研究
   - 伦理和监管框架

5. 行业应用深化
   - 医疗AI辅助诊断
   - 金融风控和量化交易
   - 智能制造和自动化""",
            "tags": ["AI", "技术趋势", "大模型", "2024"]
        },
        {
            "title": "云原生架构设计原则",
            "url": "https://cloud-architecture.dev/principles",
            "content": """云原生架构设计原则

1. 微服务架构
   - 服务拆分和边界定义
   - API网关和路由
   - 服务间通信机制

2. 容器化部署
   - Docker容器标准化
   - Kubernetes编排
   - 容器网络和服务发现

3. DevOps实践
   - CI/CD流水线
   - 基础设施即代码
   - 自动化测试和部署

4. 可观测性
   - 日志收集和分析
   - 指标监控和告警
   - 分布式追踪

5. 弹性设计
   - 自动扩缩容
   - 故障隔离和降级
   - 多区域部署""",
            "tags": ["云原生", "架构设计", "微服务", "DevOps"]
        },
        {
            "title": "前端性能优化完全指南",
            "url": "https://web-performance.guide/optimization",
            "content": """前端性能优化完全指南

1. 加载性能优化
   - 代码分割和懒加载
   - 资源压缩和缓存
   - CDN加速和预加载

2. 渲染性能优化
   - 减少DOM操作
   - 虚拟列表和分页
   - Web Workers处理

3. 网络优化
   - HTTP/2和HTTP/3
   - 请求合并和去重
   - 图片格式优化（WebP）

4. 构建优化
   - Tree Shaking
   - 按需加载
   - 打包体积优化

5. 监控和分析
   - 性能指标采集
   - 用户体验监控
   - A/B测试""",
            "tags": ["前端", "性能优化", "Web开发", "用户体验"]
        },
        {
            "title": "机器学习模型部署最佳实践",
            "url": "https://ml-ops.dev/deployment-guide",
            "content": """机器学习模型部署最佳实践

1. 模型服务化
   - RESTful API设计
   - gRPC高性能服务
   - 批量预测接口

2. 模型版本管理
   - 模型注册表
   - 版本控制和回滚
   - A/B测试支持

3. 性能优化
   - 模型压缩和量化
   - TensorRT加速
   - 批处理和异步推理

4. 监控和告警
   - 预测延迟监控
   - 数据漂移检测
   - 模型性能衰减

5. 安全考虑
   - 模型加密
   - 访问控制
   - 输入验证""",
            "tags": ["机器学习", "MLOps", "模型部署", "生产环境"]
        }
    ]
    
    for item in webpage_items:
        webpage_id = f"webpage_{uuid.uuid4().hex[:12]}"
        success = storage.add_knowledge(
            id=webpage_id,
            title=item['title'],
            content_type="webpage",
            source=item['url'],
            collected_at=datetime.now().isoformat(),
            summary=item['content'][:200],
            word_count=len(item['content'])
        )
        if success:
            storage.add_tags(webpage_id, item['tags'])
            test_data.append(webpage_id)
            print(f"  ✓ 添加: {item['title']}")
    
    # 3. 笔记类型 (Note)
    print("\n[3/6] 生成笔记类型数据...")
    note_items = [
        {
            "title": "系统设计面试准备笔记",
            "content": """系统设计面试准备笔记

核心概念
- CAP定理：一致性、可用性、分区容错性
- 负载均衡：轮询、最少连接、一致性哈希
- 缓存策略：LRU、LFU、TTL

常见系统设计
1. URL短链接服务
   - 哈希函数选择
   - 分布式ID生成
   - 缓存层设计

2. 聊天系统
   - WebSocket长连接
   - 消息队列解耦
   - 离线消息存储

3. 推荐系统
   - 协同过滤
   - 内容推荐
   - 实时特征更新

面试技巧
- 先澄清需求
- 估算容量和性能
- 从简单到复杂
- 讨论权衡取舍""",
            "tags": ["系统设计", "面试", "架构", "笔记"]
        },
        {
            "title": "Kubernetes学习要点",
            "content": """Kubernetes学习要点

核心组件
- API Server：集群入口
- etcd：配置存储
- Scheduler：调度器
- Controller Manager：控制器

工作负载
- Pod：最小部署单元
- Deployment：无状态应用
- StatefulSet：有状态应用
- DaemonSet：节点守护进程

网络
- Service：服务发现
- Ingress：外部访问
- NetworkPolicy：网络策略

存储
- Volume：数据卷
- PersistentVolume：持久化存储
- StorageClass：存储类

运维
- kubectl常用命令
- 日志查看和调试
- 资源监控""",
            "tags": ["Kubernetes", "容器编排", "云原生", "DevOps"]
        }
    ]
    
    for item in note_items:
        note_id = f"note_{uuid.uuid4().hex[:12]}"
        success = storage.add_knowledge(
            id=note_id,
            title=item['title'],
            content_type="note",
            source="manual",
            collected_at=datetime.now().isoformat(),
            summary=item['content'][:200],
            word_count=len(item['content'])
        )
        if success:
            storage.add_tags(note_id, item['tags'])
            test_data.append(note_id)
            print(f"  ✓ 添加: {item['title']}")
    
    # 4. 书签类型 (Bookmark)
    print("\n[4/6] 生成书签类型数据...")
    bookmark_items = [
        {
            "title": "GitHub Copilot使用技巧",
            "url": "https://docs.github.com/copilot",
            "content": "GitHub Copilot AI编程助手官方文档和使用指南",
            "tags": ["AI编程", "GitHub", "开发工具"]
        },
        {
            "title": "Rust编程语言教程",
            "url": "https://doc.rust-lang.org/book/",
            "content": "Rust官方教程 - The Rust Programming Language",
            "tags": ["Rust", "编程语言", "系统编程"]
        },
        {
            "title": "PostgreSQL官方文档",
            "url": "https://www.postgresql.org/docs/",
            "content": "PostgreSQL数据库完整文档和参考手册",
            "tags": ["PostgreSQL", "数据库", "SQL"]
        }
    ]
    
    for item in bookmark_items:
        bookmark_id = f"bookmark_{uuid.uuid4().hex[:12]}"
        success = storage.add_knowledge(
            id=bookmark_id,
            title=item['title'],
            content_type="bookmark",
            source=item['url'],
            collected_at=datetime.now().isoformat(),
            summary=item['content'],
            word_count=len(item['content'])
        )
        if success:
            storage.add_tags(bookmark_id, item['tags'])
            test_data.append(bookmark_id)
            print(f"  ✓ 添加: {item['title']}")
    
    # 5. 邮件类型 (Email)
    print("\n[5/6] 生成邮件类型数据...")
    email_items = [
        {
            "title": "项目周报 - 2024年第12周",
            "content": """主题：项目周报 - 2024年第12周

本周完成：
1. 用户认证模块开发完成
2. API接口文档更新
3. 单元测试覆盖率达到85%

下周计划：
1. 开始支付模块开发
2. 性能测试和优化
3. 准备v2.0版本发布

风险和问题：
- 第三方支付接口文档不完整
- 需要协调测试环境资源

需要支持：
- 申请测试服务器资源
- 协调UI设计师完成界面""",
            "tags": ["周报", "项目管理", "开发进度"]
        }
    ]
    
    for item in email_items:
        email_id = f"email_{uuid.uuid4().hex[:12]}"
        success = storage.add_knowledge(
            id=email_id,
            title=item['title'],
            content_type="email",
            source="inbox",
            collected_at=datetime.now().isoformat(),
            summary=item['content'][:200],
            word_count=len(item['content'])
        )
        if success:
            storage.add_tags(email_id, item['tags'])
            test_data.append(email_id)
            print(f"  ✓ 添加: {item['title']}")
    
    # 6. 论文类型 (Paper)
    print("\n[6/6] 生成论文类型数据...")
    paper_items = [
        {
            "title": "Attention Is All You Need",
            "content": """论文标题：Attention Is All You Need
作者：Ashish Vaswani, Noam Shazeer, Niki Parmar, et al.
发表：NeurIPS 2017

摘要：
本文提出了一种新的简单网络架构Transformer，完全基于注意力机制，
完全摒弃了循环和卷积。在机器翻译任务上，Transformer在训练成本和
质量上都达到了新的state-of-the-art。

核心贡献：
1. 提出Self-Attention机制
2. 多头注意力（Multi-Head Attention）
3. 位置编码（Positional Encoding）
4. 编码器-解码器架构

影响：
- 成为NLP领域的基础架构
- 启发了BERT、GPT等模型
- 广泛应用于视觉、语音等领域""",
            "tags": ["深度学习", "Transformer", "注意力机制", "NLP", "经典论文"]
        }
    ]
    
    for item in paper_items:
        paper_id = f"paper_{uuid.uuid4().hex[:12]}"
        success = storage.add_knowledge(
            id=paper_id,
            title=item['title'],
            content_type="paper",
            source="arxiv",
            collected_at=datetime.now().isoformat(),
            summary=item['content'][:200],
            word_count=len(item['content'])
        )
        if success:
            storage.add_tags(paper_id, item['tags'])
            test_data.append(paper_id)
            print(f"  ✓ 添加: {item['title']}")
    
    # 统计信息
    print("\n" + "=" * 70)
    print("数据生成完成")
    print("=" * 70)
    
    stats = storage.get_stats()
    print(f"\n总知识项数: {stats['total_items']}")
    print(f"按类型分布:")
    for content_type, count in stats['items_by_type'].items():
        print(f"  - {content_type}: {count}")
    
    print(f"\n总标签数: {stats['total_tags']}")
    
    print(f"\n本次新增: {len(test_data)} 条")
    print(f"  - file: {sum(1 for tid in test_data if tid.startswith('file_'))}")
    print(f"  - webpage: {sum(1 for tid in test_data if tid.startswith('webpage_'))}")
    print(f"  - note: {sum(1 for tid in test_data if tid.startswith('note_'))}")
    print(f"  - bookmark: {sum(1 for tid in test_data if tid.startswith('bookmark_'))}")
    print(f"  - email: {sum(1 for tid in test_data if tid.startswith('email_'))}")
    print(f"  - paper: {sum(1 for tid in test_data if tid.startswith('paper_'))}")
    
    return test_data


if __name__ == "__main__":
    try:
        generate_comprehensive_test_data()
        print("\n✓ 测试数据生成成功！")
    except Exception as e:
        print(f"\n✗ 生成失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
