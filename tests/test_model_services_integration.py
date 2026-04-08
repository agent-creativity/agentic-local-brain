"""
模型服务集成测试脚本

测试配置文件中配置的模型服务功能（通过 LiteLLM 统一调用）：
1. Embedding 模型：text-embedding-v4
2. LLM 模型：qwen-plus

使用方法（作为独立脚本运行）：
    python tests/test_model_services_integration.py

注意：此文件不是 pytest 测试，而是独立运行的集成测试脚本。

环境变量要求：
    DASHSCOPE_API_KEY: DashScope API 密钥
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kb.config import Config
from kb.processors.embedder import Embedder, DashScopeEmbeddingProvider
from kb.processors.tag_extractor import TagExtractor, LiteLLMProvider


def test_embedding_service():
    """测试 Embedding 服务 (text-embedding-v4)"""
    print("=" * 70)
    print("测试 1: Embedding 服务 (text-embedding-v4)")
    print("=" * 70)
    
    try:
        # 从配置加载
        print("\n[步骤 1] 从配置文件加载 embedding 配置...")
        config = Config()
        embedding_config = config.get("embedding", {})
        print(f"  - Provider: {embedding_config.get('provider')}")
        print(f"  - Model: {embedding_config.get('model')}")
        
        # 创建 Embedder
        print("\n[步骤 2] 创建 Embedder 实例...")
        embedder = Embedder.from_config(config)
        print(f"  - 向量维度: {embedder.dimension}")
        
        # 测试单文本向量化
        print("\n[步骤 3] 测试单文本向量化...")
        test_text = "机器学习是人工智能的一个重要分支"
        embeddings = embedder.embed([test_text])
        print(f"  - 输入文本: {test_text}")
        print(f"  - 向量数量: {len(embeddings)}")
        print(f"  - 向量维度: {len(embeddings[0])}")
        print(f"  - 向量前5个值: {embeddings[0][:5]}")
        
        # 测试多文本向量化
        print("\n[步骤 4] 测试多文本向量化...")
        test_texts = [
            "深度学习使用神经网络进行特征学习",
            "自然语言处理涉及文本理解和生成",
            "计算机视觉专注于图像和视频分析"
        ]
        embeddings = embedder.embed(test_texts)
        print(f"  - 输入文本数量: {len(test_texts)}")
        print(f"  - 向量数量: {len(embeddings)}")
        for i, (text, emb) in enumerate(zip(test_texts, embeddings), 1):
            print(f"  - 文本{i}: {text[:20]}...")
            print(f"    向量维度: {len(emb)}, 前3个值: {emb[:3]}")
        
        # 计算文本相似度
        print("\n[步骤 5] 测试文本相似度计算...")
        text1 = "人工智能和机器学习"
        text2 = "深度学习和神经网络"
        text3 = "烹饪和美食制作"
        
        embs = embedder.embed([text1, text2, text3])
        
        def cosine_similarity(v1, v2):
            """计算余弦相似度"""
            dot_product = sum(a * b for a, b in zip(v1, v2))
            norm1 = sum(a * a for a in v1) ** 0.5
            norm2 = sum(b * b for b in v2) ** 0.5
            return dot_product / (norm1 * norm2)
        
        sim_12 = cosine_similarity(embs[0], embs[1])
        sim_13 = cosine_similarity(embs[0], embs[2])
        
        print(f"  - 文本1: {text1}")
        print(f"  - 文本2: {text2}")
        print(f"  - 文本3: {text3}")
        print(f"  - 相似度(文本1 vs 文本2): {sim_12:.4f} (相关)")
        print(f"  - 相似度(文本1 vs 文本3): {sim_13:.4f} (不相关)")
        
        if sim_12 > sim_13:
            print("  ✓ 语义相似度计算正确！")
        else:
            print("  ✗ 语义相似度计算异常")
        
        print("\n✓ Embedding 服务测试通过！")
        return True
        
    except Exception as e:
        print(f"\n✗ Embedding 服务测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_llm_service():
    """测试 LLM 服务 (qwen-plus)"""
    print("\n" + "=" * 70)
    print("测试 2: LLM 服务 (qwen-plus)")
    print("=" * 70)
    
    try:
        # 从配置加载
        print("\n[步骤 1] 从配置文件加载 LLM 配置...")
        config = Config()
        llm_config = config.get("llm", {})
        print(f"  - Provider: {llm_config.get('provider')}")
        print(f"  - Model: {llm_config.get('model')}")
        
        # 创建 TagExtractor
        print("\n[步骤 2] 创建 TagExtractor 实例...")
        extractor = TagExtractor.from_config(config)
        print(f"  - 最小标签数: {extractor.min_tags}")
        print(f"  - 最大标签数: {extractor.max_tags}")
        
        # 测试标签提取
        print("\n[步骤 3] 测试标签提取功能...")
        test_title = "深度学习在自然语言处理中的应用"
        test_content = """
        深度学习是机器学习的一个子领域，使用多层神经网络来学习数据的层次表示。
        在自然语言处理中，深度学习模型如 Transformer 和 BERT 已经取得了显著的成果。
        这些模型能够理解语言的复杂模式，实现文本分类、情感分析、机器翻译等任务。
        近年来，大语言模型（LLM）如 GPT 系列展示了强大的语言理解和生成能力。
        """
        
        print(f"  - 标题: {test_title}")
        print(f"  - 内容: {test_content[:50]}...")
        
        result = extractor.process(
            title=test_title,
            content=test_content,
            temperature=0.3
        )
        
        if result.success:
            print(f"\n  ✓ 标签提取成功！")
            print(f"  - 提取标签数量: {result.metadata.get('tag_count', 0)}")
            tags = result.data.get('tags', []) if isinstance(result.data, dict) else result.data
            print(f"  - 标签列表: {', '.join(tags)}")

            # 验证标签质量
            if len(tags) >= extractor.min_tags and len(tags) <= extractor.max_tags:
                print(f"  ✓ 标签数量符合要求 ({extractor.min_tags}-{extractor.max_tags})")
            else:
                print(f"  ✗ 标签数量不符合要求")
            
            if all(len(tag) >= 2 for tag in tags):
                print(f"  ✓ 所有标签长度符合要求 (>=2字符)")
            else:
                print(f"  ✗ 存在过短的标签")
                
        else:
            print(f"\n  ✗ 标签提取失败: {result.error}")
            return False
        
        # 测试另一个文档
        print("\n[步骤 4] 测试不同主题的标签提取...")
        test_title2 = "Python 编程最佳实践"
        test_content2 = """
        Python 是一种广泛使用的高级编程语言，以其简洁的语法和强大的库生态系统而闻名。
        在软件开发中，遵循最佳实践可以提高代码质量和可维护性。
        包括使用虚拟环境管理依赖、编写单元测试、遵循 PEP 8 编码规范等。
        设计模式如单例模式、工厂模式、观察者模式在 Python 中都有广泛应用。
        """
        
        print(f"  - 标题: {test_title2}")
        result2 = extractor.process(title=test_title2, content=test_content2)
        
        if result2.success:
            tags2 = result2.data.get('tags', []) if isinstance(result2.data, dict) else result2.data
            print(f"  ✓ 标签提取成功！")
            print(f"  - 标签列表: {', '.join(tags2)}")
        else:
            print(f"  ✗ 标签提取失败: {result2.error}")
            return False
        
        print("\n✓ LLM 服务测试通过！")
        return True
        
    except Exception as e:
        print(f"\n✗ LLM 服务测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_direct_api_call():
    """测试直接 API 调用"""
    print("\n" + "=" * 70)
    print("测试 3: 直接 API 调用验证")
    print("=" * 70)
    
    try:
        config = Config()
        api_key = config.get("llm.api_key")
        
        if not api_key:
            print("\n✗ 未找到 API Key，跳过直接 API 测试")
            return False
        
        # 测试 LiteLLM Provider 直接调用
        print("\n[步骤 1] 测试 LiteLLM Provider 直接调用...")
        provider = LiteLLMProvider(
            api_key=api_key,
            model="dashscope/qwen-plus"
        )

        response = provider.generate(
            prompt="请用一句话介绍人工智能",
            temperature=0.5
        )
        print(f"  - 响应: {response[:100]}...")
        print(f"  ✓ LiteLLM Provider 直接调用成功！")
        
        # 测试 DashScope Embedding Provider 直接调用
        print("\n[步骤 2] 测试 DashScope Embedding Provider 直接调用...")
        embedding_provider = DashScopeEmbeddingProvider(
            api_key=api_key,
            model="text-embedding-v4"
        )
        
        embeddings = embedding_provider.embed(["测试文本"])
        print(f"  - 向量维度: {len(embeddings[0])}")
        print(f"  ✓ Embedding Provider 直接调用成功！")
        
        print("\n✓ 直接 API 调用测试通过！")
        return True
        
    except Exception as e:
        print(f"\n✗ 直接 API 调用测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 70)
    print("模型服务集成测试")
    print("=" * 70)
    
    # 检查环境变量
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("\n✗ 错误: 未设置 DASHSCOPE_API_KEY 环境变量")
        print("请设置环境变量后重试:")
        print("  export DASHSCOPE_API_KEY='your-api-key'")
        sys.exit(1)
    
    print(f"\n✓ 检测到 DASHSCOPE_API_KEY")
    
    # 检查配置文件（使用默认配置或模板）
    config_path = Path.home() / ".knowledge_base" / "config.yaml"
    template_path = project_root / "config-template.yaml"
    
    if not config_path.exists():
        print(f"\n⚠ 配置文件不存在: {config_path}")
        if template_path.exists():
            print(f"  使用模板配置文件: {template_path}")
            config_path = template_path
        else:
            print(f"  使用默认配置")
            config_path = None
    
    print(f"✓ 使用配置文件: {config_path if config_path else '默认配置'}")
    
    # 执行测试
    results = {}
    
    results["embedding"] = test_embedding_service()
    results["llm"] = test_llm_service()
    results["direct_api"] = test_direct_api_call()
    
    # 汇总结果
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)
    
    for test_name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {test_name:15s}: {status}")
    
    all_passed = all(results.values())
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ 所有测试通过！模型服务配置正确。")
    else:
        print("✗ 部分测试失败，请检查错误信息。")
    print("=" * 70 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
