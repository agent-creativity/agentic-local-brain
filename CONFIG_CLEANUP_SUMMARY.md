# 配置文件清理总结

## 问题
之前存在两个配置模板文件：
1. `/config-template.yaml` (根目录)
2. `/kb/config-template.yaml` (包内部)

这导致：
- 两个文件内容不一致
- 开发者不清楚应该修改哪个
- 容易造成混淆

## 解决方案

### 1. 确认使用的文件
代码中使用的是 `kb/config-template.yaml`：
```python
# kb/commands/utils.py
TEMPLATE_FILE = Path(__file__).parent.parent / "config-template.yaml"
```

### 2. 同步并增强配置
- 将根目录的云存储配置合并到 `kb/config-template.yaml`
- 更新 `kb/config.py` 中的 `DEFAULT_CONFIG`
- 添加了 OSS 和 S3 云存储支持

### 3. 删除冗余文件
- 删除根目录的 `config-template.yaml`
- 只保留 `kb/config-template.yaml` 作为唯一的配置模板

### 4. 添加文档
创建 `docs/CONFIG_TEMPLATE.md` 说明配置文件的位置和使用方法

## Git 提交记录

```
ab22c69 chore: remove redundant root config-template.yaml
0c62ff8 fix: sync config templates and add cloud storage support to backup config
78a2f00 release: v0.8.1 - Configuration management fixes and backup feature
```

## 当前状态

✅ 只有一个配置模板文件：`kb/config-template.yaml`  
✅ 包含完整的配置项（包括云存储）  
✅ 与 `DEFAULT_CONFIG` 保持同步  
✅ 已推送到远程仓库  
✅ 添加了说明文档

## 配置项增强

备份配置现在支持：
- 本地备份（backup_dir）
- 阿里云 OSS 云存储
- AWS S3 云存储

```yaml
backup:
  enabled: false
  schedule: "0 2 * * *"
  retention_days: 30
  backup_dir: ~/.knowledge-base/backups
  include_db: true
  include_files: true
  compression: true
  cloud_provider: oss  # 新增
  oss:                 # 新增
    endpoint: oss-cn-hangzhou.aliyuncs.com
    access_key_id: ${OSS_ACCESS_KEY_ID}
    access_key_secret: ${OSS_ACCESS_KEY_SECRET}
    bucket: localbrain-backups
  s3:                  # 新增
    region: us-west-2
    access_key_id: ${AWS_ACCESS_KEY_ID}
    secret_access_key: ${AWS_SECRET_ACCESS_KEY}
    bucket: localbrain-backups
```

## 未来维护

修改配置时只需：
1. 编辑 `kb/config-template.yaml`
2. 同步更新 `kb/config.py` 中的 `DEFAULT_CONFIG`
3. 提交更改

不要在根目录创建新的配置文件！
