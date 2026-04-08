"""
向量化和智能标签提取功能测试

测试知识库系统的核心功能：
1. 文本向量化 (Embedding)
2. 智能标签提取 (Tag Extraction)

使用方法：
    python tests/test_vectorization_and_tagging.py
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kb.config import Config
from kb.processors.embedder import Embedder
from kb.processors.tag_extractor import TagExtractor


def test_vectorization():
    """测试文本向量化功能"""
    print("=" * 70)
    print("测试 1: 文本向量化功能")
    print("=" * 70)
    
    config = Config()
    
    # 创建 Embedder
    print("\n[步骤 1] 初始化向量化引擎...")
    embedder = Embedder.from_config(config)
    print(f"  ✓ 模型: text-embedding-v4")
    print(f"  ✓ 向量维度: {embedder.dimension}")
    
    # 测试文档向量化
    print("\n[步骤 2] 测试文档向量化...")
    documents = [
        "机器学习是人工智能的核心技术，通过算法从数据中学习模式",
        "深度学习使用多层神经网络进行特征提取和表示学习",
        "自然语言处理让计算机理解和生成人类语言",
        "计算机视觉使机器能够识别和理解图像内容",
        "强化学习通过试错和奖励机制训练智能体"
    ]
    
    print(f"  输入文档数量: {len(documents)}")
    for i, doc in enumerate(documents, 1):
        print(f"  文档{i}: {doc[:30]}...")
    
    # 执行向量化
    embeddings = embedder.embed(documents)
    print(f"\n  ✓ 向量化完成")
    print(f"  ✓ 生成向量数量: {len(embeddings)}")
    print(f"  ✓ 每个向量维度: {len(embeddings[0])}")
    
    # 验证结果
    assert len(embeddings) == len(documents), "向量数量应该等于文档数量"
    assert all(len(emb) == embedder.dimension for emb in embeddings), "所有向量维度应该一致"
    
    # 计算文档相似度矩阵
    print("\n[步骤 3] 计算文档相似度矩阵...")
    
    def cosine_similarity(v1, v2):
        """计算余弦相似度"""
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(b * b for b in v2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)
    
    print("\n  文档相似度矩阵:")
    print("  " + " " * 12, end="")
    for i in range(len(documents)):
        print(f"Doc{i+1:2d}  ", end="")
    print()
    
    for i in range(len(documents)):
        print(f"  Doc{i+1:2d}  ", end="")
        for j in range(len(documents)):
            sim = cosine_similarity(embeddings[i], embeddings[j])
            print(f"{sim:5.2f} ", end="")
        print()
    
    # 语义搜索测试
    print("\n[步骤 4] 测试语义搜索...")
    query = "神经网络和深度学习"
    query_embedding = embedder.embed([query])[0]
    
    similarities = []
    for i, doc_emb in enumerate(embeddings):
        sim = cosine_similarity(query_embedding, doc_emb)
        similarities.append((i, sim, documents[i]))
    
    # 按相似度排序
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    print(f"  查询: {query}")
    print(f"\n  搜索结果 (按相关性排序):")
    for rank, (idx, sim, doc) in enumerate(similarities[:3], 1):
        print(f"  {rank}. 相似度: {sim:.4f}")
        print(f"     文档: {doc}")
    
    # 验证语义搜索准确性
    assert similarities[0][0] == 1, "最相关的应该是深度学习文档"
    assert similarities[0][1] > 0.5, "最相关文档相似度应该大于0.5"
    
    print("\n✓ 向量化功能测试通过！")


def test_tag_extraction():
    """测试智能标签提取功能"""
    print("\n" + "=" * 70)
    print("测试 2: 智能标签提取功能")
    print("=" * 70)
    
    config = Config()
    
    # 创建 TagExtractor
    print("\n[步骤 1] 初始化标签提取引擎...")
    extractor = TagExtractor.from_config(config)
    print(f"  ✓ 模型: qwen-plus")
    print(f"  ✓ 标签数量范围: {extractor.min_tags}-{extractor.max_tags}")
    
    # 测试不同主题的文档
    test_cases = [
        {
            "title": "Python Web 开发框架对比",
            "content": """
            Django、Flask 和 FastAPI 是 Python 生态中最流行的三个 Web 框架。
            Django 是一个全功能框架，提供 ORM、Admin 后台、认证系统等完整解决方案。
            Flask 是微框架，轻量灵活，适合小型项目和微服务。
            FastAPI 基于异步编程，性能优异，自动生成交互式 API 文档。
            选择框架时应根据项目规模、性能需求和团队技术栈综合考虑。
            """
        },
        {
            "title": "数据仓库与数据湖架构设计",
            "content": """
            数据仓库采用结构化存储，支持复杂的 SQL 查询和 BI 分析。
            数据湖则采用原始数据湖格式，支持结构化、半结构化和非结构化数据。
            现代数据架构通常结合两者，形成 Lakehouse 架构。
            Apache Spark、Presto、Delta Lake 等技术在此架构中发挥关键作用。
            数据治理、元数据管理和数据质量是架构成功的关键因素。
            """
        },
        {
            "title": "云原生微服务部署实践",
            "content": """
            Kubernetes 是云原生应用编排的事实标准，提供容器管理、服务发现和自动扩缩容。
            Docker 容器化技术使应用打包和部署更加一致和可重复。
            Istio 服务网格提供流量管理、安全策略和可观测性。
            CI/CD 流水线通过 GitOps 实现自动化部署和回滚。
            监控体系包括 Prometheus、Grafana 和分布式追踪系统。
            """
        }
    ]
    
    # 执行标签提取
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[步骤 {i+1}] 测试文档 {i}: {test_case['title']}")
        print(f"  内容预览: {test_case['content'][:50].strip()}...")
        
        result = extractor.process(
            title=test_case['title'],
            content=test_case['content'],
            temperature=0.3
        )
        
        assert result.success, f"标签提取应该成功: {result.error}"
        tags = result.data
        
        print(f"  ✓ 标签提取成功")
        print(f"  ✓ 标签数量: {result.metadata.get('tag_count', 0)}")
        print(f"  ✓ 标签列表: {', '.join(tags)}")
        
        # 验证标签质量
        assert extractor.min_tags <= len(tags) <= extractor.max_tags, \
            f"标签数量应该在{extractor.min_tags}-{extractor.max_tags}范围内"
        assert all(len(tag) >= 2 for tag in tags), "所有标签长度应该>=2"
        assert len(tags) == len(set(tags)), "标签不应该重复"
        
        print(f"  ✓ 质量检查通过: 数量、长度、无重复")
    
    print("\n✓ 智能标签提取功能测试通过！")


def test_combined_workflow():
    """测试向量化和标签提取的组合工作流"""
    print("\n" + "=" * 70)
    print("测试 3: 向量化 + 标签提取组合工作流")
    print("=" * 70)
    
    config = Config()
    
    # 初始化引擎
    print("\n[步骤 1] 初始化处理引擎...")
    embedder = Embedder.from_config(config)
    extractor = TagExtractor.from_config(config)
    print(f"  ✓ Embedder: text-embedding-v4 ({embedder.dimension}维)")
    print(f"  ✓ TagExtractor: qwen-plus")
    
    # 模拟知识库入库流程
    print("\n[步骤 2] 模拟知识库入库流程...")
    
    knowledge_items = [
        {
            "title": "Transformer 架构详解",
            "content": """
            Transformer 是 2017 年提出的注意力机制模型，彻底改变了 NLP 领域。
            核心组件包括自注意力机制、多头注意力、位置编码和前馈神经网络。
            BERT、GPT、T5 等预训练模型都基于 Transformer 架构。
            自注意力机制允许模型在处理序列时关注所有位置的信息。
            多头注意力通过多个注意力头捕获不同类型的依赖关系。
            """
        },
        {
            "title": "向量数据库技术选型",
            "content": """
            向量数据库用于存储和检索高维向量数据，是 AI 应用的基础设施。
            Chroma、Pinecone、Milvus、Weaviate 是主流的向量数据库。
            Chroma 轻量易用，适合本地开发和小型应用。
            Milvus 支持分布式部署，适合大规模生产环境。
            向量索引算法包括 HNSW、IVF、PQ 等，影响检索性能和精度。
            """
        }
    ]
    
    processed_items = []
    
    for i, item in enumerate(knowledge_items, 1):
        print(f"\n  处理文档 {i}: {item['title']}")
        
        # 1. 提取标签
        print(f"    → 提取标签...")
        tag_result = extractor.process(
            title=item['title'],
            content=item['content']
        )
        
        assert tag_result.success, f"标签提取应该成功: {tag_result.error}"
        tags = tag_result.data
        print(f"    ✓ 标签: {', '.join(tags)}")
        
        # 2. 内容分块（简化版）
        print(f"    → 内容分块...")
        chunks = [item['content'][:500]]  # 简化：只取前500字符
        print(f"    ✓ 分块数量: {len(chunks)}")
        
        # 3. 向量化
        print(f"    → 向量化...")
        embeddings = embedder.embed(chunks)
        print(f"    ✓ 向量维度: {len(embeddings[0])}")
        
        # 4. 构建知识库条目
        knowledge_entry = {
            "title": item['title'],
            "tags": tags,
            "chunks": len(chunks),
            "embedding_dim": len(embeddings[0]),
            "content_preview": item['content'][:50] + "..."
        }
        
        processed_items.append(knowledge_entry)
        print(f"    ✓ 入库完成")
    
    # 展示处理结果
    print(f"\n[步骤 3] 知识库入库统计...")
    print(f"  总文档数: {len(processed_items)}")
    print(f"\n  入库文档详情:")
    for i, entry in enumerate(processed_items, 1):
        print(f"\n  文档 {i}:")
        print(f"    标题: {entry['title']}")
        print(f"    标签: {', '.join(entry['tags'])}")
        print(f"    分块: {entry['chunks']}")
        print(f"    向量维度: {entry['embedding_dim']}")
        print(f"    预览: {entry['content_preview']}")
    
    # 验证结果
    assert len(processed_items) == len(knowledge_items), "所有文档都应该处理成功"
    assert all(len(entry['tags']) > 0 for entry in processed_items), "所有文档都应该有标签"
    assert all(entry['embedding_dim'] == embedder.dimension for entry in processed_items), "向量维度应该一致"
    
    print("\n✓ 组合工作流测试通过！")


def main():
    """主测试函数"""
    print("\n" + "=" * 70)
    print("向量化和智能标签提取功能测试")
    print("=" * 70)
    
    # 检查环境变量
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("\n✗ 错误: 未设置 DASHSCOPE_API_KEY 环境变量")
        print("请设置环境变量后重试:")
        print("  export DASHSCOPE_API_KEY='your-api-key'")
        sys.exit(1)
    
    print(f"\n✓ 检测到 DASHSCOPE_API_KEY")
    
    # 执行测试
    results = {}
    
    results["vectorization"] = test_vectorization()
    results["tag_extraction"] = test_tag_extraction()
    results["combined_workflow"] = test_combined_workflow()
    
    # 汇总结果
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)
    
    test_names = {
        "vectorization": "文本向量化",
        "tag_extraction": "智能标签提取",
        "combined_workflow": "组合工作流"
    }
    
    for test_key, test_name in test_names.items():
        status = "✓ 通过" if results.get(test_key) else "✗ 失败"
        print(f"  {test_name:15s}: {status}")
    
    all_passed = all(results.values())
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ 所有功能测试通过！")
        print("\n功能验证:")
        print("  • 文本向量化: 支持批量处理，语义相似度计算准确")
        print("  • 智能标签提取: 标签质量高，语义相关性强")
        print("  • 组合工作流: 向量化和标签提取协同工作正常")
    else:
        print("✗ 部分测试失败，请检查错误信息。")
    print("=" * 70 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
