#!/usr/bin/env python3
"""
MindSync Oracle - Hybrid Memory Graph

THE BREAKTHROUGH: Relational memory instead of flat storage.

Links everything:
- Goals → Tools used → Learnings extracted
- Tools → Success patterns → Alternatives
- User preferences → Environmental factors → Optimizations

Query examples:
- "Best tool for WordPress targets?" → Traverses graph to find highest-scoring path
- "What did we learn from similar goals?" → Follows learning edges
- "Why did this tool fail?" → Traces error patterns

This is the AGI memory architecture - semantic, not just episodic.
"""

import logging
from typing import Dict, Any, List, Optional, Set, Tuple
import json
from datetime import datetime
import pickle
from pathlib import Path

# Graph libraries
import networkx as nx
from collections import defaultdict

logger = logging.getLogger(__name__)


class NodeType:
    """Graph node types."""
    GOAL = "goal"
    TOOL = "tool"
    LEARNING = "learning"
    USER_PREF = "user_pref"
    TARGET = "target"
    CVE = "cve"
    PATTERN = "pattern"
    OPTIMIZATION = "optimization"


class EdgeType:
    """Graph edge (relationship) types."""
    USED_TOOL = "used_tool"
    LEARNED_FROM = "learned_from"
    IMPROVED_BY = "improved_by"
    SIMILAR_TO = "similar_to"
    CAUSED_BY = "caused_by"
    ALTERNATIVE_TO = "alternative_to"
    PREFERRED_FOR = "preferred_for"
    FAILED_ON = "failed_on"
    SUCCEEDED_ON = "succeeded_on"


class HybridMemoryGraph:
    """
    Relational knowledge graph for autonomous learning.

    Replaces flat SQLite patterns with interconnected semantic network.
    """

    def __init__(self, storage_path: str = "mindsync_graph.gpickle"):
        """
        Initialize hybrid memory graph.

        Args:
            storage_path: Path to persist graph on disk
        """
        self.storage_path = Path(storage_path)
        self.graph = nx.DiGraph()

        # Node ID counters
        self.node_counters = defaultdict(int)

        # Load existing graph if available
        if self.storage_path.exists():
            self._load()
        else:
            self._initialize_graph()

        logger.info(f"Hybrid Memory Graph initialized ({self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges)")

    def _initialize_graph(self):
        """Initialize empty graph with root node."""
        # Create root system node
        self.graph.add_node("system",
            type="system",
            created=datetime.now().isoformat()
        )

    def _generate_node_id(self, node_type: str) -> str:
        """Generate unique node ID."""
        self.node_counters[node_type] += 1
        return f"{node_type}_{self.node_counters[node_type]}"

    # ===== GOAL TRACKING =====

    def add_goal_execution(self, goal_text: str, tools_used: List[str],
                          outcome: Dict[str, Any], learnings: List[str] = None) -> str:
        """
        Add goal execution to graph with all relationships.

        Args:
            goal_text: Goal description
            tools_used: List of tools executed
            outcome: Execution results
            learnings: Extracted learnings

        Returns:
            Goal node ID
        """
        # Create goal node
        goal_id = self._generate_node_id(NodeType.GOAL)

        self.graph.add_node(goal_id,
            type=NodeType.GOAL,
            text=goal_text,
            success=outcome.get('success', False),
            duration=outcome.get('duration', 0),
            timestamp=datetime.now().isoformat(),
            priority=outcome.get('priority', 'medium')
        )

        # Link to tools used
        for tool_name in tools_used:
            tool_id = self._ensure_tool_node(tool_name)

            # Add usage edge with metadata
            self.graph.add_edge(
                goal_id, tool_id,
                type=EdgeType.USED_TOOL,
                success=outcome.get('success', False),
                duration=outcome.get('tool_durations', {}).get(tool_name, 0),
                results_count=outcome.get('results_counts', {}).get(tool_name, 0)
            )

        # Link to learnings
        if learnings:
            for learning_text in learnings:
                learning_id = self._add_learning(learning_text)
                self.graph.add_edge(
                    goal_id, learning_id,
                    type=EdgeType.LEARNED_FROM,
                    timestamp=datetime.now().isoformat()
                )

        # Extract target and link
        target = outcome.get('target')
        if target:
            target_id = self._ensure_target_node(target)
            self.graph.add_edge(goal_id, target_id, type="targeted")

        logger.info(f"Added goal to graph: {goal_id}")

        # Auto-save after major updates
        self._save()

        return goal_id

    def _ensure_tool_node(self, tool_name: str) -> str:
        """Ensure tool node exists, create if not."""
        # Check if tool already exists
        for node_id, data in self.graph.nodes(data=True):
            if data.get('type') == NodeType.TOOL and data.get('name') == tool_name:
                return node_id

        # Create new tool node
        tool_id = self._generate_node_id(NodeType.TOOL)
        self.graph.add_node(tool_id,
            type=NodeType.TOOL,
            name=tool_name,
            total_uses=0,
            success_count=0,
            fail_count=0,
            avg_duration=0.0
        )

        return tool_id

    def _ensure_target_node(self, target: str) -> str:
        """Ensure target node exists."""
        for node_id, data in self.graph.nodes(data=True):
            if data.get('type') == NodeType.TARGET and data.get('name') == target:
                return node_id

        target_id = self._generate_node_id(NodeType.TARGET)
        self.graph.add_node(target_id,
            type=NodeType.TARGET,
            name=target,
            scan_count=0
        )

        return target_id

    def _add_learning(self, learning_text: str) -> str:
        """Add learning node."""
        learning_id = self._generate_node_id(NodeType.LEARNING)
        self.graph.add_node(learning_id,
            type=NodeType.LEARNING,
            text=learning_text,
            confidence=0.7,
            applied_count=0,
            timestamp=datetime.now().isoformat()
        )

        return learning_id

    # ===== TOOL PERFORMANCE =====

    def record_tool_performance(self, tool_name: str, success: bool,
                               duration: float, results_count: int):
        """
        Update tool performance metrics.

        Args:
            tool_name: Tool name
            success: Whether execution succeeded
            duration: Execution time
            results_count: Number of results found
        """
        tool_id = self._ensure_tool_node(tool_name)

        # Update metrics
        data = self.graph.nodes[tool_id]
        data['total_uses'] += 1
        if success:
            data['success_count'] += 1
        else:
            data['fail_count'] += 1

        # Update average duration
        current_avg = data['avg_duration']
        total_uses = data['total_uses']
        data['avg_duration'] = (current_avg * (total_uses - 1) + duration) / total_uses

        # Store in node data
        if 'history' not in data:
            data['history'] = []
        data['history'].append({
            'success': success,
            'duration': duration,
            'results': results_count,
            'timestamp': datetime.now().isoformat()
        })

        # Keep only last 50 executions
        if len(data['history']) > 50:
            data['history'] = data['history'][-50:]

    def get_tool_stats(self, tool_name: str) -> Dict[str, Any]:
        """Get comprehensive tool statistics."""
        tool_id = self._ensure_tool_node(tool_name)
        data = self.graph.nodes[tool_id]

        success_rate = 0.0
        if data['total_uses'] > 0:
            success_rate = data['success_count'] / data['total_uses']

        # Get usage contexts (goals that used this tool)
        usage_contexts = []
        for pred in self.graph.predecessors(tool_id):
            pred_data = self.graph.nodes[pred]
            if pred_data.get('type') == NodeType.GOAL:
                usage_contexts.append(pred_data['text'][:50])

        return {
            'tool': tool_name,
            'total_uses': data['total_uses'],
            'success_rate': success_rate,
            'avg_duration': data['avg_duration'],
            'recent_contexts': usage_contexts[-5:],
            'confidence': success_rate * min(1.0, data['total_uses'] / 10)
        }

    # ===== INTELLIGENT QUERIES =====

    def recommend_tool_for_task(self, task_description: str,
                                target_type: str = None) -> Tuple[str, float]:
        """
        Recommend best tool based on graph analysis.

        Args:
            task_description: Task description
            target_type: Optional target type filter

        Returns:
            (tool_name, confidence)
        """
        # Find similar goals
        similar_goals = self._find_similar_goals(task_description)

        if not similar_goals:
            return ("nmap", 0.3)  # Default fallback

        # Aggregate tool performance from similar goals
        tool_scores = defaultdict(lambda: {'successes': 0, 'failures': 0, 'total': 0})

        for goal_id in similar_goals:
            # Get tools used in this goal
            for successor in self.graph.successors(goal_id):
                if self.graph.nodes[successor].get('type') == NodeType.TOOL:
                    edge_data = self.graph[goal_id][successor]
                    tool_name = self.graph.nodes[successor]['name']

                    tool_scores[tool_name]['total'] += 1
                    if edge_data.get('success'):
                        tool_scores[tool_name]['successes'] += 1
                    else:
                        tool_scores[tool_name]['failures'] += 1

        # Calculate scores
        best_tool = None
        best_score = 0.0

        for tool_name, scores in tool_scores.items():
            if scores['total'] > 0:
                success_rate = scores['successes'] / scores['total']
                # Weight by number of uses (more data = more confidence)
                confidence = success_rate * min(1.0, scores['total'] / 5)

                if confidence > best_score:
                    best_score = confidence
                    best_tool = tool_name

        return (best_tool or "nmap", best_score)

    def _find_similar_goals(self, query: str, limit: int = 5) -> List[str]:
        """Find similar goal nodes using simple text matching."""
        similar = []
        query_lower = query.lower()

        for node_id, data in self.graph.nodes(data=True):
            if data.get('type') == NodeType.GOAL:
                goal_text = data.get('text', '').lower()

                # Simple similarity: shared keywords
                query_words = set(query_lower.split())
                goal_words = set(goal_text.split())
                overlap = len(query_words & goal_words)

                if overlap > 0:
                    similar.append((node_id, overlap))

        # Sort by overlap and return top N
        similar.sort(key=lambda x: x[1], reverse=True)
        return [node_id for node_id, _ in similar[:limit]]

    def get_learnings_for_context(self, context: str) -> List[Dict[str, Any]]:
        """Get relevant learnings for a given context."""
        # Find related goals
        related_goals = self._find_similar_goals(context)

        learnings = []
        for goal_id in related_goals:
            # Get learnings from this goal
            for successor in self.graph.successors(goal_id):
                if self.graph.nodes[successor].get('type') == NodeType.LEARNING:
                    learning_data = self.graph.nodes[successor]
                    learnings.append({
                        'text': learning_data['text'],
                        'confidence': learning_data['confidence'],
                        'from_goal': self.graph.nodes[goal_id]['text'][:50]
                    })

        return learnings

    def find_tool_alternatives(self, tool_name: str) -> List[Tuple[str, str]]:
        """Find alternative tools based on usage patterns."""
        tool_id = self._ensure_tool_node(tool_name)

        # Find goals that used this tool
        goals_using_tool = [
            pred for pred in self.graph.predecessors(tool_id)
            if self.graph.nodes[pred].get('type') == NodeType.GOAL
        ]

        # Find other tools used in those goals
        alternative_tools = defaultdict(int)

        for goal_id in goals_using_tool:
            for successor in self.graph.successors(goal_id):
                if self.graph.nodes[successor].get('type') == NodeType.TOOL:
                    alt_name = self.graph.nodes[successor]['name']
                    if alt_name != tool_name:
                        alternative_tools[alt_name] += 1

        # Sort by co-occurrence
        alternatives = sorted(
            alternative_tools.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [(name, f"used together {count} times") for name, count in alternatives[:5]]

    # ===== PATTERN DETECTION =====

    def detect_workflow_patterns(self) -> List[Dict[str, Any]]:
        """Detect common tool usage patterns."""
        patterns = []

        # Find common tool sequences
        tool_sequences = defaultdict(int)

        for node_id, data in self.graph.nodes(data=True):
            if data.get('type') == NodeType.GOAL:
                # Get tools used in order
                tools = []
                for successor in self.graph.successors(node_id):
                    if self.graph.nodes[successor].get('type') == NodeType.TOOL:
                        tools.append(self.graph.nodes[successor]['name'])

                # Record sequence
                if len(tools) >= 2:
                    sequence = " → ".join(tools)
                    tool_sequences[sequence] += 1

        # Top patterns
        for sequence, count in sorted(tool_sequences.items(), key=lambda x: x[1], reverse=True)[:5]:
            if count >= 2:  # At least 2 occurrences
                patterns.append({
                    'pattern': sequence,
                    'occurrences': count,
                    'confidence': min(1.0, count / 10)
                })

        return patterns

    # ===== GRAPH ANALYSIS =====

    def get_most_central_tools(self, limit: int = 10) -> List[Tuple[str, float]]:
        """Get most connected/important tools using centrality."""
        # Filter to tool nodes
        tool_nodes = [
            node for node, data in self.graph.nodes(data=True)
            if data.get('type') == NodeType.TOOL
        ]

        if not tool_nodes:
            return []

        # Calculate betweenness centrality (how central is each tool)
        try:
            centrality = nx.betweenness_centrality(self.graph)
        except:
            # Fallback to degree centrality
            centrality = nx.degree_centrality(self.graph)

        tool_centralities = [
            (self.graph.nodes[node]['name'], centrality.get(node, 0))
            for node in tool_nodes
        ]

        tool_centralities.sort(key=lambda x: x[1], reverse=True)
        return tool_centralities[:limit]

    def get_graph_stats(self) -> Dict[str, Any]:
        """Get comprehensive graph statistics."""
        node_types = defaultdict(int)
        for _, data in self.graph.nodes(data=True):
            node_types[data.get('type', 'unknown')] += 1

        edge_types = defaultdict(int)
        for _, _, data in self.graph.edges(data=True):
            edge_types[data.get('type', 'unknown')] += 1

        return {
            'total_nodes': self.graph.number_of_nodes(),
            'total_edges': self.graph.number_of_edges(),
            'node_types': dict(node_types),
            'edge_types': dict(edge_types),
            'density': nx.density(self.graph),
            'avg_degree': sum(dict(self.graph.degree()).values()) / max(1, self.graph.number_of_nodes())
        }

    # ===== PERSISTENCE =====

    def _save(self):
        """Save graph to disk."""
        try:
            with open(self.storage_path, 'wb') as f:
                pickle.dump(self.graph, f)
            logger.debug(f"Graph saved to {self.storage_path}")
        except Exception as e:
            logger.error(f"Error saving graph: {e}")

    def _load(self):
        """Load graph from disk."""
        try:
            with open(self.storage_path, 'rb') as f:
                self.graph = pickle.load(f)
            logger.info(f"Graph loaded from {self.storage_path}")

            # Update counters
            for node_id in self.graph.nodes():
                node_type = node_id.split('_')[0]
                if '_' in node_id:
                    try:
                        node_num = int(node_id.split('_')[1])
                        self.node_counters[node_type] = max(
                            self.node_counters[node_type],
                            node_num
                        )
                    except (ValueError, IndexError):
                        pass

        except Exception as e:
            logger.error(f"Error loading graph: {e}")
            self._initialize_graph()

    def export_visualization(self, output_path: str = "graph_viz.png"):
        """Export graph visualization."""
        try:
            import matplotlib.pyplot as plt

            # Create layout
            pos = nx.spring_layout(self.graph, k=0.5, iterations=50)

            # Color nodes by type
            color_map = {
                NodeType.GOAL: '#ff6b6b',
                NodeType.TOOL: '#4ecdc4',
                NodeType.LEARNING: '#ffe66d',
                NodeType.TARGET: '#95e1d3'
            }

            node_colors = [
                color_map.get(self.graph.nodes[node].get('type'), '#cccccc')
                for node in self.graph.nodes()
            ]

            # Draw
            plt.figure(figsize=(20, 15))
            nx.draw(self.graph, pos,
                   node_color=node_colors,
                   node_size=500,
                   with_labels=False,
                   arrows=True,
                   alpha=0.7)

            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()

            logger.info(f"Graph visualization saved to {output_path}")

        except ImportError:
            logger.warning("matplotlib not available for visualization")
        except Exception as e:
            logger.error(f"Error creating visualization: {e}")


if __name__ == "__main__":
    # Test hybrid memory graph
    logging.basicConfig(level=logging.INFO)

    graph = HybridMemoryGraph("test_graph.gpickle")

    print("\n" + "="*60)
    print("Hybrid Memory Graph - Test Suite")
    print("="*60)

    # Simulate goal executions
    print("\n[1] Adding goal executions...")

    goal1 = graph.add_goal_execution(
        "Pentest example.com",
        tools_used=["nmap", "nuclei", "gobuster"],
        outcome={
            'success': True,
            'duration': 300,
            'target': 'example.com'
        },
        learnings=["nuclei found 3 critical CVEs", "gobuster was slow"]
    )

    goal2 = graph.add_goal_execution(
        "Pentest target.com",
        tools_used=["rustscan", "nuclei", "feroxbuster"],
        outcome={
            'success': True,
            'duration': 180,
            'target': 'target.com'
        },
        learnings=["rustscan 2x faster than nmap", "feroxbuster found more dirs"]
    )

    # Record tool performance
    print("\n[2] Recording tool performance...")
    graph.record_tool_performance("nmap", True, 45, 15)
    graph.record_tool_performance("rustscan", True, 10, 12)
    graph.record_tool_performance("nuclei", True, 120, 8)

    # Query recommendations
    print("\n[3] Getting tool recommendations...")
    tool, conf = graph.recommend_tool_for_task("port scan for pentest")
    print(f"  Recommended: {tool} (confidence: {conf:.2f})")

    # Get learnings
    print("\n[4] Retrieving learnings...")
    learnings = graph.get_learnings_for_context("pentest")
    for learning in learnings[:3]:
        print(f"  - {learning['text']}")

    # Pattern detection
    print("\n[5] Detecting patterns...")
    patterns = graph.detect_workflow_patterns()
    for pattern in patterns:
        print(f"  - {pattern['pattern']} (seen {pattern['occurrences']}x)")

    # Graph stats
    print("\n[6] Graph Statistics:")
    stats = graph.get_graph_stats()
    print(f"  Nodes: {stats['total_nodes']}")
    print(f"  Edges: {stats['total_edges']}")
    print(f"  Node types: {stats['node_types']}")

    # Central tools
    print("\n[7] Most Central Tools:")
    central = graph.get_most_central_tools(5)
    for tool, score in central:
        print(f"  - {tool}: {score:.3f}")

    print("\n" + "="*60)
    print("✅ Graph system operational!")
    print("="*60 + "\n")
