"""
Backup API routes for FastAPI web application.

Provides REST API endpoints for backup management:
- Create backup
- List backups
- Get backup status
- Delete backup
- Get/update backup configuration
"""

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from kb.commands.backup import (
    METADATA_FILE,
    _create_backup_async,
    _ensure_backup_dir,
    _list_oss_backups,
    _list_s3_backups,
    _load_metadata,
    _save_metadata,
)
from kb.commands.utils import CONFIG_FILE
from kb.config import Config

router = APIRouter()


class BackupConfigRequest(BaseModel):
    cloud_provider: str  # "oss" or "s3"
    endpoint: Optional[str] = None
    region: Optional[str] = None
    access_key_id: str
    access_key_secret: Optional[str] = None
    secret_access_key: Optional[str] = None
    bucket: str


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


@router.get("/backup/list")
async def list_backups(cloud: Optional[str] = None):
    """List all backups"""
    config = Config(CONFIG_FILE)
    metadata = _load_metadata()
    local_backups = metadata.get("backups", [])

    all_backups = []

    # Add local backups
    if not cloud or cloud == "local":
        all_backups.extend([b for b in local_backups if not b.get("cloud_provider")])

    # Add cloud backups from metadata
    if cloud in ["oss", "s3"]:
        all_backups.extend([b for b in local_backups if b.get("cloud_provider") == cloud])

    # Also fetch from cloud directly
    if not cloud or cloud == "oss":
        try:
            cloud_backups = _list_oss_backups(config)
            all_backups.extend(cloud_backups)
        except Exception:
            pass

    if not cloud or cloud == "s3":
        try:
            cloud_backups = _list_s3_backups(config)
            all_backups.extend(cloud_backups)
        except Exception:
            pass

    # Sort by created_at
    all_backups.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    # Normalize location field for each backup
    for backup in all_backups:
        if not backup.get('location'):
            backup['location'] = backup.get('cloud_location') or backup.get('path')

    return {
        "success": True,
        "backups": all_backups,
        "count": len(all_backups)
    }


@router.get("/backup/status/{task_id}")
async def get_backup_status(task_id: str):
    """Get backup task status"""
    metadata = _load_metadata()
    tasks = metadata.get("tasks", {})

    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]
    return {
        "success": True,
        "task": task
    }


@router.get("/backup/status")
async def list_backup_tasks():
    """List all backup tasks"""
    metadata = _load_metadata()
    tasks = metadata.get("tasks", {})

    # Convert to list and sort by created_at
    task_list = [
        {**task, "id": tid}
        for tid, task in tasks.items()
    ]
    task_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return {
        "success": True,
        "tasks": task_list,
        "count": len(task_list)
    }


@router.delete("/backup/{backup_id}")
async def delete_backup(backup_id: str):
    """Delete a backup"""
    metadata = _load_metadata()
    backups = metadata.get("backups", [])

    # Find and remove backup
    backup_info = None
    for i, b in enumerate(backups):
        if b["id"] == backup_id:
            backup_info = backups.pop(i)
            break

    if not backup_info:
        raise HTTPException(status_code=404, detail="Backup not found")

    # Delete local file if exists
    if backup_info.get("path"):
        backup_file = Path(backup_info["path"])
        if backup_file.exists():
            backup_file.unlink()

    # TODO: Delete from cloud storage if cloud_location exists

    _save_metadata(metadata)

    return {
        "success": True,
        "message": "Backup deleted"
    }


@router.get("/backup/config")
async def get_backup_config():
    """Get backup configuration"""
    config = Config(CONFIG_FILE)

    return {
        "success": True,
        "config": {
            "cloud_provider": config.get("backup.cloud_provider", "oss"),
            "oss": {
                "endpoint": config.get("backup.oss.endpoint", ""),
                "bucket": config.get("backup.oss.bucket", ""),
                "access_key_id": config.get("backup.oss.access_key_id", "")
            },
            "s3": {
                "region": config.get("backup.s3.region", ""),
                "bucket": config.get("backup.s3.bucket", ""),
                "access_key_id": config.get("backup.s3.access_key_id", "")
            }
        }
    }


@router.post("/backup/config")
async def update_backup_config(request: BackupConfigRequest):
    """Update backup configuration"""
    config = Config(CONFIG_FILE)

    # Update configuration
    config.set("backup.cloud_provider", request.cloud_provider)

    if request.cloud_provider == "oss":
        if request.endpoint:
            config.set("backup.oss.endpoint", request.endpoint)
        config.set("backup.oss.access_key_id", request.access_key_id)
        if request.access_key_secret:
            config.set("backup.oss.access_key_secret", request.access_key_secret)
        config.set("backup.oss.bucket", request.bucket)
    elif request.cloud_provider == "s3":
        if request.region:
            config.set("backup.s3.region", request.region)
        config.set("backup.s3.access_key_id", request.access_key_id)
        if request.secret_access_key:
            config.set("backup.s3.secret_access_key", request.secret_access_key)
        config.set("backup.s3.bucket", request.bucket)

    # Save configuration
    config.save()

    return {
        "success": True,
        "message": "Configuration updated"
    }


@router.post("/backup/config/test")
async def test_backup_config():
    """Test backup configuration"""
    config = Config(CONFIG_FILE)
    cloud_provider = config.get("backup.cloud_provider", "oss")

    try:
        if cloud_provider == "oss":
            # Test OSS connection
            import oss2
            endpoint = config.get("backup.oss.endpoint")
            access_key_id = config.get("backup.oss.access_key_id")
            access_key_secret = config.get("backup.oss.access_key_secret")
            bucket_name = config.get("backup.oss.bucket")

            if not all([endpoint, access_key_id, access_key_secret, bucket_name]):
                raise Exception("OSS configuration incomplete")

            auth = oss2.Auth(access_key_id, access_key_secret)
            bucket = oss2.Bucket(auth, endpoint, bucket_name)
            bucket.get_bucket_info()

            return {
                "success": True,
                "message": "OSS connection successful"
            }

        elif cloud_provider == "s3":
            # Test S3 connection
            import boto3
            region = config.get("backup.s3.region")
            access_key_id = config.get("backup.s3.access_key_id")
            secret_access_key = config.get("backup.s3.secret_access_key")
            bucket_name = config.get("backup.s3.bucket")

            if not all([region, access_key_id, secret_access_key, bucket_name]):
                raise Exception("S3 configuration incomplete")

            s3_client = boto3.client(
                's3',
                region_name=region,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key
            )
            s3_client.head_bucket(Bucket=bucket_name)

            return {
                "success": True,
                "message": "S3 connection successful"
            }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
