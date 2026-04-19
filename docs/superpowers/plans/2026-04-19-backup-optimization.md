# Backup Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Optimize knowledge base backup functionality with UI improvements, cloud storage configuration, and automatic backup scheduling.

**Architecture:** Three-part implementation: (1) Simplify backup management UI by removing per-backup cloud selection, (2) Extend settings page with cloud storage configuration and storage location selection, (3) Implement scheduler thread in web service for automatic backups with config hot-reload.

**Tech Stack:** Python 3.8+, FastAPI, schedule library, croniter, Vue.js (frontend)

---

## File Structure

### New Files
- `kb/scheduler/__init__.py` - Scheduler package init
- `kb/scheduler/backup_scheduler.py` - Backup scheduler implementation

### Modified Files
- `kb/web/app.py` - Add scheduler initialization on startup/shutdown
- `kb/web/routes/backup.py` - Simplify create_backup API
- `kb/web/routes/settings.py` - Extend backup config API with cloud storage
- `kb/web/static/backup.html` - Simplify UI, remove cloud selection
- `kb/web/static/templates/pages/settings.html` - Add cloud storage config UI
- `kb/web/static/js/pages/settings.js` - Add cloud storage config logic
- `kb/commands/backup.py` - Add cleanup_old_backups function
- `requirements.txt` - Add schedule and croniter dependencies

---

## Task 1: Add Dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add schedule and croniter to requirements.txt**

```txt
schedule>=1.2.0
croniter>=1.4.0
```

- [ ] **Step 2: Install dependencies in local virtual environment**

Run: `source .venv/bin/activate && pip install schedule croniter`
Expected: Successfully installed schedule-1.2.0 croniter-1.4.1 in .venv

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "deps: add schedule and croniter for backup scheduler"
```

---

## Task 2: Create Backup Scheduler Module

**Files:**
- Create: `kb/scheduler/__init__.py`
- Create: `kb/scheduler/backup_scheduler.py`

- [ ] **Step 1: Create scheduler package init file**

```python
"""
Backup scheduler package.
"""
from kb.scheduler.backup_scheduler import BackupScheduler, init_scheduler, stop_scheduler

__all__ = ["BackupScheduler", "init_scheduler", "stop_scheduler"]
```

- [ ] **Step 2: Create backup scheduler implementation (part 1/3)**

File: `kb/scheduler/backup_scheduler.py`

```python
"""
Backup Scheduler

Runs automatic backups based on cron schedule configuration.
Runs in a background thread within the web service.
"""

import logging
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import schedule

from kb.commands.backup import _create_backup_async, _ensure_backup_dir, _load_metadata, _save_metadata
from kb.config import Config

logger = logging.getLogger(__name__)


class BackupScheduler:
    """Backup scheduler that runs in a background thread."""
    
    def __init__(self, config: Config):
        self.config = config
        self.thread = None
        self.stop_event = threading.Event()
        self.running = False
    
    def start(self):
        """Start the scheduler in a background thread."""
        if self.running:
            logger.warning("Backup scheduler already running")
            return
        
        backup_config = self.config.get("backup", {})
        enabled = backup_config.get("enabled", False)
        
        if not enabled:
            logger.info("Automatic backup is disabled")
            return
        
        schedule_expr = backup_config.get("schedule", "0 2 * * *")
        logger.info(f"Starting backup scheduler with schedule: {schedule_expr}")
        
        # Parse cron expression and schedule job
        self._schedule_job(schedule_expr)
        
        # Start scheduler thread
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        
        logger.info("Backup scheduler started")
```

- [ ] **Step 3: Create backup scheduler implementation (part 2/3)**

Append to `kb/scheduler/backup_scheduler.py`:

```python
    
    def stop(self):
        """Stop the scheduler."""
        if not self.running:
            return
        
        logger.info("Stopping backup scheduler")
        self.stop_event.set()
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=5)
        
        schedule.clear()
        logger.info("Backup scheduler stopped")
    
    def _schedule_job(self, cron_expr: str):
        """
        Parse cron expression and schedule the job.
        
        Cron format: minute hour day month day_of_week
        Example: "0 2 * * *" = daily at 2:00 AM
        """
        try:
            parts = cron_expr.split()
            if len(parts) != 5:
                raise ValueError(f"Invalid cron expression: {cron_expr}")
            
            minute, hour, day, month, day_of_week = parts
            
            # Convert cron to schedule library format
            if day == "*" and month == "*" and day_of_week == "*":
                # Daily schedule
                time_str = f"{hour.zfill(2)}:{minute.zfill(2)}"
                schedule.every().day.at(time_str).do(self._run_backup)
                logger.info(f"Scheduled daily backup at {time_str}")
            else:
                # For complex cron patterns, check every hour
                schedule.every().hour.do(self._check_and_run, cron_expr)
                logger.info(f"Scheduled backup with cron: {cron_expr}")
        
        except Exception as e:
            logger.error(f"Failed to parse cron expression '{cron_expr}': {e}")
            # Fallback to daily at 2 AM
            schedule.every().day.at("02:00").do(self._run_backup)
            logger.info("Using fallback schedule: daily at 02:00")
    
    def _check_and_run(self, cron_expr: str):
        """Check if current time matches cron expression and run backup."""
        try:
            from croniter import croniter
            
            now = datetime.now()
            cron = croniter(cron_expr, now)
            next_run = cron.get_next(datetime)
            
            # If next run is within the next hour, run now
            if (next_run - now).total_seconds() < 3600:
                self._run_backup()
        except Exception as e:
            logger.error(f"Failed to check cron expression: {e}")
```

- [ ] **Step 4: Create backup scheduler implementation (part 3/3)**

Append to `kb/scheduler/backup_scheduler.py`:

```python
    
    def _run_backup(self):
        """Execute automatic backup."""
        logger.info("Starting automatic backup")
        
        try:
            _ensure_backup_dir()
            
            # Get storage location from config
            backup_config = self.config.get("backup", {})
            storage_location = backup_config.get("storage_location", "local")
            
            # Determine cloud_provider parameter
            cloud_provider = None if storage_location == "local" else storage_location
            
            # Generate task ID
            task_id = str(uuid.uuid4())[:8]
            
            # Save task metadata
            metadata = _load_metadata()
            metadata["tasks"][task_id] = {
                "id": task_id,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "cloud_provider": cloud_provider,
                "trigger": "automatic"
            }
            _save_metadata(metadata)
            
            # Start backup in background thread
            thread = threading.Thread(
                target=_create_backup_async,
                args=(task_id, None, cloud_provider)
            )
            thread.daemon = False
            thread.start()
            
            logger.info(f"Automatic backup task created: {task_id}")
        
        except Exception as e:
            logger.error(f"Failed to start automatic backup: {e}", exc_info=True)
    
    def _run_scheduler(self):
        """Run the scheduler loop."""
        logger.info("Scheduler loop started")
        
        while not self.stop_event.is_set():
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        
        logger.info("Scheduler loop stopped")


# Global scheduler instance
_scheduler_instance = None


def init_scheduler(config: Config):
    """Initialize and start the global scheduler."""
    global _scheduler_instance
    
    if _scheduler_instance is not None:
        logger.warning("Scheduler already initialized")
        return
    
    _scheduler_instance = BackupScheduler(config)
    _scheduler_instance.start()


def stop_scheduler():
    """Stop the global scheduler."""
    global _scheduler_instance
    
    if _scheduler_instance is not None:
        _scheduler_instance.stop()
        _scheduler_instance = None
```

- [ ] **Step 5: Commit**

```bash
git add kb/scheduler/
git commit -m "feat: add backup scheduler module"
```

---

## Task 3: Configure Scheduler Logging

**Files:**
- Modify: `kb/scheduler/backup_scheduler.py`

- [ ] **Step 1: Add logging configuration at module level**

Add after imports in `kb/scheduler/backup_scheduler.py`:

```python
# Configure scheduler logger
log_dir = Path.home() / ".localbrain" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "scheduler.log"

file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)
```

- [ ] **Step 2: Verify logging works**

Run: `source .venv/bin/activate && python -c "from kb.scheduler.backup_scheduler import logger; logger.info('test')"`
Expected: Log file created at ~/.localbrain/logs/scheduler.log

- [ ] **Step 3: Commit**

```bash
git add kb/scheduler/backup_scheduler.py
git commit -m "feat: configure scheduler logging to ~/.localbrain/logs/scheduler.log"
```

---

## Task 4: Integrate Scheduler with Web Service

**Files:**
- Modify: `kb/web/app.py:14-35`

- [ ] **Step 1: Add scheduler initialization in lifespan**

Replace the lifespan function in `kb/web/app.py`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup: Initialize backup scheduler
    try:
        from kb.scheduler.backup_scheduler import init_scheduler
        from kb.config import Config
        config = Config()
        init_scheduler(config)
        import logging
        logging.getLogger(__name__).info("Backup scheduler initialized")
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to initialize backup scheduler: {e}")
    
    yield
    
    # Shutdown: Stop scheduler and cleanup
    try:
        from kb.scheduler.backup_scheduler import stop_scheduler
        stop_scheduler()
        import logging
        logging.getLogger(__name__).info("Backup scheduler stopped")
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to stop backup scheduler: {e}")
    
    from kb.web import dependencies
    if dependencies._sqlite_storage_instance is not None:
        try:
            dependencies._sqlite_storage_instance.close()
            dependencies._sqlite_storage_instance = None
        except Exception:
            pass
    if dependencies._chroma_storage_instance is not None:
        try:
            dependencies._chroma_storage_instance.close()
            dependencies._chroma_storage_instance = None
        except Exception:
            pass
    if dependencies._pipeline_instance is not None:
        dependencies._pipeline_instance = None
    if dependencies._conversation_manager_instance is not None:
        dependencies._conversation_manager_instance = None
```

- [ ] **Step 2: Test web service starts without errors**

Run: `source .venv/bin/activate && kb web start` (in background)
Expected: Service starts, logs show "Backup scheduler initialized"

- [ ] **Step 3: Stop web service and verify scheduler stops**

Run: `pkill -f "kb web"`
Expected: Logs show "Backup scheduler stopped"

- [ ] **Step 4: Commit**

```bash
git add kb/web/app.py
git commit -m "feat: integrate backup scheduler with web service lifecycle"
```

---

## Task 5: Add Backup Cleanup Function

**Files:**
- Modify: `kb/commands/backup.py`

- [ ] **Step 1: Add cleanup function after _list_s3_backups**

Add to `kb/commands/backup.py`:

```python
def _cleanup_old_backups(retention_days: int):
    """Clean up backups older than retention_days."""
    from datetime import datetime, timedelta
    import logging
    
    logger = logging.getLogger(__name__)
    metadata = _load_metadata()
    backups = metadata.get("backups", [])
    
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    
    backups_to_remove = []
    for backup in backups:
        try:
            created_at = datetime.fromisoformat(backup.get("created_at", ""))
            if created_at < cutoff_date:
                backups_to_remove.append(backup)
        except Exception:
            continue
    
    for backup in backups_to_remove:
        try:
            # Delete local file
            if backup.get("path"):
                backup_file = Path(backup["path"])
                if backup_file.exists():
                    backup_file.unlink()
                    logger.info(f"Deleted old backup file: {backup_file}")
            
            # Remove from metadata
            backups.remove(backup)
            logger.info(f"Removed old backup from metadata: {backup['id']}")
        
        except Exception as e:
            logger.error(f"Failed to cleanup backup {backup.get('id')}: {e}")
    
    # Save updated metadata
    metadata["backups"] = backups
    _save_metadata(metadata)
    
    if backups_to_remove:
        logger.info(f"Cleaned up {len(backups_to_remove)} old backups")
```

- [ ] **Step 2: Update _create_backup_async to call cleanup**

Find the section in `_create_backup_async` after metadata is saved (around line 251), add:

```python
        # Cleanup old backups if this is an automatic backup
        if metadata["tasks"][task_id].get("trigger") == "automatic":
            try:
                from kb.config import Config
                config = Config(CONFIG_FILE)
                retention_days = config.get("backup", {}).get("retention_days", 30)
                _cleanup_old_backups(retention_days)
            except Exception as e:
                logger.error(f"Failed to cleanup old backups: {e}")
```

- [ ] **Step 3: Commit**

```bash
git add kb/commands/backup.py
git commit -m "feat: add automatic cleanup of old backups"
```

---

## Task 6: Simplify Backup API

**Files:**
- Modify: `kb/web/routes/backup.py:37-82`

- [ ] **Step 1: Remove BackupCreateRequest model**

Delete lines 37-38 in `kb/web/routes/backup.py`:

```python
class BackupCreateRequest(BaseModel):
    cloud_provider: Optional[str] = None  # "oss" or "s3"
```

- [ ] **Step 2: Update create_backup endpoint**

Replace the create_backup function (lines 51-82):

```python
@router.post("/backup/create")
async def create_backup():
    """Create a new backup using default storage location from config."""
    _ensure_backup_dir()
    
    # Load config to get default storage location
    config = Config(CONFIG_FILE)
    backup_config = config.get("backup", {})
    storage_location = backup_config.get("storage_location", "local")
    
    # Determine cloud_provider parameter
    cloud_provider = None if storage_location == "local" else storage_location
    
    # Generate task ID
    task_id = str(uuid.uuid4())[:8]
    
    # Save task metadata
    metadata = _load_metadata()
    metadata["tasks"][task_id] = {
        "id": task_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "cloud_provider": cloud_provider,
        "trigger": "manual"
    }
    _save_metadata(metadata)
    
    # Start backup in background thread
    thread = threading.Thread(
        target=_create_backup_async,
        args=(task_id, None, cloud_provider)
    )
    thread.daemon = False
    thread.start()
    
    return {
        "success": True,
        "task_id": task_id,
        "message": "Backup task created",
        "storage_location": storage_location
    }
```

- [ ] **Step 3: Test API with curl**

Run: `curl -X POST http://localhost:8000/api/backup/create`
Expected: Returns task_id and storage_location

- [ ] **Step 4: Commit**

```bash
git add kb/web/routes/backup.py
git commit -m "refactor: simplify backup API to use config storage location"
```

---

## Task 7: Extend Settings API for Cloud Storage

**Files:**
- Modify: `kb/web/routes/settings.py:45-53`
- Modify: `kb/web/routes/settings.py:572-651`

- [ ] **Step 1: Extend BackupConfigRequest model**

Replace BackupConfigRequest in `kb/web/routes/settings.py`:

```python
class BackupConfigRequest(BaseModel):
    """Request model for updating backup configuration."""
    # Basic config
    enabled: bool
    schedule: str
    retention_days: int
    storage_location: str  # "local", "oss", "s3"
    
    # OSS config
    oss_endpoint: Optional[str] = None
    oss_access_key_id: Optional[str] = None
    oss_access_key_secret: Optional[str] = None
    oss_bucket: Optional[str] = None
    
    # S3 config
    s3_region: Optional[str] = None
    s3_access_key_id: Optional[str] = None
    s3_secret_access_key: Optional[str] = None
    s3_bucket: Optional[str] = None
```

- [ ] **Step 2: Update get_backup_settings endpoint (part 1/2)**

Replace get_backup_settings function:

```python
@router.get("/settings/backup")
async def get_backup_settings() -> Dict[str, Any]:
    """Get current backup configuration including cloud storage settings."""
    try:
        raw = _load_raw_config()
        backup = raw.get("backup", {})
        
        return {
            "backup": {
                # Basic config
                "enabled": backup.get("enabled", False),
                "schedule": backup.get("schedule", "0 2 * * *"),
                "retention_days": backup.get("retention_days", 30),
                "storage_location": backup.get("storage_location", "local"),
                
                # OSS config
                "oss_endpoint": backup.get("oss", {}).get("endpoint", ""),
                "oss_access_key_id": _mask_api_key(backup.get("oss", {}).get("access_key_id", "")),
                "oss_access_key_secret": _mask_api_key(backup.get("oss", ).get("access_key_secret", "")),
                "oss_bucket": backup.get("oss", {}).get("bucket", ""),
```

- [ ] **Step 3: Update get_backup_settings endpoint (part 2/2)**

Continue the return statement:

```python
                
                # S3 config
                "s3_region": backup.get("s3", {}).get("region", ""),
                "s3_access_key_id": _mask_api_key(backup.get("s3", {}).get("access_key_id", "")),
                "s3_secret_access_key": _mask_api_key(backup.get("s3", {}).get("secret_access_key", "")),
                "s3_bucket": backup.get("s3", {}).get("bucket", ""),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load backup settings: {str(e)}")
```

- [ ] **Step 4: Commit**

```bash
git add kb/web/routes/settings.py
git commit -m "feat: extend backup settings API with cloud storage config"
```

---

## Task 8: Update Settings API Save Logic

**Files:**
- Modify: `kb/web/routes/settings.py:598-651`

- [ ] **Step 1: Add validation helper function**

Add before update_backup_settings:

```python
def _validate_cron_expression(cron_expr: str) -> bool:
    """Validate cron expression format."""
    try:
        from croniter import croniter
        croniter(cron_expr)
        return True
    except Exception:
        return False
```

- [ ] **Step 2: Update update_backup_settings (part 1/3)**

Replace update_backup_settings function start:

```python
@router.put("/settings/backup")
async def update_backup_settings(request: BackupConfigRequest) -> Dict[str, Any]:
    """Update backup configuration including cloud storage settings."""
    # Validate
    if not request.schedule.strip():
        raise HTTPException(status_code=400, detail="schedule cannot be empty")
    
    if not _validate_cron_expression(request.schedule):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cron expression: {request.schedule}. Format: minute hour day month day_of_week"
        )
    
    if request.retention_days < 1:
        raise HTTPException(status_code=400, detail="retention_days must be at least 1")
    
    if request.storage_location not in ["local", "oss", "s3"]:
        raise HTTPException(status_code=400, detail="storage_location must be local, oss, or s3")
    
    # Validate cloud storage config if selected
    if request.storage_location == "oss":
        if not all([request.oss_endpoint, request.oss_access_key_id,
                   request.oss_access_key_secret, request.oss_bucket]):
            raise HTTPException(status_code=400, detail="OSS configuration incomplete")
    
    if request.storage_location == "s3":
        if not all([request.s3_region, request.s3_access_key_id,
                   request.s3_secret_access_key, request.s3_bucket]):
            raise HTTPException(status_code=400, detail="S3 configuration incomplete")
```

- [ ] **Step 3: Update update_backup_settings (part 2/3)**

Continue the function:

```python
    
    try:
        raw = _load_raw_config()
        existing_backup = raw.get("backup", {})
        
        # Handle masked keys
        oss_access_key_id = request.oss_access_key_id
        if oss_access_key_id and _is_masked_key(oss_access_key_id):
            oss_access_key_id = existing_backup.get("oss", {}).get("access_key_id", "")
        
        oss_access_key_secret = request.oss_access_key_secret
        if oss_access_key_secret and _is_masked_key(oss_access_key_secret):
            oss_access_key_secret = existing_backup.get("oss", {}).get("access_key_secret", "")
        
        s3_access_key_id = request.s3_access_key_id
        if s3_access_key_id and _is_masked_key(s3_access_key_id):
            s3_access_key_id = existing_backup.get("s3", {}).get("access_key_id", "")
        
        s3_secret_access_key = request.s3_secret_access_key
        if s3_secret_access_key and _is_masked_key(s3_secret_access_key):
            s3_secret_access_key = existing_backup.get("s3", {}).get("secret_access_key", "")
        
        # Build new config
        backup_config = {
            "enabled": request.enabled,
            "schedule": request.schedule.strip(),
            "retention_days": request.retention_days,
            "storage_location": request.storage_location,
            "oss": {
                "endpoint": request.oss_endpoint or "",
                "access_key_id": oss_access_key_id or "",
                "access_key_secret": oss_access_key_secret or "",
                "bucket": request.oss_bucket or "",
            },
            "s3": {
                "region": request.s3_region or "",
                "access_key_id": s3_access_key_id or "",
                "secret_access_key": s3_secret_access_key or "",
                "bucket": request.s3_bucket or "",
            }
        }
```

- [ ] **Step 4: Update update_backup_settings (part 3/3)**

Complete the function:

```python
        
        raw["backup"] = backup_config
        _save_raw_config(raw)
        
        # Restart scheduler to apply new config
        from kb.scheduler.backup_scheduler import stop_scheduler, init_scheduler
        from kb.config import Config
        
        stop_scheduler()
        config = Config(CONFIG_FILE)
        init_scheduler(config)
        
        # Invalidate cached config
        try:
            from kb.web.dependencies import get_config
            get_config.cache_clear()
        except Exception:
            pass
        
        return {
            "backup": backup_config,
            "message": "Backup configuration updated successfully. Scheduler restarted."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save backup settings: {str(e)}")
```

- [ ] **Step 5: Test API with curl**

Run: `curl -X PUT http://localhost:8000/api/settings/backup -H "Content-Type: application/json" -d '{"enabled":true,"schedule":"0 2 * * *","retention_days":30,"storage_location":"local"}'`
Expected: Returns success message

- [ ] **Step 6: Commit**

```bash
git add kb/web/routes/settings.py
git commit -m "feat: implement backup config save with validation and scheduler restart"
```

---

## Task 9: Simplify Backup Management UI

**Files:**
- Modify: `kb/web/static/backup.html:228-239`

- [ ] **Step 1: Replace Create New Backup card**

Replace lines 228-239 in backup.html:

```html
        <!-- Create Backup Section -->
        <div class="card">
            <h2>备份管理 / Backup Management</h2>
            <div style="display: flex; gap: 12px; margin-top: 16px;">
                <button id="create-backup-btn" class="btn btn-primary">
                    手工触发备份 / Manual Backup
                </button>
                <button id="goto-settings-btn" class="btn" 
                        style="border: 1px solid var(--border); background: var(--bg);">
                    自动备份配置 / Auto Backup Settings
                </button>
            </div>
            <p style="margin-top: 12px; font-size: 13px; color: #666;">
                手工备份将使用设置中配置的默认存储位置。<br>
                Manual backup uses the default storage location configured in settings.
            </p>
        </div>
```

- [ ] **Step 2: Update JavaScript to remove cloud selection**

Replace the create backup button handler (around line 275):

```javascript
        // Create backup
        document.getElementById('create-backup-btn').addEventListener('click', async () => {
            const btn = document.getElementById('create-backup-btn');

            btn.disabled = true;
            btn.textContent = 'Creating...';

            try {
                const response = await fetch(`${API_BASE}/backup/create`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({})
                });

                const data = await response.json();

                if (data.success) {
                    showAlert(`Backup task created: ${data.task_id}`, 'success');
                    loadTasks();
                    setTimeout(loadBackups, 3000);
                } else {
                    showAlert('Failed to create backup', 'error');
                }
            } catch (error) {
                showAlert(`Error: ${error.message}`, 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = '手工触发备份 / Manual Backup';
            }
        });

        // Navigate to settings
        document.getElementById('goto-settings-btn').addEventListener('click', () => {
            window.location.href = '/settings.html#backup';
        });
```

- [ ] **Step 3: Test UI in browser**

Open: http://localhost:8000/backup.html
Expected: See simplified UI with two buttons

- [ ] **Step 4: Commit**

```bash
git add kb/web/static/backup.html
git commit -m "refactor: simplify backup management UI"
```

---
## Task 10: Add Cloud Storage Config UI to Settings

**Files:**
- Modify: `kb/web/static/templates/pages/settings.html:346-433`

- [ ] **Step 1: Replace backup tab content (part 1/2)**

Replace the backup tab section (lines 346-433) with three blocks:

```html
        <!-- Backup Tab -->
        <div v-if="settingsTab === 'backup'">
            <!-- Block 1: Automatic Backup -->
            <div class="card">
                <div class="card-body">
                    <h3 style="margin-bottom: 4px;">{{ locale === 'en' ? 'Automatic Backup' : '自动备份' }}</h3>
                    <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 20px;">
                        {{ locale === 'en' 
                            ? 'Configure automatic backup schedule and retention policy.' 
                            : '配置自动备份计划和保留策略。' }}
                    </p>
                    
                    <!-- Enable -->
                    <div style="margin-bottom: 16px;">
                        <label style="display: flex; align-items: center; cursor: pointer;">
                            <input type="checkbox" v-model="backupSettings.enabled"
                                   style="margin-right: 8px; width: 16px; height: 16px; cursor: pointer;" />
                            <span style="font-weight: 500;">
                                {{ locale === 'en' ? 'Enable Automatic Backup' : '启用自动备份' }}
                            </span>
                        </label>
                    </div>
                    
                    <!-- Schedule -->
                    <div style="margin-bottom: 16px;">
                        <label style="display: block; font-weight: 500; margin-bottom: 6px;">
                            {{ locale === 'en' ? 'Backup Schedule (Cron)' : '备份计划（Cron 表达式）' }}
                        </label>
                        <input type="text" v-model="backupSettings.schedule"
                               :placeholder="locale === 'en' ? 'e.g. 0 2 * * * (daily at 2 AM)' : '如 0 2 * * *（每天凌晨2点）'"
                               style="width: 100%; max-width: 400px; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px;" />
                    </div>
                    
                    <!-- Retention -->
                    <div style="margin-bottom: 16px;">
                        <label style="display: block; font-weight: 500; margin-bottom: 6px;">
                            {{ locale === 'en' ? 'Retention Days' : '保留天数' }}
                        </label>
                        <input type="number" v-model.number="backupSettings.retention_days" min="1"
                               style="width: 100%; max-width: 200px; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px;" />
                    </div>
                </div>
            </div>
            
            <!-- Block 2: Storage Location -->
            <div class="card" style="margin-top: 16px;">
                <div class="card-body">
                    <h3 style="margin-bottom: 4px;">{{ locale === 'en' ? 'Storage Location' : '存储位置' }}</h3>
                    <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 20px;">
                        {{ locale === 'en' 
                            ? 'Select default storage location for backups (manual and automatic).' 
                            : '选择备份的默认存储位置（手动和自动备份均使用此配置）。' }}
                    </p>
                    
                    <div style="margin-bottom: 16px;">
                        <label style="display: block; font-weight: 500; margin-bottom: 6px;">
                            {{ locale === 'en' ? 'Default Storage' : '默认存储' }}
                        </label>
                        <select v-model="backupSettings.storage_location"
                                style="width: 100%; max-width: 320px; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px;">
                            <option value="local">{{ locale === 'en' ? 'Local Storage' : '本地存储' }}</option>
                            <option value="oss">{{ locale === 'en' ? 'Alibaba Cloud OSS' : '阿里云 OSS' }}</option>
                            <option value="s3">{{ locale === 'en' ? 'AWS S3' : 'AWS S3' }}</option>
                        </select>
                    </div>
                </div>
            </div>
```

- [ ] **Step 2: Replace backup tab content (part 2/2)**

Continue with Block 3:

```html
            
            <!-- Block 3: Cloud Storage Config -->
            <div class="card" style="margin-top: 16px;">
                <div class="card-body">
                    <h3 style="margin-bottom: 4px;">{{ locale === 'en' ? 'Cloud Storage Configuration' : '云存储配置' }}</h3>
                    <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 20px;">
                        {{ locale === 'en' 
                            ? 'Configure cloud storage credentials for OSS and S3.' 
                            : '配置 OSS 和 S3 的云存储凭证。' }}
                    </p>
                    
                    <!-- OSS Config -->
                    <div style="margin-bottom: 24px; padding: 16px; border: 1px solid var(--border); border-radius: 6px;">
                        <h4 style="margin-bottom: 12px;">Alibaba Cloud OSS</h4>
                        
                        <div style="margin-bottom: 12px;">
                            <label style="display: block; font-weight: 500; margin-bottom: 6px;">Endpoint</label>
                            <input type="text" v-model="backupSettings.oss_endpoint"
                                   placeholder="oss-cn-hangzhou.aliyuncs.com"
                                   style="width: 100%; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px;" />
                        </div>
                        
                        <div style="margin-bottom: 12px;">
                            <label style="display: block; font-weight: 500; margin-bottom: 6px;">Access Key ID</label>
                            <input type="text" v-model="backupSettings.oss_access_key_id"
                                   placeholder="${OSS_ACCESS_KEY_ID} or raw key"
                                   style="width: 100%; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px; font-family: monospace;" />
                        </div>
                        
                        <div style="margin-bottom: 12px;">
                            <label style="display: block; font-weight: 500; margin-bottom: 6px;">Access Key Secret</label>
                            <input type="password" v-model="backupSettings.oss_access_key_secret"
                                   placeholder="${OSS_ACCESS_KEY_SECRET} or raw secret"
                                   style="width: 100%; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px; font-family: monospace;" />
                        </div>
                        
                        <div style="margin-bottom: 12px;">
                            <label style="display: block; font-weight: 500; margin-bottom: 6px;">Bucket</label>
                            <input type="text" v-model="backupSettings.oss_bucket"
                                   placeholder="my-backup-bucket"
                                   style="width: 100%; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px;" />
                        </div>
                    </div>
                    
                    <!-- S3 Config -->
                    <div style="padding: 16px; border: 1px solid var(--border); border-radius: 6px;">
                        <h4 style="margin-bottom: 12px;">AWS S3</h4>
                        
                        <div style="margin-bottom: 12px;">
                            <label style="display: block; font-weight: 500; margin-bottom: 6px;">Region</label>
                            <input type="text" v-model="backupSettings.s3_region"
                                   placeholder="us-west-2"
                                   style="width: 100%; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px;" />
                        </div>
                        
                        <div style="margin-bottom: 12px;">
                            <label style="display: block; font-weight: 500; margin-bottom: 6px;">Access Key ID</label>
                            <input type="text" v-model="backupSettings.s3_access_key_id"
                                   placeholder="${AWS_ACCESS_KEY_ID} or raw key"
                                   style="width: 100%; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px; font-family: monospace;" />
                        </div>
                        
                        <div style="margin-bottom: 12px;">
                            <label style="display: block; font-weight: 500; margin-bottom: 6px;">Secret Access Key</label>
                            <input type="password" v-model="backupSettings.s3_secret_access_key"
                                   placeholder="${AWS_SECRET_ACCESS_KEY} or raw secret"
                                   style="width: 100%; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px; font-family: monospace;" />
                        </div>
                        
                        <div style="margin-bottom: 12px;">
                            <label style="display: block; font-weight: 500; margin-bottom: 6px;">Bucket</label>
                            <input type="text" v-model="backupSettings.s3_bucket"
                                   placeholder="my-backup-bucket"
                                   style="width: 100%; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px;" />
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Save Button -->
            <div style="margin-top: 20px;">
                <button @click="saveBackupSettings" :disabled="backupSettingsSaving"
                        style="padding: 10px 24px; background: var(--primary); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 14px;">
                    {{ backupSettingsSaving ? (locale === 'en' ? 'Saving...' : '保存中...') : (locale === 'en' ? 'Save Settings' : '保存设置') }}
                </button>
                <span v-if="backupSettingsSaved" style="margin-left: 12px; color: var(--success); font-size: 14px;">
                    ✓ {{ locale === 'en' ? 'Saved successfully' : '保存成功' }}
                </span>
                <span v-if="backupSettingsError" style="margin-left: 12px; color: var(--danger); font-size: 14px;">
                    {{ backupSettingsError }}
                </span>
            </div>
        </div>
```

- [ ] **Step 3: Commit**

```bash
git add kb/web/static/templates/pages/settings.html
git commit -m "feat: add cloud storage configuration UI to settings"
```

---

## Task 11: Add Settings JavaScript Logic

**Files:**
- Modify: `kb/web/static/js/pages/settings.js`

- [ ] **Step 1: Extend Vue data model**

Add to the data() return object:

```javascript
        backupSettings: {
            enabled: false,
            schedule: '0 2 * * *',
            retention_days: 30,
            storage_location: 'local',
            oss_endpoint: '',
            oss_access_key_id: '',
            oss_access_key_secret: '',
            oss_bucket: '',
            s3_region: '',
            s3_access_key_id: '',
            s3_secret_access_key: '',
            s3_bucket: ''
        },
        backupSettingsSaving: false,
        backupSettingsSaved: false,
        backupSettingsError: ''
```

- [ ] **Step 2: Add loadBackupSettings method**

Add to methods:

```javascript
        async loadBackupSettings() {
            try {
                const response = await fetch('/api/settings/backup');
                const data = await response.json();
                
                if (data.backup) {
                    this.backupSettings = { ...data.backup };
                }
            } catch (error) {
                console.error('Failed to load backup settings:', error);
            }
        },
```

- [ ] **Step 3: Add saveBackupSettings method**

Add to methods:

```javascript
        async saveBackupSettings() {
            this.backupSettingsSaving = true;
            this.backupSettingsSaved = false;
            this.backupSettingsError = '';
            
            try {
                const response = await fetch('/api/settings/backup', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.backupSettings)
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    this.backupSettingsSaved = true;
                    setTimeout(() => {
                        this.backupSettingsSaved = false;
                    }, 3000);
                } else {
                    this.backupSettingsError = data.detail || 'Failed to save settings';
                }
            } catch (error) {
                this.backupSettingsError = error.message;
            } finally {
                this.backupSettingsSaving = false;
            }
        },
```

- [ ] **Step 4: Call loadBackupSettings in mounted**

Add to mounted() hook:

```javascript
        this.loadBackupSettings();
```

- [ ] **Step 5: Test in browser**

Open: http://localhost:8000/settings.html#backup
Expected: See three blocks with all fields

- [ ] **Step 6: Commit**

```bash
git add kb/web/static/js/pages/settings.js
git commit -m "feat: add backup settings JavaScript logic"
```

---

## Task 12: Integration Testing

**Files:**
- Test: All components together

- [ ] **Step 1: Test automatic backup scheduling**

Run: `source .venv/bin/activate && kb web start` (check logs in background)
Expected: "Backup scheduler initialized" in logs

- [ ] **Step 2: Test manual backup with default storage**

Run: Click "Manual Backup" button in UI (with web service running in venv)
Expected: Backup created using storage_location from config

- [ ] **Step 3: Test settings save and scheduler restart**

Run: Change backup schedule in settings and save (with web service running in venv)
Expected: Scheduler restarts with new schedule

- [ ] **Step 4: Test backup cleanup**

Run: Create multiple backups, wait for automatic backup (with web service running in venv)
Expected: Old backups cleaned up based on retention_days

- [ ] **Step 5: Verify logs**

Run: `tail -f ~/.localbrain/logs/scheduler.log`
Expected: See scheduler activity and backup triggers

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "test: verify backup optimization integration"
```

---

## Self-Review Checklist

**Spec Coverage:**
- [x] Backup management UI simplified (Task 9)
- [x] Cloud storage configuration UI added (Task 10-11)
- [x] Automatic backup scheduler implemented (Task 2-4)
- [x] Config hot-reload on settings save (Task 8)
- [x] Backup cleanup strategy (Task 5)
- [x] API simplified to use config storage (Task 6)
- [x] Settings API extended with cloud storage (Task 7-8)

**No Placeholders:**
- [x] All code blocks are complete
- [x] All file paths are exact
- [x] All commands have expected output
- [x] No TBD or TODO markers

**Type Consistency:**
- [x] BackupConfigRequest fields match across tasks
- [x] storage_location values consistent (local/oss/s3)
- [x] API response fields match frontend expectations
- [x] Config structure matches between backend and frontend

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-19-backup-optimization.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
