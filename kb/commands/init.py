"""
CLI Init Commands

Initialization and setup commands for the knowledge base.
"""

import shutil
from pathlib import Path

import click

from kb.commands.utils import CONFIG_DIR, CONFIG_FILE, TEMPLATE_FILE, _ensure_config_dir, _get_sqlite_storage


@click.group()
def init() -> None:
    """Initialize and setup the knowledge base."""
    pass


@init.command()
@click.option("--no-sample", is_flag=True, help="Skip generating sample data")
def setup(no_sample: bool) -> None:
    """Initialize knowledge base configuration and data directories."""
    from kb.config import Config
    
    _ensure_config_dir()
    
    # Check if already initialized — refuse if local data exists
    if CONFIG_FILE.exists():
        config = Config(CONFIG_FILE)
        data_dir = Path(config.get("data_dir", "~/.knowledge-base")).expanduser()
        db_file = data_dir / "db" / "metadata.db"
        collect_dir = data_dir / "1_collect"
        
        has_data = db_file.exists() or (collect_dir.exists() and any(collect_dir.iterdir()))
        
        if has_data:
            click.echo(f"⚠️  Knowledge base already initialized with existing data.")
            click.echo(f"   Config: {CONFIG_FILE}")
            click.echo(f"   Data:   {data_dir}")
            click.echo()
            click.echo("To re-initialize, please manually clean up first:")
            click.echo(f"   rm -rf {data_dir}")
            click.echo(f"   rm {CONFIG_FILE}")
            click.echo()
            click.echo("Then run 'localbrain init setup' again.")
            return
        
        click.echo(f"⚠️  Configuration already exists at: {CONFIG_FILE}")
        click.echo("   But no data found — proceeding with re-initialization...")
        click.echo()
    
    # Copy template config
    if TEMPLATE_FILE.exists():
        shutil.copy2(TEMPLATE_FILE, CONFIG_FILE)
        click.echo(f"✓ Created configuration file: {CONFIG_FILE}")
    else:
        click.echo(f"✗ Template file not found: {TEMPLATE_FILE}", err=True)
        raise SystemExit(1)
    
    # Initialize config
    config = Config(CONFIG_FILE)
    data_dir = Path(config.get("data_dir", "~/.knowledge-base")).expanduser()
    raw_dir = data_dir / "1_collect"
    
    # Create data directories
    data_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    # Create new phase directories
    (data_dir / "2_process").mkdir(parents=True, exist_ok=True)
    (data_dir / "3_refine").mkdir(parents=True, exist_ok=True)
    (data_dir / "db").mkdir(parents=True, exist_ok=True)
    (data_dir / "exports").mkdir(parents=True, exist_ok=True)
    
    # Create runtime directories under config dir (~/.localbrain)
    (CONFIG_DIR / "logs").mkdir(parents=True, exist_ok=True)
    (CONFIG_DIR / ".runtime").mkdir(parents=True, exist_ok=True)
    
    click.echo(f"✓ Created data directory: {data_dir}")
    
    # Initialize database (ensure db parent directory exists)
    (data_dir / "db").mkdir(parents=True, exist_ok=True)
    storage = _get_sqlite_storage()
    try:
        click.echo(f"✓ Initialized metadata database")
    finally:
        storage.close()
    
    # Generate sample data
    if not no_sample:
        click.echo("\nGenerating sample data...")
        _generate_sample_data(data_dir, raw_dir)
    
    click.echo("\nInitialization complete!")
    click.echo(f"Data directory: {data_dir}")
    click.echo(f"Configuration file: {CONFIG_FILE}")
    click.echo("\nUse 'localbrain config show' to view configuration")
    click.echo("Use 'localbrain collect file <path>' to start collecting files")
    click.echo("Use 'localbrain stats' to view knowledge base statistics")


def _generate_sample_data(data_dir: Path, raw_dir: Path) -> None:
    """Generate sample data for each knowledge type."""
    from kb.storage.sqlite_storage import SQLiteStorage
    
    # Initialize storage
    db_path = str(data_dir / "db" / "metadata.db")
    storage = SQLiteStorage(db_path=db_path)
    
    try:
        # 1. Generate file sample
        _generate_sample_file(raw_dir / "files", storage)
        
        # 2. Generate webpage sample
        _generate_sample_webpage(raw_dir / "webpages", storage)
        
        # 3. Generate bookmark sample
        _generate_sample_bookmark(raw_dir / "bookmarks", storage)
        
        # 4. Generate paper sample
        _generate_sample_paper(raw_dir / "papers", storage)
        
        # 5. Generate email sample
        _generate_sample_email(raw_dir / "emails", storage)
        
        # 6. Generate note sample
        _generate_sample_note(raw_dir / "notes", storage)
        
        click.echo("  ✓ Generated 6 sample data (1 for each type)")
        
    finally:
        storage.close()


def _generate_sample_file(output_dir: Path, storage) -> None:
    """Generate file sample - Knowledge Management Basics"""
    from kb.commands.utils import _generate_content_hash
    
    title = "Knowledge Management Basics"
    content = """# 知识管理基础

知识管理（Knowledge Management, KM）是组织或个人系统化地收集、组织、存储和使用知识的过程。

## 核心概念

### 1. 显性知识 vs 隐性知识

- **显性知识**：可以用语言、文字、数字、图表等明确表达的知识
- **隐性知识**：难以用语言明确表达,通常需要通过实践和经验获得

### 2. 知识生命周期

1. **获取**：从各种来源收集知识
2. **组织**：对知识进行分类、标引和结构化
3. **存储**：将知识保存在适当的媒介中
4. **分享**：促进知识的传播和交流
5. **应用**：将知识用于解决问题和决策
6. **更新**：持续维护和更新知识

### 3. 个人知识管理工具

- **笔记应用**：Obsidian、Notion、Evernote
- **书签管理**：Raindrop.io、Pocket
- **文献管理**：Zotero、Mendeley
- **代码仓库**：GitHub、GitLab

## 最佳实践

- 建立统一的命名规范
- 定期整理和归档
- 使用标签系统进行多维分类
- 建立知识之间的关联
- 保持持续学习的习惯
"""
    
    # Generate metadata
    timestamp = __import__('datetime').datetime.now()
    item_id = f"sample_file_{timestamp.strftime('%Y%m%d_%H%M%S')}"
    file_path = output_dir / f"{timestamp.strftime('%Y-%m-%d_%H%M%S')}_knowledge-management-basics.md"
    
    # Generate content hash
    content_hash = _generate_content_hash(content)
    
    # Save file (with YAML Front Matter)
    metadata_yaml = f"""---
id: {item_id}
title: "{title}"
source: "sample"
content_type: file
collected_at: {timestamp.isoformat()}
tags:
  - 知识管理
  - 基础概念
  - 示例数据
word_count: {len(content.split())}
status: processed
original_filename: "knowledge-management-basics.md"
file_extension: .md
---

"""
    
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path.write_text(metadata_yaml + content, encoding="utf-8")
    
    # Save to database
    storage.add_knowledge(
        id=item_id,
        title=title,
        content_type="file",
        source="sample",
        collected_at=timestamp.isoformat(),
        summary="知识管理的基础概念、生命周期和最佳实践",
        word_count=len(content.split()),
        file_path=str(file_path),
        content_hash=content_hash
    )
    storage.add_tags(item_id, ["知识管理", "基础概念", "示例数据"])


def _generate_sample_webpage(output_dir: Path, storage) -> None:
    """Generate webpage sample - AI Overview"""
    from kb.commands.utils import _generate_content_hash
    
    title = "AI Development Overview"
    content = """# 人工智能发展概述

人工智能（Artificial Intelligence, AI）是计算机科学的一个分支，致力于创建能够执行通常需要人类智能才能完成的任务的系统。

## 发展历程

### 1950s - 诞生期
- 图灵测试的提出
- 早期符号主义 AI

### 1980s - 专家系统
- 基于规则的系统
- 知识工程兴起

### 2010s - 深度学习革命
- 卷积神经网络（CNN）
- 循环神经网络（RNN）
- 生成对抗网络（GAN）

### 2020s - 大语言模型时代
- GPT 系列模型
- 多模态学习
- 通用人工智能（AGI）探索

## 主要应用领域

1. **自然语言处理**：机器翻译、文本生成、情感分析
2. **计算机视觉**：图像识别、目标检测、视频分析
3. **语音技术**：语音识别、语音合成
4. **推荐系统**：个性化推荐、内容分发
5. **自动驾驶**：感知、决策、控制

## 未来趋势

- 可解释 AI（XAI）
- 联邦学习
- 边缘 AI
- AI 伦理与治理
"""
    
    timestamp = __import__('datetime').datetime.now()
    item_id = f"sample_webpage_{timestamp.strftime('%Y%m%d_%H%M%S')}"
    file_path = output_dir / f"{timestamp.strftime('%Y-%m-%d_%H%M%S')}_ai-overview.md"
    
    content_hash = _generate_content_hash(content)
    
    metadata_yaml = f"""---
id: {item_id}
title: "{title}"
source: "https://example.com/ai-overview"
content_type: webpage
collected_at: {timestamp.isoformat()}
tags:
  - 人工智能
  - 技术趋势
  - 示例数据
word_count: {len(content.split())}
status: processed
---

"""
    
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path.write_text(metadata_yaml + content, encoding="utf-8")
    
    storage.add_knowledge(
        id=item_id,
        title=title,
        content_type="webpage",
        source="https://example.com/ai-overview",
        collected_at=timestamp.isoformat(),
        summary="人工智能的发展历程、主要应用领域和未来趋势",
        word_count=len(content.split()),
        file_path=str(file_path),
        content_hash=content_hash
    )
    storage.add_tags(item_id, ["人工智能", "技术趋势", "示例数据"])


def _generate_sample_bookmark(output_dir: Path, storage) -> None:
    """Generate bookmark sample"""
    from kb.commands.utils import _generate_content_hash
    
    title = "Python Official Documentation"
    content = """# Python 官方文档

Python 是一种广泛使用的高级编程语言，以其简洁易读的语法而闻名。

## 主要特性

- **简洁优雅**：代码可读性强
- **跨平台**：支持 Windows、macOS、Linux
- **丰富的库**：标准库和第三方库
- **广泛应用**：Web 开发、数据科学、人工智能、自动化等

## 学习资源

- [官方文档](https://docs.python.org/3/)
- [Python Tutorial](https://docs.python.org/3/tutorial/)
- [Python Package Index](https://pypi.org/)

## 版本信息

- Python 3.x：当前主流版本
- Python 2.x：已于 2020 年停止维护
"""
    
    timestamp = __import__('datetime').datetime.now()
    item_id = f"sample_bookmark_{timestamp.strftime('%Y%m%d_%H%M%S')}"
    file_path = output_dir / f"{timestamp.strftime('%Y-%m-%d_%H%M%S')}_python-docs.md"
    
    content_hash = _generate_content_hash(content)
    
    metadata_yaml = f"""---
id: {item_id}
title: "{title}"
source: "https://docs.python.org/3/"
content_type: bookmark
collected_at: {timestamp.isoformat()}
tags:
  - Python
  - 编程
  - 示例数据
word_count: {len(content.split())}
status: processed
---

"""
    
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path.write_text(metadata_yaml + content, encoding="utf-8")
    
    storage.add_knowledge(
        id=item_id,
        title=title,
        content_type="bookmark",
        source="https://docs.python.org/3/",
        collected_at=timestamp.isoformat(),
        summary="Python官方文档的书签，包含学习资源和版本信息",
        word_count=len(content.split()),
        file_path=str(file_path),
        content_hash=content_hash
    )
    storage.add_tags(item_id, ["Python", "编程", "示例数据"])


def _generate_sample_paper(output_dir: Path, storage) -> None:
    """Generate paper sample"""
    from kb.commands.utils import _generate_content_hash
    
    title = "Attention Is All You Need"
    content = """# Attention Is All You Need

## Abstract

The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.

## Key Contributions

1. **Transformer Architecture**: Novel architecture based entirely on attention mechanisms
2. **Self-Attention**: Allows model to attend to different positions in the input sequence
3. **Multi-Head Attention**: Enables model to jointly attend to information from different representation subspaces
4. **Positional Encoding**: Provides information about token positions in the sequence

## Impact

This paper introduced the Transformer architecture, which has become the foundation for:
- BERT, GPT, and other large language models
- Modern NLP systems
- Vision Transformers (ViT)
- Multi-modal AI systems
"""
    
    timestamp = __import__('datetime').datetime.now()
    item_id = f"sample_paper_{timestamp.strftime('%Y%m%d_%H%M%S')}"
    file_path = output_dir / f"{timestamp.strftime('%Y-%m-%d_%H%M%S')}_attention-is-all-you-need.md"
    
    content_hash = _generate_content_hash(content)
    
    metadata_yaml = f"""---
id: {item_id}
title: "{title}"
source: "arxiv:1706.03762"
content_type: paper
collected_at: {timestamp.isoformat()}
tags:
  - 深度学习
  - Transformer
  - 示例数据
word_count: {len(content.split())}
status: processed
authors: ["Vaswani, Ashish", "Shazeer, Noam", "Parmar, Niki"]
---

"""
    
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path.write_text(metadata_yaml + content, encoding="utf-8")
    
    storage.add_knowledge(
        id=item_id,
        title=title,
        content_type="paper",
        source="arxiv:1706.03762",
        collected_at=timestamp.isoformat(),
        summary="Transformer架构的开创性论文，提出了基于注意力机制的新型网络结构",
        word_count=len(content.split()),
        file_path=str(file_path),
        content_hash=content_hash
    )
    storage.add_tags(item_id, ["深度学习", "Transformer", "示例数据"])


def _generate_sample_email(output_dir: Path, storage) -> None:
    """Generate email sample"""
    from kb.commands.utils import _generate_content_hash
    
    title = "Weekly Team Sync - Project Update"
    content = """# Weekly Team Sync - Project Update

**From**: team-lead@example.com
**To**: dev-team@example.com
**Date**: 2024-01-15

## Agenda

1. Sprint progress review
2. Blockers and challenges
3. Next week's priorities

## Updates

### Frontend Team
- Completed user dashboard redesign
- Started implementing new search feature
- Blocker: Waiting for API documentation

### Backend Team
- Deployed new authentication service
- Performance optimization in progress
- On track for milestone delivery

### QA Team
- Test coverage increased to 75%
- Automated regression tests running
- Found 3 critical bugs (being fixed)

## Action Items

- [ ] Complete API documentation by Wednesday
- [ ] Schedule design review for new features
- [ ] Update project timeline
"""
    
    timestamp = __import__('datetime').datetime.now()
    item_id = f"sample_email_{timestamp.strftime('%Y%m%d_%H%M%S')}"
    file_path = output_dir / f"{timestamp.strftime('%Y-%m-%d_%H%M%S')}_team-sync.md"
    
    content_hash = _generate_content_hash(content)
    
    metadata_yaml = f"""---
id: {item_id}
title: "{title}"
source: "sample"
content_type: email
collected_at: {timestamp.isoformat()}
tags:
  - 团队协作
  - 项目管理
  - 示例数据
word_count: {len(content.split())}
status: processed
from: "team-lead@example.com"
to: "dev-team@example.com"
---

"""
    
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path.write_text(metadata_yaml + content, encoding="utf-8")
    
    storage.add_knowledge(
        id=item_id,
        title=title,
        content_type="email",
        source="sample",
        collected_at=timestamp.isoformat(),
        summary="团队周会邮件，包含项目进展、阻塞问题和行动计划",
        word_count=len(content.split()),
        file_path=str(file_path),
        content_hash=content_hash
    )
    storage.add_tags(item_id, ["团队协作", "项目管理", "示例数据"])


def _generate_sample_note(output_dir: Path, storage) -> None:
    """Generate note sample"""
    from kb.commands.utils import _generate_content_hash
    
    title = "Key Insights from ML Reading"
    content = """# Key Insights from ML Reading

## Transfer Learning

- Pre-trained models can be fine-tuned for specific tasks
- Reduces training time and data requirements
- Works well when target domain is similar to source domain

## Model Interpretability

- SHAP values provide feature importance
- LIME explains individual predictions
- Attention weights can indicate model focus

## Best Practices

1. Start with simple baselines
2. Use cross-validation for robust evaluation
3. Monitor for data drift in production
4. Document model decisions and assumptions

## Resources

- "Deep Learning" by Goodfellow et al.
- "Hands-On Machine Learning" by Géron
- Papers with Code website
"""
    
    timestamp = __import__('datetime').datetime.now()
    item_id = f"sample_note_{timestamp.strftime('%Y%m%d_%H%M%S')}"
    file_path = output_dir / f"{timestamp.strftime('%Y-%m-%d_%H%M%S')}_ml-insights.md"
    
    content_hash = _generate_content_hash(content)
    
    metadata_yaml = f"""---
id: {item_id}
title: "{title}"
source: "manual"
content_type: note
collected_at: {timestamp.isoformat()}
tags:
  - 机器学习
  - 学习笔记
  - 示例数据
word_count: {len(content.split())}
status: processed
---

"""
    
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path.write_text(metadata_yaml + content, encoding="utf-8")
    
    storage.add_knowledge(
        id=item_id,
        title=title,
        content_type="note",
        source="manual",
        collected_at=timestamp.isoformat(),
        summary="机器学习阅读笔记，包含迁移学习、模型可解释性和最佳实践",
        word_count=len(content.split()),
        file_path=str(file_path),
        content_hash=content_hash
    )
    storage.add_tags(item_id, ["机器学习", "学习笔记", "示例数据"])
