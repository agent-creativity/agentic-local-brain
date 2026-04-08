"""
Phase 2a: Embedding 一致性验证测试

验证 LiteLLM embedding 与原生 DashScope SDK embedding 的输出是否一致。
迁移 embedding 层之前必须通过此测试。

使用方法（需要 DASHSCOPE_API_KEY 环境变量）：
    # 运行对比测试（需要网络和 API key）
    python tests/test_embedding_consistency.py

    # 作为 pytest 运行（仅单元测试，不需要 API key）
    pytest tests/test_embedding_consistency.py -v

判定标准：
    - 同一文本的两种 embedding 的 cosine similarity >= 1 - 1e-6
    - 向量维度完全一致
    - 批量处理结果与单条处理结果一致
"""

import math
import os
import sys
from pathlib import Path
from typing import List, Tuple
from unittest.mock import Mock, patch

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """计算两个向量的余弦相似度"""
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)


def max_abs_diff(v1: List[float], v2: List[float]) -> float:
    """计算两个向量的最大绝对差"""
    return max(abs(a - b) for a, b in zip(v1, v2))


# --- Unit tests (no API key needed) ---

class TestCosineHelper:
    """cosine_similarity 辅助函数测试"""

    def test_identical_vectors(self):
        v = [1.0, 2.0, 3.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]
        assert cosine_similarity(v1, v2) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        v1 = [1.0, 2.0]
        v2 = [-1.0, -2.0]
        assert cosine_similarity(v1, v2) == pytest.approx(-1.0)

    def test_zero_vector(self):
        v1 = [0.0, 0.0]
        v2 = [1.0, 2.0]
        assert cosine_similarity(v1, v2) == 0.0


class TestMaxAbsDiff:
    """max_abs_diff 辅助函数测试"""

    def test_identical_vectors(self):
        v = [1.0, 2.0, 3.0]
        assert max_abs_diff(v, v) == 0.0

    def test_small_diff(self):
        v1 = [1.0, 2.0, 3.0]
        v2 = [1.0, 2.0 + 1e-7, 3.0]
        assert max_abs_diff(v1, v2) < 1e-6


class TestEmbeddingConsistencyMocked:
    """
    Embedding 一致性验证 — mock 版本
    验证对比逻辑本身是否正确
    """

    def test_consistency_check_passes_with_identical_output(self):
        """当两个 provider 输出完全相同时，一致性检查通过"""
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]

        sim = cosine_similarity(embedding, embedding)
        assert sim >= 1 - 1e-6

        diff = max_abs_diff(embedding, embedding)
        assert diff < 1e-6

    def test_consistency_check_fails_with_different_output(self):
        """当两个 provider 输出差异较大时，一致性检查失败"""
        emb1 = [0.1, 0.2, 0.3, 0.4, 0.5]
        emb2 = [0.5, 0.4, 0.3, 0.2, 0.1]

        sim = cosine_similarity(emb1, emb2)
        assert sim < 1 - 1e-6

    def test_consistency_check_with_near_identical_output(self):
        """当差异极小（< 1e-7）时，一致性检查通过"""
        emb1 = [0.12345678, 0.23456789, 0.34567890]
        emb2 = [0.12345678 + 1e-8, 0.23456789 - 1e-8, 0.34567890 + 1e-8]

        sim = cosine_similarity(emb1, emb2)
        assert sim >= 1 - 1e-6

        diff = max_abs_diff(emb1, emb2)
        assert diff < 1e-6

    def test_dimension_mismatch_detection(self):
        """维度不一致应被检测到"""
        emb1 = [0.1, 0.2, 0.3]
        emb2 = [0.1, 0.2, 0.3, 0.4]

        assert len(emb1) != len(emb2)

    def test_batch_vs_single_consistency(self):
        """批量处理和单条处理的结果应一致"""
        # Simulate: batch returns same as individual calls
        batch_results = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        single_results = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]

        for i, (batch, single) in enumerate(zip(batch_results, single_results)):
            sim = cosine_similarity(batch, single)
            assert sim >= 1 - 1e-6, f"Mismatch at index {i}: similarity={sim}"


# --- Integration test (requires API key, run as script) ---

CONSISTENCY_THRESHOLD = 1e-6
TEST_TEXTS = [
    "机器学习是人工智能的一个重要分支",
    "深度学习使用神经网络进行特征学习",
    "自然语言处理涉及文本理解和生成",
    "计算机视觉专注于图像和视频分析",
    "强化学习通过奖励信号优化决策策略",
]


def run_native_dashscope_embedding(api_key: str, texts: List[str]) -> Tuple[List[List[float]], int]:
    """使用原生 DashScope SDK 生成 embedding"""
    import dashscope
    from dashscope import TextEmbedding

    dashscope.api_key = api_key

    response = TextEmbedding.call(
        model="text-embedding-v4",
        input=texts,
    )

    if response.status_code != 200:
        raise Exception(f"DashScope API error: {response.status_code} - {response.message}")

    embeddings = [item["embedding"] for item in response.output["embeddings"]]
    dimension = len(embeddings[0])
    return embeddings, dimension


def run_litellm_embedding(api_key: str, texts: List[str]) -> Tuple[List[List[float]], int]:
    """使用 LiteLLM 生成 embedding

    DashScope 不直接支持 litellm 的 dashscope/ provider embedding，
    需要通过 OpenAI-compatible 模式访问 DashScope 的兼容接口，
    并显式设置 encoding_format='float'（DashScope 不支持 litellm 默认的格式）。
    """
    import litellm

    response = litellm.embedding(
        model="openai/text-embedding-v4",
        input=texts,
        api_key=api_key,
        api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
        encoding_format="float",
    )

    embeddings = [item["embedding"] for item in response.data]
    dimension = len(embeddings[0])
    return embeddings, dimension


def run_consistency_test():
    """运行完整的一致性对比测试"""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("ERROR: DASHSCOPE_API_KEY environment variable is required")
        return False

    print("=" * 70)
    print("Phase 2a: Embedding Consistency Test")
    print("Native DashScope SDK vs LiteLLM")
    print("=" * 70)

    all_passed = True

    # Test 1: Dimension consistency
    print("\n[Test 1] Dimension consistency")
    try:
        native_embeddings, native_dim = run_native_dashscope_embedding(api_key, TEST_TEXTS)
        litellm_embeddings, litellm_dim = run_litellm_embedding(api_key, TEST_TEXTS)

        if native_dim == litellm_dim:
            print(f"  PASS: Both produce {native_dim}-dim vectors")
        else:
            print(f"  FAIL: Native={native_dim}, LiteLLM={litellm_dim}")
            all_passed = False
            return False  # No point continuing if dimensions differ
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 2: Per-text cosine similarity
    print(f"\n[Test 2] Per-text cosine similarity (threshold: 1 - {CONSISTENCY_THRESHOLD})")
    for i, text in enumerate(TEST_TEXTS):
        sim = cosine_similarity(native_embeddings[i], litellm_embeddings[i])
        diff = max_abs_diff(native_embeddings[i], litellm_embeddings[i])
        passed = sim >= 1 - CONSISTENCY_THRESHOLD
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] Text {i+1}: cosine_sim={sim:.10f}, max_abs_diff={diff:.2e}")
        print(f"         \"{text[:30]}...\"")
        if not passed:
            all_passed = False

    # Test 3: Batch vs single consistency (native SDK)
    print(f"\n[Test 3] Batch vs single-text consistency (native SDK)")
    single_embeddings = []
    for text in TEST_TEXTS[:3]:
        emb, _ = run_native_dashscope_embedding(api_key, [text])
        single_embeddings.append(emb[0])

    for i in range(3):
        sim = cosine_similarity(native_embeddings[i], single_embeddings[i])
        passed = sim >= 1 - CONSISTENCY_THRESHOLD
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] Text {i+1}: cosine_sim={sim:.10f}")
        if not passed:
            all_passed = False

    # Test 4: Batch vs single consistency (LiteLLM)
    print(f"\n[Test 4] Batch vs single-text consistency (LiteLLM)")
    single_litellm = []
    for text in TEST_TEXTS[:3]:
        emb, _ = run_litellm_embedding(api_key, [text])
        single_litellm.append(emb[0])

    for i in range(3):
        sim = cosine_similarity(litellm_embeddings[i], single_litellm[i])
        passed = sim >= 1 - CONSISTENCY_THRESHOLD
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] Text {i+1}: cosine_sim={sim:.10f}")
        if not passed:
            all_passed = False

    # Test 5: Cross-provider semantic ordering
    print(f"\n[Test 5] Cross-provider semantic ordering consistency")
    # Check that relative similarity ordering is preserved
    # "机器学习" should be more similar to "深度学习" than to "计算机视觉"
    native_sim_01 = cosine_similarity(native_embeddings[0], native_embeddings[1])
    native_sim_03 = cosine_similarity(native_embeddings[0], native_embeddings[3])
    litellm_sim_01 = cosine_similarity(litellm_embeddings[0], litellm_embeddings[1])
    litellm_sim_03 = cosine_similarity(litellm_embeddings[0], litellm_embeddings[3])

    native_order = native_sim_01 > native_sim_03
    litellm_order = litellm_sim_01 > litellm_sim_03

    if native_order == litellm_order:
        print(f"  PASS: Semantic ordering preserved")
        print(f"         Native:  sim(0,1)={native_sim_01:.4f} vs sim(0,3)={native_sim_03:.4f}")
        print(f"         LiteLLM: sim(0,1)={litellm_sim_01:.4f} vs sim(0,3)={litellm_sim_03:.4f}")
    else:
        print(f"  FAIL: Semantic ordering differs")
        all_passed = False

    # Summary
    print("\n" + "=" * 70)
    if all_passed:
        print("ALL TESTS PASSED - LiteLLM embedding is consistent with native SDK")
        print("Safe to proceed with embedding layer migration.")
    else:
        print("SOME TESTS FAILED - DO NOT migrate embedding layer")
        print("LiteLLM embedding output differs from native SDK.")
    print("=" * 70)

    return all_passed


if __name__ == "__main__":
    success = run_consistency_test()
    sys.exit(0 if success else 1)
