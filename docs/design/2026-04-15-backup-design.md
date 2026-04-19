# 知识库备份功能设计方案

**文档版本**: v1.1  
**创建日期**: 2026-04-15  
**更新日期**: 2026-04-15 (增加 Web 实现方案)  
**负责人**: Allen (Team Leader)  
**参与人员**: Steven (PM), Tom (Developer), Alice (QA)

---

## 1. 需求概述

### 1.1 核心需求
为 LocalBrain 知识库系统增加备份功能，支持：
- 整个知识库目录的完整备份
- 手动触发和自动定时备份
- 云存储支持（阿里云 OSS、AWS S3）
- 安全的恢复功能（不直接覆盖现有数据）
- **Web 界面管理**（CLI + Web 双接口）

### 1.2 使用场景
- **数据保护**: 防止意外数据丢失
- **系统迁移**: 支持知识库在不同环境间迁移
- **版本管理**: 保留历史版本以便回溯

---

## 2. 技术架构

### 2.1 当前系统架构
LocalBrain 使用双存储架构：
- **SQLite** (`~/.knowledge-base/db/metadata.db`): 元数据、标签、实体关系、全文索引
- **ChromaDB** (`~/.knowledge-base/db/chroma`): 向量嵌入数据
- **配置文件**: `~/.knowledge-base/config.yaml`

### 2.2 备份范围
完整备份 `~/.knowledge-base` 目录，包括：
- SQLite 数据库文件
- ChromaDB 向量数据目录
- 配置文件
- 日志文件（可选）

---

## 3. 分阶段实现方案

### Phase 1: 核心备份功能（MVP）

#### 3.1.1 功能范围
- ✅ 全量备份（不支持增量）
- ✅ ZIP 压缩格式
- ✅ 后台异步执行
- ✅ 云存储上传（OSS/S3）
- ✅ 本地临时存储（上传后删除）
- ✅ CLI 命令行接口
- ✅ Web 管理界面
- ❌ 暂不实现：备份一致性保证、完整性校验

#### 3.1.2 命令设计
```bash
# 创建备份（后台异步执行）
kb backup create [--cloud <oss|s3>]

# 列出云端备份
kb backup list [--cloud <oss|s3>]

# 查看备份任务状态
kb backup status [<task-id>]
```

#### 3.1.3 技术实现

**备份流程**:
1. 创建临时备份文件：`/tmp/kb-backup-YYYYMMDD-HHMMSS.zip`
2. 使用 `zipfile` 模块打包 `~/.knowledge-base` 目录
3. 后台异步执行（使用 `threading` 模块）
4. 上传到云存储（OSS 或 S3）
5. 上传成功后删除本地临时文件
6. 记录备份元数据

**文件组织**:
- 临时备份位置: `/tmp/kb-backup-YYYYMMDD-HHMMSS.zip`
- 元数据存储: `~/.knowledge-base/backups/metadata.json`
- 云端路径: `<bucket>/localbrain-backups/kb-backup-YYYYMMDD-HHMMSS.zip`

**元数据结构**:
```json
{
  "backups": [
    {
      "id": "backup-20260415-231853",
      "timestamp": "2026-04-15T23:18:53Z",
      "filename": "kb-backup-20260415-231853.zip",
      "size_bytes": 1048576,
      "cloud_provider": "oss",
      "cloud_path": "oss://my-bucket/localbrain-backups/kb-backup-20260415-231853.zip",
      "status": "completed",
      "created_by": "manual"
    }
  ]
}
```

**云存储配置**:
```yaml
# ~/.knowledge-base/config.yaml
backup:
  cloud:
    provider: "oss"  # or "s3"
    oss:
      endpoint: "oss-cn-hangzhou.aliyuncs.com"
      access_key_id: "${OSS_ACCESS_KEY_ID}"
      access_key_secret: "${OSS_ACCESS_KEY_SECRET}"
      bucket: "my-backup-bucket"
    s3:
      region: "us-west-2"
      access_key_id: "${AWS_ACCESS_KEY_ID}"
      secret_access_key: "${AWS_SECRET_ACCESS_KEY}"
      bucket: "my-backup-bucket"
```

#### 3.1.4 异步任务管理
- 使用 `threading.Thread` 在后台执行备份
- 任务状态存储在内存或临时文件
- 支持查询任务进度（running/completed/failed）
- 任务完成后通知用户（可选）

#### 3.1.5 错误处理
- 磁盘空间不足：提前检查 `/tmp` 可用空间
- 云存储连接失败：重试机制（最多 3 次）
- 上传中断：保留本地文件，等待手动重试
- 权限问题：明确错误提示

#### 3.1.6 Web 界面实现

**功能页面**：

1. **备份管理页面** (`/backup`)
   - 创建备份按钮（触发后台任务）
   - 备份列表表格：
     - 列：备份时间、文件名、大小、云端位置、状态、操作
     - 支持排序和筛选
     - 操作：查看详情、删除备份
   - 实时任务状态显示（进行中的备份）
   - 刷新按钮

2. **备份配置页面** (`/backup/settings`)
   - 云存储配置表单：
     - 选择云服务商（OSS/S3）
     - OSS 配置：Endpoint、Access Key ID、Access Key Secret、Bucket
     - S3 配置：Region、Access Key ID、Secret Access Key、Bucket
     - 测试连接按钮
   - 保存配置按钮

**API 端点设计**：

```python
# 备份管理 API
POST   /api/backup/create          # 创建备份
GET    /api/backup/list            # 获取备份列表
GET    /api/backup/status/<id>     # 获取任务状态
DELETE /api/backup/<id>            # 删除备份

# 配置管理 API
GET    /api/backup/config          # 获取当前配置
POST   /api/backup/config          # 保存配置
POST   /api/backup/config/test     # 测试云存储连接

# WebSocket 实时推送
WS     /api/backup/ws              # 实时推送备份进度和状态
```

**前端技术栈**：
- 基于现有的 LocalBrain Web 前端架构
- 使用 React/Vue（根据现有技术栈）
- WebSocket 实时更新任务状态
- 进度条显示备份/上传进度

**UI 组件**：
- 备份列表表格（支持分页）
- 创建备份按钮和确认对话框
- 任务状态卡片（显示进行中的任务）
- 配置表单（云存储凭证）
- 进度条组件（实时更新）
- Toast 通知（成功/失败提示）

**实时状态更新**：
- 使用 WebSocket 推送备份进度
- 消息格式：
```json
{
  "type": "backup_progress",
  "task_id": "backup-20260415-231853",
  "status": "uploading",
  "progress": 45,
  "message": "上传中... 45%"
}
```

**页面布局**：
```
┌─────────────────────────────────────────┐
│  LocalBrain - 备份管理                   │
├─────────────────────────────────────────┤
│  [创建备份]  [刷新]  [配置]              │
├─────────────────────────────────────────┤
│  当前任务：                              │
│  ┌───────────────────────────────────┐  │
│  │ 正在备份... ████████░░░░ 65%     │  │
│  └───────────────────────────────────┘  │
├─────────────────────────────────────────┤
│  备份历史：                              │
│  ┌───────────────────────────────────┐  │
│  │ 时间 | 文件名 | 大小 | 位置 | 操作│  │
│  │ 2026-04-15 23:18 | kb-backup... │  │
│  │ 2026-04-14 02:00 | kb-backup... │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

---

### Phase 2: 自动化与增强

#### 3.2.1 功能范围
- ✅ 定时自动备份（cron 风格配置）
- ✅ 增量备份支持
- ✅ 备份版本管理和清理策略
- ✅ 备份完整性校验（SHA256）

#### 3.2.2 定时备份配置
```yaml
backup:
  schedule:
    enabled: true
    cron: "0 2 * * *"  # 每天凌晨 2 点
    retention_days: 30  # 保留 30 天
```

#### 3.2.3 增量备份策略
- 基于文件修改时间检测变更
- 仅打包变更的文件
- 依赖基准全量备份

---

### Phase 3: 恢复与管理

#### 3.3.1 功能范围
- ✅ 从云端恢复备份
- ✅ 安全恢复机制（恢复前自动备份当前数据）
- ✅ 恢复预览和对比
- ✅ 回滚支持

#### 3.3.2 恢复命令设计
```bash
# 列出可恢复的备份
kb backup list --cloud oss

# 恢复到临时目录预览
kb backup restore <backup-id> --preview

# 确认恢复（自动备份当前数据）
kb backup restore <backup-id> --confirm

# 回滚到恢复前状态
kb backup rollback
```

#### 3.3.3 安全恢复流程
1. 恢复前自动创建当前数据的备份
2. 下载云端备份到临时目录
3. 解压到 `~/.knowledge-base.restore-preview/`
4. 用户确认后，重命名目录完成恢复
5. 保留原数据备份以支持回滚

---

## 4. 关键技术点

### 4.1 云存储集成

**阿里云 OSS**:
- SDK: `oss2`
- 分片上传: 大于 100MB 的文件使用分片上传
- 断点续传: 支持上传中断后继续

**AWS S3**:
- SDK: `boto3`
- 分片上传: 使用 `TransferConfig` 自动处理
- 断点续传: 通过 `upload_fileobj` 实现

### 4.2 异步执行
- 使用 `threading.Thread` 实现后台任务
- 任务状态通过共享变量或文件传递
- 支持任务取消（可选）

### 4.3 临时文件管理
- 备份文件存储在 `/tmp` 目录
- 上传成功后立即删除
- 上传失败时保留文件供手动重试
- 定期清理超过 24 小时的临时备份文件

---

## 5. 测试计划

### 5.1 Phase 1 测试重点（@alice）

**功能测试**:
- ✅ 备份创建和 ZIP 压缩
- ✅ 后台异步执行（不阻塞主进程）
- ✅ 云存储上传（OSS/S3）
- ✅ 备份列表查询
- ✅ 任务状态查询
- ✅ Web 界面功能测试（创建、列表、配置）
- ✅ WebSocket 实时状态更新

**异常场景测试**:
- ❌ 磁盘空间不足
- ❌ 云存储连接失败
- ❌ 上传中断
- ❌ 权限问题
- ❌ 大文件处理（>1GB）
- ❌ Web 界面异常处理（网络断开、超时）

**性能测试**:
- 不同大小知识库的备份时间
- 云存储上传速度
- 后台任务对系统性能的影响
- Web 界面响应速度

**Web UI 测试**:
- 跨浏览器兼容性（Chrome、Firefox、Safari）
- 响应式设计（桌面端、移动端）
- 实时状态更新准确性
- 表单验证和错误提示

### 5.2 Phase 2/3 测试重点
- 定时任务可靠性
- 增量备份正确性
- 恢复功能完整性
- 回滚机制验证

---

## 6. 实施计划

### 6.1 Phase 1 (预计 3-5 天)
- **Day 1-2**: 实现基础备份和 ZIP 压缩功能（CLI）
- **Day 3**: 集成云存储上传（OSS/S3）
- **Day 4**: 实现 Web 界面（备份管理页面、配置页面）
- **Day 5**: 测试和 bug 修复

### 6.2 Phase 2 (预计 3-5 天)
- 实现定时备份
- 增量备份支持
- 版本管理和清理

### 6.3 Phase 3 (预计 3-5 天)
- 实现恢复功能
- 安全机制和回滚
- 完整测试

---

## 7. 风险与限制

### 7.1 已知限制
- **Phase 1 不保证数据一致性**: 备份过程中如有写入，可能导致数据不一致
- **无完整性校验**: Phase 1 不验证备份文件完整性
- **单线程上传**: 大文件上传可能较慢

### 7.2 风险缓解
- **Phase 2 增加一致性保证**: 使用 SQLite VACUUM INTO 创建快照
- **Phase 2 增加校验**: 生成 SHA256 校验和
- **Phase 2 优化上传**: 使用分片并行上传

---

## 8. 后续优化方向

- 支持更多云存储（Google Cloud Storage、Azure Blob）
- 备份加密（AES-256）
- 备份压缩率优化
- 跨区域备份冗余
- Web UI 管理界面

---

## 9. 参考资料

- [阿里云 OSS Python SDK](https://help.aliyun.com/document_detail/32026.html)
- [AWS S3 Boto3 文档](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3.html)
- [Python zipfile 模块](https://docs.python.org/3/library/zipfile.html)
- [Python threading 模块](https://docs.python.org/3/library/threading.html)
