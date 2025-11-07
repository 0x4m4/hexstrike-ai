#!/usr/bin/env python3
"""
MindSync Oracle v5 - X Researcher Dossier Generator

THE BREAKTHROUGH: Comprehensive profiling of security researchers on X.

Automatically generate "dossiers" for researchers:
- Influence metrics (who listens to them?)
- Expertise areas (what do they talk about?)
- Collaboration networks (who do they work with?)
- Activity patterns (when are they most active?)
- Sentiment analysis (positive/negative/neutral)

This creates a living directory of the security research community.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import json

logger = logging.getLogger(__name__)


class ResearcherProfile:
    """Structured researcher profile."""

    def __init__(self, user_id: str, handle: str, name: str):
        self.user_id = user_id
        self.handle = handle
        self.name = name

        # Metrics
        self.influence_score = 0.0
        self.expertise_areas = {}  # topic -> confidence
        self.total_posts = 0
        self.total_engagement = 0

        # Network
        self.collaborators = []  # [(user_id, interaction_count)]
        self.followers_estimate = 0
        self.connections = []

        # Activity
        self.activity_by_hour = defaultdict(int)
        self.activity_by_day = defaultdict(int)
        self.first_seen = None
        self.last_seen = None

        # Content
        self.top_hashtags = []
        self.top_mentions = []
        self.sentiment_distribution = {'positive': 0, 'neutral': 0, 'negative': 0}

        # Insights
        self.key_insights = []


class XResearcherDossier:
    """
    Generate comprehensive researcher dossiers.

    Analyzes X activity to profile security researchers and build
    a living directory of the community.
    """

    def __init__(self, x_nexus, timeline_analyzer, config=None):
        """
        Initialize dossier generator.

        Args:
            x_nexus: DeepXNexus instance
            timeline_analyzer: XTimelineAnalyzer instance
            config: Optional configuration
        """
        self.nexus = x_nexus
        self.timeline = timeline_analyzer
        self.config = config or {}

        # Dossier cache
        self.dossiers = {}  # user_id -> ResearcherProfile

        # Analysis parameters
        self.min_posts_for_profile = self.config.get('min_posts', 5)

        logger.info("X Researcher Dossier Generator initialized")

    # ===== PROFILE GENERATION =====

    def generate_dossier(self, user_id: str) -> ResearcherProfile:
        """
        Generate complete dossier for a researcher.

        Args:
            user_id: X user ID

        Returns:
            ResearcherProfile
        """
        # Check cache
        if user_id in self.dossiers:
            return self.dossiers[user_id]

        # Get user node from graph
        if user_id not in self.nexus.x_graph:
            logger.warning(f"User {user_id} not found in X graph")
            return None

        user_data = self.nexus.x_graph.nodes[user_id]

        # Create profile
        profile = ResearcherProfile(
            user_id=user_id,
            handle=user_data.get('handle', ''),
            name=user_data.get('name', '')
        )

        # Extract metrics
        profile.influence_score = user_data.get('influence_score', 0.0)

        # Analyze posts
        self._analyze_posts(profile)

        # Analyze network
        self._analyze_network(profile)

        # Analyze activity patterns
        self._analyze_activity(profile)

        # Analyze content
        self._analyze_content(profile)

        # Generate insights
        self._generate_insights(profile)

        # Cache
        self.dossiers[user_id] = profile

        return profile

    def _analyze_posts(self, profile: ResearcherProfile):
        """Analyze user's posts for metrics."""
        user_id = profile.user_id

        # Find all posts by this user
        posts = []
        for successor in self.nexus.x_graph.successors(user_id):
            node_data = self.nexus.x_graph.nodes[successor]
            if node_data.get('type') == 'x_post':
                posts.append((successor, node_data))

        profile.total_posts = len(posts)

        # Calculate engagement
        total_engagement = 0
        for post_id, post_data in posts:
            metrics = post_data.get('metrics', {})
            engagement = metrics.get('likes', 0) + metrics.get('retweets', 0) + metrics.get('replies', 0)
            total_engagement += engagement

        profile.total_engagement = total_engagement

        # Track timestamps
        timestamps = []
        for post_id, post_data in posts:
            ts = post_data.get('timestamp')
            if ts:
                try:
                    import pandas as pd
                    timestamps.append(pd.to_datetime(ts))
                except:
                    pass

        if timestamps:
            profile.first_seen = min(timestamps)
            profile.last_seen = max(timestamps)

    def _analyze_network(self, profile: ResearcherProfile):
        """Analyze user's network connections."""
        user_id = profile.user_id

        # Find mentions (who they interact with)
        mentions = defaultdict(int)

        for successor in self.nexus.x_graph.successors(user_id):
            # This is a post by the user
            if self.nexus.x_graph.nodes[successor].get('type') != 'x_post':
                continue

            # Find who this post mentions
            for mentioned in self.nexus.x_graph.successors(successor):
                if self.nexus.x_graph.nodes[mentioned].get('type') == 'x_user':
                    edge_data = self.nexus.x_graph.get_edge_data(successor, mentioned)
                    if edge_data and edge_data.get('type') == 'mentioned':
                        mentions[mentioned] += 1

        # Top collaborators
        profile.collaborators = sorted(mentions.items(), key=lambda x: x[1], reverse=True)[:10]

        # Estimate followers from mentions/engagement
        if profile.total_posts > 0:
            avg_engagement = profile.total_engagement / profile.total_posts
            # Rough heuristic: followers ~ engagement * 100
            profile.followers_estimate = int(avg_engagement * 100)

    def _analyze_activity(self, profile: ResearcherProfile):
        """Analyze activity patterns."""
        user_id = profile.user_id

        # Find all posts
        for successor in self.nexus.x_graph.successors(user_id):
            node_data = self.nexus.x_graph.nodes[successor]
            if node_data.get('type') != 'x_post':
                continue

            ts = node_data.get('timestamp')
            if not ts:
                continue

            try:
                import pandas as pd
                dt = pd.to_datetime(ts)

                # Hour of day
                profile.activity_by_hour[dt.hour] += 1

                # Day of week
                profile.activity_by_day[dt.day_name()] += 1

            except Exception as e:
                logger.debug(f"Error parsing timestamp {ts}: {e}")

    def _analyze_content(self, profile: ResearcherProfile):
        """Analyze content themes and sentiment."""
        user_id = profile.user_id

        # Collect all content
        all_content = []
        all_hashtags = []
        all_mentions = []

        for successor in self.nexus.x_graph.successors(user_id):
            node_data = self.nexus.x_graph.nodes[successor]
            if node_data.get('type') != 'x_post':
                continue

            content = node_data.get('content', '')
            all_content.append(content)

            # Extract hashtags and mentions
            import re
            all_hashtags.extend(re.findall(r'#(\w+)', content))
            all_mentions.extend(re.findall(r'@(\w+)', content))

        # Top hashtags
        if all_hashtags:
            hashtag_counts = Counter(all_hashtags)
            profile.top_hashtags = hashtag_counts.most_common(10)

        # Top mentions
        if all_mentions:
            mention_counts = Counter(all_mentions)
            profile.top_mentions = mention_counts.most_common(10)

        # Extract expertise areas (simplified - based on keywords)
        expertise_keywords = {
            'web_security': ['xss', 'csrf', 'sqli', 'sql injection', 'web vulnerability'],
            'network_security': ['nmap', 'port scan', 'firewall', 'network', 'packet'],
            'exploit_dev': ['exploit', 'shellcode', 'rop', 'buffer overflow', 'metasploit'],
            'reverse_engineering': ['ida', 'ghidra', 'reverse', 'binary', 'disassembly'],
            'cloud_security': ['aws', 'azure', 'gcp', 'cloud', 'kubernetes'],
            'mobile_security': ['android', 'ios', 'mobile', 'apk', 'frida'],
            'malware_analysis': ['malware', 'ransomware', 'trojan', 'virus', 'ioc'],
            'osint': ['osint', 'reconnaissance', 'footprint', 'information gathering']
        }

        all_text = ' '.join(all_content).lower()

        for area, keywords in expertise_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in all_text)
            if matches > 0:
                # Confidence based on frequency
                confidence = min(matches / len(all_content) if all_content else 0, 1.0)
                profile.expertise_areas[area] = confidence

        # Simple sentiment analysis (keyword-based)
        positive_keywords = ['great', 'excellent', 'amazing', 'awesome', 'good', 'love', 'best']
        negative_keywords = ['bad', 'terrible', 'awful', 'worst', 'hate', 'broken', 'fail']

        positive_count = sum(text.lower().count(keyword) for text in all_content for keyword in positive_keywords)
        negative_count = sum(text.lower().count(keyword) for text in all_content for keyword in negative_keywords)
        neutral_count = len(all_content) - positive_count - negative_count

        total = positive_count + negative_count + neutral_count
        if total > 0:
            profile.sentiment_distribution = {
                'positive': positive_count / total,
                'neutral': neutral_count / total,
                'negative': negative_count / total
            }

    def _generate_insights(self, profile: ResearcherProfile):
        """Generate key insights about researcher."""
        insights = []

        # Influence insight
        if profile.influence_score > 0.5:
            insights.append(f"High-influence researcher (score: {profile.influence_score:.2f})")
        elif profile.influence_score > 0.2:
            insights.append(f"Moderate influence in community (score: {profile.influence_score:.2f})")

        # Activity insight
        if profile.total_posts > 100:
            insights.append(f"Highly active ({profile.total_posts} posts)")
        elif profile.total_posts > 50:
            insights.append(f"Active contributor ({profile.total_posts} posts)")

        # Engagement insight
        if profile.total_posts > 0:
            avg_engagement = profile.total_engagement / profile.total_posts
            if avg_engagement > 100:
                insights.append(f"High engagement per post ({avg_engagement:.0f} avg)")

        # Expertise insights
        if profile.expertise_areas:
            top_expertise = max(profile.expertise_areas.items(), key=lambda x: x[1])
            insights.append(f"Primary expertise: {top_expertise[0]} (confidence: {top_expertise[1]:.0%})")

        # Collaboration insight
        if len(profile.collaborators) > 5:
            insights.append(f"Well-connected ({len(profile.collaborators)} frequent collaborators)")

        # Activity pattern insight
        if profile.activity_by_hour:
            peak_hour = max(profile.activity_by_hour.items(), key=lambda x: x[1])[0]
            insights.append(f"Most active at {peak_hour}:00 UTC")

        profile.key_insights = insights

    # ===== BATCH OPERATIONS =====

    def generate_top_researchers(self, n: int = 20,
                                expertise_filter: Optional[str] = None) -> List[ResearcherProfile]:
        """
        Generate dossiers for top researchers.

        Args:
            n: Number of researchers to profile
            expertise_filter: Optional expertise area filter

        Returns:
            List of researcher profiles
        """
        # Get top influencers from nexus
        influencers = self.nexus.get_top_influencers(n * 2)  # Get more to filter

        profiles = []

        for influencer in influencers:
            user_id = influencer['user_id']

            # Generate dossier
            profile = self.generate_dossier(user_id)

            if not profile:
                continue

            # Filter by expertise if specified
            if expertise_filter:
                if expertise_filter not in profile.expertise_areas:
                    continue

            # Require minimum posts
            if profile.total_posts < self.min_posts_for_profile:
                continue

            profiles.append(profile)

            if len(profiles) >= n:
                break

        return profiles

    # ===== EXPORT =====

    def export_dossier(self, profile: ResearcherProfile) -> Dict[str, Any]:
        """
        Export dossier as dictionary.

        Args:
            profile: ResearcherProfile

        Returns:
            Dossier dictionary
        """
        return {
            'user_id': profile.user_id,
            'handle': profile.handle,
            'name': profile.name,
            'metrics': {
                'influence_score': profile.influence_score,
                'total_posts': profile.total_posts,
                'total_engagement': profile.total_engagement,
                'followers_estimate': profile.followers_estimate
            },
            'expertise': dict(sorted(profile.expertise_areas.items(),
                                   key=lambda x: x[1], reverse=True)),
            'network': {
                'top_collaborators': [
                    {
                        'user_id': user_id,
                        'handle': self.nexus.x_graph.nodes.get(user_id, {}).get('handle', ''),
                        'interactions': count
                    }
                    for user_id, count in profile.collaborators[:5]
                ]
            },
            'activity': {
                'first_seen': str(profile.first_seen) if profile.first_seen else None,
                'last_seen': str(profile.last_seen) if profile.last_seen else None,
                'peak_hours': dict(sorted(profile.activity_by_hour.items(),
                                        key=lambda x: x[1], reverse=True)[:3]),
                'active_days': dict(sorted(profile.activity_by_day.items(),
                                         key=lambda x: x[1], reverse=True)[:3])
            },
            'content': {
                'top_hashtags': profile.top_hashtags[:5],
                'top_mentions': profile.top_mentions[:5],
                'sentiment': profile.sentiment_distribution
            },
            'insights': profile.key_insights
        }

    def export_directory(self, profiles: List[ResearcherProfile],
                        output_path: str):
        """
        Export researcher directory as JSON.

        Args:
            profiles: List of profiles
            output_path: Output file path
        """
        directory = {
            'generated': datetime.now().isoformat(),
            'total_researchers': len(profiles),
            'researchers': [self.export_dossier(p) for p in profiles]
        }

        with open(output_path, 'w') as f:
            json.dump(directory, f, indent=2)

        logger.info(f"Researcher directory exported to {output_path}")


if __name__ == "__main__":
    # Test X Researcher Dossier
    import asyncio
    import sys
    sys.path.append('..')

    from deep_x_nexus import DeepXNexus
    from x_timeline_analyzer import XTimelineAnalyzer
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

        # Create nexus and ingest data
        nexus = DeepXNexus(orchestrator, graph)
        await nexus.ingest_x_query("cybersecurity WordPress", max_posts=30)

        # Calculate influence
        nexus.calculate_influence_scores()

        timeline = XTimelineAnalyzer(nexus)
        dossier_gen = XResearcherDossier(nexus, timeline)

        print("\n" + "="*60)
        print("X Researcher Dossier Test")
        print("="*60)

        # Generate top researchers
        print("\n[Test] Generating top researcher dossiers...")
        profiles = dossier_gen.generate_top_researchers(n=5)
        print(f"Profiles generated: {len(profiles)}")

        for profile in profiles:
            print(f"\n--- {profile.handle} ---")
            print(f"Influence: {profile.influence_score:.3f}")
            print(f"Posts: {profile.total_posts}")
            print(f"Engagement: {profile.total_engagement}")

            if profile.expertise_areas:
                top_expertise = max(profile.expertise_areas.items(), key=lambda x: x[1])
                print(f"Top expertise: {top_expertise[0]} ({top_expertise[1]:.0%})")

            if profile.key_insights:
                print(f"Key insights: {profile.key_insights[0]}")

        # Export directory
        if profiles:
            print("\n[Test] Exporting researcher directory...")
            dossier_gen.export_directory(profiles, "test_researcher_directory.json")
            print("Directory exported")

        print("\n" + "="*60)
        print("✅ X Researcher Dossier operational!")
        print("="*60)

    asyncio.run(test())
