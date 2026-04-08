"""
生成测试数据脚本

为知识库系统生成各种类型的测试数据，包括：
1. 笔记 (Notes)
2. 文件 (Files)
3. URL 收集
4. 书签 (Bookmarks)

使用方法：
    python tests/generate_test_data.py
"""

import os
import sys
import json
import uuid
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kb.config import Config
from kb.storage.sqlite_storage import SQLiteStorage


def create_test_notes(storage: SQLiteStorage):
    """创建测试笔记数据"""
    print("\n" + "=" * 70)
    print("生成测试笔记数据")
    print("=" * 70)
    
    notes = [
        {
            "title": "Python 异步编程最佳实践",
            "content": """
Python 的异步编程模型基于 asyncio 库，提供了高效的并发处理能力。

核心概念：
1. 协程 (Coroutine)：使用 async/await 语法定义的函数
2. 事件循环 (Event Loop)：管理和执行协程的机制
3. 任务 (Task)：包装协程的对象，支持取消和状态查询

最佳实践：
- 使用 async with 管理异步资源
- 避免在协程中使用阻塞调用
- 使用 asyncio.gather() 并发执行多个任务
- 合理设置超时时间防止死锁

示例代码：
```python
import asyncio

async def fetch_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

async def main():
    tasks = [fetch_data(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return results
```

性能优化：
- 使用连接池减少连接开销
- 批量处理减少上下文切换
- 监控事件循环延迟
            """,
            "tags": ["Python", "异步编程", "asyncio", "并发", "性能优化"],
            "source": "manual"
        },
        {
            "title": "机器学习模型评估指标详解",
            "content": """
机器学习模型的评估是模型开发流程中的关键环节。

分类任务指标：
1. 准确率 (Accuracy)：正确预测的比例
   - 适用场景：类别均衡的数据集
   - 局限性：类别不平衡时误导性强

2. 精确率 (Precision)：预测为正的样本中实际为正的比例
   - 公式：TP / (TP + FP)
   - 适用场景：关注误报成本高的场景

3. 召回率 (Recall)：实际为正的样本中被正确预测的比例
   - 公式：TP / (TP + FN)
   - 适用场景：关注漏报成本高的场景

4. F1 分数：精确率和召回率的调和平均
   - 公式：2 * (Precision * Recall) / (Precision + Recall)
   - 适用场景：需要平衡精确率和召回率

5. ROC-AUC：ROC 曲线下的面积
   - 取值范围：0.5-1.0
   - 优势：不受分类阈值影响

回归任务指标：
- MAE (平均绝对误差)
- MSE (均方误差)
- R² (决定系数)

选择建议：
- 业务导向：根据业务需求选择指标
- 多指标结合：综合评估模型性能
- 交叉验证：确保评估结果稳定
            """,
            "tags": ["机器学习", "模型评估", "指标", "分类", "回归"],
            "source": "manual"
        },
        {
            "title": "Docker 容器化部署实战",
            "content": """
Docker 容器化技术简化了应用的打包和部署流程。

Dockerfile 编写最佳实践：

1. 使用官方基础镜像
FROM python:3.11-slim

2. 设置工作目录
WORKDIR /app

3. 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

4. 复制应用代码
COPY . .

5. 声明暴露端口
EXPOSE 8000

6. 定义启动命令
CMD ["python", "app.py"]

多阶段构建优化：
```dockerfile
# 构建阶段
FROM node:18 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# 生产阶段
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Docker Compose 配置：
```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://db:5432/myapp
    depends_on:
      - db
  
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secret
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

部署注意事项：
- 使用 .dockerignore 排除不必要文件
- 最小化镜像层数
- 使用非 root 用户运行容器
- 定期更新基础镜像
            """,
            "tags": ["Docker", "容器化", "部署", "DevOps", "最佳实践"],
            "source": "manual"
        },
        {
            "title": "数据库索引优化策略",
            "content": """
数据库索引是提升查询性能的关键技术。

索引类型：

1. B-Tree 索引
   - 默认索引类型
   - 适用场景：等值查询、范围查询
   - 时间复杂度：O(log n)

2. Hash 索引
   - 适用场景：精确匹配查询
   - 不支持范围查询
   - 时间复杂度：O(1)

3. 全文索引
   - 适用场景：文本搜索
   - 支持分词和相关性排序

4. 复合索引
   - 多列组合索引
   - 遵循最左前缀原则
   - 示例：(A, B, C) 可用于查询 A、(A,B)、(A,B,C)

索引优化策略：

1. 选择合适的列
   - 高频查询列
   - WHERE 条件列
   - JOIN 关联列
   - ORDER BY 排序列

2. 避免过度索引
   - 每个索引增加写入开销
   - 占用额外存储空间
   - 影响 UPDATE/DELETE 性能

3. 使用覆盖索引
   - 查询所需数据全部在索引中
   - 避免回表操作
   - 显著提升查询速度

4. 监控索引使用情况
   ```sql
   -- PostgreSQL 查看索引使用情况
   SELECT schemaname, tablename, indexname, idx_scan
   FROM pg_stat_user_indexes
   ORDER BY idx_scan;
   ```

5. 定期维护
   - 重建碎片化索引
   - 删除未使用索引
   - 更新统计信息

性能测试示例：
```sql
-- 创建索引前
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'test@example.com';
-- 扫描时间：500ms

-- 创建索引
CREATE INDEX idx_users_email ON users(email);

-- 创建索引后
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'test@example.com';
-- 扫描时间：2ms
```
            """,
            "tags": ["数据库", "索引", "性能优化", "SQL", "PostgreSQL"],
            "source": "manual"
        },
        {
            "title": "微服务架构设计模式",
            "content": """
微服务架构将应用拆分为多个独立部署的服务。

核心设计模式：

1. 服务发现 (Service Discovery)
   - 问题：服务实例动态变化
   - 方案：Consul、Eureka、Kubernetes DNS
   - 实现：客户端发现 vs 服务端发现

2. API 网关 (API Gateway)
   - 功能：路由、认证、限流、监控
   - 工具：Kong、Nginx、AWS API Gateway
   - 优势：统一入口、简化客户端

3. 断路器 (Circuit Breaker)
   - 问题：级联故障
   - 模式：Closed → Open → Half-Open
   - 工具：Hystrix、Resilience4j

4. 事件驱动架构 (Event-Driven)
   - 消息队列：Kafka、RabbitMQ
   - 优势：解耦、异步、可扩展
   - 挑战：消息顺序、重复消费

5. CQRS (命令查询职责分离)
   - 写操作：Command Model
   - 读操作：Query Model
   - 优势：独立优化、提高性能

6. Saga 模式
   - 问题：分布式事务
   - 方案：编排式 vs 协同式
   - 补偿机制：失败回滚

部署策略：

1. 蓝绿部署
   - 两个相同环境交替使用
   - 零停机部署
   - 快速回滚

2. 金丝雀发布
   - 逐步增加新版本流量
   - 监控指标验证
   - 降低风险

3. 滚动更新
   - 逐个实例更新
   - 保持服务可用
   - Kubernetes 默认策略

监控和可观测性：
- 指标 (Metrics)：Prometheus + Grafana
- 日志 (Logging)：ELK Stack
- 追踪 (Tracing)：Jaeger、Zipkin
            """,
            "tags": ["微服务", "架构设计", "分布式系统", "设计模式", "DevOps"],
            "source": "manual"
        }
    ]
    
    print(f"\n准备创建 {len(notes)} 条笔记...")
    
    for i, note in enumerate(notes, 1):
        print(f"\n  [{i}/{len(notes)}] 创建笔记: {note['title']}")
        
        try:
            # 生成唯一 ID
            note_id = f"note_{uuid.uuid4().hex[:12]}"
            collected_at = datetime.now().isoformat()
            
            # 创建知识项
            success = storage.add_knowledge(
                id=note_id,
                title=note["title"],
                content_type="note",
                source=note["source"],
                collected_at=collected_at,
                summary=note["content"][:200],
                word_count=len(note["content"])
            )
            
            if success:
                # 添加标签
                if note.get("tags"):
                    storage.add_tags(note_id, note["tags"])
                print(f"    ✓ 创建成功 (ID: {note_id})")
                print(f"    ✓ 标签: {', '.join(note['tags'])}")
            else:
                print(f"    ✗ 创建失败")
        except Exception as e:
            print(f"    ✗ 创建失败: {str(e)}")
    
    print(f"\n✓ 笔记数据生成完成")


def create_test_files(storage: SQLiteStorage, data_dir: Path):
    """创建测试文件数据"""
    print("\n" + "=" * 70)
    print("生成测试文件数据")
    print("=" * 70)
    
    # 创建测试文件目录
    files_dir = data_dir / "raw" / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    
    test_files = [
        {
            "filename": "machine-learning-basics.txt",
            "content": """机器学习基础概念

1. 监督学习 (Supervised Learning)
   - 有标签数据训练
   - 分类任务：垃圾邮件检测、图像识别
   - 回归任务：房价预测、股票预测
   - 常见算法：线性回归、决策树、SVM、神经网络

2. 无监督学习 (Unsupervised Learning)
   - 无标签数据训练
   - 聚类：K-Means、DBSCAN
   - 降维：PCA、t-SNE
   - 异常检测：孤立森林、One-Class SVM

3. 强化学习 (Reinforcement Learning)
   - 通过与环境交互学习
   - 奖励机制驱动
   - 应用：游戏 AI、机器人控制、自动驾驶

4. 深度学习 (Deep Learning)
   - 多层神经网络
   - CNN：图像处理
   - RNN/LSTM：序列数据
   - Transformer：NLP 任务

5. 模型训练流程
   - 数据收集和预处理
   - 特征工程
   - 模型选择和训练
   - 评估和调优
   - 部署和监控
            """,
            "tags": ["机器学习", "深度学习", "AI", "算法"]
        },
        {
            "filename": "web-development-trends.txt",
            "content": """2024 Web 开发趋势

前端技术：
- React 18+：并发特性、Server Components
- Vue 3：Composition API、性能优化
- Next.js/Remix：全栈框架
- TypeScript：类型安全成为标配
- WebAssembly：高性能计算

后端技术：
- Node.js：异步编程、微服务
- Python FastAPI：高性能 API
- Go：并发性能优异
- Rust：内存安全、高性能

架构模式：
- 边缘计算 (Edge Computing)
- Serverless 架构
- 微前端 (Micro-Frontends)
- Jamstack

开发工具：
- Vite：快速构建工具
- Turborepo：Monorepo 管理
- GitHub Copilot：AI 辅助编程
            """,
            "tags": ["Web开发", "前端", "后端", "技术趋势"]
        },
        {
            "filename": "data-structures-algorithms.txt",
            "content": """数据结构与算法核心知识点

基础数据结构：
1. 数组 (Array)
   - 连续内存存储
   - 随机访问 O(1)
   - 插入删除 O(n)

2. 链表 (Linked List)
   - 节点链接存储
   - 插入删除 O(1)
   - 随机访问 O(n)

3. 栈 (Stack)
   - LIFO 原则
   - 应用：函数调用、括号匹配

4. 队列 (Queue)
   - FIFO 原则
   - 应用：任务调度、BFS

5. 哈希表 (Hash Table)
   - 键值对存储
   - 平均查询 O(1)
   - 冲突解决：链地址法、开放地址法

高级数据结构：
- 树 (Tree)：二叉树、AVL、红黑树
- 图 (Graph)：邻接矩阵、邻接表
- 堆 (Heap)：优先队列实现

核心算法：
1. 排序算法
   - 快速排序：O(n log n)
   - 归并排序：O(n log n)
   - 堆排序：O(n log n)

2. 搜索算法
   - 二分查找：O(log n)
   - BFS：广度优先
   - DFS：深度优先

3. 动态规划
   - 重叠子问题
   - 最优子结构
   - 状态转移方程

4. 贪心算法
   - 局部最优选择
   - 不一定全局最优
            """,
            "tags": ["数据结构", "算法", "计算机科学", "编程基础"]
        }
    ]
    
    print(f"\n准备创建 {len(test_files)} 个测试文件...")
    
    for i, file_info in enumerate(test_files, 1):
        print(f"\n  [{i}/{len(test_files)}] 创建文件: {file_info['filename']}")
        
        try:
            # 写入文件
            file_path = files_dir / file_info['filename']
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_info['content'])
            
            # 生成唯一 ID
            file_id = f"file_{uuid.uuid4().hex[:12]}"
            collected_at = datetime.now().isoformat()
            
            # 记录到数据库
            success = storage.add_knowledge(
                id=file_id,
                title=file_info['filename'],
                content_type="file",
                source=str(file_path),
                collected_at=collected_at,
                summary=file_info['content'][:200],
                word_count=len(file_info['content']),
                file_path=str(file_path)
            )
            
            if success:
                # 添加标签
                if file_info.get('tags'):
                    storage.add_tags(file_id, file_info['tags'])
                print(f"    ✓ 文件创建成功 (ID: {file_id})")
                print(f"    ✓ 路径: {file_path}")
                print(f"    ✓ 标签: {', '.join(file_info['tags'])}")
            else:
                print(f"    ✗ 创建失败")
        except Exception as e:
            print(f"    ✗ 创建失败: {str(e)}")
    
    print(f"\n✓ 文件数据生成完成")


def create_test_urls(storage: SQLiteStorage):
    """创建测试 URL 数据"""
    print("\n" + "=" * 70)
    print("生成测试 URL 数据")
    print("=" * 70)
    
    urls = [
        {
            "url": "https://docs.python.org/3/library/asyncio.html",
            "title": "Python Asyncio 官方文档",
            "tags": ["Python", "异步编程", "官方文档"]
        },
        {
            "url": "https://scikit-learn.org/stable/user_guide.html",
            "title": "Scikit-learn 用户指南",
            "tags": ["机器学习", "Python", "教程"]
        },
        {
            "url": "https://kubernetes.io/docs/concepts/",
            "title": "Kubernetes 核心概念",
            "tags": ["Kubernetes", "容器编排", "云原生"]
        },
        {
            "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
            "title": "MDN JavaScript 文档",
            "tags": ["JavaScript", "Web开发", "参考文档"]
        },
        {
            "url": "https://www.postgresql.org/docs/current/indexes.html",
            "title": "PostgreSQL 索引文档",
            "tags": ["PostgreSQL", "数据库", "性能优化"]
        }
    ]
    
    print(f"\n准备创建 {len(urls)} 个 URL 记录...")
    
    for i, url_info in enumerate(urls, 1):
        print(f"\n  [{i}/{len(urls)}] 创建 URL: {url_info['title']}")
        
        try:
            # 生成唯一 ID
            url_id = f"url_{uuid.uuid4().hex[:12]}"
            collected_at = datetime.now().isoformat()
            
            success = storage.add_knowledge(
                id=url_id,
                title=url_info['title'],
                content_type="url",
                source=url_info['url'],
                collected_at=collected_at
            )
            
            if success:
                # 添加标签
                if url_info.get('tags'):
                    storage.add_tags(url_id, url_info['tags'])
                print(f"    ✓ 创建成功 (ID: {url_id})")
                print(f"    ✓ URL: {url_info['url']}")
                print(f"    ✓ 标签: {', '.join(url_info['tags'])}")
            else:
                print(f"    ✗ 创建失败")
        except Exception as e:
            print(f"    ✗ 创建失败: {str(e)}")
    
    print(f"\n✓ URL 数据生成完成")


def create_test_bookmarks(storage: SQLiteStorage):
    """创建测试书签数据"""
    print("\n" + "=" * 70)
    print("生成测试书签数据")
    print("=" * 70)
    
    bookmarks = [
        {
            "title": "GitHub - 代码托管平台",
            "url": "https://github.com",
            "tags": ["开发工具", "代码管理", "协作"]
        },
        {
            "title": "Stack Overflow - 技术问答",
            "url": "https://stackoverflow.com",
            "tags": ["技术社区", "问答", "编程"]
        },
        {
            "title": "Medium - 技术博客",
            "url": "https://medium.com",
            "tags": ["技术博客", "文章", "学习"]
        },
        {
            "title": "Hacker News - 科技新闻",
            "url": "https://news.ycombinator.com",
            "tags": ["科技新闻", "创业", "技术趋势"]
        }
    ]
    
    print(f"\n准备创建 {len(bookmarks)} 个书签...")
    
    for i, bookmark in enumerate(bookmarks, 1):
        print(f"\n  [{i}/{len(bookmarks)}] 创建书签: {bookmark['title']}")
        
        try:
            # 生成唯一 ID
            bookmark_id = f"bookmark_{uuid.uuid4().hex[:12]}"
            collected_at = datetime.now().isoformat()
            
            success = storage.add_knowledge(
                id=bookmark_id,
                title=bookmark['title'],
                content_type="bookmark",
                source=bookmark['url'],
                collected_at=collected_at
            )
            
            if success:
                # 添加标签
                if bookmark.get('tags'):
                    storage.add_tags(bookmark_id, bookmark['tags'])
                print(f"    ✓ 创建成功 (ID: {bookmark_id})")
                print(f"    ✓ 标签: {', '.join(bookmark['tags'])}")
            else:
                print(f"    ✗ 创建失败")
        except Exception as e:
            print(f"    ✗ 创建失败: {str(e)}")
    
    print(f"\n✓ 书签数据生成完成")


def print_statistics(storage: SQLiteStorage):
    """打印数据统计"""
    print("\n" + "=" * 70)
    print("数据统计")
    print("=" * 70)
    
    try:
        # 统计各类型文档数量
        content_types = ["note", "file", "url", "bookmark", "paper", "email"]
        print(f"\n  文档统计:")
        
        total = 0
        for ctype in content_types:
            count = storage.count_knowledge(content_type=ctype)
            if count > 0:
                print(f"    {ctype:12s}: {count}")
                total += count
        
        print(f"    {'总计':12s}: {total}")
        
        # 获取热门标签
        tags = storage.list_tags(limit=10)
        if tags:
            print(f"\n  热门标签 (Top 10):")
            for tag in tags:
                print(f"    - {tag}")
    except Exception as e:
        print(f"\n✗ 获取统计信息失败: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("知识库测试数据生成器")
    print("=" * 70)
    
    # 检查环境变量
    if not os.getenv("DASHSCOPE_API_KEY"):
        print("\n✗ 错误: 未设置 DASHSCOPE_API_KEY 环境变量")
        sys.exit(1)
    
    # 初始化配置和存储
    config = Config()
    data_dir = config.data_dir
    
    # 确保数据目录存在
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "metadata.db"
    
    print(f"\n数据目录: {data_dir}")
    print(f"数据库路径: {db_path}")
    
    # 创建存储实例
    storage = SQLiteStorage(db_path=str(db_path))
    
    # 生成测试数据
    try:
        create_test_notes(storage)
        create_test_files(storage, data_dir)
        create_test_urls(storage)
        create_test_bookmarks(storage)
        
        # 打印统计信息
        print_statistics(storage)
        
        print("\n" + "=" * 70)
        print("✓ 所有测试数据生成完成！")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ 测试数据生成失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
