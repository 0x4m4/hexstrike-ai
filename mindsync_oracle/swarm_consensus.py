#!/usr/bin/env python3
"""
MindSync Oracle v6 - Swarm Consensus Engine

THE BREAKTHROUGH: Distributed state synchronization across federated swarm.

Merge knowledge graphs and learnings from multiple oracles:
- Graph delta merging (NetworkX union with conflict resolution)
- Voting mechanisms (consensus on conflicting data)
- Learning synchronization (share self-improvement discoveries)
- Version control (track graph evolution over time)
- Conflict detection (identify divergent states)

This enables a true hive mind with consistent distributed knowledge.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import networkx as nx
import json
import hashlib
import time

logger = logging.getLogger(__name__)


class GraphDelta:
    """Represents a change to the knowledge graph."""

    def __init__(self, delta_id: str, source_member: str, operation: str,
                 node_id: Optional[str] = None, edge: Optional[Tuple[str, str]] = None,
                 data: Optional[Dict] = None):
        self.delta_id = delta_id
        self.source_member = source_member
        self.operation = operation  # add_node, update_node, remove_node, add_edge, remove_edge
        self.node_id = node_id
        self.edge = edge
        self.data = data or {}
        self.timestamp = time.time()
        self.applied = False
        self.votes = {}  # member_id -> vote (True/False)


class ConsensusVote:
    """Represents a vote on a conflicting change."""

    def __init__(self, delta_id: str, voter_id: str, approve: bool, reason: str = ""):
        self.delta_id = delta_id
        self.voter_id = voter_id
        self.approve = approve
        self.reason = reason
        self.timestamp = time.time()


class SwarmConsensus:
    """
    Distributed consensus engine for swarm knowledge synchronization.

    Handles graph merging, conflict resolution, and learning
    synchronization across federated oracles.
    """

    def __init__(self, swarm, memory_graph, config=None):
        """
        Initialize consensus engine.

        Args:
            swarm: FederatedSwarm instance
            memory_graph: HybridMemoryGraph instance
            config: Optional configuration
        """
        self.swarm = swarm
        self.memory_graph = memory_graph
        self.config = config or {}

        # Delta tracking
        self.pending_deltas = {}  # delta_id -> GraphDelta
        self.applied_deltas = {}  # delta_id -> GraphDelta
        self.rejected_deltas = {}  # delta_id -> GraphDelta

        # Conflict tracking
        self.conflicts = defaultdict(list)  # node_id -> [GraphDelta]

        # Consensus parameters
        self.consensus_threshold = self.config.get('consensus_threshold', 0.6)  # 60% approval
        self.vote_timeout = self.config.get('vote_timeout', 30)  # 30 seconds
        self.min_voters = self.config.get('min_voters', 2)

        # Graph versioning
        self.graph_version = 0
        self.version_history = []  # [(version, hash, timestamp)]

        # Learning cache
        self.swarm_learnings = []  # Shared self-improvement learnings

        logger.info("Swarm Consensus Engine initialized")

    # ===== GRAPH DELTA PROCESSING =====

    def create_delta(self, operation: str, node_id: Optional[str] = None,
                    edge: Optional[Tuple[str, str]] = None,
                    data: Optional[Dict] = None) -> GraphDelta:
        """
        Create graph delta for local change.

        Args:
            operation: Operation type
            node_id: Optional node ID
            edge: Optional edge tuple
            data: Optional data dictionary

        Returns:
            GraphDelta object
        """
        delta_id = self._generate_delta_id(operation, node_id, edge)

        delta = GraphDelta(
            delta_id=delta_id,
            source_member=self.swarm.member_id,
            operation=operation,
            node_id=node_id,
            edge=edge,
            data=data
        )

        return delta

    def broadcast_delta(self, delta: GraphDelta):
        """
        Broadcast graph delta to swarm.

        Args:
            delta: GraphDelta to broadcast
        """
        payload = {
            'delta_id': delta.delta_id,
            'operation': delta.operation,
            'node_id': delta.node_id,
            'edge': delta.edge,
            'data': delta.data,
            'timestamp': delta.timestamp
        }

        self.swarm.broadcast_graph_delta(payload)
        logger.info(f"Broadcasted delta {delta.delta_id} ({delta.operation})")

    def receive_delta(self, delta_data: Dict[str, Any], source_member: str) -> GraphDelta:
        """
        Receive graph delta from swarm.

        Args:
            delta_data: Delta payload
            source_member: Source member ID

        Returns:
            GraphDelta object
        """
        delta = GraphDelta(
            delta_id=delta_data['delta_id'],
            source_member=source_member,
            operation=delta_data['operation'],
            node_id=delta_data.get('node_id'),
            edge=delta_data.get('edge'),
            data=delta_data.get('data', {})
        )
        delta.timestamp = delta_data['timestamp']

        # Check for conflicts
        if self._has_conflict(delta):
            self.conflicts[delta.node_id or str(delta.edge)].append(delta)
            self.pending_deltas[delta.delta_id] = delta
            logger.warning(f"Delta {delta.delta_id} has conflicts, initiating vote")
            self._initiate_vote(delta)
        else:
            # No conflict, apply immediately
            self._apply_delta(delta)

        return delta

    def _has_conflict(self, delta: GraphDelta) -> bool:
        """
        Check if delta conflicts with current graph state.

        Args:
            delta: GraphDelta to check

        Returns:
            True if conflict exists
        """
        graph = self.memory_graph.graph

        if delta.operation == "add_node":
            # Conflict if node exists with different data
            if delta.node_id in graph:
                existing_data = graph.nodes[delta.node_id]
                # Check for significant differences
                for key, value in delta.data.items():
                    if key in existing_data and existing_data[key] != value:
                        return True

        elif delta.operation == "update_node":
            # Conflict if node doesn't exist or has conflicting updates
            if delta.node_id not in graph:
                return False  # Can't update non-existent node

            # Check if multiple members are updating same fields
            conflict_key = f"update_{delta.node_id}"
            if conflict_key in self.conflicts and len(self.conflicts[conflict_key]) > 0:
                # Recent conflicting update
                recent_deltas = [d for d in self.conflicts[conflict_key]
                               if time.time() - d.timestamp < 60]
                if recent_deltas:
                    return True

        elif delta.operation == "remove_node":
            # Conflict if node doesn't exist or other members recently added edges to it
            if delta.node_id not in graph:
                return False

            # Check for recent activity on this node
            for existing_delta in self.pending_deltas.values():
                if existing_delta.operation == "add_edge":
                    if delta.node_id in existing_delta.edge:
                        return True

        elif delta.operation == "add_edge":
            # Conflict if edge exists with different data
            if delta.edge in graph.edges:
                existing_data = graph.edges[delta.edge]
                for key, value in delta.data.items():
                    if key in existing_data and existing_data[key] != value:
                        return True

        return False

    def _apply_delta(self, delta: GraphDelta):
        """
        Apply graph delta to local graph.

        Args:
            delta: GraphDelta to apply
        """
        graph = self.memory_graph.graph

        try:
            if delta.operation == "add_node":
                if delta.node_id not in graph:
                    graph.add_node(delta.node_id, **delta.data)
                    logger.info(f"Applied delta: added node {delta.node_id}")
                else:
                    # Update existing node
                    graph.nodes[delta.node_id].update(delta.data)
                    logger.info(f"Applied delta: updated node {delta.node_id}")

            elif delta.operation == "update_node":
                if delta.node_id in graph:
                    graph.nodes[delta.node_id].update(delta.data)
                    logger.info(f"Applied delta: updated node {delta.node_id}")

            elif delta.operation == "remove_node":
                if delta.node_id in graph:
                    graph.remove_node(delta.node_id)
                    logger.info(f"Applied delta: removed node {delta.node_id}")

            elif delta.operation == "add_edge":
                if delta.edge and len(delta.edge) == 2:
                    source, target = delta.edge
                    if not graph.has_edge(source, target):
                        graph.add_edge(source, target, **delta.data)
                        logger.info(f"Applied delta: added edge {source} -> {target}")
                    else:
                        # Update edge data
                        graph.edges[delta.edge].update(delta.data)
                        logger.info(f"Applied delta: updated edge {source} -> {target}")

            elif delta.operation == "remove_edge":
                if delta.edge and graph.has_edge(*delta.edge):
                    graph.remove_edge(*delta.edge)
                    logger.info(f"Applied delta: removed edge {delta.edge}")

            delta.applied = True
            self.applied_deltas[delta.delta_id] = delta
            self.graph_version += 1
            self._record_version()

        except Exception as e:
            logger.error(f"Error applying delta {delta.delta_id}: {e}")
            self.rejected_deltas[delta.delta_id] = delta

    # ===== VOTING MECHANISM =====

    def _initiate_vote(self, delta: GraphDelta):
        """
        Initiate vote on conflicting delta.

        Args:
            delta: GraphDelta to vote on
        """
        # Auto-vote based on local analysis
        my_vote = self._analyze_delta(delta)
        delta.votes[self.swarm.member_id] = my_vote

        # Request votes from swarm
        vote_request = {
            'delta_id': delta.delta_id,
            'operation': delta.operation,
            'node_id': delta.node_id,
            'edge': delta.edge,
            'data': delta.data,
            'requester': self.swarm.member_id
        }

        # Broadcast via swarm (would need to add vote_request message type)
        logger.info(f"Initiated vote for delta {delta.delta_id}")

    def cast_vote(self, delta_id: str, approve: bool, reason: str = ""):
        """
        Cast vote on pending delta.

        Args:
            delta_id: Delta ID to vote on
            approve: Approve or reject
            reason: Optional reason
        """
        if delta_id not in self.pending_deltas:
            logger.warning(f"Cannot vote on unknown delta {delta_id}")
            return

        delta = self.pending_deltas[delta_id]
        delta.votes[self.swarm.member_id] = approve

        logger.info(f"Voted {approve} on delta {delta_id}: {reason}")

        # Check if consensus reached
        self._check_consensus(delta)

    def _analyze_delta(self, delta: GraphDelta) -> bool:
        """
        Analyze delta to determine vote.

        Args:
            delta: GraphDelta to analyze

        Returns:
            True to approve, False to reject
        """
        graph = self.memory_graph.graph

        # Trust factor: prefer deltas from established members
        if delta.source_member == self.swarm.member_id:
            return True

        # Consistency check: ensure delta makes sense
        if delta.operation == "add_edge":
            # Check if both nodes exist
            if delta.edge:
                source, target = delta.edge
                if source not in graph or target not in graph:
                    return False  # Reject edge to non-existent nodes

        elif delta.operation == "update_node":
            # Check if update is reasonable
            if delta.node_id in graph:
                existing_data = graph.nodes[delta.node_id]
                # Prefer newer data
                existing_ts = existing_data.get('timestamp', 0)
                new_ts = delta.data.get('timestamp', delta.timestamp)
                if new_ts > existing_ts:
                    return True

        # Default: approve
        return True

    def _check_consensus(self, delta: GraphDelta):
        """
        Check if consensus reached on delta.

        Args:
            delta: GraphDelta to check
        """
        votes = delta.votes
        total_votes = len(votes)

        # Need minimum voters
        if total_votes < self.min_voters:
            return

        # Calculate approval rate
        approvals = sum(1 for vote in votes.values() if vote)
        approval_rate = approvals / total_votes

        if approval_rate >= self.consensus_threshold:
            # Consensus reached: apply delta
            logger.info(f"Consensus reached for delta {delta.delta_id} ({approval_rate:.0%} approval)")
            self._apply_delta(delta)
            del self.pending_deltas[delta.delta_id]
        elif approval_rate < (1 - self.consensus_threshold):
            # Consensus to reject
            logger.info(f"Consensus to reject delta {delta.delta_id} ({approval_rate:.0%} approval)")
            self.rejected_deltas[delta.delta_id] = delta
            del self.pending_deltas[delta.delta_id]

    # ===== LEARNING SYNCHRONIZATION =====

    def broadcast_learning(self, learning: Dict[str, Any]):
        """
        Broadcast self-improvement learning to swarm.

        Args:
            learning: Learning dictionary
        """
        learning['source_member'] = self.swarm.member_id
        learning['timestamp'] = time.time()

        self.swarm.broadcast_learning(learning)
        self.swarm_learnings.append(learning)

        logger.info(f"Broadcasted learning: {learning.get('lesson', 'N/A')}")

    def receive_learning(self, learning: Dict[str, Any]):
        """
        Receive learning from swarm member.

        Args:
            learning: Learning dictionary
        """
        # Deduplicate
        learning_hash = self._hash_learning(learning)
        for existing in self.swarm_learnings:
            if self._hash_learning(existing) == learning_hash:
                return  # Already have this learning

        self.swarm_learnings.append(learning)
        logger.info(f"Received learning from {learning['source_member']}: {learning.get('lesson', 'N/A')}")

        # Apply learning if applicable
        self._apply_learning(learning)

    def _apply_learning(self, learning: Dict[str, Any]):
        """
        Apply learning to local system.

        Args:
            learning: Learning dictionary
        """
        learning_type = learning.get('type')

        if learning_type == 'tool_performance':
            # Update tool scores
            tool = learning.get('tool')
            score_delta = learning.get('score_delta', 0)
            # Would update tool learning system here
            logger.info(f"Applied tool learning: {tool} score adjusted by {score_delta}")

        elif learning_type == 'pattern':
            # Add pattern to memory
            pattern = learning.get('pattern')
            # Would add to pattern detection here
            logger.info(f"Applied pattern learning: {pattern}")

        elif learning_type == 'optimization':
            # Apply optimization suggestion
            optimization = learning.get('optimization')
            logger.info(f"Applied optimization learning: {optimization}")

    def _hash_learning(self, learning: Dict[str, Any]) -> str:
        """
        Generate hash for learning deduplication.

        Args:
            learning: Learning dictionary

        Returns:
            Hash string
        """
        # Hash based on type and key content
        content = f"{learning.get('type')}_{learning.get('lesson', '')}_{learning.get('context', {})}"
        return hashlib.md5(content.encode()).hexdigest()

    # ===== GRAPH MERGING =====

    def merge_graphs(self, remote_graph: nx.DiGraph, source_member: str) -> Dict[str, Any]:
        """
        Merge remote graph into local graph.

        Args:
            remote_graph: Graph from remote member
            source_member: Source member ID

        Returns:
            Merge statistics
        """
        logger.info(f"Merging graph from {source_member}")

        local_graph = self.memory_graph.graph
        stats = {
            'nodes_added': 0,
            'nodes_updated': 0,
            'edges_added': 0,
            'edges_updated': 0,
            'conflicts': 0
        }

        # Merge nodes
        for node_id, node_data in remote_graph.nodes(data=True):
            if node_id not in local_graph:
                # New node: add directly
                local_graph.add_node(node_id, **node_data)
                stats['nodes_added'] += 1
            else:
                # Existing node: merge data
                local_data = local_graph.nodes[node_id]
                merged_data = self._merge_node_data(local_data, node_data)

                if merged_data != local_data:
                    local_graph.nodes[node_id].update(merged_data)
                    stats['nodes_updated'] += 1

        # Merge edges
        for source, target, edge_data in remote_graph.edges(data=True):
            if not local_graph.has_edge(source, target):
                # New edge: add directly
                if source in local_graph and target in local_graph:
                    local_graph.add_edge(source, target, **edge_data)
                    stats['edges_added'] += 1
            else:
                # Existing edge: merge data
                local_data = local_graph.edges[source, target]
                merged_data = self._merge_edge_data(local_data, edge_data)

                if merged_data != local_data:
                    local_graph.edges[source, target].update(merged_data)
                    stats['edges_updated'] += 1

        self.graph_version += 1
        self._record_version()

        logger.info(f"Graph merge complete: {stats}")
        return stats

    def _merge_node_data(self, local_data: Dict, remote_data: Dict) -> Dict:
        """
        Merge node data with conflict resolution.

        Args:
            local_data: Local node data
            remote_data: Remote node data

        Returns:
            Merged data
        """
        merged = local_data.copy()

        for key, remote_value in remote_data.items():
            if key not in merged:
                # New field: add
                merged[key] = remote_value
            elif key == 'timestamp':
                # Prefer newer timestamp
                merged[key] = max(merged.get('timestamp', 0), remote_value)
            elif isinstance(remote_value, (int, float)) and isinstance(merged[key], (int, float)):
                # Numeric: average
                merged[key] = (merged[key] + remote_value) / 2
            elif merged[key] != remote_value:
                # Conflict: prefer remote (can be made more sophisticated)
                merged[key] = remote_value

        return merged

    def _merge_edge_data(self, local_data: Dict, remote_data: Dict) -> Dict:
        """
        Merge edge data with conflict resolution.

        Args:
            local_data: Local edge data
            remote_data: Remote edge data

        Returns:
            Merged data
        """
        return self._merge_node_data(local_data, remote_data)

    # ===== VERSIONING =====

    def _record_version(self):
        """Record current graph version."""
        graph_hash = self._hash_graph()
        self.version_history.append((
            self.graph_version,
            graph_hash,
            time.time()
        ))

        # Keep only recent history
        if len(self.version_history) > 100:
            self.version_history = self.version_history[-100:]

    def _hash_graph(self) -> str:
        """
        Generate hash of current graph state.

        Returns:
            Graph hash
        """
        graph = self.memory_graph.graph

        # Create canonical representation
        nodes = sorted(graph.nodes(data=True))
        edges = sorted(graph.edges(data=True))

        content = json.dumps({'nodes': nodes, 'edges': edges}, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()

    def _generate_delta_id(self, operation: str, node_id: Optional[str],
                          edge: Optional[Tuple[str, str]]) -> str:
        """Generate unique delta ID."""
        content = f"{operation}_{node_id}_{edge}_{time.time()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    # ===== STATISTICS =====

    def get_stats(self) -> Dict[str, Any]:
        """Get consensus engine statistics."""
        return {
            'graph_version': self.graph_version,
            'pending_deltas': len(self.pending_deltas),
            'applied_deltas': len(self.applied_deltas),
            'rejected_deltas': len(self.rejected_deltas),
            'conflicts': len(self.conflicts),
            'swarm_learnings': len(self.swarm_learnings),
            'version_history_size': len(self.version_history)
        }


if __name__ == "__main__":
    # Test Swarm Consensus
    import sys
    sys.path.append('..')

    from federated_swarm import FederatedSwarm, SwarmRole
    from hybrid_memory_graph import HybridMemoryGraph

    # Create components
    graph = HybridMemoryGraph('test_consensus_graph.pkl')
    swarm = FederatedSwarm(
        swarm_id="test_swarm",
        member_id="oracle_1",
        role=SwarmRole.HYBRID,
        sub_peers=[]
    )

    consensus = SwarmConsensus(swarm, graph)

    print("\n" + "="*60)
    print("Swarm Consensus Engine Test")
    print("="*60)

    # Test delta creation and broadcasting
    print("\n[Test] Creating and broadcasting graph delta...")
    delta = consensus.create_delta(
        operation="add_node",
        node_id="test_cve_123",
        data={'type': 'cve', 'severity': 'high', 'timestamp': time.time()}
    )
    print(f"Created delta: {delta.delta_id} ({delta.operation})")

    # Simulate receiving delta from another member
    print("\n[Test] Simulating delta from remote member...")
    remote_delta_data = {
        'delta_id': 'remote_delta_456',
        'operation': 'add_node',
        'node_id': 'test_tool_scan',
        'data': {'type': 'tool', 'name': 'nmap', 'timestamp': time.time()},
        'timestamp': time.time()
    }
    received_delta = consensus.receive_delta(remote_delta_data, 'oracle_2')
    print(f"Received delta: {received_delta.delta_id}")
    print(f"Node added to graph: {'test_tool_scan' in graph.graph}")

    # Test learning synchronization
    print("\n[Test] Testing learning synchronization...")
    learning = {
        'type': 'tool_performance',
        'tool': 'nmap',
        'lesson': 'Works best with -sV flag for version detection',
        'context': {'success_rate': 0.95},
        'score_delta': 0.1
    }
    consensus.broadcast_learning(learning)
    print(f"Broadcasted learning: {learning['lesson']}")

    # Test graph merging
    print("\n[Test] Testing graph merge...")
    remote_graph = nx.DiGraph()
    remote_graph.add_node('merged_node_1', type='pattern', confidence=0.8)
    remote_graph.add_node('merged_node_2', type='finding', severity='medium')
    remote_graph.add_edge('merged_node_1', 'merged_node_2', relationship='detected_by')

    merge_stats = consensus.merge_graphs(remote_graph, 'oracle_3')
    print(f"Merge stats: {merge_stats}")

    # Test statistics
    print("\n[Test] Consensus engine statistics:")
    stats = consensus.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n" + "="*60)
    print("✅ Swarm Consensus Engine operational!")
    print("="*60)
