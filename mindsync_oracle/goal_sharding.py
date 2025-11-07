#!/usr/bin/env python3
"""
MindSync Oracle v6 - Goal Sharding Engine

THE BREAKTHROUGH: Intelligent goal distribution across federated swarm.

Automatically decompose goals and route sub-tasks to appropriate oracles:
- Capability matching (route "scan X" to oracle with tools)
- Load balancing (distribute evenly across available members)
- Priority queuing (urgent goals processed first)
- Execution tracking (monitor distributed task completion)
- Result aggregation (merge outcomes from multiple oracles)

This enables true distributed intelligence.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import asyncio
import json
import time

logger = logging.getLogger(__name__)


class TaskPriority(str, Enum):
    """Task priority levels."""
    URGENT = "urgent"      # Process immediately
    HIGH = "high"          # Process within minutes
    MEDIUM = "medium"      # Process within hours
    LOW = "low"            # Process when idle
    BACKGROUND = "background"  # Process during off-peak


class ShardedTask:
    """Represents a sharded goal sub-task."""

    def __init__(self, task_id: str, goal_id: str, description: str,
                 required_capabilities: List[str], priority: TaskPriority,
                 context: Optional[Dict] = None):
        self.task_id = task_id
        self.goal_id = goal_id
        self.description = description
        self.required_capabilities = required_capabilities
        self.priority = priority
        self.context = context or {}

        # Execution tracking
        self.assigned_to = None
        self.status = "pending"  # pending, assigned, running, completed, failed
        self.created_at = time.time()
        self.assigned_at = None
        self.completed_at = None
        self.result = None
        self.error = None

        # Retry logic
        self.retry_count = 0
        self.max_retries = 3


class GoalShardingEngine:
    """
    Intelligent goal distribution engine.

    Decomposes goals into sub-tasks and routes them to appropriate
    swarm members based on capabilities and load.
    """

    def __init__(self, swarm, config=None):
        """
        Initialize goal sharding engine.

        Args:
            swarm: FederatedSwarm instance
            config: Optional configuration
        """
        self.swarm = swarm
        self.config = config or {}

        # Task tracking
        self.task_queue = defaultdict(deque)  # priority -> deque of tasks
        self.active_tasks = {}  # task_id -> ShardedTask
        self.completed_tasks = {}  # task_id -> ShardedTask

        # Member tracking
        self.member_capabilities = {}  # member_id -> [capabilities]
        self.member_load = defaultdict(int)  # member_id -> active_task_count
        self.member_performance = defaultdict(lambda: {"success": 0, "failure": 0, "avg_time": 0})

        # Sharding parameters
        self.max_tasks_per_member = self.config.get('max_tasks_per_member', 5)
        self.task_timeout = self.config.get('task_timeout', 600)  # 10 minutes

        logger.info("Goal Sharding Engine initialized")

    # ===== GOAL DECOMPOSITION =====

    def decompose_goal(self, goal: str, context: Optional[Dict] = None) -> List[ShardedTask]:
        """
        Decompose goal into sharded sub-tasks.

        Args:
            goal: Goal description
            context: Optional context

        Returns:
            List of ShardedTask objects
        """
        tasks = []
        goal_id = f"goal_{int(time.time() * 1000)}"

        # Analyze goal to determine decomposition strategy
        goal_lower = goal.lower()

        # Pattern 1: Multi-target reconnaissance
        if any(keyword in goal_lower for keyword in ['recon', 'reconnaissance', 'scan', 'enumerate']):
            tasks.extend(self._decompose_recon_goal(goal_id, goal, context))

        # Pattern 2: Vulnerability research
        elif any(keyword in goal_lower for keyword in ['vuln', 'cve', 'exploit', 'research']):
            tasks.extend(self._decompose_research_goal(goal_id, goal, context))

        # Pattern 3: X intelligence gathering
        elif any(keyword in goal_lower for keyword in ['x.com', 'twitter', 'social', 'osint']):
            tasks.extend(self._decompose_x_intelligence_goal(goal_id, goal, context))

        # Pattern 4: Threat monitoring
        elif any(keyword in goal_lower for keyword in ['monitor', 'watch', 'track', 'alert']):
            tasks.extend(self._decompose_monitoring_goal(goal_id, goal, context))

        # Pattern 5: Analysis and reporting
        elif any(keyword in goal_lower for keyword in ['analyze', 'report', 'summarize', 'assess']):
            tasks.extend(self._decompose_analysis_goal(goal_id, goal, context))

        # Pattern 6: Complex multi-phase goals
        elif ' and ' in goal_lower or ' then ' in goal_lower:
            tasks.extend(self._decompose_complex_goal(goal_id, goal, context))

        # Default: Single task
        else:
            tasks.append(ShardedTask(
                task_id=f"{goal_id}_0",
                goal_id=goal_id,
                description=goal,
                required_capabilities=['general'],
                priority=TaskPriority.MEDIUM,
                context=context
            ))

        logger.info(f"Decomposed goal into {len(tasks)} tasks")
        return tasks

    def _decompose_recon_goal(self, goal_id: str, goal: str, context: Optional[Dict]) -> List[ShardedTask]:
        """Decompose reconnaissance goal."""
        tasks = []
        target = self._extract_target(goal)
        if context is None:
            context = {}

        # Task 1: Port scan
        tasks.append(ShardedTask(
            task_id=f"{goal_id}_portscan",
            goal_id=goal_id,
            description=f"Port scan {target}",
            required_capabilities=['tools', 'nmap'],
            priority=TaskPriority.HIGH,
            context={**context, 'target': target, 'phase': 'portscan'}
        ))

        # Task 2: Web enumeration (if web target)
        if any(indicator in goal.lower() for indicator in ['web', 'http', 'website']):
            tasks.append(ShardedTask(
                task_id=f"{goal_id}_webenum",
                goal_id=goal_id,
                description=f"Web enumeration on {target}",
                required_capabilities=['tools', 'web_security'],
                priority=TaskPriority.HIGH,
                context={**context, 'target': target, 'phase': 'web_enum'}
            ))

        # Task 3: CVE research
        tasks.append(ShardedTask(
            task_id=f"{goal_id}_cve",
            goal_id=goal_id,
            description=f"Research CVEs for {target}",
            required_capabilities=['intelligence', 'search'],
            priority=TaskPriority.MEDIUM,
            context={**context, 'target': target, 'phase': 'cve_research'}
        ))

        # Task 4: X intelligence
        tasks.append(ShardedTask(
            task_id=f"{goal_id}_x_intel",
            goal_id=goal_id,
            description=f"X intelligence on {target}",
            required_capabilities=['deep_x', 'intelligence'],
            priority=TaskPriority.LOW,
            context={**context, 'target': target, 'phase': 'x_intel'}
        ))

        return tasks

    def _decompose_research_goal(self, goal_id: str, goal: str, context: Optional[Dict]) -> List[ShardedTask]:
        """Decompose vulnerability research goal."""
        tasks = []
        if context is None:
            context = {}

        # Task 1: CVE database search
        tasks.append(ShardedTask(
            task_id=f"{goal_id}_cve_search",
            goal_id=goal_id,
            description=f"Search CVE databases: {goal}",
            required_capabilities=['intelligence', 'search'],
            priority=TaskPriority.HIGH,
            context={**context, 'phase': 'cve_search'}
        ))

        # Task 2: Exploit database search
        tasks.append(ShardedTask(
            task_id=f"{goal_id}_exploit_search",
            goal_id=goal_id,
            description=f"Search exploit databases: {goal}",
            required_capabilities=['intelligence', 'search'],
            priority=TaskPriority.HIGH,
            context={**context, 'phase': 'exploit_search'}
        ))

        # Task 3: X researcher analysis
        tasks.append(ShardedTask(
            task_id=f"{goal_id}_x_researchers",
            goal_id=goal_id,
            description=f"Analyze X researchers discussing: {goal}",
            required_capabilities=['deep_x'],
            priority=TaskPriority.MEDIUM,
            context={**context, 'phase': 'x_analysis'}
        ))

        return tasks

    def _decompose_x_intelligence_goal(self, goal_id: str, goal: str, context: Optional[Dict]) -> List[ShardedTask]:
        """Decompose X intelligence goal."""
        tasks = []
        if context is None:
            context = {}

        # Task 1: X post ingestion
        tasks.append(ShardedTask(
            task_id=f"{goal_id}_x_ingest",
            goal_id=goal_id,
            description=f"Ingest X posts: {goal}",
            required_capabilities=['deep_x', 'intelligence'],
            priority=TaskPriority.HIGH,
            context={**context, 'phase': 'x_ingest'}
        ))

        # Task 2: Researcher profiling
        tasks.append(ShardedTask(
            task_id=f"{goal_id}_x_profile",
            goal_id=goal_id,
            description=f"Profile key researchers: {goal}",
            required_capabilities=['deep_x'],
            priority=TaskPriority.MEDIUM,
            context={**context, 'phase': 'x_profile'}
        ))

        # Task 3: Timeline analysis
        tasks.append(ShardedTask(
            task_id=f"{goal_id}_x_timeline",
            goal_id=goal_id,
            description=f"Analyze timeline trends: {goal}",
            required_capabilities=['deep_x'],
            priority=TaskPriority.MEDIUM,
            context={**context, 'phase': 'x_timeline'}
        ))

        return tasks

    def _decompose_monitoring_goal(self, goal_id: str, goal: str, context: Optional[Dict]) -> List[ShardedTask]:
        """Decompose monitoring goal."""
        if context is None:
            context = {}
        # Monitoring goals are typically long-running background tasks
        return [ShardedTask(
            task_id=f"{goal_id}_monitor",
            goal_id=goal_id,
            description=goal,
            required_capabilities=['threat_feed', 'intelligence'],
            priority=TaskPriority.BACKGROUND,
            context={**context, 'phase': 'monitoring', 'recurring': True}
        )]

    def _decompose_analysis_goal(self, goal_id: str, goal: str, context: Optional[Dict]) -> List[ShardedTask]:
        """Decompose analysis goal."""
        tasks = []
        if context is None:
            context = {}

        # Task 1: Data collection
        tasks.append(ShardedTask(
            task_id=f"{goal_id}_collect",
            goal_id=goal_id,
            description=f"Collect data for: {goal}",
            required_capabilities=['intelligence', 'tools'],
            priority=TaskPriority.HIGH,
            context={**context, 'phase': 'collection'}
        ))

        # Task 2: Analysis
        tasks.append(ShardedTask(
            task_id=f"{goal_id}_analyze",
            goal_id=goal_id,
            description=f"Analyze collected data: {goal}",
            required_capabilities=['reasoning'],
            priority=TaskPriority.MEDIUM,
            context={**context, 'phase': 'analysis'}
        ))

        return tasks

    def _decompose_complex_goal(self, goal_id: str, goal: str, context: Optional[Dict]) -> List[ShardedTask]:
        """Decompose complex multi-phase goal."""
        tasks = []
        if context is None:
            context = {}

        # Split by "and" or "then"
        import re
        phases = re.split(r'\s+(?:and|then)\s+', goal, flags=re.IGNORECASE)

        for i, phase in enumerate(phases):
            tasks.append(ShardedTask(
                task_id=f"{goal_id}_phase{i}",
                goal_id=goal_id,
                description=phase.strip(),
                required_capabilities=['general'],
                priority=TaskPriority.HIGH if i == 0 else TaskPriority.MEDIUM,
                context={**context, 'phase': f'phase_{i}', 'total_phases': len(phases)}
            ))

        return tasks

    def _extract_target(self, goal: str) -> str:
        """Extract target from goal description."""
        import re

        # Look for domain names
        domain_match = re.search(r'(?:[\w-]+\.)+[\w-]+', goal)
        if domain_match:
            return domain_match.group(0)

        # Look for IP addresses
        ip_match = re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', goal)
        if ip_match:
            return ip_match.group(0)

        # Look for quoted targets
        quoted_match = re.search(r'["\']([^"\']+)["\']', goal)
        if quoted_match:
            return quoted_match.group(1)

        # Default: return last word
        words = goal.split()
        return words[-1] if words else "unknown"

    # ===== TASK ROUTING =====

    def route_task(self, task: ShardedTask) -> Optional[str]:
        """
        Route task to best available member.

        Args:
            task: ShardedTask to route

        Returns:
            Member ID or None if no suitable member
        """
        # Find members with required capabilities
        candidates = []

        for member_id, capabilities in self.member_capabilities.items():
            # Check if member has all required capabilities
            if all(cap in capabilities or 'general' in capabilities
                   for cap in task.required_capabilities):
                candidates.append(member_id)

        if not candidates:
            logger.warning(f"No members with capabilities {task.required_capabilities}")
            return None

        # Select member with lowest load
        best_member = min(candidates, key=lambda m: (
            self.member_load[m],
            -self.member_performance[m]['success']  # Prefer successful members
        ))

        # Check load limits
        if self.member_load[best_member] >= self.max_tasks_per_member:
            logger.warning(f"Member {best_member} at max load ({self.max_tasks_per_member})")
            return None

        return best_member

    def assign_task(self, task: ShardedTask, member_id: str):
        """
        Assign task to member.

        Args:
            task: ShardedTask to assign
            member_id: Target member ID
        """
        task.assigned_to = member_id
        task.assigned_at = time.time()
        task.status = "assigned"

        self.active_tasks[task.task_id] = task
        self.member_load[member_id] += 1

        # Send shard message to swarm
        self.swarm.shard_goal(task.description, {
            'task_id': task.task_id,
            'goal_id': task.goal_id,
            'priority': task.priority,
            'context': task.context
        })

        logger.info(f"Assigned task {task.task_id} to {member_id}")

    # ===== TASK SCHEDULING =====

    async def schedule_tasks(self, tasks: List[ShardedTask]):
        """
        Add tasks to priority queue.

        Args:
            tasks: List of tasks to schedule
        """
        for task in tasks:
            self.task_queue[task.priority].append(task)
            logger.info(f"Scheduled task {task.task_id} (priority: {task.priority})")

    async def process_queue(self):
        """Process task queue in priority order."""
        priority_order = [
            TaskPriority.URGENT,
            TaskPriority.HIGH,
            TaskPriority.MEDIUM,
            TaskPriority.LOW,
            TaskPriority.BACKGROUND
        ]

        for priority in priority_order:
            while self.task_queue[priority]:
                task = self.task_queue[priority].popleft()

                # Route task
                member_id = self.route_task(task)

                if member_id:
                    self.assign_task(task, member_id)
                else:
                    # No available member, re-queue
                    self.task_queue[priority].append(task)
                    break

                # Small delay to avoid overwhelming swarm
                await asyncio.sleep(0.1)

    # ===== TASK TRACKING =====

    def update_task_status(self, task_id: str, status: str, result: Optional[Any] = None,
                          error: Optional[str] = None):
        """
        Update task execution status.

        Args:
            task_id: Task ID
            status: New status
            result: Optional result
            error: Optional error message
        """
        if task_id not in self.active_tasks:
            logger.warning(f"Task {task_id} not found in active tasks")
            return

        task = self.active_tasks[task_id]
        task.status = status

        if status == "completed":
            task.completed_at = time.time()
            task.result = result

            # Update member metrics
            if task.assigned_to:
                self.member_load[task.assigned_to] -= 1
                self.member_performance[task.assigned_to]['success'] += 1

                # Update average time
                execution_time = task.completed_at - task.assigned_at
                perf = self.member_performance[task.assigned_to]
                perf['avg_time'] = (perf['avg_time'] * (perf['success'] - 1) + execution_time) / perf['success']

            # Move to completed
            self.completed_tasks[task_id] = task
            del self.active_tasks[task_id]

            logger.info(f"Task {task_id} completed successfully")

        elif status == "failed":
            task.error = error

            if task.assigned_to:
                self.member_load[task.assigned_to] -= 1
                self.member_performance[task.assigned_to]['failure'] += 1

            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = "pending"
                task.assigned_to = None
                self.task_queue[task.priority].append(task)
                logger.info(f"Task {task_id} failed, re-queuing (retry {task.retry_count}/{task.max_retries})")
            else:
                # Max retries reached
                self.completed_tasks[task_id] = task
                del self.active_tasks[task_id]
                logger.error(f"Task {task_id} failed after {task.max_retries} retries: {error}")

    # ===== MEMBER MANAGEMENT =====

    def register_member(self, member_id: str, capabilities: List[str]):
        """
        Register swarm member capabilities.

        Args:
            member_id: Member ID
            capabilities: List of capability strings
        """
        self.member_capabilities[member_id] = capabilities
        logger.info(f"Registered member {member_id} with capabilities: {capabilities}")

    def unregister_member(self, member_id: str):
        """
        Unregister swarm member and reassign tasks.

        Args:
            member_id: Member ID
        """
        if member_id in self.member_capabilities:
            del self.member_capabilities[member_id]

        # Find tasks assigned to this member
        orphaned_tasks = [
            task for task in self.active_tasks.values()
            if task.assigned_to == member_id
        ]

        # Re-queue orphaned tasks
        for task in orphaned_tasks:
            task.status = "pending"
            task.assigned_to = None
            self.task_queue[task.priority].append(task)
            del self.active_tasks[task.task_id]

        logger.warning(f"Member {member_id} unregistered, re-queued {len(orphaned_tasks)} tasks")

    # ===== STATISTICS =====

    def get_stats(self) -> Dict[str, Any]:
        """Get sharding engine statistics."""
        total_queued = sum(len(q) for q in self.task_queue.values())

        return {
            'queued_tasks': total_queued,
            'active_tasks': len(self.active_tasks),
            'completed_tasks': len(self.completed_tasks),
            'registered_members': len(self.member_capabilities),
            'queue_by_priority': {
                priority: len(self.task_queue[priority])
                for priority in TaskPriority
            },
            'member_load': dict(self.member_load),
            'member_performance': dict(self.member_performance)
        }


if __name__ == "__main__":
    # Test Goal Sharding
    import sys
    sys.path.append('..')

    from federated_swarm import FederatedSwarm, SwarmRole

    # Mock swarm
    swarm = FederatedSwarm(
        swarm_id="test_swarm",
        member_id="coordinator",
        role=SwarmRole.COORDINATOR,
        sub_peers=[]
    )

    # Create sharding engine
    sharding = GoalShardingEngine(swarm)

    # Register members
    sharding.register_member("oracle_1", ['tools', 'nmap', 'web_security'])
    sharding.register_member("oracle_2", ['intelligence', 'search', 'deep_x'])
    sharding.register_member("oracle_3", ['reasoning', 'general'])

    print("\n" + "="*60)
    print("Goal Sharding Engine Test")
    print("="*60)

    # Test goal decomposition
    test_goals = [
        "Reconnaissance on example.com",
        "Research CVE-2024-1234",
        "Monitor X for WordPress exploits",
        "Analyze security posture of target.com and generate report"
    ]

    for goal in test_goals:
        print(f"\n[Test] Decomposing goal: {goal}")
        tasks = sharding.decompose_goal(goal, context={})
        print(f"Generated {len(tasks)} sub-tasks:")

        for task in tasks:
            print(f"  - {task.task_id}: {task.description}")
            print(f"    Capabilities: {task.required_capabilities}, Priority: {task.priority}")

            # Route task
            member = sharding.route_task(task)
            if member:
                print(f"    → Routed to: {member}")

    # Test statistics
    print("\n[Test] Sharding engine statistics:")
    stats = sharding.get_stats()
    print(f"Registered members: {stats['registered_members']}")
    print(f"Member capabilities:")
    for member_id, caps in sharding.member_capabilities.items():
        print(f"  - {member_id}: {caps}")

    print("\n" + "="*60)
    print("✅ Goal Sharding Engine operational!")
    print("="*60)
