# v0.8.1 快速参考

## 修复的问题

### 1. API Key 被掩码保存
**问题**: 配置文件中保存 `sk-s******************************3e32` 而不是真实 key

**解决**: 后端自动检测掩码 key 并保留原始值

**用户操作**: 重新输入一次真实 API key 即可

### 2. 配置项丢失
**问题**: 保存 LLM 配置后，其他配置段（chunking、storage、query 等）消失

**解决**: 保存时自动合并默认配置，保留所有配置段

**用户操作**: 无需操作，自动修复

## 新功能

### 备份配置
```yaml
backup:
  enabled: false                       # 启用自动备份
  schedule: "0 2 * * *"                # Cron 计划
  retention_days: 30                   # 保留天数
  backup_dir: ~/.knowledge-base/backups
  include_db: true
  include_files: true
  compression: true
```

**API 端点**:
- `GET /api/settings/backup` - 获取配置
- `PUT /api/settings/backup` - 更新配置

### 配置迁移
运行 `localbrain init setup` 时自动检测并添加缺失的配置项

## 测试命令

```bash
# 启动虚拟环境
source .venv/bin/activate

# 安装包
pip install -e .

# 启动 Web 服务
localbrain web --port 8765

# 测试备份 API
curl http://localhost:8765/api/settings/backup

# 更新备份配置
curl -X PUT http://localhost:8765/api/settings/backup \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "schedule": "0 3 * * *", "retention_days": 60, ...}'
```

## 文件清单

### 代码文件
- `kb/config.py` - 添加备份配置
- `kb/config-template.yaml` - 配置模板
- `kb/web/routes/settings.py` - API 端点和修复
- `kb/commands/init.py` - 配置迁移

### 文档文件
- `CHANGELOG_0.8.1.md` - 变更日志
- `SETTINGS_UI_REDESIGN.md` - 前端实现指南
- `DEVELOPMENT_SUMMARY_0.8.1.md` - 开发总结
- `TEST_REPORT_0.8.1.md` - 测试报告
- `FINAL_SUMMARY_0.8.1.md` - 最终总结
- `QUICK_REFERENCE_0.8.1.md` - 本文档

## 升级步骤

1. 更新代码到 v0.8.1
2. 重新输入真实 API key（如果之前是掩码）
3. 运行 `localbrain init setup`（可选，自动迁移配置）
4. 配置备份功能（可选）

## 验证

```bash
# 检查配置文件
cat ~/.localbrain/config.yaml

# 应该包含所有配置段：
# - backup
# - chunking
# - data_dir
# - embedding
# - llm
# - logging
# - query
# - storage
# - wiki
```

## 已知问题

用户现有配置文件中的 API key 如果已经是掩码，需要重新输入真实 key。

## 下一步

前端 Tab 界面实现（参考 `SETTINGS_UI_REDESIGN.md`）
