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
