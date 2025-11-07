#!/usr/bin/env python3
"""
MindSync Oracle v5 - Deep X Intelligence Nexus

THE BREAKTHROUGH: X/Twitter as a living threat intelligence graph.

Instead of just monitoring X for threats, we BUILD A DYNAMIC GRAPH:
- Researcher networks (who influences who)
- Thread evolution (how exploits spread)
- Temporal patterns (surge detection)
- Influence scoring (who to follow)

This transforms X from a feed into a KNOWLEDGE GRAPH that feeds
the entire MindSync system.

Use cases:
- "Who are the top WordPress security researchers on X?"
- "Track CVE-2024-1234 discussion evolution"
- "Alert me when researcher clusters form around zero-days"
- "Find emerging threat patterns from X chatter"
"""

import logging
import networkx as nx
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import json
import re

logger = logging.getLogger(__name__)


class XNodeType:
    """X Nexus node types."""
    POST = "x_post"
    USER = "x_user"
    THREAD = "x_thread"
    TOPIC = "x_topic"
    HASHTAG = "x_hashtag"
    URL = "x_url"


class XEdgeType:
    """X Nexus edge types."""
    AUTHORED = "authored"
    REPLIED_TO = "replied_to"
    QUOTED = "quoted"
    MENTIONED = "mentioned"
    TAGGED = "tagged"
    LINKED = "linked"
    CO_MENTIONED = "co_mentioned"  # Users mentioned together
    INFLUENCES = "influences"  # Derived influence


class DeepXNexus:
    """
    Deep X Intelligence Nexus.

    Builds and maintains a dynamic knowledge graph from X/Twitter data,
    tracking researchers, threads, topics, and temporal patterns.
    """

    def __init__(self, multi_llm_orchestrator, memory_graph, config=None):
        """
        Initialize Deep X Nexus.

        Args:
            multi_llm_orchestrator: MultiLLMOrchestrator for X queries
            memory_graph: HybridMemoryGraph for persistence
            config: Optional configuration
        """
        self.orchestrator = multi_llm_orchestrator
        self.memory_graph = memory_graph
        self.config = config or {}

        # X-specific subgraph (view into main graph)
        self.x_graph = nx.DiGraph()
        self.x_graph.graph['type'] = 'x_nexus'

        # Caches
        self.user_cache = {}  # user_id -> user data
        self.post_cache = {}  # post_id -> post data
        self.topic_cache = defaultdict(list)  # topic -> [post_ids]

        # Tracking
        self.ingestion_stats = {
            'posts_ingested': 0,
            'users_tracked': 0,
            'threads_analyzed': 0,
            'clusters_detected': 0
        }

        logger.info("Deep X Nexus initialized")

    # ===== DATA INGESTION =====

    async def ingest_x_query(self, query: str, since: Optional[str] = None,
                            max_posts: int = 100) -> Dict[str, Any]:
        """
        Ingest X data from a semantic query.

        Args:
            query: Search query (e.g., "WordPress vulnerabilities")
            since: Optional timestamp to filter from
            max_posts: Maximum posts to retrieve

        Returns:
            Ingestion result with stats
        """
        logger.info(f"Ingesting X query: {query}")

        # Use Grok via multi-LLM orchestrator for X search
        from multi_llm_orchestrator import LLMType

        search_prompt = f"""Search X/Twitter for: {query}

Return posts in this JSON format:
[
  {{
    "id": "post_id",
    "user": {{"id": "user_id", "handle": "@username", "name": "Display Name"}},
    "content": "post text",
    "timestamp": "ISO timestamp",
    "metrics": {{"likes": 0, "retweets": 0, "replies": 0}},
    "reply_to": "post_id or null",
    "quoted_post": "post_id or null",
    "mentions": ["@user1", "@user2"],
    "hashtags": ["#tag1", "#tag2"],
    "urls": ["url1", "url2"]
  }}
]

Focus on security research, vulnerability discussions, and exploit analysis.
Limit to {max_posts} most relevant posts."""

        if since:
            search_prompt += f"\nOnly posts since: {since}"

        result = await self.orchestrator.execute(
            search_prompt,
            context={'search_focus': 'x_intelligence', 'structured_output': True},
            force_llm=LLMType.GROK
        )

        if not result['success']:
            logger.error(f"X query failed: {result.get('error')}")
            return {'success': False, 'error': result.get('error')}

        # Parse JSON response
        posts = self._parse_x_response(result['content'])

        # Ingest into graph
        ingestion_stats = self._ingest_posts(posts)

        # Detect clusters
        clusters = self._detect_clusters()

        return {
            'success': True,
            'posts_ingested': len(posts),
            'stats': ingestion_stats,
            'clusters': clusters
        }

    def _parse_x_response(self, content: str) -> List[Dict[str, Any]]:
        """Parse X data from LLM response."""
        try:
            # Try to extract JSON from response
            # Look for JSON array
            import json

            # Find JSON array in content
            start = content.find('[')
            end = content.rfind(']') + 1

            if start >= 0 and end > start:
                json_str = content[start:end]
                posts = json.loads(json_str)
                return posts

            # Fallback: Parse line by line (simpler format)
            posts = []
            lines = content.split('\n')
            current_post = None

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Look for post indicators
                if '@' in line or '#' in line or 'http' in line:
                    # Extract user handle
                    user_match = re.search(r'@(\w+)', line)
                    if user_match:
                        handle = user_match.group(1)

                        # Create simple post
                        posts.append({
                            'id': f"post_{len(posts)}",
                            'user': {
                                'id': f"user_{handle}",
                                'handle': f"@{handle}",
                                'name': handle
                            },
                            'content': line,
                            'timestamp': datetime.now().isoformat(),
                            'metrics': {'likes': 0, 'retweets': 0, 'replies': 0},
                            'mentions': re.findall(r'@(\w+)', line),
                            'hashtags': re.findall(r'#(\w+)', line),
                            'urls': re.findall(r'https?://\S+', line)
                        })

            return posts

        except Exception as e:
            logger.error(f"Error parsing X response: {e}")
            return []

    def _ingest_posts(self, posts: List[Dict[str, Any]]) -> Dict[str, int]:
        """Ingest posts into X graph."""
        stats = defaultdict(int)

        for post in posts:
            try:
                # Add post node
                post_id = f"xpost_{post['id']}"
                self.x_graph.add_node(
                    post_id,
                    type=XNodeType.POST,
                    content=post.get('content', ''),
                    timestamp=post.get('timestamp'),
                    metrics=post.get('metrics', {}),
                    raw_data=post
                )
                self.post_cache[post_id] = post
                stats['posts'] += 1

                # Add user node
                user = post.get('user', {})
                user_id = f"xuser_{user.get('id', 'unknown')}"

                if user_id not in self.x_graph:
                    self.x_graph.add_node(
                        user_id,
                        type=XNodeType.USER,
                        handle=user.get('handle', ''),
                        name=user.get('name', ''),
                        influence_score=0.0
                    )
                    self.user_cache[user_id] = user
                    stats['users'] += 1

                # Link user to post
                self.x_graph.add_edge(user_id, post_id, type=XEdgeType.AUTHORED)

                # Handle replies
                if post.get('reply_to'):
                    reply_to_id = f"xpost_{post['reply_to']}"
                    if reply_to_id in self.x_graph:
                        self.x_graph.add_edge(post_id, reply_to_id, type=XEdgeType.REPLIED_TO)
                        stats['replies'] += 1

                # Handle quotes
                if post.get('quoted_post'):
                    quoted_id = f"xpost_{post['quoted_post']}"
                    if quoted_id in self.x_graph:
                        self.x_graph.add_edge(post_id, quoted_id, type=XEdgeType.QUOTED)
                        stats['quotes'] += 1

                # Handle mentions
                for mention in post.get('mentions', []):
                    mention_id = f"xuser_{mention.replace('@', '')}"

                    # Ensure mentioned user exists
                    if mention_id not in self.x_graph:
                        self.x_graph.add_node(
                            mention_id,
                            type=XNodeType.USER,
                            handle=mention,
                            name=mention.replace('@', ''),
                            influence_score=0.0
                        )

                    self.x_graph.add_edge(post_id, mention_id, type=XEdgeType.MENTIONED)
                    stats['mentions'] += 1

                # Handle hashtags
                for hashtag in post.get('hashtags', []):
                    tag_id = f"xtag_{hashtag.replace('#', '')}"

                    if tag_id not in self.x_graph:
                        self.x_graph.add_node(
                            tag_id,
                            type=XNodeType.HASHTAG,
                            tag=hashtag
                        )

                    self.x_graph.add_edge(post_id, tag_id, type=XEdgeType.TAGGED)
                    stats['hashtags'] += 1

                # Handle URLs
                for url in post.get('urls', []):
                    url_id = f"xurl_{hash(url)}"

                    if url_id not in self.x_graph:
                        self.x_graph.add_node(
                            url_id,
                            type=XNodeType.URL,
                            url=url
                        )

                    self.x_graph.add_edge(post_id, url_id, type=XEdgeType.LINKED)
                    stats['urls'] += 1

            except Exception as e:
                logger.error(f"Error ingesting post {post.get('id')}: {e}")

        # Update global stats
        self.ingestion_stats['posts_ingested'] += stats['posts']
        self.ingestion_stats['users_tracked'] += stats['users']

        return dict(stats)

    # ===== CLUSTER DETECTION =====

    def _detect_clusters(self) -> List[Dict[str, Any]]:
        """
        Detect clusters/communities in X graph.

        Uses community detection to find groups of related users/topics.
        """
        clusters = []

        try:
            # Get undirected version for community detection
            undirected = self.x_graph.to_undirected()

            # Use Louvain method for community detection (if available)
            try:
                import community as community_louvain
                partition = community_louvain.best_partition(undirected)

                # Group by community
                communities = defaultdict(list)
                for node, comm_id in partition.items():
                    communities[comm_id].append(node)

                for comm_id, nodes in communities.items():
                    if len(nodes) >= 3:  # Minimum cluster size
                        clusters.append({
                            'id': f"cluster_{comm_id}",
                            'size': len(nodes),
                            'nodes': nodes[:10],  # Sample
                            'type': 'louvain_community'
                        })

            except ImportError:
                # Fallback: Use connected components
                for component in nx.connected_components(undirected):
                    if len(component) >= 3:
                        clusters.append({
                            'id': f"cluster_{hash(frozenset(component))}",
                            'size': len(component),
                            'nodes': list(component)[:10],
                            'type': 'connected_component'
                        })

            self.ingestion_stats['clusters_detected'] = len(clusters)

        except Exception as e:
            logger.error(f"Error detecting clusters: {e}")

        return clusters

    # ===== INFLUENCE ANALYSIS =====

    def calculate_influence_scores(self) -> Dict[str, float]:
        """
        Calculate influence scores for X users.

        Uses PageRank and centrality measures.
        """
        scores = {}

        try:
            # PageRank for overall influence
            pagerank = nx.pagerank(self.x_graph, alpha=0.85)

            # Betweenness centrality for bridge influence
            betweenness = nx.betweenness_centrality(self.x_graph)

            # Combine scores
            for node in self.x_graph.nodes():
                if self.x_graph.nodes[node].get('type') == XNodeType.USER:
                    pr_score = pagerank.get(node, 0.0)
                    bt_score = betweenness.get(node, 0.0)

                    # Weighted combination
                    combined = (pr_score * 0.7) + (bt_score * 0.3)

                    scores[node] = combined

                    # Update graph
                    self.x_graph.nodes[node]['influence_score'] = combined

        except Exception as e:
            logger.error(f"Error calculating influence: {e}")

        return scores

    def get_top_influencers(self, n: int = 10, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get top influencers.

        Args:
            n: Number of influencers to return
            topic: Optional topic filter

        Returns:
            List of influencer data
        """
        scores = self.calculate_influence_scores()

        # Filter by topic if specified
        if topic:
            # Find posts about topic
            topic_posts = [
                node for node in self.x_graph.nodes()
                if self.x_graph.nodes[node].get('type') == XNodeType.POST
                and topic.lower() in self.x_graph.nodes[node].get('content', '').lower()
            ]

            # Get authors of those posts
            topic_users = set()
            for post_id in topic_posts:
                # Find author (user -> post edge reversed)
                for pred in self.x_graph.predecessors(post_id):
                    if self.x_graph.nodes[pred].get('type') == XNodeType.USER:
                        topic_users.add(pred)

            # Filter scores
            scores = {user: score for user, score in scores.items() if user in topic_users}

        # Sort and return top N
        top_users = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n]

        influencers = []
        for user_id, score in top_users:
            user_data = self.x_graph.nodes[user_id]
            influencers.append({
                'user_id': user_id,
                'handle': user_data.get('handle'),
                'name': user_data.get('name'),
                'influence_score': score,
                'post_count': len(list(self.x_graph.successors(user_id)))
            })

        return influencers

    # ===== THREAD ANALYSIS =====

    def extract_thread(self, root_post_id: str) -> nx.DiGraph:
        """
        Extract a conversation thread as a subgraph.

        Args:
            root_post_id: Starting post ID

        Returns:
            Thread subgraph
        """
        thread_nodes = set([root_post_id])

        # BFS to find all replies
        queue = [root_post_id]
        visited = set()

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            # Find replies to this post
            for node in self.x_graph.nodes():
                if self.x_graph.has_edge(node, current):
                    edge_data = self.x_graph.get_edge_data(node, current)
                    if edge_data and edge_data.get('type') == XEdgeType.REPLIED_TO:
                        thread_nodes.add(node)
                        queue.append(node)

        # Create subgraph
        thread_graph = self.x_graph.subgraph(thread_nodes).copy()
        thread_graph.graph['type'] = 'x_thread'
        thread_graph.graph['root'] = root_post_id

        self.ingestion_stats['threads_analyzed'] += 1

        return thread_graph

    # ===== INTEGRATION =====

    def sync_to_main_graph(self):
        """Sync X graph to main memory graph."""
        try:
            # Add X nodes to main graph
            for node, data in self.x_graph.nodes(data=True):
                if node not in self.memory_graph.graph:
                    self.memory_graph.graph.add_node(node, **data)

            # Add X edges to main graph
            for source, target, data in self.x_graph.edges(data=True):
                if not self.memory_graph.graph.has_edge(source, target):
                    self.memory_graph.graph.add_edge(source, target, **data)

            # Link to threats/tools if relevant
            self._link_x_to_threats()
            self._link_x_to_tools()

            self.memory_graph._save()

            logger.info(f"Synced {len(self.x_graph.nodes())} X nodes to main graph")

        except Exception as e:
            logger.error(f"Error syncing to main graph: {e}")

    def _link_x_to_threats(self):
        """Link X posts to threat nodes if they mention CVEs/threats."""
        for node in self.x_graph.nodes():
            if self.x_graph.nodes[node].get('type') != XNodeType.POST:
                continue

            content = self.x_graph.nodes[node].get('content', '')

            # Look for CVE mentions
            cve_pattern = r'CVE-\d{4}-\d{4,}'
            cves = re.findall(cve_pattern, content)

            for cve_id in cves:
                cve_node_id = f"cve_{cve_id.replace('-', '_')}"

                # Link in main graph
                if cve_node_id in self.memory_graph.graph:
                    self.memory_graph.graph.add_edge(
                        node,
                        cve_node_id,
                        type='discusses'
                    )

    def _link_x_to_tools(self):
        """Link X posts to tool nodes if they mention tools."""
        tool_keywords = {
            'nmap': ['nmap', 'port scan', 'network scan'],
            'nuclei': ['nuclei', 'vulnerability scan'],
            'gobuster': ['gobuster', 'directory brute'],
            'sqlmap': ['sqlmap', 'sql injection'],
            'metasploit': ['metasploit', 'msf', 'exploit framework']
        }

        for node in self.x_graph.nodes():
            if self.x_graph.nodes[node].get('type') != XNodeType.POST:
                continue

            content = self.x_graph.nodes[node].get('content', '').lower()

            for tool, keywords in tool_keywords.items():
                if any(keyword in content for keyword in keywords):
                    tool_node_id = f"tool_{tool}"

                    # Link in main graph
                    if tool_node_id in self.memory_graph.graph:
                        self.memory_graph.graph.add_edge(
                            node,
                            tool_node_id,
                            type='recommends'
                        )

    def get_stats(self) -> Dict[str, Any]:
        """Get X nexus statistics."""
        return {
            'x_nodes': len(self.x_graph.nodes()),
            'x_edges': len(self.x_graph.edges()),
            **self.ingestion_stats,
            'node_types': {
                XNodeType.POST: len([n for n in self.x_graph.nodes() if self.x_graph.nodes[n].get('type') == XNodeType.POST]),
                XNodeType.USER: len([n for n in self.x_graph.nodes() if self.x_graph.nodes[n].get('type') == XNodeType.USER]),
                XNodeType.HASHTAG: len([n for n in self.x_graph.nodes() if self.x_graph.nodes[n].get('type') == XNodeType.HASHTAG]),
            }
        }


if __name__ == "__main__":
    # Test Deep X Nexus
    import asyncio
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
        config = ConfigManager('config.yaml')
        graph = HybridMemoryGraph('test_graph.pkl')
        claude = MockClaude()
        orchestrator = MockGrokOrchestrator(config, claude, graph)

        nexus = DeepXNexus(orchestrator, graph)

        print("\n" + "="*60)
        print("Deep X Nexus Test")
        print("="*60)

        # Test ingestion
        print("\n[Test] Ingesting X query...")
        result = await nexus.ingest_x_query("WordPress vulnerabilities CVE", max_posts=10)
        print(f"Success: {result['success']}")
        print(f"Posts ingested: {result.get('posts_ingested', 0)}")

        # Test influence
        print("\n[Test] Calculating influence...")
        influencers = nexus.get_top_influencers(5)
        for inf in influencers:
            print(f"  - {inf['handle']}: {inf['influence_score']:.3f}")

        # Sync to main graph
        print("\n[Test] Syncing to main graph...")
        nexus.sync_to_main_graph()

        # Stats
        print("\n[Stats]")
        stats = nexus.get_stats()
        for key, value in stats.items():
            print(f"{key}: {value}")

        print("\n" + "="*60)
        print("✅ Deep X Nexus operational!")
        print("="*60)

    asyncio.run(test())
