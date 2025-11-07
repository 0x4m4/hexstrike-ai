#!/usr/bin/env python3
"""
Background Scheduler for MindSync Oracle

Runs periodic tasks for autonomous operation:
- Goal processing
- Pattern analysis
- CVE monitoring
- Memory cleanup
"""

import logging
from typing import Callable, Optional
from datetime import datetime
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class BackgroundScheduler:
    """
    Manages background periodic tasks for autonomous operation.

    This is what enables true autonomous behavior - tasks run without
    user prompting.
    """

    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.jobs = {}
        logger.info("Background scheduler initialized")

    def start(self):
        """Start the scheduler."""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            logger.info("📅 Background scheduler started")

    def stop(self):
        """Stop the scheduler."""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Background scheduler stopped")

    def add_job(self, job_id: str, func: Callable,
                interval_seconds: Optional[int] = None,
                interval_minutes: Optional[int] = None,
                interval_hours: Optional[int] = None,
                interval_days: Optional[int] = None,
                cron: Optional[str] = None):
        """
        Add a job to the scheduler.

        Args:
            job_id: Unique job identifier
            func: Function to execute (can be async)
            interval_seconds: Run every N seconds
            interval_minutes: Run every N minutes
            interval_hours: Run every N hours
            interval_days: Run every N days
            cron: Cron expression (alternative to interval)
        """
        if job_id in self.jobs:
            logger.warning(f"Job {job_id} already exists, replacing")
            self.remove_job(job_id)

        # Determine trigger
        if cron:
            trigger = CronTrigger.from_crontab(cron)
        else:
            trigger = IntervalTrigger(
                seconds=interval_seconds or 0,
                minutes=interval_minutes or 0,
                hours=interval_hours or 0,
                days=interval_days or 0
            )

        # Add job
        job = self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            name=job_id,
            replace_existing=True
        )

        self.jobs[job_id] = job
        logger.info(f"Added job: {job_id}")

        return job

    def remove_job(self, job_id: str):
        """Remove a job from the scheduler."""
        if job_id in self.jobs:
            self.scheduler.remove_job(job_id)
            del self.jobs[job_id]
            logger.info(f"Removed job: {job_id}")

    def pause_job(self, job_id: str):
        """Pause a job."""
        if job_id in self.jobs:
            self.scheduler.pause_job(job_id)
            logger.info(f"Paused job: {job_id}")

    def resume_job(self, job_id: str):
        """Resume a paused job."""
        if job_id in self.jobs:
            self.scheduler.resume_job(job_id)
            logger.info(f"Resumed job: {job_id}")

    def get_jobs(self):
        """Get all scheduled jobs."""
        return self.scheduler.get_jobs()

    def get_job_status(self, job_id: str):
        """Get status of a specific job."""
        job = self.jobs.get(job_id)
        if job:
            return {
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'pending': job.pending
            }
        return None


class MindSyncScheduler:
    """
    Pre-configured scheduler for MindSync Oracle tasks.

    Sets up all the autonomous background tasks.
    """

    def __init__(self, goal_engine, memory_manager, notification_system):
        """
        Initialize MindSync scheduler with required components.

        Args:
            goal_engine: GoalDirectedEngine instance
            memory_manager: MemoryManager instance
            notification_system: NotificationSystem instance
        """
        self.scheduler = BackgroundScheduler()
        self.goal_engine = goal_engine
        self.memory = memory_manager
        self.notifier = notification_system

        self._setup_jobs()

    def _setup_jobs(self):
        """Set up all background jobs."""
        logger.info("Setting up background jobs...")

        # Goal processor - check and process goals every minute
        self.scheduler.add_job(
            'goal_processor',
            self._process_goals,
            interval_minutes=1
        )

        # Pattern analyzer - analyze patterns every 30 minutes
        self.scheduler.add_job(
            'pattern_analyzer',
            self._analyze_patterns,
            interval_minutes=30
        )

        # Memory cleanup - clean old data weekly
        self.scheduler.add_job(
            'memory_cleanup',
            self._cleanup_memory,
            interval_days=7
        )

        logger.info("Background jobs configured")

    async def _process_goals(self):
        """Process active goals autonomously."""
        try:
            active_goals = self.memory.get_active_goals()

            if not active_goals:
                return

            logger.debug(f"Processing {len(active_goals)} active goals")

            # Process each goal
            for goal in active_goals[:3]:  # Limit to 3 concurrent
                try:
                    # Check if goal needs work
                    if goal['progress'] < 1.0:
                        logger.info(f"Working on goal: {goal['goal_text']}")

                        # This would trigger actual goal execution
                        # For now, we log it
                        # In production, this calls goal_engine.work_on_goal(goal)

                except Exception as e:
                    logger.error(f"Error processing goal {goal['id']}: {e}")

        except Exception as e:
            logger.error(f"Error in goal processor: {e}", exc_info=True)

    async def _analyze_patterns(self):
        """Analyze user patterns and suggest improvements."""
        try:
            patterns = self.memory.get_patterns(min_confidence=0.7)

            logger.debug(f"Analyzing {len(patterns)} patterns")

            # Look for actionable patterns
            for pattern in patterns:
                if pattern['occurrence_count'] >= 5:  # Strong pattern
                    # Check if we've already notified about this
                    pattern_key = f"{pattern['pattern_type']}_{pattern['pattern_data']}"

                    # Could suggest workflow improvements
                    # For now, just log
                    logger.info(f"Strong pattern detected: {pattern['pattern_type']}")

        except Exception as e:
            logger.error(f"Error analyzing patterns: {e}", exc_info=True)

    async def _cleanup_memory(self):
        """Clean up old data from memory."""
        try:
            logger.info("Running memory cleanup...")

            # In production, this would:
            # - Remove old conversations (>365 days)
            # - Archive completed goals
            # - Compress old data
            # - Backup database

            logger.info("Memory cleanup completed")

        except Exception as e:
            logger.error(f"Error in memory cleanup: {e}", exc_info=True)

    def add_cve_monitor(self, project_id: int, check_interval_hours: int = 6):
        """
        Add CVE monitoring for a specific project.

        Args:
            project_id: Project ID to monitor
            check_interval_hours: How often to check (default: every 6 hours)
        """
        job_id = f'cve_monitor_{project_id}'

        async def check_cves():
            """Check for new CVEs affecting project."""
            try:
                # Get project details
                projects = self.memory.get_active_projects()
                project = next((p for p in projects if p['id'] == project_id), None)

                if not project:
                    logger.warning(f"Project {project_id} not found")
                    return

                logger.info(f"Checking CVEs for project: {project['project_name']}")

                # In production, this would:
                # 1. Extract technologies from project metadata
                # 2. Query CVE databases
                # 3. Check for new CVEs since last check
                # 4. Notify on critical findings

                # Example notification
                # self.notifier.cve_alert("CVE-2024-XXXX", "CRITICAL", project['project_name'])

            except Exception as e:
                logger.error(f"Error checking CVEs: {e}", exc_info=True)

        self.scheduler.add_job(
            job_id,
            check_cves,
            interval_hours=check_interval_hours
        )

        logger.info(f"CVE monitoring enabled for project {project_id}")

    def add_target_monitor(self, target: str, check_interval_hours: int = 24):
        """
        Monitor a target for changes (new ports, services, etc.).

        Args:
            target: Target to monitor (domain, IP)
            check_interval_hours: How often to check
        """
        job_id = f'target_monitor_{target.replace(".", "_")}'

        async def check_target():
            """Check target for changes."""
            try:
                logger.info(f"Monitoring target: {target}")

                # In production, this would:
                # 1. Run periodic scans (nmap, subdomain enum)
                # 2. Compare with previous results
                # 3. Detect changes (new ports, subdomains, etc.)
                # 4. Notify on significant changes

                # Example:
                # self.notifier.notify(
                #     "Target Change Detected",
                #     f"New port 8080 opened on {target}",
                #     NotificationLevel.WARNING
                # )

            except Exception as e:
                logger.error(f"Error monitoring target: {e}", exc_info=True)

        self.scheduler.add_job(
            job_id,
            check_target,
            interval_hours=check_interval_hours
        )

        logger.info(f"Target monitoring enabled for {target}")

    def start(self):
        """Start the scheduler."""
        self.scheduler.start()

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.stop()


# Global instance
_scheduler: Optional[MindSyncScheduler] = None


def get_scheduler(goal_engine, memory_manager, notification_system) -> MindSyncScheduler:
    """Get or create global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = MindSyncScheduler(goal_engine, memory_manager, notification_system)
    return _scheduler


if __name__ == "__main__":
    # Test scheduler
    import sys
    sys.path.append('..')

    logging.basicConfig(level=logging.INFO)

    async def test_job():
        print(f"[{datetime.now()}] Test job executed!")

    scheduler = BackgroundScheduler()
    scheduler.start()

    # Add test job (every 5 seconds)
    scheduler.add_job('test', test_job, interval_seconds=5)

    print("Scheduler started. Will run test job every 5 seconds.")
    print("Press Ctrl+C to stop...")

    try:
        # Keep running
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
        scheduler.stop()
