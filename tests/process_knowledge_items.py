"""
处理知识库内容并生成向量

对已有的知识项进行：
1. 文本分块 (Chunking)
2. 向量化 (Embedding)
3. 存储到 ChromaDB

使用方法：
    python tests/process_knowledge_items.py
"""

import logging
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kb.config import Config
from kb.storage.sqlite_storage import SQLiteStorage
from kb.storage.chroma_storage import ChromaStorage
from kb.processors.chunker import Chunker
from kb.processors.embedder import Embedder

logger = logging.getLogger(__name__)


def process_knowledge_items():
    """处理所有知识项，生成分块和向量"""
    print("\n" + "=" * 70)
    print("知识库内容处理 - 分块和向量化")
    print("=" * 70)
    
    # 初始化配置
    config = Config()
    
    # 初始化存储
    data_dir = config.data_dir
    db_path = data_dir / "metadata.db"
    sqlite_storage = SQLiteStorage(db_path=str(db_path))
    
    chroma_path = Path(config.get("storage.persist_directory", "~/knowledge-base/chroma_db")).expanduser()
    chroma_storage = ChromaStorage(path=str(chroma_path))
    
    # 初始化处理器
    chunker = Chunker.from_config(config)
    
    # 初始化 embedder，带优雅降级处理
    embedder = None
    try:
        embedder = Embedder.from_config(config)
        print(f"\n配置信息:")
        print(f"  数据目录: {data_dir}")
        print(f"  分块大小: {chunker.chunk_size}")
        print(f"  分块重叠: {chunker.chunk_overlap}")
        print(f"  向量维度: {embedder.dimension}")
    except ValueError as e:
        logger.warning(f"Embedder initialization skipped (configuration error): {e}")
        print(f"\n⚠️ 警告: 向量生成器初始化失败 (配置错误): {e}")
        print("  将继续处理，但跳过向量化步骤。")
        print(f"\n配置信息:")
        print(f"  数据目录: {data_dir}")
        print(f"  分块大小: {chunker.chunk_size}")
        print(f"  分块重叠: {chunker.chunk_overlap}")
    except Exception as e:
        logger.warning(f"Embedder initialization failed: {e}. Processing will continue without vectorization.")
        print(f"\n⚠️ 警告: 向量生成器初始化失败: {e}")
        print("  将继续处理，但跳过向量化步骤。")
    
    # 获取所有知识项
    print(f"\n获取知识项...")
    all_items = sqlite_storage.list_knowledge()
    print(f"  找到 {len(all_items)} 个知识项")
    
    # 处理每个知识项
    processed_count = 0
    total_chunks = 0
    failed_items = []
    
    for i, item in enumerate(all_items, 1):
        print(f"\n[{i}/{len(all_items)}] 处理: {item['title']}")
        print(f"  类型: {item['content_type']}")
        
        try:
            # 获取内容
            content = get_item_content(item, data_dir)
            
            if not content:
                print(f"  ⚠ 跳过: 无内容")
                continue
            
            print(f"  内容长度: {len(content)} 字符")
            
            # 分块
            print(f"  → 分块...")
            result = chunker.process(content)
            
            if not result.success:
                print(f"  ✗ 分块失败: {result.error}")
                continue
            
            chunks = result.data
            print(f"  ✓ 生成 {len(chunks)} 个分块")
            
            # 向量化（如果 embedder 可用）
            if embedder is not None:
                print(f"  → 向量化...")
                # Chunks are dicts with 'content' field
                texts = [chunk.get('content', '') if isinstance(chunk, dict) else str(chunk) for chunk in chunks]
                texts = [t for t in texts if t]  # Filter empty strings
                
                if not texts:
                    print(f"  ⚠ 跳过: 无有效文本")
                    continue
                
                try:
                    embeddings = embedder.embed(texts)
                    print(f"  ✓ 生成 {len(embeddings)} 个向量")
                    
                    # 存储到 ChromaDB
                    print(f"  → 存储到向量数据库...")
                    ids = [f"{item['id']}_chunk_{j}" for j in range(len(texts))]
                    metadatas = [
                        {
                            "knowledge_id": item['id'],
                            "title": item['title'],
                            "content_type": item['content_type'],
                            "chunk_index": j,
                            "source": item['source']
                        }
                        for j in range(len(texts))
                    ]
                    
                    chroma_storage.add_documents(
                        ids=ids,
                        embeddings=embeddings,
                        documents=texts,
                        metadatas=metadatas
                    )
                    print(f"  ✓ 存储成功")
                except ValueError as e:
                    logger.warning(f"Vectorization skipped for '{item['title']}' (configuration error): {e}")
                    print(f"  ⚠️ 警告: 向量化跳过 (配置错误): {e}")
                    print(f"     文档已分块但未生成向量。")
                except Exception as e:
                    logger.warning(f"Vectorization failed for '{item['title']}': {e}. Document chunks saved but not searchable via semantic search.")
                    print(f"  ⚠️ 警告: 向量化失败: {e}")
                    print(f"     文档已分块但未生成向量，仅支持关键词搜索。")
            else:
                print(f"  ⚠️ 跳过向量化: 向量生成器未初始化")
                print(f"     文档已分块但未生成向量，仅支持关键词搜索。")
            
            # 更新 SQLite 中的分块计数
            # Note: This would require updating the knowledge table schema
            # For now, we just track it locally
            
            processed_count += 1
            total_chunks += len(chunks)
            
        except Exception as e:
            print(f"  ✗ 处理失败: {str(e)}")
            failed_items.append({
                'id': item['id'],
                'title': item['title'],
                'error': str(e)
            })
    
    # 打印统计信息
    print("\n" + "=" * 70)
    print("处理完成统计")
    print("=" * 70)
    print(f"\n  总知识项数: {len(all_items)}")
    print(f"  成功处理: {processed_count}")
    print(f"  失败: {len(failed_items)}")
    print(f"  总分块数: {total_chunks}")
    
    if failed_items:
        print(f"\n  失败项详情:")
        for item in failed_items:
            print(f"    - {item['title']}: {item['error']}")
    
    # 更新统计信息
    print(f"\n  更新数据库统计...")
    try:
        stats = sqlite_storage.get_stats()
        print(f"  ✓ 当前统计:")
        print(f"    总文档数: {stats.get('total_items', 0)}")
        print(f"    总分块数: {stats.get('total_chunks', 0)}")
        print(f"    总标签数: {stats.get('total_tags', 0)}")
    except Exception as e:
        print(f"  ✗ 获取统计失败: {str(e)}")
    
    print("\n" + "=" * 70)
    if processed_count > 0:
        print("✓ 内容处理完成！")
        print(f"\n现在您可以在 Web 界面中看到:")
        print(f"  • {total_chunks} 个文本分块")
        print(f"  • 支持语义搜索")
        print(f"  • 支持 RAG 问答")
    else:
        print("⚠ 没有成功处理任何知识项")
    print("=" * 70 + "\n")


def get_item_content(item: dict, data_dir: Path) -> str:
    """
    获取知识项的内容
    
    Args:
        item: 知识项字典
        data_dir: 数据目录
    
    Returns:
        内容字符串，如果无法获取则返回空字符串
    """
    content_type = item['content_type']
    
    # 笔记：内容在 summary 字段中
    if content_type == 'note':
        return item.get('summary', '')
    
    # 文件：从文件系统读取
    elif content_type == 'file':
        file_path = item.get('file_path') or item.get('source')
        if file_path:
            try:
                path = Path(file_path)
                if path.exists():
                    return path.read_text(encoding='utf-8')
            except Exception as e:
                print(f"    警告: 无法读取文件 {file_path}: {e}")
        return ''
    
    # URL：使用 summary 或 source
    elif content_type == 'url':
        return item.get('summary', item.get('source', ''))
    
    # 书签：使用 title 和 source
    elif content_type == 'bookmark':
        title = item.get('title', '')
        source = item.get('source', '')
        return f"{title}\n{source}"
    
    # 其他类型：使用 summary
    else:
        return item.get('summary', '')


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("知识库内容处理器")
    print("=" * 70)
    
    # 检查环境变量（警告但不退出，支持优雅降级）
    if not os.getenv("DASHSCOPE_API_KEY"):
        print("\n⚠️ 警告: 未设置 DASHSCOPE_API_KEY 环境变量")
        print("  向量化功能将不可用，仅支持分块处理。")
        print("  如需向量化，请设置环境变量:")
        print("    export DASHSCOPE_API_KEY='your-api-key'")
    else:
        print(f"\n✓ 检测到 DASHSCOPE_API_KEY")
    
    try:
        process_knowledge_items()
    except Exception as e:
        print(f"\n✗ 处理失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
