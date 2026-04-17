# LocalBrain 知识库备份功能设计方案

**版本**: v1.0  
**日期**: 2026-04-15  
**状态**: 待审核

## 1. 需求概述

### 1.1 核心需求
- **备份范围**: 整个知识库目录 (`~/.knowledge-base`)
- **触发方式**: 支持手动备份和自动定时备份
- **存储位置**: 支持云存储（阿里云 OSS、AWS S3）
- **恢复功能**: 支持从备份恢复，需要安全机制避免直接覆盖
- **使用场景**: 防止数据丢失、支持知识库迁移

### 1.2 技术约束
- **压缩格式**: ZIP
- **备份策略**: 仅全量备份（不做增量备份）
- **一致性**: 暂不考虑备份一致性保证
- **执行方式**: 后台异步执行，不阻塞用户操作
- **完整性校验**: Phase 1 暂不实现

### 1.3 关键设计决策
- **本地备份位置**: `/tmp/kb-backups/` （避免递归备份问题）
- **本地文件清理**: 上传到云端后自动删除本地备份文件
- **元数据管理**: 元数据文件存储在 `~/.knowledge-base/backup-metadata.json`（不在 /tmp 下）

## 2. 系统架构

### 2.1 当前架构分析
LocalBrain 使用双存储架构：
- **SQLite** (`~/.knowledge-base/db/metadata.db`): 存储元数据、标签、实体关系、全文索引
- **ChromaDB** (`~/.knowledge-base/db/chroma`): 存储向量嵌入数据
- **配置文件** (`~/.knowledge-base/config.yaml`): 系统配置

现有 `kb export` 命令仅导出元数据（JSON/Markdown 格式），不包含向量数据，且无恢复功能。

### 2.2 备份架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    LocalBrain 知识库                          │
│  ~/.knowledge-base/                                          │
│  ├── db/                                                     │
│  │   ├── metadata.db (SQLite)                               │
│  │   └── chroma/ (向量数据)                                  │
│  ├── config.yaml                                             │
│  └── backup-metadata.json (备份元数据)                        │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ kb backup create
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  临时备份目录 /tmp/kb-backups/                │
│  kb-backup-20260415-231853.zip                              │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ 上传到云端
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    云存储 (OSS/S3)                           │
│  bucket/kb-backups/                                         │
│  ├── kb-backup-20260415-231853.zip                          │
│  ├── kb-backup-20260416-120000.zip                          │
│  └── ...                                                    │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ 上传成功后删除本地文件
                          ▼
                    本地临时文件清理
```

## 3. 分阶段实现方案

### Phase 1: 核心备份功能 (MVP)

#### 3.1.1 功能范围
- 全量备份整个 `~/.knowledge-base` 目录
- ZIP 格式压缩，文件名带时间戳
- 本地临时存储在 `/tmp/kb-backups/`
- 后台异步执行
- 备份元数据管理

#### 3.1.2 命令设计
```bash
# 创建备份（后台异步执行）
kb backup create [--output <path>]

# 列出备份（本地 + 云端）
kb backup list [--local | --remote]

# 查看备份任务状态
kb backup status [<task-id>]
```

#### 3.1.3 文件组织
- **临时备份目录**: `/tmp/kb-backups/`
- **备份文件命名**: `kb-backup-YYYYMMDD-HHMMSS.zip`
- **元数据文件**: `~/.knowledge-base/backup-metadata.json`

#### 3.1.4 元数据结构
```json
{
  "backups": [
    {
      "id": "backup-20260415-231853",
      "timestamp": "2026-04-15T23:18:53Z",
      "filename": "kb-backup-20260415-231853.zip",
      "size_bytes": 1048576,
      "location": "local",
      "local_path": "/tmp/kb-backups/kb-backup-20260415-231853.zip",
      "status": "completed",
      "created_at": "2026-04-15T23:18:53Z",
      "completed_at": "2026-04-15T23:19:10Z"
    },
    {
      "id": "backup-20260416-120000",
      "timestamp": "2026-04-16T12:00:00Z",
      "filename": "kb-backup-20260416-120000.zip",
      "size_bytes": 2097152,
      "location": "remote",
      "remote_url": "oss://bucket/kb-backups/kb-backup-20260416-120000.zip",
      "status": "completed",
      "created_at": "2026-04-16T12:00:00Z",
      "completed_at": "2026-04-16T12:01:30Z",
      "uploaded_at": "2026-04-16T12:02:00Z"
    }
  ],
  "tasks": [
    {
      "task_id": "task-abc123",
      "backup_id": "backup-20260415-231853",
      "status": "running",
      "progress": 45,
      "started_at": "2026-04-15T23:18:53Z"
    }
  ]
}
```

#### 3.1.5 技术实现
- **压缩**: Python `zipfile` 模块
- **异步执行**: `threading.Thread` 后台线程
- **进度跟踪**: 通过元数据文件记录任务状态
- **错误处理**: 捕获磁盘空间不足、权限问题等异常

### Phase 2: 云存储 + 自动化

#### 3.2.1 功能范围
- 支持阿里云 OSS 和 AWS S3
- 自动上传到云端
- 上传成功后删除本地临时文件
- 定时自动备份（cron 风格配置）

#### 3.2.2 云存储配置
```yaml
# ~/.knowledge-base/config.yaml
backup:
  cloud:
    provider: "oss"  # 或 "s3"
    oss:
      endpoint: "oss-cn-hangzhou.aliyuncs.com"
      bucket: "my-kb-backups"
      access_key_id: "${OSS_ACCESS_KEY_ID}"
      access_key_secret: "${OSS_ACCESS_KEY_SECRET}"
    s3:
      region: "us-west-2"
      bucket: "my-kb-backups"
      access_key_id: "${AWS_ACCESS_KEY_ID}"
      secret_access_key: "${AWS_SECRET_ACCESS_KEY}"
  schedule:
    enabled: true
    cron: "0 2 * * *"  # 每天凌晨 2 点
```

#### 3.2.3 命令扩展
```bash
# 配置云存储
kb backup config --provider oss --bucket my-kb-backups

# 手动上传到云端
kb backup upload <backup-id>

# 配置定时备份
kb backup schedule --cron "0 2 * * *"
```

#### 3.2.4 技术实现
- **OSS SDK**: `oss2` Python 库
- **S3 SDK**: `boto3` Python 库
- **分片上传**: 支持大文件分片上传
- **断点续传**: 上传失败时支持续传
- **定时任务**: 使用 `schedule` 库或系统 cron

### Phase 3: 恢复 + 管理

#### 3.3.1 功能范围
- 安全恢复机制
- 备份版本管理
- 备份清理策略
- 完整性校验

#### 3.3.2 恢复流程
```
1. 用户执行 kb backup restore <backup-id>
2. 系统自动备份当前知识库（防止误操作）
3. 下载备份文件到临时目录（如果是云端备份）
4. 解压到临时目录 ~/.knowledge-base-restore-temp/
5. 显示恢复预览（文件列表、大小对比）
6. 用户确认后，停止 LocalBrain 服务
7. 重命名当前目录为 ~/.knowledge-base.backup-TIMESTAMP
8. 将恢复目录重命名为 ~/.knowledge-base
9. 重启 LocalBrain 服务
10. 验证恢复成功
```

#### 3.3.3 命令设计
```bash
# 恢复备份（交互式）
kb backup restore <backup-id>

# 恢复到指定目录（不覆盖当前）
kb backup restore <backup-id> --to <path>

# 删除备份
kb backup delete <backup-id>

# 清理旧备份（保留最近 N 个）
kb backup cleanup --keep 10

# 校验备份完整性
kb backup verify <backup-id>
```

## 4. 关键技术点

### 4.1 避免递归备份
- **问题**: 如果备份文件存储在 `~/.knowledge-base/backups/` 下，会被下次备份打包进去
- **解决方案**: 备份文件存储在 `/tmp/kb-backups/`，上传到云端后删除本地文件

### 4.2 异步执行
- **实现**: 使用 `threading.Thread` 在后台执行备份任务
- **进度跟踪**: 通过元数据文件记录任务状态和进度
- **错误处理**: 捕获异常并记录到元数据文件

### 4.3 云存储上传
- **分片上传**: 大文件（>100MB）使用分片上传
- **断点续传**: 上传失败时记录已上传的分片，支持续传
- **并发控制**: 限制同时上传的任务数量

### 4.4 本地文件清理
- **时机**: 上传到云端成功后立即删除本地临时文件
- **失败处理**: 上传失败时保留本地文件，支持重试
- **手动清理**: 提供 `kb backup cleanup --local` 命令清理本地临时文件

### 4.5 元数据管理
- **存储位置**: `~/.knowledge-base/backup-metadata.json`（不在 /tmp 下，避免被系统清理）
- **内容**: 记录所有备份的元数据（本地 + 云端）
- **同步**: 定期从云端同步备份列表

## 5. 异常场景处理

### 5.1 磁盘空间不足
- **检测**: 备份前检查 `/tmp` 目录可用空间
- **处理**: 如果空间不足，提示用户并终止备份

### 5.2 权限问题
- **检测**: 检查 `/tmp/kb-backups/` 目录的读写权限
- **处理**: 如果权限不足，提示用户并终止备份

### 5.3 云存储上传失败
- **重试**: 自动重试 3 次，每次间隔 5 秒
- **保留本地文件**: 上传失败时保留本地备份文件
- **通知**: 记录错误日志，提示用户手动上传

### 5.4 恢复失败
- **回滚**: 如果恢复过程中出错，自动回滚到备份的当前知识库
- **验证**: 恢复后验证数据库完整性
- **通知**: 记录错误日志，提示用户

## 6. 测试计划

### 6.1 Phase 1 测试
- 基本备份创建和列表功能
- 后台异步执行（不阻塞主进程）
- ZIP 压缩包完整性和可解压性
- 异常场景（磁盘空间不足、权限问题）
- 元数据文件正确性

### 6.2 Phase 2 测试
- OSS 上传功能（连接失败、超时、权限不足）
- S3 上传功能（同上）
- 大文件分片上传和断点续传
- 上传成功后本地文件清理
- 定时备份功能

### 6.3 Phase 3 测试
- 恢复功能（本地备份、云端备份）
- 恢复前自动备份当前知识库
- 恢复失败回滚机制
- 备份清理策略
- 完整性校验

## 7. 实施计划

### 7.1 Phase 1 (预计 2-3 天)
- [ ] 实现 `kb backup create` 命令（后台异步）
- [ ] 实现 `kb backup list` 命令（列出本地备份）
- [ ] 实现 `kb backup status` 命令（查看任务状态）
- [ ] 实现元数据管理
- [ ] 单元测试和集成测试

### 7.2 Phase 2 (预计 3-4 天)
- [ ] 实现 OSS 上传功能
- [ ] 实现 S3 上传功能
- [ ] 实现上传后本地文件清理
- [ ] 实现定时备份功能
- [ ] 测试云存储功能

### 7.3 Phase 3 (预计 3-4 天)
- [ ] 实现恢复功能
- [ ] 实现备份管理功能
- [ ] 实现完整性校验
- [ ] 完整的端到端测试

## 8. 风险和缓解措施

### 8.1 风险
1. **数据丢失**: 备份或恢复过程中可能导致数据丢失
2. **云存储成本**: 频繁备份可能导致云存储成本增加
3. **性能影响**: 大型知识库备份可能耗时较长

### 8.2 缓解措施
1. **数据丢失**: 恢复前自动备份当前知识库，提供回滚机制
2. **云存储成本**: 提供备份清理策略，用户可配置保留策略
3. **性能影响**: 后台异步执行，不阻塞用户操作

## 9. Web 界面实现

### 9.1 功能概述
为备份功能提供 Web 界面，方便用户通过浏览器管理备份，无需使用命令行。

### 9.2 页面设计

#### 9.2.1 备份管理页面
**路由**: `/backup`

**功能模块**:
1. **创建备份区域**
   - "创建备份" 按钮（主操作按钮）
   - 云存储选择下拉框（本地/OSS/S3）
   - 创建后显示任务 ID 和状态

2. **备份列表**
   - 表格展示所有备份
   - 列：时间、文件名、大小、位置（本地/云端）、状态、操作
   - 操作按钮：下载、删除、恢复
   - 支持筛选（本地/云端）和排序（按时间）
   - 分页显示（每页 20 条）

3. **任务状态区域**
   - 显示当前正在进行的备份任务
   - 实时进度条（百分比）
   - 任务状态：准备中、压缩中、上传中、完成、失败
   - 预计剩余时间

**页面布局**:
```
┌─────────────────────────────────────────────────────────┐
│  备份管理                                    [创建备份]   │
├─────────────────────────────────────────────────────────┤
│  当前任务                                                │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 正在备份... [████████░░] 80%  预计剩余: 2分钟      │  │
│  └───────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│  备份列表                    [本地] [云端] [全部]        │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 时间              文件名           大小    位置  操作│  │
│  │ 2026-04-15 23:18  kb-backup-...  10MB   OSS  [...]│  │
│  │ 2026-04-14 02:00  kb-backup-...  9.8MB  S3   [...]│  │
│  └───────────────────────────────────────────────────┘  │
│                                          [1] 2 3 ... 10 │
└─────────────────────────────────────────────────────────┘
```

#### 9.2.2 云存储配置页面
**路由**: `/backup/config`

**功能模块**:
1. **OSS 配置**
   - Endpoint 输入框
   - Access Key ID 输入框
   - Access Key Secret 输入框（密码类型）
   - Bucket 名称输入框
   - "测试连接" 按钮
   - "保存" 按钮

2. **S3 配置**
   - Region 选择下拉框
   - Access Key ID 输入框
   - Secret Access Key 输入框（密码类型）
   - Bucket 名称输入框
   - "测试连接" 按钮
   - "保存" 按钮

3. **定时备份配置** (Phase 2)
   - 启用/禁用开关
   - Cron 表达式输入框
   - 可视化 Cron 编辑器
   - 下次执行时间预览

**页面布局**:
```
┌─────────────────────────────────────────────────────────┐
│  云存储配置                                              │
├─────────────────────────────────────────────────────────┤
│  阿里云 OSS                                              │
│  Endpoint:     [oss-cn-hangzhou.aliyuncs.com        ]  │
│  Access Key:   [LTAI...                             ]  │
│  Secret Key:   [••••••••••••••••                    ]  │
│  Bucket:       [my-kb-backups                       ]  │
│                              [测试连接]  [保存配置]      │
├─────────────────────────────────────────────────────────┤
│  AWS S3                                                 │
│  Region:       [us-west-2 ▼]                            │
│  Access Key:   [AKIA...                             ]  │
│  Secret Key:   [••••••••••••••••                    ]  │
│  Bucket:       [my-kb-backups                       ]  │
│                              [测试连接]  [保存配置]      │
└─────────────────────────────────────────────────────────┘
```

#### 9.2.3 恢复页面 (Phase 3)
**路由**: `/backup/restore`

**功能模块**:
1. **选择备份**
   - 备份列表（单选）
   - 显示备份详情（时间、大小、来源）

2. **恢复预览**
   - 当前知识库信息
   - 备份内容预览
   - 文件差异对比

3. **恢复确认**
   - 警告提示（将覆盖当前数据）
   - 自动备份当前数据选项（默认勾选）
   - "确认恢复" 按钮

### 9.3 API 接口设计

#### 9.3.1 备份管理 API
```python
# 创建备份
POST /api/backup/create
Request: {
  "cloud_provider": "oss" | "s3" | null,
  "output_path": "/custom/path" (optional)
}
Response: {
  "task_id": "task-abc123",
  "backup_id": "backup-20260415-231853",
  "status": "running"
}

# 获取备份列表
GET /api/backup/list?location=all|local|remote&page=1&size=20
Response: {
  "backups": [...],
  "total": 100,
  "page": 1,
  "size": 20
}

# 获取任务状态
GET /api/backup/status/<task_id>
Response: {
  "task_id": "task-abc123",
  "backup_id": "backup-20260415-231853",
  "status": "running" | "completed" | "failed",
  "progress": 45,
  "message": "正在压缩文件..."
}

# 删除备份
DELETE /api/backup/<backup_id>
Response: {
  "success": true,
  "message": "备份已删除"
}

# 下载备份
GET /api/backup/download/<backup_id>
Response: 文件流
```

#### 9.3.2 云存储配置 API
```python
# 保存 OSS 配置
POST /api/backup/config/oss
Request: {
  "endpoint": "oss-cn-hangzhou.aliyuncs.com",
  "access_key_id": "LTAI...",
  "access_key_secret": "...",
  "bucket": "my-kb-backups"
}
Response: {
  "success": true,
  "message": "配置已保存"
}

# 测试 OSS 连接
POST /api/backup/config/oss/test
Request: { ... }
Response: {
  "success": true,
  "message": "连接成功"
}

# 获取配置
GET /api/backup/config
Response: {
  "oss": { "endpoint": "...", "bucket": "..." },
  "s3": { "region": "...", "bucket": "..." }
}
```

#### 9.3.3 WebSocket 实时推送
```python
# WebSocket 连接
WS /ws/backup/status

# 服务端推送消息格式
{
  "type": "task_update",
  "task_id": "task-abc123",
  "status": "running",
  "progress": 45,
  "message": "正在压缩文件..."
}

{
  "type": "task_completed",
  "task_id": "task-abc123",
  "backup_id": "backup-20260415-231853",
  "message": "备份完成"
}

{
  "type": "task_failed",
  "task_id": "task-abc123",
  "error": "磁盘空间不足"
}
```

### 9.4 前端技术实现

#### 9.4.1 技术栈
- **框架**: React / Vue.js（根据现有项目技术栈）
- **UI 组件库**: Ant Design / Element UI
- **状态管理**: Redux / Vuex
- **HTTP 客户端**: Axios
- **WebSocket**: Socket.io-client / native WebSocket

#### 9.4.2 关键功能实现

**实时进度更新**:
```javascript
// 建立 WebSocket 连接
const ws = new WebSocket('ws://localhost:8000/ws/backup/status');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'task_update') {
    updateTaskProgress(data.task_id, data.progress, data.message);
  }
};

// 创建备份
async function createBackup(cloudProvider) {
  const response = await axios.post('/api/backup/create', {
    cloud_provider: cloudProvider
  });
  
  // 开始监听任务状态
  monitorTask(response.data.task_id);
}
```

**备份列表刷新**:
```javascript
// 定期刷新备份列表
useEffect(() => {
  const interval = setInterval(() => {
    fetchBackupList();
  }, 5000); // 每 5 秒刷新一次
  
  return () => clearInterval(interval);
}, []);
```

### 9.5 后端技术实现

#### 9.5.1 FastAPI 路由
```python
from fastapi import APIRouter, WebSocket
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/backup")

@router.post("/create")
async def create_backup(request: BackupCreateRequest):
    task_id = backup_service.create_backup_async(
        cloud_provider=request.cloud_provider
    )
    return {"task_id": task_id, "status": "running"}

@router.get("/list")
async def list_backups(location: str = "all", page: int = 1, size: int = 20):
    backups = backup_service.list_backups(location, page, size)
    return backups

@router.websocket("/ws/backup/status")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # 订阅任务状态更新
    async for update in backup_service.subscribe_task_updates():
        await websocket.send_json(update)
```

#### 9.5.2 任务状态广播
```python
import asyncio
from typing import Set

class BackupService:
    def __init__(self):
        self.websocket_clients: Set[WebSocket] = set()
    
    async def broadcast_task_update(self, task_id: str, status: str, progress: int):
        message = {
            "type": "task_update",
            "task_id": task_id,
            "status": status,
            "progress": progress
        }
        
        # 广播给所有连接的客户端
        for client in self.websocket_clients:
            await client.send_json(message)
```

### 9.6 实施计划

#### 9.6.1 Phase 1 Web UI (预计 3-4 天)
- [ ] 备份管理页面（创建、列表、状态）
- [ ] API 接口实现（create, list, status）
- [ ] WebSocket 实时推送
- [ ] 前端页面开发和集成

#### 9.6.2 Phase 2 Web UI (预计 2-3 天)
- [ ] 云存储配置页面
- [ ] 配置 API 实现
- [ ] 连接测试功能
- [ ] 定时备份配置界面

#### 9.6.3 Phase 3 Web UI (预计 2-3 天)
- [ ] 恢复页面
- [ ] 恢复预览功能
- [ ] 恢复 API 实现
- [ ] 完整的 UI 测试

### 9.7 UI/UX 设计要点

1. **响应式设计**: 支持桌面和移动端访问
2. **实时反馈**: 通过 WebSocket 实时显示备份进度
3. **错误提示**: 清晰的错误信息和操作建议
4. **确认对话框**: 删除和恢复操作需要二次确认
5. **加载状态**: 所有异步操作显示加载指示器
6. **无障碍支持**: 符合 WCAG 2.1 标准

### 9.8 测试计划

#### 9.8.1 功能测试
- 备份创建、列表、删除功能
- 实时进度更新
- 云存储配置和测试
- 恢复功能

#### 9.8.2 UI 测试
- 跨浏览器兼容性（Chrome, Firefox, Safari, Edge）
- 响应式布局测试（桌面、平板、手机）
- 交互体验测试

#### 9.8.3 性能测试
- 大量备份列表加载性能
- WebSocket 连接稳定性
- 并发用户测试

## 10. 未来优化方向

1. **增量备份**: 基于文件变更检测，只备份变化的文件
2. **加密备份**: 支持备份文件加密
3. **多云支持**: 支持更多云存储提供商（Google Cloud Storage、Azure Blob Storage）
4. **备份压缩优化**: 使用更高效的压缩算法
5. **备份去重**: 跨备份的文件去重，节省存储空间
6. **移动端 App**: 开发独立的移动端应用
