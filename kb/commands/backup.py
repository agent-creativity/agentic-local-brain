"""
CLI Backup Commands

Backup commands: create, list, status, restore.
These commands handle knowledge base backup and restore operations with cloud storage support.
"""

import json
import os
import shutil
import threading
import time
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from kb.commands.utils import CONFIG_DIR, CONFIG_FILE
from kb.config import Config


# Backup directory - use /tmp to avoid recursive backup
BACKUP_DIR = Path("/tmp") / "kb-backups"
# Metadata stored in knowledge base to persist across reboots
METADATA_FILE = Path.home() / ".knowledge-base" / "backup-metadata.json"
KB_DIR = Path.home() / ".knowledge-base"


def _ensure_backup_dir():
    """Ensure backup directory exists"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _load_metadata():
    """Load backup metadata"""
    if not METADATA_FILE.exists():
        return {"backups": [], "tasks": {}}

    try:
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"backups": [], "tasks": {}}


def _save_metadata(metadata):
    """Save backup metadata"""
    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def _upload_to_oss(file_path: Path, config: Config) -> str:
    """Upload backup file to Alibaba Cloud OSS"""
    try:
        import oss2
    except ImportError:
        raise Exception("oss2 package not installed. Install with: pip install oss2")

    endpoint = config.get("backup.oss.endpoint")
    access_key_id = config.get("backup.oss.access_key_id")
    access_key_secret = config.get("backup.oss.access_key_secret")
    bucket_name = config.get("backup.oss.bucket")

    if not all([endpoint, access_key_id, access_key_secret, bucket_name]):
        raise Exception("OSS configuration incomplete. Check config.yaml")

    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)

    object_name = f"localbrain-backups/{file_path.name}"
    bucket.put_object_from_file(object_name, str(file_path))

    return f"oss://{bucket_name}/{object_name}"


def _upload_to_s3(file_path: Path, config: Config) -> str:
    """Upload backup file to AWS S3"""
    try:
        import boto3
    except ImportError:
        raise Exception("boto3 package not installed. Install with: pip install boto3")

    region = config.get("backup.s3.region")
    access_key_id = config.get("backup.s3.access_key_id")
    secret_access_key = config.get("backup.s3.secret_access_key")
    bucket_name = config.get("backup.s3.bucket")

    if not all([region, access_key_id, secret_access_key, bucket_name]):
        raise Exception("S3 configuration incomplete. Check config.yaml")

    s3_client = boto3.client(
        's3',
        region_name=region,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key
    )

    object_name = f"localbrain-backups/{file_path.name}"
    s3_client.upload_file(str(file_path), bucket_name, object_name)

    return f"s3://{bucket_name}/{object_name}"


def _list_oss_backups(config: Config) -> list:
    """List backups from Alibaba Cloud OSS"""
    try:
        import oss2
    except ImportError:
        return []

    try:
        endpoint = config.get("backup.oss.endpoint")
        access_key_id = config.get("backup.oss.access_key_id")
        access_key_secret = config.get("backup.oss.access_key_secret")
        bucket_name = config.get("backup.oss.bucket")

        if not all([endpoint, access_key_id, access_key_secret, bucket_name]):
            return []

        auth = oss2.Auth(access_key_id, access_key_secret)
        bucket = oss2.Bucket(auth, endpoint, bucket_name)

        backups = []
        for obj in oss2.ObjectIterator(bucket, prefix="localbrain-backups/"):
            backups.append({
                "filename": obj.key.split("/")[-1],
                "size": obj.size,
                "created_at": datetime.fromtimestamp(obj.last_modified).isoformat(),
                "location": f"oss://{bucket_name}/{obj.key}",
                "cloud": "oss"
            })
        return backups
    except Exception:
        return []


def _list_s3_backups(config: Config) -> list:
    """List backups from AWS S3"""
    try:
        import boto3
    except ImportError:
        return []

    try:
        region = config.get("backup.s3.region")
        access_key_id = config.get("backup.s3.access_key_id")
        secret_access_key = config.get("backup.s3.secret_access_key")
        bucket_name = config.get("backup.s3.bucket")

        if not all([region, access_key_id, secret_access_key, bucket_name]):
            return []

        s3_client = boto3.client(
            's3',
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key
        )

        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix="localbrain-backups/"
        )

        backups = []
        for obj in response.get('Contents', []):
            backups.append({
                "filename": obj['Key'].split("/")[-1],
                "size": obj['Size'],
                "created_at": obj['LastModified'].isoformat(),
                "location": f"s3://{bucket_name}/{obj['Key']}",
                "cloud": "s3"
            })
        return backups
    except Exception:
        return []


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


def _create_backup_async(task_id: str, output_path: Optional[str], cloud_provider: Optional[str]):
    """Create backup in background thread"""
    metadata = _load_metadata()
    config = Config(CONFIG_FILE)

    try:
        # Update task status to running
        metadata["tasks"][task_id]["status"] = "running"
        metadata["tasks"][task_id]["started_at"] = datetime.now().isoformat()
        _save_metadata(metadata)

        # Determine output path
        if output_path:
            backup_file = Path(output_path)
        else:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_file = BACKUP_DIR / f"kb-backup-{timestamp}.zip"

        backup_file.parent.mkdir(parents=True, exist_ok=True)

        # Create zip file
        with zipfile.ZipFile(backup_file, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(KB_DIR):
                # Skip the backups directory itself
                if str(BACKUP_DIR) in root:
                    continue

                for file in files:
                    file_path = Path(root) / file
                    try:
                        arcname = file_path.relative_to(KB_DIR.parent)
                        zipf.write(file_path, arcname)
                    except Exception:
                        # Skip files that can't be read (e.g., permission issues)
                        continue

        # Get file size
        file_size = backup_file.stat().st_size

        # Upload to cloud if specified
        cloud_location = None
        if cloud_provider:
            if cloud_provider == "oss":
                cloud_location = _upload_to_oss(backup_file, config)
            elif cloud_provider == "s3":
                cloud_location = _upload_to_s3(backup_file, config)

            # Delete local file after successful upload
            if cloud_location:
                backup_file.unlink()

        # Update metadata
        backup_info = {
            "id": task_id,
            "filename": backup_file.name,
            "path": str(backup_file) if not cloud_provider else None,
            "cloud_location": cloud_location,
            "cloud_provider": cloud_provider,
            "size": file_size,
            "created_at": datetime.now().isoformat(),
            "status": "completed"
        }

        metadata["backups"].append(backup_info)
        metadata["tasks"][task_id]["status"] = "completed"
        metadata["tasks"][task_id]["completed_at"] = datetime.now().isoformat()
        metadata["tasks"][task_id]["backup_file"] = cloud_location if cloud_location else str(backup_file)
        metadata["tasks"][task_id]["size"] = file_size
        _save_metadata(metadata)

        # Cleanup old backups if this is an automatic backup
        if metadata["tasks"][task_id].get("trigger") == "automatic":
            try:
                from kb.config import Config
                config = Config(CONFIG_FILE)
                retention_days = config.get("backup", {}).get("retention_days", 30)
                _cleanup_old_backups(retention_days)
            except Exception as e:
                logger.error(f"Failed to cleanup old backups: {e}")

    except Exception as e:
        # Update task status to failed
        metadata["tasks"][task_id]["status"] = "failed"
        metadata["tasks"][task_id]["error"] = str(e)
        metadata["tasks"][task_id]["failed_at"] = datetime.now().isoformat()
        _save_metadata(metadata)


@click.group()
def backup():
    """Backup management"""
    pass


@backup.command("create")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--cloud", "-c", type=click.Choice(["oss", "s3"]), help="Upload to cloud storage")
@click.option("--wait", "-w", is_flag=True, help="Wait for backup to complete")
def backup_create(output: Optional[str], cloud: Optional[str], wait: bool):
    """Create a backup of the knowledge base"""
    _ensure_backup_dir()

    # Generate task ID
    task_id = str(uuid.uuid4())[:8]

    # Save task metadata
    metadata = _load_metadata()
    metadata["tasks"][task_id] = {
        "id": task_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "cloud_provider": cloud
    }
    _save_metadata(metadata)

    # Start backup in background thread
    thread = threading.Thread(target=_create_backup_async, args=(task_id, output, cloud))
    thread.daemon = False  # Non-daemon thread so it completes
    thread.start()

    click.echo(f"✓ Backup task created: {task_id}")
    if cloud:
        click.echo(f"  Cloud provider: {cloud}")

    if wait:
        click.echo("  Waiting for backup to complete...")
        thread.join()

        # Check final status
        metadata = _load_metadata()
        task = metadata["tasks"].get(task_id, {})
        if task.get("status") == "completed":
            click.echo(f"✓ Backup completed successfully")
            click.echo(f"  Location: {task.get('backup_file')}")
            size_mb = task.get('size', 0) / (1024 * 1024)
            click.echo(f"  Size: {size_mb:.2f} MB")
        elif task.get("status") == "failed":
            click.echo(f"✗ Backup failed: {task.get('error')}")
        else:
            click.echo(f"  Status: {task.get('status')}")
    else:
        click.echo(f"  Use 'kb backup status {task_id}' to check progress")
        click.echo("  Note: Backup is running in background")


@backup.command("list")
@click.option("--cloud", "-c", type=click.Choice(["oss", "s3", "local"]), help="Filter by location")
def backup_list(cloud: Optional[str]):
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
        cloud_backups = _list_oss_backups(config)
        all_backups.extend(cloud_backups)

    if not cloud or cloud == "s3":
        cloud_backups = _list_s3_backups(config)
        all_backups.extend(cloud_backups)

    if not all_backups:
        click.echo("No backups found.")
        return

    click.echo(f"Available backups ({len(all_backups)}):")
    click.echo("-" * 80)

    for backup_info in sorted(all_backups, key=lambda x: x.get("created_at", ""), reverse=True):
        size_mb = backup_info.get("size", 0) / (1024 * 1024)
        click.echo(f"  File: {backup_info.get('filename', 'N/A')}")
        click.echo(f"  Size: {size_mb:.2f} MB")
        click.echo(f"  Created: {backup_info.get('created_at', 'N/A')}")
        location = backup_info.get("cloud_location") or backup_info.get("location") or backup_info.get("path", "N/A")
        click.echo(f"  Location: {location}")
        click.echo()


@backup.command("status")
@click.argument("task_id", required=False)
def backup_status(task_id: Optional[str]):
    """Check backup task status"""
    metadata = _load_metadata()
    tasks = metadata.get("tasks", {})

    if not tasks:
        click.echo("No backup tasks found.")
        return

    if task_id:
        # Show specific task
        if task_id not in tasks:
            click.echo(f"Task {task_id} not found.")
            return

        task = tasks[task_id]
        click.echo(f"Task: {task_id}")
        click.echo(f"  Status: {task['status']}")
        click.echo(f"  Created: {task['created_at']}")
        if task.get('cloud_provider'):
            click.echo(f"  Cloud: {task['cloud_provider']}")

        if task['status'] == "running":
            click.echo(f"  Started: {task.get('started_at', 'N/A')}")
        elif task['status'] == "completed":
            click.echo(f"  Completed: {task.get('completed_at', 'N/A')}")
            click.echo(f"  Location: {task.get('backup_file', 'N/A')}")
            size_mb = task.get('size', 0) / (1024 * 1024)
            click.echo(f"  Size: {size_mb:.2f} MB")
        elif task['status'] == "failed":
            click.echo(f"  Failed: {task.get('failed_at', 'N/A')}")
            click.echo(f"  Error: {task.get('error', 'Unknown error')}")
    else:
        # Show all tasks
        click.echo(f"Backup tasks ({len(tasks)}):")
        click.echo("-" * 80)

        for tid, task in sorted(tasks.items(), key=lambda x: x[1]['created_at'], reverse=True):
            click.echo(f"  Task: {tid}")
            click.echo(f"  Status: {task['status']}")
            click.echo(f"  Created: {task['created_at']}")
            if task.get('cloud_provider'):
                click.echo(f"  Cloud: {task['cloud_provider']}")
            click.echo()


@backup.command("restore")
@click.argument("backup_id")
@click.option("--target", "-t", type=click.Path(), help="Target directory (default: new directory with timestamp)")
def backup_restore(backup_id: str, target: Optional[str]):
    """Restore from a backup"""
    metadata = _load_metadata()
    backups = metadata.get("backups", [])

    # Find backup by ID
    backup_info = None
    for b in backups:
        if b["id"] == backup_id:
            backup_info = b
            break

    if not backup_info:
        click.echo(f"Backup {backup_id} not found.")
        return

    backup_file = Path(backup_info["path"]) if backup_info.get("path") else None
    if not backup_file or not backup_file.exists():
        click.echo(f"Backup file not found locally. Cloud restore not yet implemented.")
        return

    # Determine target directory
    if target:
        target_dir = Path(target)
    else:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        target_dir = Path.home() / f".knowledge-base-restore-{timestamp}"

    if target_dir.exists():
        click.echo(f"Target directory already exists: {target_dir}")
        click.echo("Please specify a different target or remove the existing directory.")
        return

    try:
        click.echo(f"Restoring backup to: {target_dir}")

        # Extract zip file
        with zipfile.ZipFile(backup_file, "r") as zipf:
            zipf.extractall(target_dir.parent)

        click.echo(f"✓ Backup restored successfully")
        click.echo(f"  Location: {target_dir}")
        click.echo()
        click.echo("To use this restored backup:")
        click.echo(f"  1. Stop any running kb services")
        click.echo(f"  2. Backup your current ~/.knowledge-base if needed")
        click.echo(f"  3. Move {target_dir} to ~/.knowledge-base")

    except Exception as e:
        click.echo(f"Failed to restore backup: {e}", err=True)
        raise SystemExit(1)
