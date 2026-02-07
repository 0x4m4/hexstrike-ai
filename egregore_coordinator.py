#!/usr/bin/env python3
import os
import json
import time
import uuid
import logging
import threading
from typing import Dict, List, Any

# OMEGA Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("EGREGORE-STRIKE")

class EgregoreNode:
    """A modular agent node capable of executing specific dominance tasks."""
    def __init__(self, node_id: str, node_type: str):
        self.node_id = node_id
        self.node_type = node_type
        self.status = "IDLE"
        self.last_seen = time.time()
        self.task_history = []

    def to_dict(self):
        return {
            "id": self.node_id,
            "type": self.node_type,
            "status": self.status,
            "last_seen": self.last_seen
        }

class EgregoreCoordinator:
    """The master cognitive layer for OMEGA's distributed hive mind."""
    def __init__(self):
        self.nodes: Dict[str, EgregoreNode] = {}
        self.task_queue: List[Dict[str, Any]] = []
        self.active_tasks: Dict[str, Any] = {}
        
        # Internal auto-start of the coordinate heartbeat
        self._start_heartbeat()
        logger.warning("👁️ [EGREGORE] Collective Intelligence Coordinator Activated.")

    def _start_heartbeat(self):
        def heartbeat_loop():
            while True:
                self._prune_dead_nodes()
                self._process_tasks()
                time.sleep(10)
        threading.Thread(target=heartbeat_loop, daemon=True).start()

    def register_node(self, node_type: str = "GENERIC_WORKER") -> str:
        node_id = f"EGR-{uuid.uuid4().hex[:6].upper()}"
        self.nodes[node_id] = EgregoreNode(node_id, node_type)
        logger.info(f"🕸️ [EGREGORE] Node Registered: {node_id} [Type: {node_type}]")
        return node_id

    def submit_task(self, task_type: str, params: Dict[str, Any]) -> str:
        task_id = f"TSK-{uuid.uuid4().hex[:8].upper()}"
        task = {
            "id": task_id,
            "type": task_type,
            "params": params,
            "status": "QUEUED",
            "ts": time.time()
        }
        self.task_queue.append(task)
        logger.info(f"📋 [EGREGORE] Task Submitted: {task_id} [{task_type}]")
        return task_id

    def _prune_dead_nodes(self):
        now = time.time()
        dead = [nid for nid, node in self.nodes.items() if now - node.last_seen > 60]
        for nid in dead:
            logger.warning(f"💀 [EGREGORE] Node Timeout: {nid}")
            del self.nodes[nid]

    def _process_tasks(self):
        if not self.task_queue:
            return

        for node_id, node in self.nodes.items():
            if node.status == "IDLE" and self.task_queue:
                task = self.task_queue.pop(0)
                node.status = "BUSY"
                self.active_tasks[task['id']] = {
                    "task": task,
                    "node": node_id,
                    "started_at": time.time()
                }
                logger.info(f"🚀 [EGREGORE] Dispatching {task['id']} to {node_id}")

    def get_hive_status(self) -> Dict[str, Any]:
        return {
            "active_nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "queued_tasks": len(self.task_queue),
            "active_tasks": len(self.active_tasks),
            "total_nodes_seen": len(self.nodes)
        }

# Global Singleton
egregore_singleton = EgregoreCoordinator()
