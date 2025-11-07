#!/usr/bin/env python3
"""
MindSync Oracle v4 - Live Threat Intelligence Feed

THE BREAKTHROUGH: Proactive intelligence gathering from live sources.

Runs in background, continuously:
- Monitors X/web for emerging threats
- Ingests into memory graph
- Auto-generates goals for high-priority threats
- Learns what intelligence is actually useful

This is the "always-on sensor array" for the AGI.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class ThreatPriority:
    """Threat priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    URGENT = "urgent"


class LiveThreatFeed:
    """
    Background threat intelligence feed.

    Continuously monitors for emerging threats and auto-injects
    into the system's goal queue when appropriate.
    """

    def __init__(self, multi_llm_orchestrator, memory_graph, goal_engine=None,
                 config=None):
        """
        Initialize live threat feed.

        Args:
            multi_llm_orchestrator: MultiLLMOrchestrator for intelligence gathering
            memory_graph: HybridMemoryGraph for storing intel
            goal_engine: Optional ProductionGoalEngine for auto-goal creation
            config: Optional configuration
        """
        self.orchestrator = multi_llm_orchestrator
        self.memory_graph = memory_graph
        self.goal_engine = goal_engine
        self.config = config or {}

        # Feed configuration
        self.enabled = self.config.get('threat_feed.enabled', True)
        self.check_interval = self.config.get('threat_feed.check_interval', 3600)  # 1 hour
        self.auto_create_goals = self.config.get('threat_feed.auto_create_goals', False)
        self.priority_threshold = self.config.get('threat_feed.priority_threshold', 'high')

        # Threat tracking
        self.seen_threats = set()  # Hash of threats we've already processed
        self.threat_stats = defaultdict(int)

        # Feed sources configuration
        self.sources = self.config.get('threat_feed.sources', [
            'x_security',      # X/Twitter security community
            'cve_new',         # New CVEs
            'exploit_db',      # Exploit database
            'threat_intel'     # General threat intel
        ])

        self.is_running = False

        logger.info(f"Live Threat Feed initialized (enabled: {self.enabled}, interval: {self.check_interval}s)")

    async def start(self):
        """Start the threat feed background loop."""
        if not self.enabled:
            logger.info("Threat feed disabled in config")
            return

        self.is_running = True
        logger.info("🔴 Live threat feed started")

        while self.is_running:
            try:
                await self._check_threats()
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Error in threat feed loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait 1 min before retry

    async def stop(self):
        """Stop the threat feed."""
        self.is_running = False
        logger.info("Threat feed stopped")

    async def _check_threats(self):
        """Check all configured sources for new threats."""
        logger.info("Checking threat sources...")

        threats_found = []

        for source in self.sources:
            try:
                source_threats = await self._check_source(source)
                threats_found.extend(source_threats)
            except Exception as e:
                logger.error(f"Error checking source {source}: {e}")

        logger.info(f"Found {len(threats_found)} potential threats")

        # Process new threats
        new_threats = self._filter_new_threats(threats_found)
        logger.info(f"Processing {len(new_threats)} new threats")

        for threat in new_threats:
            await self._process_threat(threat)

    async def _check_source(self, source: str) -> List[Dict[str, Any]]:
        """
        Check a specific threat source.

        Args:
            source: Source identifier

        Returns:
            List of threat dictionaries
        """
        queries = {
            'x_security': "Search X for latest cybersecurity threats, zero-days, and vulnerability discussions from the past 24 hours. Focus on high-severity findings.",
            'cve_new': "Find newly published CVEs from the past 24 hours, especially those with active exploitation or high CVSS scores.",
            'exploit_db': "Check for new exploit publications and proof-of-concept code released in the past 24 hours.",
            'threat_intel': "Gather latest threat intelligence reports, indicators of compromise, and security advisories from the past 24 hours."
        }

        query = queries.get(source, f"Find latest security threats for {source}")

        # Use Grok for intelligence gathering
        from multi_llm_orchestrator import LLMType
        result = await self.orchestrator.execute(
            query,
            context={'search_focus': 'cybersecurity', 'source': source},
            force_llm=LLMType.GROK
        )

        if not result['success']:
            logger.warning(f"Failed to check source {source}")
            return []

        # Parse threats from response
        threats = self._parse_threats(result['content'], source)

        return threats

    def _parse_threats(self, content: str, source: str) -> List[Dict[str, Any]]:
        """
        Parse threat information from LLM response.

        Args:
            content: LLM response content
            source: Source identifier

        Returns:
            List of parsed threats
        """
        threats = []

        # Split by lines and look for threat indicators
        lines = content.split('\n')

        current_threat = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for CVE patterns
            if 'CVE-' in line.upper():
                if current_threat:
                    threats.append(current_threat)

                current_threat = {
                    'title': line,
                    'source': source,
                    'priority': self._infer_priority(line),
                    'timestamp': datetime.now().isoformat(),
                    'content': line,
                    'type': 'cve'
                }

            # Look for exploit/vulnerability keywords
            elif any(keyword in line.lower() for keyword in [
                'zero-day', 'exploit', 'vulnerability', 'rce', 'critical',
                'active exploitation', 'poc', 'proof of concept'
            ]):
                if current_threat:
                    current_threat['content'] += '\n' + line
                else:
                    current_threat = {
                        'title': line[:100],
                        'source': source,
                        'priority': self._infer_priority(line),
                        'timestamp': datetime.now().isoformat(),
                        'content': line,
                        'type': 'threat'
                    }

            # Continuation of current threat
            elif current_threat:
                current_threat['content'] += '\n' + line

        # Add final threat
        if current_threat:
            threats.append(current_threat)

        return threats

    def _infer_priority(self, content: str) -> str:
        """
        Infer threat priority from content.

        Args:
            content: Threat content

        Returns:
            Priority level
        """
        content_lower = content.lower()

        # Urgent keywords
        if any(keyword in content_lower for keyword in [
            'zero-day', 'active attack', 'ransomware', 'worm'
        ]):
            return ThreatPriority.URGENT

        # Critical keywords
        if any(keyword in content_lower for keyword in [
            'critical', 'rce', 'remote code execution', 'authentication bypass',
            'privilege escalation', 'root access'
        ]):
            return ThreatPriority.CRITICAL

        # High keywords
        if any(keyword in content_lower for keyword in [
            'high severity', 'exploit available', 'poc', 'actively exploited'
        ]):
            return ThreatPriority.HIGH

        # Medium keywords
        if any(keyword in content_lower for keyword in [
            'medium', 'vulnerability', 'cve', 'security advisory'
        ]):
            return ThreatPriority.MEDIUM

        return ThreatPriority.LOW

    def _filter_new_threats(self, threats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out threats we've already seen.

        Args:
            threats: List of all threats

        Returns:
            List of new threats
        """
        new_threats = []

        for threat in threats:
            # Create hash of threat
            threat_hash = hash(threat['title'] + threat.get('content', '')[:100])

            if threat_hash not in self.seen_threats:
                self.seen_threats.add(threat_hash)
                new_threats.append(threat)

        return new_threats

    async def _process_threat(self, threat: Dict[str, Any]):
        """
        Process a new threat.

        Args:
            threat: Threat dictionary
        """
        logger.info(f"Processing threat: {threat['title'][:80]}...")

        # Add to memory graph
        self._add_to_graph(threat)

        # Track stats
        self.threat_stats[threat['priority']] += 1
        self.threat_stats[threat['source']] += 1

        # Auto-create goal if high priority and enabled
        if self.auto_create_goals and self.goal_engine:
            if self._should_create_goal(threat):
                await self._create_goal_from_threat(threat)

    def _add_to_graph(self, threat: Dict[str, Any]):
        """Add threat to memory graph."""
        if not self.memory_graph:
            return

        try:
            # Create threat node
            threat_id = self.memory_graph._generate_node_id('threat')

            self.memory_graph.graph.add_node(
                threat_id,
                type='threat',
                title=threat['title'],
                priority=threat['priority'],
                source=threat['source'],
                content=threat.get('content', ''),
                timestamp=threat['timestamp'],
                threat_type=threat.get('type', 'unknown')
            )

            # Link to relevant CVEs if mentioned
            if 'CVE-' in threat['title']:
                # Extract CVE IDs
                import re
                cve_ids = re.findall(r'CVE-\d{4}-\d{4,}', threat['title'])

                for cve_id in cve_ids:
                    # Create CVE node if it doesn't exist
                    cve_node_id = f"cve_{cve_id.replace('-', '_')}"
                    if cve_node_id not in self.memory_graph.graph:
                        self.memory_graph.graph.add_node(
                            cve_node_id,
                            type='cve',
                            cve_id=cve_id,
                            timestamp=threat['timestamp']
                        )
                    self.memory_graph.graph.add_edge(
                        threat_id,
                        cve_node_id,
                        type='related_to'
                    )

            # Link to tools that might be relevant
            tool_keywords = {
                'nmap': ['port scan', 'network scan', 'service detection'],
                'nuclei': ['vulnerability scan', 'cve', 'exploit template'],
                'gobuster': ['directory', 'brute force', 'fuzzing'],
                'sqlmap': ['sql injection', 'sqli', 'database'],
                'metasploit': ['exploit', 'framework', 'payload']
            }

            content_lower = (threat['title'] + ' ' + threat.get('content', '')).lower()

            for tool, keywords in tool_keywords.items():
                if any(keyword in content_lower for keyword in keywords):
                    tool_node_id = self.memory_graph._ensure_tool_node(tool)
                    self.memory_graph.graph.add_edge(
                        threat_id,
                        tool_node_id,
                        type='recommends_tool'
                    )

            self.memory_graph._save()

            logger.debug(f"Added threat to graph: {threat_id}")

        except Exception as e:
            logger.error(f"Error adding threat to graph: {e}")

    def _should_create_goal(self, threat: Dict[str, Any]) -> bool:
        """
        Determine if a threat warrants auto-goal creation.

        Args:
            threat: Threat dictionary

        Returns:
            True if goal should be created
        """
        priority_levels = {
            ThreatPriority.LOW: 0,
            ThreatPriority.MEDIUM: 1,
            ThreatPriority.HIGH: 2,
            ThreatPriority.CRITICAL: 3,
            ThreatPriority.URGENT: 4
        }

        threshold_levels = {
            'low': 0,
            'medium': 1,
            'high': 2,
            'critical': 3,
            'urgent': 4
        }

        threat_level = priority_levels.get(threat['priority'], 0)
        threshold_level = threshold_levels.get(self.priority_threshold, 2)

        return threat_level >= threshold_level

    async def _create_goal_from_threat(self, threat: Dict[str, Any]):
        """
        Auto-create goal from threat.

        Args:
            threat: Threat dictionary
        """
        goal_text = f"Investigate threat: {threat['title']}"

        context = {
            'threat_source': threat['source'],
            'threat_priority': threat['priority'],
            'threat_content': threat.get('content', ''),
            'auto_generated': True,
            'timestamp': threat['timestamp']
        }

        try:
            goal_id = self.goal_engine.add_goal(
                goal_text,
                priority=threat['priority'],
                context=context
            )

            logger.info(f"Auto-created goal {goal_id} from threat: {threat['title'][:60]}...")

            # Track in stats
            self.threat_stats['goals_created'] += 1

        except Exception as e:
            logger.error(f"Error creating goal from threat: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get threat feed statistics."""
        return {
            'threats_seen': len(self.seen_threats),
            'by_priority': dict(self.threat_stats),
            'sources_enabled': self.sources,
            'auto_create_goals': self.auto_create_goals,
            'is_running': self.is_running
        }

    async def query_threats(self, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Query recent threats from memory graph.

        Args:
            filters: Optional filters (priority, source, timeframe)

        Returns:
            List of matching threats
        """
        if not self.memory_graph:
            return []

        threats = []

        for node_id, data in self.memory_graph.graph.nodes(data=True):
            if data.get('type') != 'threat':
                continue

            # Apply filters
            if filters:
                if 'priority' in filters and data.get('priority') != filters['priority']:
                    continue
                if 'source' in filters and data.get('source') != filters['source']:
                    continue
                if 'since' in filters:
                    threat_time = datetime.fromisoformat(data.get('timestamp', ''))
                    if threat_time < filters['since']:
                        continue

            threats.append({
                'id': node_id,
                'title': data.get('title', ''),
                'priority': data.get('priority', ''),
                'source': data.get('source', ''),
                'timestamp': data.get('timestamp', ''),
                'type': data.get('threat_type', '')
            })

        # Sort by timestamp (newest first)
        threats.sort(key=lambda x: x['timestamp'], reverse=True)

        return threats


if __name__ == "__main__":
    # Test live threat feed
    import sys
    sys.path.append('..')

    from multi_llm_orchestrator import MockGrokOrchestrator
    from hybrid_memory_graph import HybridMemoryGraph
    from config_manager import ConfigManager

    # Mock Claude
    class MockClaude:
        async def chat(self, query, store_in_memory=True):
            return "[Claude] Response"

        async def execute_with_tools(self, query):
            return "[Claude] Executed"

    async def test():
        config_data = {
            'threat_feed': {
                'enabled': True,
                'check_interval': 10,  # Short interval for testing
                'auto_create_goals': False,
                'sources': ['x_security', 'cve_new']
            }
        }

        config = ConfigManager('config.yaml')
        for key, value in config_data.items():
            config.config[key] = value

        graph = HybridMemoryGraph('test_graph.pkl')
        claude = MockClaude()
        orchestrator = MockGrokOrchestrator(config, claude, graph)

        feed = LiveThreatFeed(orchestrator, graph, config=config)

        print("\n" + "="*60)
        print("Live Threat Feed Test")
        print("="*60)

        # Test single check
        print("\n[Test] Running single threat check...")
        await feed._check_threats()

        # Query threats
        print("\n[Threats Found]")
        threats = await feed.query_threats()
        for threat in threats[:5]:
            print(f"- [{threat['priority'].upper()}] {threat['title'][:60]}...")

        # Stats
        print("\n[Stats]")
        stats = feed.get_stats()
        for key, value in stats.items():
            print(f"{key}: {value}")

        print("\n" + "="*60)
        print("✅ Threat feed operational!")
        print("="*60)

    asyncio.run(test())
