"""
清理URL数据并添加Webpage测试数据脚本

功能：
1. 清理所有历史URL类型的知识项
2. 添加多样化的Webpage测试数据
3. 自动提取标签和向量化处理

使用方法：
    python tests/cleanup_and_add_webpage_data.py
"""

import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kb.config import Config
from kb.storage.sqlite_storage import SQLiteStorage
from kb.storage.chroma_storage import ChromaStorage
from kb.processors.chunker import Chunker
from kb.processors.embedder import Embedder
from kb.processors.tag_extractor import TagExtractor

logger = logging.getLogger(__name__)


def cleanup_url_data(storage: SQLiteStorage) -> int:
    """清理所有URL类型的知识项"""
    print("=" * 70)
    print("步骤 1: 清理历史URL数据")
    print("=" * 70)
    
    # 获取所有URL类型的知识项
    url_items = storage.list_knowledge(content_type="url", limit=10000)
    
    if not url_items:
        print("\n✓ 没有找到URL类型的知识项，无需清理")
        return 0
    
    print(f"\n找到 {len(url_items)} 条URL数据，开始清理...")
    
    deleted_count = 0
    for item in url_items:
        item_id = item['id']
        title = item['title']
        
        if storage.delete_knowledge(item_id):
            deleted_count += 1
            print(f"  ✓ 已删除: {title}")
        else:
            print(f"  ✗ 删除失败: {title}")
    
    print(f"\n✓ 清理完成，共删除 {deleted_count} 条URL数据")
    return deleted_count


def add_webpage_data(storage: SQLiteStorage) -> list:
    """添加Webpage测试数据"""
    print("\n" + "=" * 70)
    print("步骤 2: 添加Webpage测试数据")
    print("=" * 70)
    
    # 定义Webpage测试数据
    webpage_items = [
        {
            "title": "深度学习中的注意力机制详解",
            "url": "https://example.com/attention-mechanism",
            "content": """注意力机制（Attention Mechanism）是深度学习领域的重要突破，
最初在机器翻译任务中提出。其核心思想是让模型在处理序列数据时，
能够动态地关注输入序列的不同部分。

自注意力（Self-Attention）机制允许序列中的每个位置关注序列中的所有位置，
从而捕获长距离依赖关系。多头注意力（Multi-Head Attention）通过并行计算
多个注意力头，使模型能够从不同的表示子空间中学习信息。

Transformer架构完全基于注意力机制，摒弃了传统的RNN和CNN结构，
在自然语言处理、计算机视觉等多个领域取得了突破性进展。
BERT、GPT等预训练模型都采用了自注意力机制作为核心组件。""",
            "tags": ["深度学习", "注意力机制", "Transformer", "NLP", "神经网络"]
        },
        {
            "title": "向量数据库技术对比与选型指南",
            "url": "https://example.com/vector-database-comparison",
            "content": """向量数据库是AI应用的核心基础设施，用于存储和检索高维向量数据。

主流向量数据库对比：

1. Chroma：轻量级开源向量数据库，适合本地开发和小规模应用。
   支持持久化存储和语义搜索，API简洁易用。

2. Milvus：企业级分布式向量数据库，支持大规模数据和高并发查询。
   提供多种索引类型（HNSW、IVF、PQ等），适合生产环境。

3. Pinecone：托管式向量数据库服务，无需运维，自动扩缩容。
   适合快速原型开发和中小规模应用。

4. Weaviate：支持混合搜索（向量+关键词），内置模块化架构。
   提供GraphQL API和丰富的插件生态。

选型建议：
- 小规模/本地开发：Chroma
- 大规模/生产环境：Milvus
- 快速原型/云服务：Pinecone
- 混合搜索需求：Weaviate""",
            "tags": ["向量数据库", "Chroma", "Milvus", "AI基础设施", "技术选型"]
        },
        {
            "title": "Python异步编程最佳实践",
            "url": "https://example.com/python-async-best-practices",
            "content": """Python的asyncio库提供了强大的异步编程能力，
特别适合I/O密集型应用，如Web爬虫、API调用和数据库操作。

核心概念：
- async/await：定义和调用异步函数
- asyncio.run()：运行异步程序的主入口
- asyncio.gather()：并发执行多个协程
- asyncio.create_task()：创建后台任务

最佳实践：
1. 使用async with管理异步资源
2. 避免阻塞调用，使用aiohttp替代requests
3. 合理使用信号量控制并发数量
4. 使用asyncio.TimeoutError处理超时
5. 在CPU密集型任务中使用ProcessPoolExecutor

性能优化：
- 批量处理减少I/O次数
- 使用连接池复用连接
- 合理设置超时时间
- 监控异步任务执行情况""",
            "tags": ["Python", "异步编程", "asyncio", "性能优化", "最佳实践"]
        },
        {
            "title": "Kubernetes容器编排入门教程",
            "url": "https://example.com/kubernetes-tutorial",
            "content": """Kubernetes（K8s）是开源的容器编排平台，用于自动化部署、
扩缩容和管理容器化应用。

核心概念：
- Pod：最小部署单元，包含一个或多个容器
- Deployment：管理Pod的创建和更新
- Service：提供稳定的网络访问入口
- Namespace：资源隔离和分组
- ConfigMap/Secret：配置管理

基本操作：
1. 部署应用：kubectl apply -f deployment.yaml
2. 查看状态：kubectl get pods
3. 扩缩容：kubectl scale deployment --replicas=3
4. 查看日志：kubectl logs <pod-name>
5. 进入容器：kubectl exec -it <pod-name> -- /bin/bash

架构组件：
- API Server：集群控制平面入口
- etcd：分布式键值存储
- Scheduler：Pod调度器
- Controller Manager：控制器管理
- kubelet：节点代理
- kube-proxy：网络代理""",
            "tags": ["Kubernetes", "容器编排", "Docker", "云原生", "DevOps"]
        },
        {
            "title": "RAG检索增强生成技术原理",
            "url": "https://example.com/rag-technology",
            "content": """RAG（Retrieval-Augmented Generation）检索增强生成是一种
结合信息检索和文本生成的技术架构，有效解决了大语言模型的幻觉问题。

工作流程：
1. 文档处理：将知识库文档分块并向量化
2. 检索阶段：根据用户查询检索相关文档片段
3. 增强提示：将检索结果作为上下文添加到prompt中
4. 生成阶段：LLM基于增强后的提示生成回答

核心优势：
- 减少幻觉：基于真实文档生成回答
- 知识更新：无需重新训练模型即可更新知识
- 可追溯性：可以引用信息来源
- 成本效益：避免频繁微调大模型

技术组件：
- 向量数据库：存储和检索文档向量
- Embedding模型：文本向量化
- LLM：文本生成
- Reranker：重排序提高检索精度

应用场景：
- 企业知识库问答
- 技术文档助手
- 客服智能问答
- 学术研究辅助""",
            "tags": ["RAG", "大语言模型", "检索增强", "AI应用", "知识问答"]
        },
        {
            "title": "微服务架构设计模式总结",
            "url": "https://example.com/microservices-patterns",
            "content": """微服务架构将单体应用拆分为多个独立部署的服务，
每个服务负责特定的业务功能。

常见设计模式：

1. 服务拆分模式
   - 按业务能力拆分
   - 按子域拆分（DDD）
   -  strangler fig模式（渐进式迁移）

2. 数据管理模式
   - Database per Service
   - Saga模式（分布式事务）
   - CQRS（命令查询职责分离）
   - Event Sourcing（事件溯源）

3. 通信模式
   - 同步：REST、gRPC
   - 异步：消息队列（Kafka、RabbitMQ）
   - API Gateway：统一入口

4. 部署模式
   - 容器化部署（Docker）
   - 服务网格（Istio）
   - 蓝绿部署、金丝雀发布

5. 可观测性
   - 分布式追踪（Jaeger、Zipkin）
   - 指标监控（Prometheus）
   - 日志聚合（ELK）

挑战与解决方案：
- 分布式事务：Saga、2PC
- 服务发现：Consul、Eureka
- 负载均衡：客户端/服务端负载均衡
- 容错处理：熔断器、重试、降级""",
            "tags": ["微服务", "架构设计", "分布式系统", "设计模式", "软件工程"]
        },
        {
            "title": "数据湖与数据仓库架构对比",
            "url": "https://example.com/data-lake-vs-warehouse",
            "content": """数据湖（Data Lake）和数据仓库（Data Warehouse）是两种
不同的数据存储和处理架构，各有适用场景。

数据仓库特点：
- 结构化数据：Schema-on-Write
- 高度优化：针对SQL查询优化
- 数据质量：严格的数据治理
- 适用场景：BI报表、OLAP分析
- 技术栈：Snowflake、Redshift、BigQuery

数据湖特点：
- 原始数据：Schema-on-Read
- 灵活存储：支持结构化、半结构化、非结构化数据
- 低成本：使用对象存储（S3、OSS）
- 适用场景：机器学习、数据探索
- 技术栈：Hadoop、Spark、Delta Lake

Lakehouse架构：
结合数据湖和数据仓库的优势，提供：
- 统一存储：低成本对象存储
- ACID事务：数据一致性保证
- 多引擎支持：SQL、Spark、ML
- 开放格式：Parquet、ORC

选型建议：
- 传统BI分析：数据仓库
- 大数据处理：数据湖
- 统一平台：Lakehouse
- 实时分析：流处理+数据湖""",
            "tags": ["数据湖", "数据仓库", "Lakehouse", "大数据", "数据架构"]
        },
        {
            "title": "大语言模型微调技术详解",
            "url": "https://example.com/llm-finetuning",
            "content": """大语言模型（LLM）微调是让预训练模型适应特定任务的关键技术。

微调方法分类：

1. 全参数微调（Full Fine-tuning）
   - 更新模型所有参数
   - 效果最好但成本最高
   - 需要大量计算资源和数据

2. 参数高效微调（PEFT）
   - LoRA（Low-Rank Adaptation）：低秩矩阵适配
   - QLoRA：量化+LoRA，大幅降低显存需求
   - Adapter：插入小型适配层
   - Prefix Tuning：优化前缀向量

3. 指令微调（Instruction Tuning）
   - 使用指令-响应对训练
   - 提升模型遵循指令能力
   - Alpaca、Vicuna等模型采用此方法

4. 人类反馈强化学习（RLHF）
   - 收集人类偏好数据
   - 训练奖励模型
   - 使用PPO算法优化模型

实践建议：
- 小数据集：优先使用LoRA/QLoRA
- 特定领域：指令微调+领域数据
- 对话场景：RLHF提升安全性
- 资源有限：量化+PEFT组合""",
            "tags": ["大语言模型", "模型微调", "LoRA", "RLHF", "AI训练"]
        },
        {
            "title": "GraphQL API设计与最佳实践",
            "url": "https://example.com/graphql-best-practices",
            "content": """GraphQL是一种用于API的查询语言，相比REST提供更灵活的数据获取方式。

核心优势：
- 精确查询：客户端指定需要的字段
- 单次请求：获取多个资源的数据
- 强类型：Schema定义数据结构
- 内省：自动文档生成

设计原则：

1. Schema设计
   - 使用清晰的命名约定
   - 合理组织Type和Query
   - 使用枚举和联合类型
   - 添加详细的字段描述

2. 查询优化
   - 避免N+1查询问题
   - 使用DataLoader批量加载
   - 实现查询复杂度限制
   - 缓存频繁查询结果

3. 错误处理
   - 使用标准错误格式
   - 提供详细的错误信息
   - 区分客户端和服务器错误
   - 实现错误追踪

4. 安全性
   - 身份验证和授权
   - 查询深度限制
   - 速率限制
   - 输入验证

工具推荐：
- Apollo Server：Node.js实现
- Graphene：Python实现
- GraphQL Playground：调试工具
- Apollo Client：前端客户端""",
            "tags": ["GraphQL", "API设计", "Web开发", "后端开发", "最佳实践"]
        },
        {
            "title": "Redis缓存策略与性能优化",
            "url": "https://example.com/redis-caching-strategies",
            "content": """Redis是高性能的内存数据存储，广泛用于缓存、会话管理和消息队列。

缓存策略：

1. Cache-Aside（旁路缓存）
   - 应用先查缓存，未命中再查数据库
   - 更新时同时更新缓存和数据库
   - 最常用的缓存模式

2. Read-Through（读穿透）
   - 缓存层负责从数据库加载数据
   - 应用只与缓存交互
   - 简化应用逻辑

3. Write-Through（写穿透）
   - 写入时同时更新缓存和数据库
   - 保证数据一致性
   - 写入性能较低

4. Write-Behind（异步写入）
   - 先写缓存，异步写入数据库
   - 提高写入性能
   - 可能丢失数据

性能优化：

1. 数据结构选择
   - String：简单键值对
   - Hash：对象存储
   - List：队列实现
   - Set/ZSet：去重和排序

2. 内存管理
   - 设置合理的maxmemory
   - 选择合适的淘汰策略
   - 使用压缩列表优化小对象

3. 持久化配置
   - RDB：定期快照，恢复快
   - AOF：记录命令，数据更安全
   - 混合模式：兼顾性能和安全性

4. 集群部署
   - 主从复制：读写分离
   - 哨兵模式：高可用
   - Cluster模式：分布式扩展""",
            "tags": ["Redis", "缓存", "性能优化", "数据库", "架构设计"]
        },
        {
            "title": "Docker容器化部署实战指南",
            "url": "https://example.com/docker-deployment-guide",
            "content": """Docker容器化技术使应用打包、分发和部署更加标准化和可重复。

核心概念：

1. 镜像（Image）
   - 只读模板，包含应用和依赖
   - 基于Dockerfile构建
   - 分层存储，共享基础层

2. 容器（Container）
   - 镜像的运行实例
   - 隔离的运行环境
   - 轻量级，启动快速

3. 数据卷（Volume）
   - 持久化数据存储
   - 容器间共享数据
   - 独立于容器生命周期

Dockerfile最佳实践：

1. 选择合适的基础镜像
   - 使用官方镜像
   - 选择alpine版本减小体积
   - 固定版本号保证可重复性

2. 优化构建层
   - 合并RUN命令减少层数
   - 将不常变化的指令放前面
   - 使用多阶段构建减小最终镜像

3. 安全最佳实践
   - 使用非root用户运行
   - 扫描镜像漏洞
   - 最小化安装依赖

Docker Compose：
- 定义多容器应用
- 管理容器网络和卷
- 简化开发环境配置

部署流程：
1. 编写Dockerfile
2. 构建镜像：docker build
3. 推送镜像：docker push
4. 拉取运行：docker run
5. 使用Compose编排多服务""",
            "tags": ["Docker", "容器化", "DevOps", "部署", "微服务"]
        },
        {
            "title": "CI/CD流水线设计与实现",
            "url": "https://example.com/cicd-pipeline-design",
            "content": """CI/CD（持续集成/持续交付）是现代软件开发的核心实践，
自动化构建、测试和部署流程。

持续集成（CI）：

1. 代码提交触发
   - Git hook自动触发构建
   - 代码静态分析（Lint）
   - 单元测试执行
   - 代码覆盖率检查

2. 构建流程
   - 依赖安装
   - 代码编译
   - 打包构建
   - 制品存储

3. 质量门禁
   - 测试通过率要求
   - 代码覆盖率阈值
   - 安全扫描通过
   - 代码审查通过

持续交付（CD）：

1. 环境管理
   - 开发环境
   - 测试环境
   - 预发布环境
   - 生产环境

2. 部署策略
   - 蓝绿部署：零停机切换
   - 金丝雀发布：逐步放量
   - 滚动更新：逐个替换
   - A/B测试：对比验证

3. 回滚机制
   - 自动化回滚
   - 快速恢复服务
   - 保留历史版本

工具链：
- Jenkins：经典CI/CD工具
- GitLab CI：集成在GitLab中
- GitHub Actions：GitHub原生
- ArgoCD：Kubernetes原生CD
- Tekton：云原生CI/CD框架

最佳实践：
- 一切代码化（Infrastructure as Code）
- 快速反馈循环
- 自动化测试覆盖
- 监控和日志集成""",
            "tags": ["CI/CD", "DevOps", "自动化", "部署", "软件工程"]
        },
        {
            "title": "PostgreSQL高级特性与性能调优",
            "url": "https://example.com/postgresql-advanced-features",
            "content": """PostgreSQL是功能强大的开源关系型数据库，支持丰富的数据类型和高级特性。

高级特性：

1. JSON/JSONB支持
   - 存储半结构化数据
   - JSONB提供索引支持
   - 丰富的JSON操作符

2. 全文搜索
   - 内置全文搜索功能
   - 支持中文分词
   - 排名和相关性计算

3. 窗口函数
   - ROW_NUMBER()：行号
   - RANK()：排名
   - LAG()/LEAD()：前后行访问
   - 聚合函数over子句

4. 分区表
   - 按范围分区
   - 按列表分区
   - 按哈希分区
   - 自动分区管理

性能调优：

1. 索引优化
   - B-Tree：默认索引类型
   - GIN：全文搜索和JSON
   - GiST：地理空间数据
   - BRIN：大数据范围查询

2. 查询优化
   - EXPLAIN分析执行计划
   - 避免全表扫描
   - 合理使用JOIN
   - 子查询优化

3. 配置调优
   - shared_buffers：共享内存
   - work_mem：排序和哈希内存
   - effective_cache_size：缓存估计
   - max_connections：连接数限制

4. 维护优化
   - VACUUM：清理死元组
   - ANALYZE：更新统计信息
   - REINDEX：重建索引
   - 定期维护计划""",
            "tags": ["PostgreSQL", "数据库", "性能优化", "SQL", "索引"]
        }
    ]
    
    print(f"\n准备添加 {len(webpage_items)} 条Webpage数据...")
    
    added_items = []
    for i, item in enumerate(webpage_items, 1):
        print(f"\n[{i}/{len(webpage_items)}] 处理: {item['title']}")
        
        # 生成唯一ID
        webpage_id = f"webpage_{uuid.uuid4().hex[:12]}"
        collected_at = datetime.now().isoformat()
        
        # 添加到SQLite
        success = storage.add_knowledge(
            id=webpage_id,
            title=item['title'],
            content_type="webpage",
            source=item['url'],
            collected_at=collected_at,
            summary=item['content'][:200],
            word_count=len(item['content'])
        )
        
        if success:
            # 添加标签
            if item.get('tags'):
                storage.add_tags(webpage_id, item['tags'])
            
            added_items.append({
                'id': webpage_id,
                'title': item['title'],
                'content': item['content'],
                'url': item['url']
            })
            
            print(f"  ✓ 已添加知识项")
            print(f"  ✓ 标签: {', '.join(item['tags'])}")
        else:
            print(f"  ✗ 添加失败")
    
    print(f"\n✓ 成功添加 {len(added_items)} 条Webpage数据")
    return added_items


def process_webpage_chunks(added_items: list, storage: SQLiteStorage, chroma_storage: ChromaStorage):
    """处理Webpage内容为分块和向量"""
    print("\n" + "=" * 70)
    print("步骤 3: 处理Webpage内容为分块和向量")
    print("=" * 70)
    
    config = Config()
    chunker = Chunker.from_config(config)
    
    # 初始化 embedder，带优雅降级处理
    embedder = None
    try:
        embedder = Embedder.from_config(config)
    except ValueError as e:
        logger.warning(f"Embedder initialization skipped (configuration error): {e}")
        print(f"\n⚠️ 警告: 向量生成器初始化失败 (配置错误): {e}")
        print("  将继续处理，但跳过向量化步骤。")
    except Exception as e:
        logger.warning(f"Embedder initialization failed: {e}. Processing will continue without vectorization.")
        print(f"\n⚠️ 警告: 向量生成器初始化失败: {e}")
        print("  将继续处理，但跳过向量化步骤。")
    
    total_chunks = 0
    vectorized_count = 0
    
    for i, item in enumerate(added_items, 1):
        print(f"\n[{i}/{len(added_items)}] 处理: {item['title']}")
        
        try:
            # 分块
            result = chunker.process(item['content'])
            chunks = result.data
            
            if not chunks:
                print(f"  ⚠ 未生成分块，跳过")
                continue
            
            print(f"  ✓ 生成分块: {len(chunks)}")
            total_chunks += len(chunks)
            
            # 提取文本
            texts = [chunk.get('content', '') if isinstance(chunk, dict) else str(chunk) for chunk in chunks]
            
            # 向量化（如果 embedder 可用）
            if embedder is not None:
                try:
                    embeddings = embedder.embed(texts)
                    
                    # 生成chunk IDs
                    chunk_ids = [f"{item['id']}_chunk_{j}" for j in range(len(chunks))]
                    
                    # 构建元数据
                    metadatas = [
                        {
                            'knowledge_id': item['id'],
                            'chunk_index': j,
                            'title': item['title'],
                            'url': item['url']
                        }
                        for j in range(len(chunks))
                    ]
                    
                    # 存储到ChromaDB
                    chroma_storage.add_documents(
                        ids=chunk_ids,
                        embeddings=embeddings,
                        documents=texts,
                        metadatas=metadatas
                    )
                    
                    vectorized_count += len(chunks)
                    print(f"  ✓ 向量维度: {len(embeddings[0])}")
                except ValueError as e:
                    logger.warning(f"Vectorization skipped for '{item['title']}' (configuration error): {e}")
                    print(f"  ⚠️ 警告: 向量化跳过 (配置错误): {e}")
                except Exception as e:
                    logger.warning(f"Vectorization failed for '{item['title']}': {e}. Document chunks saved but not searchable via semantic search.")
                    print(f"  ⚠️ 警告: 向量化失败: {e}")
                    print(f"     文档已分块但未生成向量，仅支持关键词搜索。")
            else:
                print(f"  ⚠️ 跳过向量化: 向量生成器未初始化")
                print(f"     文档已分块但未生成向量，仅支持关键词搜索。")
            
        except Exception as e:
            print(f"  ✗ 处理失败: {str(e)}")
    
    print(f"\n✓ 总分块数: {total_chunks}")
    if embedder is not None:
        print(f"✓ 成功向量化: {vectorized_count} 个分块")
    else:
        print(f"⚠️ 未生成向量（向量生成器未初始化）")


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("清理URL数据并添加Webpage测试数据")
    print("=" * 70)
    
    # 初始化存储
    config = Config()
    storage = SQLiteStorage()
    
    # 从配置获取ChromaDB路径
    chroma_path = config.get("chroma.path", "~/knowledge-base/chroma")
    chroma_storage = ChromaStorage(path=chroma_path)
    
    # 步骤1: 清理URL数据
    deleted_count = cleanup_url_data(storage)
    
    # 步骤2: 添加Webpage数据
    added_items = add_webpage_data(storage)
    
    # 步骤3: 处理分块和向量
    if added_items:
        process_webpage_chunks(added_items, storage, chroma_storage)
    
    # 显示最终统计
    print("\n" + "=" * 70)
    print("最终统计")
    print("=" * 70)
    
    stats = storage.get_stats()
    print(f"\n知识项统计:")
    print(f"  总知识项数: {stats['total_items']}")
    print(f"  按类型分布:")
    for content_type, count in stats['items_by_type'].items():
        print(f"    - {content_type}: {count}")
    print(f"  总标签数: {stats['total_tags']}")
    print(f"  总分块数: {stats['total_chunks']}")
    
    print(f"\nChromaDB统计:")
    chroma_count = chroma_storage.count()
    print(f"  向量总数: {chroma_count}")
    
    print("\n✓ 所有操作完成！")


if __name__ == "__main__":
    main()

