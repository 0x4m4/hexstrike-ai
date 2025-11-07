#!/usr/bin/env python3
"""
MindSync Oracle v6 - Swarm Dashboard

THE BREAKTHROUGH: Real-time monitoring of federated swarm intelligence.

Visualize swarm health and coordination:
- Member status (online, health, capabilities)
- Graph density & "swarm IQ" metrics
- Goal distribution heat map
- Learning flow visualization
- Performance metrics per oracle
- Network topology visualization

This provides operational visibility into the distributed hive mind.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import time
import json

logger = logging.getLogger(__name__)


class SwarmMetrics:
    """Real-time swarm metrics."""

    def __init__(self):
        self.total_members = 0
        self.active_members = 0
        self.total_goals_sharded = 0
        self.active_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0

        # Graph metrics
        self.total_nodes = 0
        self.total_edges = 0
        self.graph_density = 0.0
        self.swarm_iq = 0.0  # Combined intelligence score

        # Learning metrics
        self.total_learnings = 0
        self.learnings_applied = 0

        # Consensus metrics
        self.pending_deltas = 0
        self.applied_deltas = 0
        self.rejected_deltas = 0
        self.conflicts_resolved = 0

        # Performance
        self.avg_task_time = 0.0
        self.avg_consensus_time = 0.0
        self.messages_per_second = 0.0

        # Health
        self.overall_health = 100.0  # 0-100


class MemberStatus:
    """Individual member status."""

    def __init__(self, member_id: str):
        self.member_id = member_id
        self.role = "unknown"
        self.capabilities = []

        self.status = "unknown"  # online, offline, degraded
        self.last_seen = None
        self.uptime = 0.0

        # Task metrics
        self.active_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.avg_task_time = 0.0

        # Graph contributions
        self.nodes_contributed = 0
        self.edges_contributed = 0
        self.deltas_applied = 0
        self.deltas_rejected = 0

        # Learning contributions
        self.learnings_shared = 0

        # Health
        self.health = 100.0
        self.load = 0.0  # 0-100%


class SwarmDashboard:
    """
    Real-time swarm monitoring dashboard.

    Collects and visualizes metrics from federated swarm.
    """

    def __init__(self, swarm, sharding_engine, consensus_engine, config=None):
        """
        Initialize swarm dashboard.

        Args:
            swarm: FederatedSwarm instance
            sharding_engine: GoalShardingEngine instance
            consensus_engine: SwarmConsensus instance
            config: Optional configuration
        """
        self.swarm = swarm
        self.sharding = sharding_engine
        self.consensus = consensus_engine
        self.config = config or {}

        # Member tracking
        self.members = {}  # member_id -> MemberStatus

        # Metrics
        self.metrics = SwarmMetrics()
        self.metrics_history = []  # [(timestamp, SwarmMetrics)]

        # Configuration
        self.refresh_interval = self.config.get('refresh_interval', 5)  # seconds
        self.history_retention = self.config.get('history_retention', 3600)  # 1 hour

        logger.info("Swarm Dashboard initialized")

    # ===== METRICS COLLECTION =====

    def refresh_metrics(self):
        """Refresh all swarm metrics."""
        self._refresh_member_status()
        self._refresh_swarm_metrics()
        self._refresh_graph_metrics()
        self._refresh_performance_metrics()
        self._calculate_swarm_iq()
        self._calculate_overall_health()

        # Record history
        self.metrics_history.append((time.time(), self._snapshot_metrics()))

        # Cleanup old history
        cutoff = time.time() - self.history_retention
        self.metrics_history = [(ts, m) for ts, m in self.metrics_history if ts > cutoff]

    def _refresh_member_status(self):
        """Refresh member status from swarm."""
        swarm_health = self.swarm.get_swarm_health()

        self.metrics.total_members = swarm_health.get('total_members', 0)
        self.metrics.active_members = swarm_health.get('active_members', 0)

        # Update member status from swarm.members
        for member_id, member_data in self.swarm.members.items():
            if member_id not in self.members:
                self.members[member_id] = MemberStatus(member_id)

            member = self.members[member_id]
            member.status = 'online' if member_id in swarm_health.get('active_list', []) else 'offline'
            member.last_seen = member_data.get('last_heartbeat')
            member.role = member_data.get('role', 'unknown')
            member.capabilities = member_data.get('capabilities', [])

    def _refresh_swarm_metrics(self):
        """Refresh swarm-wide metrics."""
        # Get sharding stats
        shard_stats = self.sharding.get_stats()
        self.metrics.active_tasks = shard_stats['active_tasks']
        self.metrics.completed_tasks = shard_stats['completed_tasks']
        self.metrics.total_goals_sharded = shard_stats['completed_tasks'] + shard_stats['active_tasks']

        # Get consensus stats
        consensus_stats = self.consensus.get_stats()
        self.metrics.pending_deltas = consensus_stats['pending_deltas']
        self.metrics.applied_deltas = consensus_stats['applied_deltas']
        self.metrics.rejected_deltas = consensus_stats['rejected_deltas']
        self.metrics.total_learnings = consensus_stats['swarm_learnings']

    def _refresh_graph_metrics(self):
        """Refresh graph metrics."""
        graph = self.consensus.memory_graph.graph

        self.metrics.total_nodes = graph.number_of_nodes()
        self.metrics.total_edges = graph.number_of_edges()

        # Calculate graph density
        n = self.metrics.total_nodes
        if n > 1:
            max_edges = n * (n - 1)  # Directed graph
            self.metrics.graph_density = self.metrics.total_edges / max_edges if max_edges > 0 else 0
        else:
            self.metrics.graph_density = 0

    def _refresh_performance_metrics(self):
        """Refresh performance metrics."""
        # Calculate average task time from sharding engine
        task_times = []
        for task in self.sharding.completed_tasks.values():
            if task.completed_at and task.assigned_at:
                task_times.append(task.completed_at - task.assigned_at)

        if task_times:
            self.metrics.avg_task_time = sum(task_times) / len(task_times)

        # Member-specific metrics
        for member_id, member in self.members.items():
            if member_id in self.sharding.member_load:
                member.active_tasks = self.sharding.member_load[member_id]
                member.load = (member.active_tasks / self.sharding.max_tasks_per_member) * 100

            if member_id in self.sharding.member_performance:
                perf = self.sharding.member_performance[member_id]
                member.completed_tasks = perf['success']
                member.failed_tasks = perf['failure']
                member.avg_task_time = perf['avg_time']

    def _calculate_swarm_iq(self):
        """
        Calculate "Swarm IQ" - combined intelligence metric.

        Factors:
        - Graph density (knowledge richness)
        - Member count (collective intelligence)
        - Task success rate (execution capability)
        - Learning rate (self-improvement)
        """
        # Factor 1: Graph density (0-30 points)
        graph_score = min(self.metrics.graph_density * 100, 30)

        # Factor 2: Active members (0-25 points)
        member_score = min(self.metrics.active_members * 5, 25)

        # Factor 3: Task success rate (0-30 points)
        total_tasks = self.metrics.completed_tasks + self.metrics.failed_tasks
        if total_tasks > 0:
            success_rate = self.metrics.completed_tasks / total_tasks
            success_score = success_rate * 30
        else:
            success_score = 0

        # Factor 4: Learning accumulation (0-15 points)
        learning_score = min(self.metrics.total_learnings, 15)

        self.metrics.swarm_iq = graph_score + member_score + success_score + learning_score

    def _calculate_overall_health(self):
        """Calculate overall swarm health."""
        if not self.members:
            self.metrics.overall_health = 0
            return

        # Average member health
        member_healths = [m.health for m in self.members.values() if m.status == 'online']

        if member_healths:
            avg_health = sum(member_healths) / len(member_healths)
        else:
            avg_health = 0

        # Penalize if few active members
        activity_factor = min(self.metrics.active_members / max(self.metrics.total_members, 1), 1.0)

        self.metrics.overall_health = avg_health * activity_factor

    def _snapshot_metrics(self) -> SwarmMetrics:
        """Create snapshot of current metrics."""
        snapshot = SwarmMetrics()
        snapshot.__dict__.update(self.metrics.__dict__)
        return snapshot

    # ===== VISUALIZATION =====

    def render_ascii_dashboard(self) -> str:
        """
        Render ASCII dashboard.

        Returns:
            Dashboard string
        """
        lines = []

        # Header
        lines.append("="*70)
        lines.append("MINDSYNC ORACLE SWARM DASHBOARD".center(70))
        lines.append(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(70))
        lines.append("="*70)

        # Overall metrics
        lines.append("")
        lines.append("┌─ SWARM OVERVIEW " + "─"*51 + "┐")
        lines.append(f"│ Swarm IQ:        {self.metrics.swarm_iq:6.1f}/100  " +
                    f"Overall Health:  {self.metrics.overall_health:5.1f}%  │")
        lines.append(f"│ Active Members:  {self.metrics.active_members:3}/{self.metrics.total_members:<3}      " +
                    f"Graph Density:   {self.metrics.graph_density:5.1%}   │")
        lines.append(f"│ Graph Nodes:     {self.metrics.total_nodes:6}      " +
                    f"Graph Edges:     {self.metrics.total_edges:6}  │")
        lines.append("└" + "─"*68 + "┘")

        # Task metrics
        lines.append("")
        lines.append("┌─ TASK EXECUTION " + "─"*51 + "┐")
        total_tasks = self.metrics.completed_tasks + self.metrics.failed_tasks
        success_rate = (self.metrics.completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        lines.append(f"│ Active Tasks:    {self.metrics.active_tasks:6}      " +
                    f"Completed:       {self.metrics.completed_tasks:6}  │")
        lines.append(f"│ Failed:          {self.metrics.failed_tasks:6}      " +
                    f"Success Rate:    {success_rate:5.1f}%   │")
        lines.append(f"│ Avg Task Time:   {self.metrics.avg_task_time:6.1f}s    " +
                    f"Total Sharded:   {self.metrics.total_goals_sharded:6}  │")
        lines.append("└" + "─"*68 + "┘")

        # Consensus metrics
        lines.append("")
        lines.append("┌─ CONSENSUS & LEARNING " + "─"*45 + "┐")
        lines.append(f"│ Pending Deltas:  {self.metrics.pending_deltas:6}      " +
                    f"Applied:         {self.metrics.applied_deltas:6}  │")
        lines.append(f"│ Rejected:        {self.metrics.rejected_deltas:6}      " +
                    f"Conflicts:       {self.metrics.conflicts_resolved:6}  │")
        lines.append(f"│ Total Learnings: {self.metrics.total_learnings:6}      " +
                    f"Applied:         {self.metrics.learnings_applied:6}  │")
        lines.append("└" + "─"*68 + "┘")

        # Member status
        lines.append("")
        lines.append("┌─ MEMBER STATUS " + "─"*52 + "┐")

        if not self.members:
            lines.append("│ No members registered" + " "*46 + "│")
        else:
            for member_id, member in sorted(self.members.items()):
                status_icon = {
                    'online': '●',
                    'offline': '○',
                    'degraded': '◐'
                }.get(member.status, '?')

                member_line = f"│ {status_icon} {member_id[:20]:<20} "
                member_line += f"Load: {member.load:4.0f}% "
                member_line += f"Tasks: {member.completed_tasks:3}/{member.failed_tasks:<3} "
                member_line += f"Health: {member.health:3.0f}%"

                # Pad to 68 chars
                member_line += " " * (69 - len(member_line)) + "│"
                lines.append(member_line)

        lines.append("└" + "─"*68 + "┘")

        # Capabilities matrix
        lines.append("")
        lines.append("┌─ CAPABILITY MATRIX " + "─"*48 + "┐")

        all_capabilities = set()
        for member in self.members.values():
            all_capabilities.update(member.capabilities)

        if all_capabilities:
            cap_list = sorted(list(all_capabilities))[:5]  # Top 5
            for cap in cap_list:
                members_with_cap = [m.member_id for m in self.members.values() if cap in m.capabilities]
                cap_line = f"│ {cap[:20]:<20}: {len(members_with_cap)} members "
                cap_line += f"({', '.join(m[:8] for m in members_with_cap[:3])})"
                cap_line += " " * (69 - len(cap_line)) + "│"
                lines.append(cap_line)
        else:
            lines.append("│ No capabilities registered" + " "*40 + "│")

        lines.append("└" + "─"*68 + "┘")

        lines.append("")

        return "\n".join(lines)

    def render_json_dashboard(self) -> str:
        """
        Render JSON dashboard.

        Returns:
            JSON string
        """
        dashboard = {
            'timestamp': time.time(),
            'metrics': {
                'swarm_iq': self.metrics.swarm_iq,
                'overall_health': self.metrics.overall_health,
                'active_members': self.metrics.active_members,
                'total_members': self.metrics.total_members,
                'graph': {
                    'nodes': self.metrics.total_nodes,
                    'edges': self.metrics.total_edges,
                    'density': self.metrics.graph_density
                },
                'tasks': {
                    'active': self.metrics.active_tasks,
                    'completed': self.metrics.completed_tasks,
                    'failed': self.metrics.failed_tasks,
                    'avg_time': self.metrics.avg_task_time
                },
                'consensus': {
                    'pending_deltas': self.metrics.pending_deltas,
                    'applied_deltas': self.metrics.applied_deltas,
                    'rejected_deltas': self.metrics.rejected_deltas
                },
                'learning': {
                    'total': self.metrics.total_learnings,
                    'applied': self.metrics.learnings_applied
                }
            },
            'members': [
                {
                    'id': member.member_id,
                    'status': member.status,
                    'role': member.role,
                    'capabilities': member.capabilities,
                    'health': member.health,
                    'load': member.load,
                    'tasks': {
                        'active': member.active_tasks,
                        'completed': member.completed_tasks,
                        'failed': member.failed_tasks
                    }
                }
                for member in self.members.values()
            ]
        }

        return json.dumps(dashboard, indent=2)

    # ===== ALERTS =====

    def check_alerts(self) -> List[Dict[str, Any]]:
        """
        Check for alert conditions.

        Returns:
            List of alerts
        """
        alerts = []

        # Low health alert
        if self.metrics.overall_health < 50:
            alerts.append({
                'severity': 'high',
                'type': 'health',
                'message': f"Swarm health critical: {self.metrics.overall_health:.0f}%"
            })

        # No active members
        if self.metrics.active_members == 0:
            alerts.append({
                'severity': 'critical',
                'type': 'availability',
                'message': "No active swarm members"
            })

        # High task failure rate
        total_tasks = self.metrics.completed_tasks + self.metrics.failed_tasks
        if total_tasks > 10:
            failure_rate = self.metrics.failed_tasks / total_tasks
            if failure_rate > 0.3:
                alerts.append({
                    'severity': 'medium',
                    'type': 'performance',
                    'message': f"High task failure rate: {failure_rate:.0%}"
                })

        # Too many pending deltas
        if self.metrics.pending_deltas > 50:
            alerts.append({
                'severity': 'medium',
                'type': 'consensus',
                'message': f"Many pending deltas: {self.metrics.pending_deltas}"
            })

        # Member overload
        for member in self.members.values():
            if member.load > 90:
                alerts.append({
                    'severity': 'low',
                    'type': 'load',
                    'message': f"Member {member.member_id} overloaded: {member.load:.0f}%"
                })

        return alerts


if __name__ == "__main__":
    # Test Swarm Dashboard
    import sys
    sys.path.append('..')

    from federated_swarm import FederatedSwarm, SwarmRole
    from hybrid_memory_graph import HybridMemoryGraph
    from goal_sharding import GoalShardingEngine
    from swarm_consensus import SwarmConsensus

    # Create components
    graph = HybridMemoryGraph('test_dashboard_graph.pkl')
    swarm = FederatedSwarm(
        swarm_id="test_swarm",
        member_id="coordinator",
        role=SwarmRole.COORDINATOR,
        sub_peers=[]
    )

    sharding = GoalShardingEngine(swarm)
    consensus = SwarmConsensus(swarm, graph)
    dashboard = SwarmDashboard(swarm, sharding, consensus)

    print("\n" + "="*70)
    print("Swarm Dashboard Test")
    print("="*70)

    # Simulate some activity
    print("\n[Test] Simulating swarm activity...")

    # Register members
    sharding.register_member("oracle_1", ['tools', 'nmap'])
    sharding.register_member("oracle_2", ['intelligence', 'deep_x'])
    sharding.register_member("oracle_3", ['reasoning'])

    # Add some nodes to graph
    graph.graph.add_node('test_1', type='cve')
    graph.graph.add_node('test_2', type='tool')
    graph.graph.add_edge('test_1', 'test_2', relationship='scans')

    # Simulate completed tasks
    for i in range(5):
        sharding.completed_tasks[f"task_{i}"] = type('Task', (), {
            'completed_at': time.time(),
            'assigned_at': time.time() - 10
        })()

    # Refresh and display
    print("\n[Test] Refreshing dashboard metrics...")
    dashboard.refresh_metrics()

    print("\n[Test] ASCII Dashboard:")
    print(dashboard.render_ascii_dashboard())

    print("\n[Test] Checking for alerts...")
    alerts = dashboard.check_alerts()
    if alerts:
        for alert in alerts:
            print(f"  [{alert['severity'].upper()}] {alert['type']}: {alert['message']}")
    else:
        print("  No alerts")

    print("\n" + "="*70)
    print("✅ Swarm Dashboard operational!")
    print("="*70)
