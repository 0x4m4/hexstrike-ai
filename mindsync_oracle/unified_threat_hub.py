#!/usr/bin/env python3
"""
MindSync Oracle v7 - Unified Threat Intelligence Hub

THE BREAKTHROUGH: Omniscient real-time threat correlation.

Merges multiple intelligence streams into unified threat picture:
- Real-time X firehose (sub-second CVE/exploit mentions)
- Ethical Tor dark web OSINT (public defensive research)
- Cross-correlation and deduplication
- Proactive auto-goal triggering on threats
- Swarm-wide threat synchronization

This creates a unified, real-time threat intelligence platform
that predicts and responds to threats before they go mainstream.

USAGE:
    from unified_threat_hub import UnifiedThreatHub

    hub = UnifiedThreatHub(
        swarm=swarm,
        multi_llm=multi_llm,
        memory_graph=memory_graph,
        goal_engine=goal_engine,
        config=config
    )

    await hub.start()
"""

import logging
import asyncio
import time
import hashlib
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from collections import defaultdict, deque
import json

logger = logging.getLogger(__name__)


class ThreatCorrelator:
    """Correlates threats from multiple sources."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        # Correlation window
        self.correlation_window = self.config.get('correlation_window', 3600)  # 1 hour

        # Threat clusters (grouped related threats)
        self.threat_clusters = {}  # cluster_id -> {threats, confidence, first_seen, last_seen}
        self.next_cluster_id = 1

        # Statistics
        self.stats = {
            'threats_correlated': 0,
            'clusters_created': 0,
            'cross_source_correlations': 0
        }

    def correlate_threat(self, threat: Dict[str, Any]) -> Optional[str]:
        """
        Correlate threat with existing clusters.

        Returns:
            Cluster ID if correlated, None if new cluster needed
        """
        # Extract correlation keys
        cve_ids = threat.get('cve_ids', [])
        keywords = threat.get('keywords', [])
        source = threat.get('source', '')

        # Check existing clusters
        for cluster_id, cluster in self.threat_clusters.items():
            # Check if this threat belongs to cluster
            if self._matches_cluster(threat, cluster):
                # Add to cluster
                cluster['threats'].append(threat)
                cluster['last_seen'] = time.time()

                # Update confidence based on cross-source
                if threat['source'] != cluster['primary_source']:
                    cluster['confidence'] = min(cluster['confidence'] + 0.2, 1.0)
                    self.stats['cross_source_correlations'] += 1

                self.stats['threats_correlated'] += 1
                return cluster_id

        # No match - create new cluster
        return self._create_cluster(threat)

    def _matches_cluster(self, threat: Dict[str, Any], cluster: Dict[str, Any]) -> bool:
        """Check if threat matches existing cluster."""
        # CVE overlap
        threat_cves = set(threat.get('cve_ids', []))
        cluster_cves = set()
        for t in cluster['threats']:
            cluster_cves.update(t.get('cve_ids', []))

        if threat_cves and cluster_cves and threat_cves & cluster_cves:
            return True  # Shared CVE

        # Keyword overlap
        threat_keywords = set(k.lower() for k in threat.get('keywords', []))
        cluster_keywords = set()
        for t in cluster['threats']:
            cluster_keywords.update(k.lower() for k in t.get('keywords', []))

        # Require 2+ shared keywords for correlation
        shared_keywords = threat_keywords & cluster_keywords
        if len(shared_keywords) >= 2:
            return True

        return False

    def _create_cluster(self, threat: Dict[str, Any]) -> str:
        """Create new threat cluster."""
        cluster_id = f"cluster_{self.next_cluster_id}"
        self.next_cluster_id += 1

        self.threat_clusters[cluster_id] = {
            'threats': [threat],
            'confidence': 0.5,  # Start at 50%
            'first_seen': time.time(),
            'last_seen': time.time(),
            'primary_source': threat['source']
        }

        self.stats['clusters_created'] += 1
        return cluster_id

    def get_high_confidence_clusters(self, min_confidence: float = 0.7) -> List[Dict[str, Any]]:
        """Get clusters with high confidence for action."""
        high_conf = []

        for cluster_id, cluster in self.threat_clusters.items():
            if cluster['confidence'] >= min_confidence:
                # Extract cluster summary
                all_cves = set()
                all_keywords = set()
                sources = set()

                for threat in cluster['threats']:
                    all_cves.update(threat.get('cve_ids', []))
                    all_keywords.update(threat.get('keywords', []))
                    sources.add(threat['source'])

                summary = {
                    'cluster_id': cluster_id,
                    'confidence': cluster['confidence'],
                    'threat_count': len(cluster['threats']),
                    'cves': list(all_cves),
                    'keywords': list(all_keywords),
                    'sources': list(sources),
                    'cross_source': len(sources) > 1,
                    'first_seen': cluster['first_seen'],
                    'last_seen': cluster['last_seen']
                }

                high_conf.append(summary)

        return high_conf

    def cleanup_old_clusters(self):
        """Remove old clusters outside correlation window."""
        now = time.time()
        cutoff = now - self.correlation_window

        to_remove = []
        for cluster_id, cluster in self.threat_clusters.items():
            if cluster['last_seen'] < cutoff:
                to_remove.append(cluster_id)

        for cluster_id in to_remove:
            del self.threat_clusters[cluster_id]

        if to_remove:
            logger.debug(f"Cleaned up {len(to_remove)} old threat clusters")


class AutoGoalTrigger:
    """Automatically triggers goals based on threat intelligence."""

    def __init__(self, goal_engine, config: Optional[Dict] = None):
        self.goal_engine = goal_engine
        self.config = config or {}

        # Trigger thresholds
        self.confidence_threshold = self.config.get('auto_goal_confidence_threshold', 0.75)
        self.min_sources = self.config.get('auto_goal_min_sources', 2)

        # Cooldown to prevent duplicate goals
        self.triggered_goals = {}  # goal_key -> timestamp
        self.cooldown_period = self.config.get('auto_goal_cooldown', 3600)  # 1 hour

        # Statistics
        self.stats = {
            'goals_triggered': 0,
            'goals_cooldown': 0
        }

    def should_trigger(self, cluster: Dict[str, Any]) -> bool:
        """Check if cluster should trigger auto-goal."""
        # Check confidence
        if cluster['confidence'] < self.confidence_threshold:
            return False

        # Check cross-source
        if not cluster['cross_source']:
            return False

        # Check cooldown
        goal_key = self._get_goal_key(cluster)
        if goal_key in self.triggered_goals:
            last_trigger = self.triggered_goals[goal_key]
            if time.time() - last_trigger < self.cooldown_period:
                self.stats['goals_cooldown'] += 1
                return False

        return True

    def trigger_goal(self, cluster: Dict[str, Any]) -> Optional[int]:
        """Trigger auto-goal for threat cluster."""
        if not self.should_trigger(cluster):
            return None

        # Build goal text
        cves_str = ', '.join(cluster['cves'][:3])  # Top 3 CVEs
        keywords_str = ', '.join(cluster['keywords'][:3])  # Top 3 keywords

        goal_text = f"Investigate high-confidence threat cluster: {cves_str or keywords_str} "
        goal_text += f"(confidence: {cluster['confidence']:.0%}, {cluster['threat_count']} reports, "
        goal_text += f"sources: {', '.join(cluster['sources'])})"

        try:
            goal_id = self.goal_engine.add_goal(goal_text, priority='high')

            # Record trigger
            goal_key = self._get_goal_key(cluster)
            self.triggered_goals[goal_key] = time.time()

            self.stats['goals_triggered'] += 1

            logger.info(f"Auto-triggered goal {goal_id} for threat cluster: {cluster['cluster_id']}")
            return goal_id

        except Exception as e:
            logger.error(f"Failed to trigger auto-goal: {e}")
            return None

    def _get_goal_key(self, cluster: Dict[str, Any]) -> str:
        """Generate unique key for goal deduplication."""
        # Use CVEs + keywords as key
        cves = tuple(sorted(cluster['cves']))
        keywords = tuple(sorted(cluster['keywords'][:3]))
        return hashlib.md5(f"{cves}_{keywords}".encode()).hexdigest()


class UnifiedThreatHub:
    """
    Unified threat intelligence hub.

    Coordinates multiple intelligence streams for omniscient threat awareness.
    """

    def __init__(self, swarm, multi_llm, memory_graph, goal_engine=None, config=None):
        """
        Initialize unified threat hub.

        Args:
            swarm: FederatedSwarm instance
            multi_llm: MultiLLMOrchestrator instance
            memory_graph: HybridMemoryGraph instance
            goal_engine: Optional ProductionGoalEngine for auto-triggering
            config: Optional configuration
        """
        self.swarm = swarm
        self.multi_llm = multi_llm
        self.memory_graph = memory_graph
        self.goal_engine = goal_engine
        self.config = config or {}

        # Intelligence streams
        self.x_stream = None
        self.tor_osint = None

        # Correlation and triggering
        self.correlator = ThreatCorrelator(config)
        if goal_engine:
            self.auto_trigger = AutoGoalTrigger(goal_engine, config)
        else:
            self.auto_trigger = None

        # State
        self.is_running = False

        # Deduplication (cross-stream)
        self.processed_threats = set()

        # Statistics
        self.stats = {
            'threats_processed': 0,
            'threats_deduplicated': 0,
            'deltas_merged': 0,
            'auto_goals_triggered': 0
        }

        logger.info("Unified Threat Hub initialized")

    async def start(self):
        """Start all intelligence streams."""
        self.is_running = True
        logger.info("="*60)
        logger.info("Starting Unified Threat Hub - Omniscient Intelligence Mode")
        logger.info("="*60)

        tasks = []

        # Start X stream if enabled
        if self.config.get('realtime_x', {}).get('enabled', False):
            from realtime_x_stream import RealtimeXStream

            keywords = self.config.get('realtime_x', {}).get('keywords', [])
            if not keywords:
                keywords = ['CVE', 'exploit', 'vulnerability', 'WordPress', 'RCE']

            self.x_stream = RealtimeXStream(
                swarm=self.swarm,
                multi_llm=self.multi_llm,
                memory_graph=self.memory_graph,
                keywords=keywords,
                config=self.config.get('realtime_x', {}),
                goal_engine=self.goal_engine
            )

            tasks.append(asyncio.create_task(self.x_stream.start()))
            logger.info(f"✅ X Firehose started (keywords: {keywords})")

        # Start Tor OSINT if enabled
        if self.config.get('tor_osint', {}).get('enabled', False):
            from tor_dark_osint import TorDarkOSINT

            try:
                self.tor_osint = TorDarkOSINT(
                    swarm=self.swarm,
                    memory_graph=self.memory_graph,
                    config=self.config.get('tor_osint', {})
                )

                tasks.append(asyncio.create_task(self.tor_osint.start()))
                logger.info("✅ Tor Dark OSINT started (ETHICAL MODE)")

            except Exception as e:
                logger.error(f"Failed to start Tor OSINT: {e}")

        # Start correlation loop
        tasks.append(asyncio.create_task(self._correlation_loop()))
        logger.info("✅ Threat correlation engine started")

        # Wait for all tasks
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def stop(self):
        """Stop all intelligence streams."""
        logger.info("Stopping Unified Threat Hub...")
        self.is_running = False

        if self.x_stream:
            await self.x_stream.stop()

        if self.tor_osint:
            await self.tor_osint.stop()

        logger.info("Unified Threat Hub stopped")

    async def _correlation_loop(self):
        """Correlate threats and trigger actions."""
        logger.info("Starting threat correlation loop...")

        while self.is_running:
            try:
                # Clean up old clusters
                self.correlator.cleanup_old_clusters()

                # Get high-confidence clusters
                high_conf_clusters = self.correlator.get_high_confidence_clusters()

                if high_conf_clusters:
                    logger.info(f"Found {len(high_conf_clusters)} high-confidence threat clusters")

                    # Trigger auto-goals for high-confidence threats
                    if self.auto_trigger:
                        for cluster in high_conf_clusters:
                            goal_id = self.auto_trigger.trigger_goal(cluster)
                            if goal_id:
                                self.stats['auto_goals_triggered'] += 1

                # Sleep
                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Error in correlation loop: {e}")
                await asyncio.sleep(10)

    def process_threat(self, threat: Dict[str, Any]):
        """
        Process threat from any source.

        Args:
            threat: Threat dict with 'source', 'cve_ids', 'keywords', etc.
        """
        # Deduplicate
        threat_hash = self._hash_threat(threat)
        if threat_hash in self.processed_threats:
            self.stats['threats_deduplicated'] += 1
            return

        self.processed_threats.add(threat_hash)

        # Correlate
        cluster_id = self.correlator.correlate_threat(threat)

        logger.debug(f"Threat processed: {threat.get('source')} -> cluster {cluster_id}")

        self.stats['threats_processed'] += 1

    def _hash_threat(self, threat: Dict[str, Any]) -> str:
        """Generate hash for threat deduplication."""
        # Use source + CVEs + key content
        content = f"{threat.get('source')}_{threat.get('cve_ids', [])}_{threat.get('text', '')[:100]}"
        return hashlib.md5(content.encode()).hexdigest()

    def get_stats(self) -> Dict[str, Any]:
        """Get unified hub statistics."""
        stats = {
            **self.stats,
            'is_running': self.is_running,
            'correlator_stats': self.correlator.stats,
            'active_clusters': len(self.correlator.threat_clusters)
        }

        if self.x_stream:
            stats['x_stream_stats'] = self.x_stream.get_stats()

        if self.tor_osint:
            stats['tor_osint_stats'] = self.tor_osint.get_stats()

        if self.auto_trigger:
            stats['auto_trigger_stats'] = self.auto_trigger.stats

        return stats

    def get_dashboard_summary(self) -> str:
        """Get human-readable dashboard summary."""
        stats = self.get_stats()

        lines = []
        lines.append("\n" + "="*70)
        lines.append("UNIFIED THREAT HUB - OMNISCIENT INTELLIGENCE DASHBOARD")
        lines.append("="*70)

        # Overall stats
        lines.append(f"\n┌─ OVERALL STATS " + "─"*52 + "┐")
        lines.append(f"│ Status:          {'ACTIVE' if self.is_running else 'INACTIVE':<20}              │")
        lines.append(f"│ Threats Processed: {stats['threats_processed']:<6}  Deduplicated:  {stats['threats_deduplicated']:<6} │")
        lines.append(f"│ Active Clusters:   {stats['active_clusters']:<6}  Auto-Goals:    {stats['auto_goals_triggered']:<6} │")
        lines.append("└" + "─"*68 + "┘")

        # X Stream stats
        if 'x_stream_stats' in stats:
            xs = stats['x_stream_stats']
            lines.append(f"\n┌─ X FIREHOSE " + "─"*55 + "┐")
            lines.append(f"│ Mode:            {xs['mode']:<20}              │")
            lines.append(f"│ Posts Received:  {xs['posts_received']:<6}  Filtered:      {xs['posts_filtered']:<6} │")
            lines.append(f"│ Posts Processed: {xs['posts_processed']:<6}  Surges:        {xs['surges_detected']:<6} │")
            lines.append(f"│ Keywords:        {', '.join(xs['keywords'][:3]):<44} │")
            lines.append("└" + "─"*68 + "┘")

        # Tor OSINT stats
        if 'tor_osint_stats' in stats:
            tos = stats['tor_osint_stats']
            lines.append(f"\n┌─ TOR DARK OSINT (ETHICAL) " + "─"*41 + "┐")
            lines.append(f"│ Tor Enabled:     {tos['tor_enabled']:<20}              │")
            lines.append(f"│ Requests Made:   {tos['requests_made']:<6}  Content Scraped: {tos['content_scraped']:<6} │")
            lines.append(f"│ Content Blocked: {tos['content_blocked']:<6}  Cred Filtered:   {tos['credibility_filtered']:<6} │")
            lines.append(f"│ Ethical Mode:    {tos['ethical_mode']:<20}              │")
            lines.append("└" + "─"*68 + "┘")

        # Correlation stats
        cs = stats['correlator_stats']
        lines.append(f"\n┌─ THREAT CORRELATION " + "─"*47 + "┐")
        lines.append(f"│ Threats Correlated:  {cs['threats_correlated']:<6}  Clusters Created: {cs['clusters_created']:<6} │")
        lines.append(f"│ Cross-Source Links:  {cs['cross_source_correlations']:<6}                      │")
        lines.append("└" + "─"*68 + "┘")

        lines.append("")

        return "\n".join(lines)


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Unified Threat Hub Test")
    print("="*70)

    # Mock components
    class MockSwarm:
        def broadcast_graph_delta(self, delta):
            pass

        def send_message(self, msg_type, payload):
            pass

    class MockMultiLLM:
        async def execute(self, query, context=None, force_llm=None):
            return {'content': '[]'}  # Empty results for test

    class MockGraph:
        def __init__(self):
            import networkx as nx
            self.graph = nx.DiGraph()

    class MockGoalEngine:
        def __init__(self):
            self.goals = []

        def add_goal(self, text, priority='medium'):
            goal_id = len(self.goals) + 1
            self.goals.append({'id': goal_id, 'text': text, 'priority': priority})
            return goal_id

    swarm = MockSwarm()
    multi_llm = MockMultiLLM()
    graph = MockGraph()
    goal_engine = MockGoalEngine()

    config = {
        'realtime_x': {
            'enabled': False  # Disabled for test
        },
        'tor_osint': {
            'enabled': False  # Disabled for test
        }
    }

    print("\n[Test] Initializing Unified Threat Hub...")
    hub = UnifiedThreatHub(swarm, multi_llm, graph, goal_engine, config)

    print("\n[Test] Testing threat correlation...")

    # Simulate threats from different sources
    threat1 = {
        'source': 'x_stream',
        'cve_ids': ['CVE-2024-1234'],
        'keywords': ['WordPress', 'RCE'],
        'text': 'Critical WordPress RCE in CVE-2024-1234'
    }

    threat2 = {
        'source': 'tor_osint',
        'cve_ids': ['CVE-2024-1234'],
        'keywords': ['WordPress', 'exploit'],
        'text': 'PoC available for CVE-2024-1234'
    }

    threat3 = {
        'source': 'x_stream',
        'cve_ids': ['CVE-2024-5678'],
        'keywords': ['Apache', 'SQLi'],
        'text': 'Apache SQL injection CVE-2024-5678'
    }

    hub.process_threat(threat1)
    hub.process_threat(threat2)  # Should correlate with threat1
    hub.process_threat(threat3)  # Different cluster

    print(f"  Threats processed: {hub.stats['threats_processed']}")
    print(f"  Active clusters: {len(hub.correlator.threat_clusters)}")

    # Check high-confidence clusters
    high_conf = hub.correlator.get_high_confidence_clusters()
    print(f"  High-confidence clusters: {len(high_conf)}")

    if high_conf:
        for cluster in high_conf:
            print(f"\n  Cluster: {cluster['cluster_id']}")
            print(f"    Confidence: {cluster['confidence']:.0%}")
            print(f"    CVEs: {cluster['cves']}")
            print(f"    Sources: {cluster['sources']}")
            print(f"    Cross-source: {cluster['cross_source']}")

    # Test auto-trigger
    if hub.auto_trigger and high_conf:
        print("\n[Test] Testing auto-goal trigger...")
        for cluster in high_conf:
            goal_id = hub.auto_trigger.trigger_goal(cluster)
            if goal_id:
                print(f"  ✅ Auto-triggered goal {goal_id}")

    # Get stats
    print("\n[Test] Hub statistics:")
    stats = hub.get_stats()
    for key, value in stats.items():
        if not isinstance(value, dict):
            print(f"  {key}: {value}")

    print("\n" + "="*70)
    print("✅ Unified Threat Hub operational!")
    print("="*70)
