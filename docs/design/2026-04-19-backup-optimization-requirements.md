# 知识库备份功能优化需求

**文档版本**: v1.0  
**创建日期**: 2026-04-19  
**状态**: 需求澄清完成

---

## 1. 需求概述

对现有的知识库备份功能进行优化，主要包括三个方面：
1. 备份管理 UI 调整
2. 系统配置中新增云存储配置
3. 实现自动备份功能

---

## 2. 详细需求

### 2.1 备份管理页面 UI 调整

**当前状态**：
- 页面标题："Create and manage knowledge base backups"
- "Create New Backup" 卡片包含：
  - 云存储选择下拉框（可选：Local only / OSS / S3）
  - "Create Backup" 按钮

**优化需求**：
- 去掉页面描述文字
- 去掉"Create New Backup"卡片中的云存储选择下拉框
- 将"Create Backup"按钮改为"手工触发备份"
- 新增"自动备份配置"按钮，点击时跳转到系统配置的备份配置页面
- 手动触发备份时，使用系统设置中配置的默认存储位置，不再需要每次选择

**设计原则**：
- 简化操作流程，减少用户每次手动备份时的选择步骤
- 统一配置管理，所有备份相关配置集中在系统设置中

---

### 2.2 系统配置 - 备份配置页面改造

**当前状态**：
- 系统配置页面有"备份配置"标签页
- 包含基础配置：启用自动备份、备份计划（Cron）、保留天数、备份目录等

**优化需求**：

将备份配置页面分为三个区块：

#### 区块 1：自动备份配置
- 启用自动备份（复选框）
- 备份计划（Cron 表达式输入框）
  - 示例：`0 2 * * *`（每天凌晨2点）
- 保留天数（数字输入框）
  - 用于自动清理过期备份

#### 区块 2：存储位置配置
- 默认存储位置（下拉选择）
  - 选项：本地存储 / 阿里云 OSS / AWS S3
  - 默认值：本地存储（初次安装时）
  - 说明：手动和自动备份均使用此配置

#### 区块 3：云存储配置
- **阿里云 OSS 配置**（独立区域）
  - Endpoint（如：oss-cn-hangzhou.aliyuncs.com）
  - Access Key ID
  - Access Key Secret
  - Bucket 名称

- **AWS S3 配置**（独立区域）
  - Region（如：us-west-2）
  - Access Key ID
  - Secret Access Key
  - Bucket 名称

**配置说明**：
- 支持环境变量格式：`${OSS_ACCESS_KEY_ID}`
- 密钥字段在显示时需要脱敏（masked）
- 保存时如果是 masked 值，保留原有配置

---

### 2.3 自动备份功能实现

**当前状态**：
- 自动备份功能尚未实现
- 配置文件中有 `backup.enabled` 和 `backup.schedule` 字段，但无实际调度器

**实现需求**：

#### 功能要求
1. **调度器实现**
   - 使用 Python `schedule` 库实现轻量级调度器
   - 在 Web 服务启动时初始化调度器线程
   - 根据配置中的 Cron 表达式定时触发备份

2. **备份逻辑统一**
   - 手动备份和自动备份共用同一套备份逻辑（`_create_backup_async`）
   - 根据配置中的 `backup.storage_location` 决定存储位置
   - 在任务元数据中标记触发方式（manual / automatic）

3. **配置热重载**
   - 当用户更新备份配置时，自动重启调度器以应用新配置
   - 无需重启 Web 服务

4. **备份清理策略**
   - 自动备份完成后，根据 `retention_days` 清理过期备份
   - 删除本地文件和元数据记录
   - 云端备份清理（待后续实现）

#### 技术方案
- **方案选择**：渐进式改造（方案 A）
  - 调度器集成在 Web 服务中，作为后台线程运行
  - 依赖 Web 服务运行，适合本地知识库工具的使用场景
  - 实现简单，风险低，易于测试

- **依赖库**：
  - `schedule>=1.2.0` - 任务调度
  - `croniter>=1.4.0` - Cron 表达式解析
  - 注意：依赖应安装在项目的本地虚拟环境中（如 `.venv/`）

- **日志位置**：
  - `~/.localbrain/logs/scheduler.log`

---

## 3. 配置文件结构

### 3.1 新配置格式

```yaml
backup:
  # 基础配置
  enabled: true                    # 是否启用自动备份
  schedule: "0 2 * * *"           # Cron 表达式
  retention_days: 30              # 保留天数
  storage_location: "local"       # 默认存储位置: local/oss/s3（初次安装默认为 local）
  
  # 云存储配置 - OSS
  oss:
    endpoint: "oss-cn-hangzhou.aliyuncs.com"
    access_key_id: "${OSS_ACCESS_KEY_ID}"
    access_key_secret: "${OSS_ACCESS_KEY_SECRET}"
    bucket: "my-backup-bucket"
  
  # 云存储配置 - S3
  s3:
    region: "us-west-2"
    access_key_id: "${AWS_ACCESS_KEY_ID}"
    secret_access_key: "${AWS_SECRET_ACCESS_KEY}"
    bucket: "my-backup-bucket"
```

### 3.2 配置迁移

**旧格式**（如果存在）：
```yaml
backup:
  cloud:
    provider: "oss"
    oss:
      endpoint: "..."
```

**迁移规则**：
- 当用户保存备份配置时，自动将旧格式转换为新格式
- `backup.cloud.provider` → `backup.storage_location`
- `backup.cloud.oss` → `backup.oss`
- `backup.cloud.s3` → `backup.s3`
- 删除 `backup.cloud` 节点

---

## 4. API 变更

### 4.1 手动备份 API 简化

**旧接口**：
```http
POST /api/backup/create
Content-Type: application/json

{
  "cloud_provider": "oss"  // 可选
}
```

**新接口**：
```http
POST /api/backup/create

// 无请求体，使用配置中的 storage_location
```

**响应**：
```json
{
  "success": true,
  "task_id": "abc12345",
  "message": "Backup task created",
  "storage_location": "oss"
}
```

### 4.2 备份配置 API 扩展

**GET /api/settings/backup** - 返回完整配置（包括云存储）

**PUT /api/settings/backup** - 更新完整配置
- 请求体包含所有配置字段
- 自动执行配置格式迁移
- 保存后重启调度器

---

## 5. 用户体验流程

### 5.1 首次配置流程

1. 用户访问"系统设置 > 备份配置"
2. 默认存储位置为"本地存储"
3. 用户可选择切换到云存储（OSS/S3）
4. 如选择云存储，填写云存储凭证
5. 配置自动备份计划（可选）
6. 保存配置

### 5.2 手动备份流程

1. 用户访问"备份管理"页面
2. 点击"手工触发备份"按钮
3. 系统使用配置中的默认存储位置执行备份
4. 在"备份任务"区域查看进度
5. 完成后在"备份历史"中查看结果

### 5.3 自动备份流程

1. Web 服务启动时初始化调度器
2. 调度器根据 Cron 表达式定时触发备份
3. 备份完成后自动清理过期备份
4. 用户可在"备份管理"页面查看自动备份的历史记录

---

## 6. 边界情况与约束

### 6.1 约束条件

- 调度器依赖 Web 服务运行，服务停止时自动备份不会执行
- 最多允许 3 个并发备份任务
- 备份前检查磁盘空间，至少需要 1GB 可用空间
- 选择云存储时，必须完整配置云存储凭证

### 6.2 错误处理

- Cron 表达式格式验证
- 云存储配置完整性验证
- 磁盘空间不足时拒绝备份
- 并发备份数量限制
- 调度器异常恢复机制

---

## 7. 非功能需求

### 7.1 性能要求

- 备份操作在后台异步执行，不阻塞主服务
- 调度器每分钟检查一次待执行任务
- 配置更新后 1 分钟内生效（重启调度器）

### 7.2 安全要求

- 支持环境变量存储敏感信息
- API 返回时脱敏显示密钥
- 保存时保留原有密钥（如前端发送 masked 值）

### 7.3 可维护性

- 调度器日志独立记录：`~/.localbrain/logs/scheduler.log`
- 备份任务元数据包含触发方式（manual/automatic）
- 配置格式向后兼容，自动迁移

---

## 8. 验收标准

### 8.1 功能验收

- [ ] 备份管理页面 UI 符合设计要求
- [ ] 系统配置页面三个区块正确显示
- [ ] 手动备份使用配置中的默认存储位置
- [ ] 自动备份按 Cron 表达式定时执行
- [ ] 配置更新后调度器自动重启
- [ ] 过期备份自动清理

### 8.2 兼容性验收

- [ ] 旧配置格式自动迁移为新格式
- [ ] 现有备份数据和元数据不受影响
- [ ] API 向后兼容（旧客户端仍可使用）

### 8.3 错误处理验收

- [ ] 无效 Cron 表达式被拒绝
- [ ] 云存储配置不完整时提示错误
- [ ] 磁盘空间不足时拒绝备份
- [ ] 并发备份超限时返回 429 错误
- [ ] 调度器异常时自动恢复或停止

---

## 9. 后续优化方向

- 备份进度实时推送（WebSocket）
- 云端备份文件的删除功能
- 备份恢复功能增强
- 独立调度器模式（可选）
- 备份加密支持
