"""
Process Pool Management for HexStrike AI

Intelligent process pool with auto-scaling capabilities for efficient
task execution and resource management.
"""

import logging
import time
import queue
import threading
import psutil
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)


class ProcessPool:
    """Intelligent process pool with auto-scaling capabilities"""

    def __init__(self, min_workers: int = 2, max_workers: int = 20, scale_threshold: float = 0.8):
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.scale_threshold = scale_threshold
        self.workers = []
        self.task_queue = queue.Queue()
        self.results = {}
        self.pool_lock = threading.Lock()
        self.active_tasks = {}
        self.performance_metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "avg_task_time": 0.0,
            "cpu_usage": 0.0,
            "memory_usage": 0.0
        }

        # Initialize minimum workers
        self._scale_up(self.min_workers)

        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_performance, daemon=True)
        self.monitor_thread.start()

    def submit_task(self, task_id: str, func: Callable, *args, **kwargs) -> str:
        """Submit a task to the process pool"""
        task = {
            "id": task_id,
            "func": func,
            "args": args,
            "kwargs": kwargs,
            "submitted_at": time.time(),
            "status": "queued"
        }

        with self.pool_lock:
            self.active_tasks[task_id] = task
            self.task_queue.put(task)

        logger.info(f"📋 Task submitted to pool: {task_id}")
        return task_id

    def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """Get result of a submitted task"""
        with self.pool_lock:
            if task_id in self.results:
                return self.results[task_id]
            elif task_id in self.active_tasks:
                return {"status": self.active_tasks[task_id]["status"], "result": None}
            else:
                return {"status": "not_found", "result": None}

    def _worker_thread(self, worker_id: int):
        """Worker thread that processes tasks"""
        logger.info(f"🔧 Process pool worker {worker_id} started")

        while True:
            try:
                # Get task from queue with timeout
                task = self.task_queue.get(timeout=30)
                if task is None:  # Shutdown signal
                    break

                task_id = task["id"]
                start_time = time.time()

                # Update task status
                with self.pool_lock:
                    if task_id in self.active_tasks:
                        self.active_tasks[task_id]["status"] = "running"
                        self.active_tasks[task_id]["worker_id"] = worker_id
                        self.active_tasks[task_id]["started_at"] = start_time

                try:
                    # Execute task
                    result = task["func"](*task["args"], **task["kwargs"])

                    # Store result
                    execution_time = time.time() - start_time
                    with self.pool_lock:
                        self.results[task_id] = {
                            "status": "completed",
                            "result": result,
                            "execution_time": execution_time,
                            "worker_id": worker_id,
                            "completed_at": time.time()
                        }

                        # Update performance metrics
                        self.performance_metrics["tasks_completed"] += 1
                        self.performance_metrics["avg_task_time"] = (
                            (self.performance_metrics["avg_task_time"] * (self.performance_metrics["tasks_completed"] - 1) + execution_time) /
                            self.performance_metrics["tasks_completed"]
                        )

                        # Remove from active tasks
                        if task_id in self.active_tasks:
                            del self.active_tasks[task_id]

                    logger.info(f"✅ Task completed: {task_id} in {execution_time:.2f}s")

                except Exception as e:
                    # Handle task failure
                    with self.pool_lock:
                        self.results[task_id] = {
                            "status": "failed",
                            "error": str(e),
                            "execution_time": time.time() - start_time,
                            "worker_id": worker_id,
                            "failed_at": time.time()
                        }

                        self.performance_metrics["tasks_failed"] += 1

                        if task_id in self.active_tasks:
                            del self.active_tasks[task_id]

                    logger.error(f"❌ Task failed: {task_id} - {str(e)}")

                self.task_queue.task_done()

            except queue.Empty:
                # No tasks available, continue waiting
                continue
            except Exception as e:
                logger.error(f"💥 Worker {worker_id} error: {str(e)}")

    def _monitor_performance(self):
        """Monitor pool performance and auto-scale"""
        while True:
            try:
                time.sleep(10)  # Monitor every 10 seconds

                with self.pool_lock:
                    queue_size = self.task_queue.qsize()
                    active_workers = len([w for w in self.workers if w.is_alive()])
                    active_tasks_count = len(self.active_tasks)

                # Calculate load metrics
                if active_workers > 0:
                    load_ratio = (active_tasks_count + queue_size) / active_workers
                else:
                    load_ratio = float('inf')

                # Auto-scaling logic
                if load_ratio > self.scale_threshold and active_workers < self.max_workers:
                    # Scale up
                    new_workers = min(2, self.max_workers - active_workers)
                    self._scale_up(new_workers)
                    logger.info(f"📈 Scaled up process pool: +{new_workers} workers (total: {active_workers + new_workers})")

                elif load_ratio < 0.3 and active_workers > self.min_workers:
                    # Scale down
                    workers_to_remove = min(1, active_workers - self.min_workers)
                    self._scale_down(workers_to_remove)
                    logger.info(f"📉 Scaled down process pool: -{workers_to_remove} workers (total: {active_workers - workers_to_remove})")

                # Update performance metrics
                try:
                    cpu_percent = psutil.cpu_percent()
                    memory_info = psutil.virtual_memory()

                    with self.pool_lock:
                        self.performance_metrics["cpu_usage"] = cpu_percent
                        self.performance_metrics["memory_usage"] = memory_info.percent

                except Exception:
                    pass  # Ignore psutil errors

            except Exception as e:
                logger.error(f"💥 Pool monitor error: {str(e)}")

    def _scale_up(self, count: int):
        """Add workers to the pool"""
        with self.pool_lock:
            for i in range(count):
                worker_id = len(self.workers)
                worker = threading.Thread(target=self._worker_thread, args=(worker_id,), daemon=True)
                worker.start()
                self.workers.append(worker)

    def _scale_down(self, count: int):
        """Remove workers from the pool"""
        with self.pool_lock:
            for _ in range(count):
                if len(self.workers) > self.min_workers:
                    # Signal worker to shutdown by putting None in queue
                    self.task_queue.put(None)
                    # Remove from workers list (worker will exit naturally)
                    if self.workers:
                        self.workers.pop()

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get current pool statistics"""
        with self.pool_lock:
            active_workers = len([w for w in self.workers if w.is_alive()])
            return {
                "active_workers": active_workers,
                "queue_size": self.task_queue.qsize(),
                "active_tasks": len(self.active_tasks),
                "performance_metrics": self.performance_metrics.copy(),
                "min_workers": self.min_workers,
                "max_workers": self.max_workers
            }
