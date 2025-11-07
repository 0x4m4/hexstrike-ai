#!/usr/bin/env python3
"""
MindSync Oracle v5 - X Timeline Analyzer

THE BREAKTHROUGH: Temporal intelligence from X data.

Track how threats evolve over time:
- Surge detection (when does chatter spike?)
- Causality analysis (tweet → CVE → exploit)
- Trend prediction (what's emerging?)
- Historical patterns (similar surges in past?)

This turns X from a snapshot into a TIME MACHINE.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class SurgeType:
    """Types of detected surges."""
    SUDDEN = "sudden"          # Rapid spike
    GRADUAL = "gradual"        # Steady increase
    PERIODIC = "periodic"      # Recurring pattern
    ANOMALOUS = "anomalous"    # Unexpected deviation


class XTimelineAnalyzer:
    """
    Temporal analysis of X intelligence.

    Detects surges, tracks evolution, predicts trends.
    """

    def __init__(self, x_nexus, config=None):
        """
        Initialize timeline analyzer.

        Args:
            x_nexus: DeepXNexus instance
            config: Optional configuration
        """
        self.nexus = x_nexus
        self.config = config or {}

        # Analysis parameters
        self.surge_threshold = self.config.get('surge_threshold', 2.0)  # 2x baseline
        self.window_days = self.config.get('window_days', 30)
        self.baseline_days = self.config.get('baseline_days', 7)

        # Caches
        self.timeline_cache = {}
        self.surge_history = []

        logger.info("X Timeline Analyzer initialized")

    # ===== TIMELINE CONSTRUCTION =====

    def build_timeline(self, topic: Optional[str] = None,
                      since: Optional[datetime] = None,
                      until: Optional[datetime] = None) -> pd.DataFrame:
        """
        Build timeline DataFrame from X graph.

        Args:
            topic: Optional topic filter
            since: Start date
            until: End date

        Returns:
            DataFrame with timestamp index and metrics
        """
        # Extract posts from X graph
        posts = []

        for node in self.nexus.x_graph.nodes():
            node_data = self.nexus.x_graph.nodes[node]

            if node_data.get('type') != 'x_post':
                continue

            # Topic filter
            if topic:
                content = node_data.get('content', '').lower()
                if topic.lower() not in content:
                    continue

            # Get timestamp
            timestamp = node_data.get('timestamp')
            if not timestamp:
                continue

            try:
                ts = pd.to_datetime(timestamp)

                # Date range filter
                if since and ts < since:
                    continue
                if until and ts > until:
                    continue

                posts.append({
                    'timestamp': ts,
                    'node_id': node,
                    'content': node_data.get('content', ''),
                    'likes': node_data.get('metrics', {}).get('likes', 0),
                    'retweets': node_data.get('metrics', {}).get('retweets', 0),
                    'replies': node_data.get('metrics', {}).get('replies', 0)
                })

            except Exception as e:
                logger.debug(f"Error parsing timestamp {timestamp}: {e}")

        if not posts:
            return pd.DataFrame()

        # Create DataFrame
        df = pd.DataFrame(posts)
        df = df.set_index('timestamp').sort_index()

        # Add derived metrics
        df['engagement'] = df['likes'] + df['retweets'] + df['replies']

        return df

    def aggregate_timeline(self, df: pd.DataFrame, freq: str = 'D') -> pd.DataFrame:
        """
        Aggregate timeline by time period.

        Args:
            df: Timeline DataFrame
            freq: Frequency ('H'=hourly, 'D'=daily, 'W'=weekly)

        Returns:
            Aggregated DataFrame
        """
        if df.empty:
            return df

        # Resample by frequency
        agg_df = df.resample(freq).agg({
            'content': 'count',  # Renamed to 'post_count'
            'likes': 'sum',
            'retweets': 'sum',
            'replies': 'sum',
            'engagement': 'sum'
        })

        agg_df = agg_df.rename(columns={'content': 'post_count'})

        # Add rolling averages
        agg_df['post_count_ma7'] = agg_df['post_count'].rolling(window=7, min_periods=1).mean()
        agg_df['engagement_ma7'] = agg_df['engagement'].rolling(window=7, min_periods=1).mean()

        return agg_df

    # ===== SURGE DETECTION =====

    def detect_surges(self, df: pd.DataFrame, metric: str = 'post_count') -> List[Dict[str, Any]]:
        """
        Detect surges in timeline data.

        Args:
            df: Aggregated timeline DataFrame
            metric: Metric to analyze ('post_count', 'engagement', etc.)

        Returns:
            List of detected surges
        """
        surges = []

        if df.empty or metric not in df.columns:
            return surges

        values = df[metric].values
        timestamps = df.index

        # Calculate baseline (median of first baseline_days)
        baseline_window = min(self.baseline_days, len(values) // 3)
        if baseline_window < 1:
            return surges

        baseline = np.median(values[:baseline_window])

        if baseline == 0:
            baseline = 1  # Avoid division by zero

        # Detect points above threshold
        threshold = baseline * self.surge_threshold

        for i, (timestamp, value) in enumerate(zip(timestamps, values)):
            if value > threshold:
                # Calculate surge magnitude
                magnitude = value / baseline

                # Look for surge duration
                duration = 1
                j = i + 1
                while j < len(values) and values[j] > threshold:
                    duration += 1
                    j += 1

                # Classify surge type
                if i > 0:
                    previous = values[i-1]
                    if previous < baseline and value > threshold:
                        surge_type = SurgeType.SUDDEN
                    elif previous > baseline * 1.2:
                        surge_type = SurgeType.GRADUAL
                    else:
                        surge_type = SurgeType.ANOMALOUS
                else:
                    surge_type = SurgeType.SUDDEN

                surge = {
                    'timestamp': str(timestamp),
                    'value': float(value),
                    'baseline': float(baseline),
                    'magnitude': float(magnitude),
                    'duration': duration,
                    'type': surge_type,
                    'metric': metric
                }

                surges.append(surge)

                # Record in history
                self.surge_history.append(surge)

                # Skip ahead past this surge
                i = j

        return surges

    def analyze_surge_context(self, surge: Dict[str, Any],
                              df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze context around a surge.

        Args:
            surge: Surge dictionary
            df: Full timeline DataFrame

        Returns:
            Context analysis
        """
        surge_time = pd.to_datetime(surge['timestamp'])

        # Get posts around surge time (±1 day)
        start = surge_time - timedelta(days=1)
        end = surge_time + timedelta(days=1)

        context_posts = df[(df.index >= start) & (df.index <= end)]

        if context_posts.empty:
            return {'posts': []}

        # Extract top engaging posts
        top_posts = context_posts.nlargest(5, 'engagement')

        # Extract common themes (simplified - just look at content)
        all_content = ' '.join(context_posts['content'].values)

        # Extract hashtags
        import re
        hashtags = re.findall(r'#(\w+)', all_content)
        hashtag_counts = pd.Series(hashtags).value_counts().to_dict()

        # Extract mentions
        mentions = re.findall(r'@(\w+)', all_content)
        mention_counts = pd.Series(mentions).value_counts().to_dict()

        return {
            'posts_count': len(context_posts),
            'top_posts': [
                {
                    'content': post['content'][:100],
                    'engagement': post['engagement']
                }
                for _, post in top_posts.iterrows()
            ],
            'top_hashtags': dict(list(hashtag_counts.items())[:5]),
            'top_mentions': dict(list(mention_counts.items())[:5])
        }

    # ===== TREND ANALYSIS =====

    def detect_trends(self, df: pd.DataFrame, metric: str = 'post_count') -> Dict[str, Any]:
        """
        Detect overall trends in timeline.

        Args:
            df: Aggregated timeline DataFrame
            metric: Metric to analyze

        Returns:
            Trend analysis
        """
        if df.empty or metric not in df.columns:
            return {'trend': 'unknown', 'confidence': 0.0}

        values = df[metric].values

        if len(values) < 3:
            return {'trend': 'insufficient_data', 'confidence': 0.0}

        # Simple linear regression for trend direction
        x = np.arange(len(values))
        y = values

        # Remove NaN values
        mask = ~np.isnan(y)
        x = x[mask]
        y = y[mask]

        if len(x) < 2:
            return {'trend': 'insufficient_data', 'confidence': 0.0}

        # Fit line
        coeffs = np.polyfit(x, y, 1)
        slope = coeffs[0]

        # Calculate R-squared for confidence
        p = np.poly1d(coeffs)
        yhat = p(x)
        ybar = np.mean(y)
        ssreg = np.sum((yhat - ybar) ** 2)
        sstot = np.sum((y - ybar) ** 2)
        r_squared = ssreg / sstot if sstot != 0 else 0

        # Determine trend
        if abs(slope) < 0.01:
            trend = 'stable'
        elif slope > 0:
            if slope > 0.5:
                trend = 'rapidly_increasing'
            else:
                trend = 'increasing'
        else:
            if slope < -0.5:
                trend = 'rapidly_decreasing'
            else:
                trend = 'decreasing'

        return {
            'trend': trend,
            'slope': float(slope),
            'confidence': float(r_squared),
            'direction': 'up' if slope > 0 else 'down' if slope < 0 else 'stable'
        }

    # ===== CAUSALITY ANALYSIS =====

    def analyze_causality(self, event_a: str, event_b: str,
                         window_days: int = 7) -> Dict[str, Any]:
        """
        Analyze potential causal relationship between events.

        Args:
            event_a: First event (e.g., "CVE-2024-1234 published")
            event_b: Second event (e.g., "exploit code released")
            window_days: Time window to analyze

        Returns:
            Causality analysis
        """
        # Build timelines for both events
        df_a = self.build_timeline(topic=event_a)
        df_b = self.build_timeline(topic=event_b)

        if df_a.empty or df_b.empty:
            return {'correlation': 0.0, 'likely_causal': False}

        # Aggregate daily
        agg_a = self.aggregate_timeline(df_a, freq='D')
        agg_b = self.aggregate_timeline(df_b, freq='D')

        # Align timelines
        combined = pd.DataFrame({
            'event_a': agg_a['post_count'],
            'event_b': agg_b['post_count']
        }).fillna(0)

        if len(combined) < 2:
            return {'correlation': 0.0, 'likely_causal': False}

        # Calculate cross-correlation
        correlation = combined['event_a'].corr(combined['event_b'])

        # Check for time lag (does event_a precede event_b?)
        # Find first significant occurrence of each
        threshold = 2  # Minimum posts to count

        first_a = None
        first_b = None

        for timestamp, row in combined.iterrows():
            if row['event_a'] >= threshold and first_a is None:
                first_a = timestamp
            if row['event_b'] >= threshold and first_b is None:
                first_b = timestamp

        likely_causal = False
        time_lag = None

        if first_a and first_b:
            time_lag = (first_b - first_a).days
            # Causal if A precedes B and correlation is positive
            likely_causal = (time_lag > 0 and time_lag <= window_days and correlation > 0.5)

        return {
            'correlation': float(correlation) if not np.isnan(correlation) else 0.0,
            'likely_causal': likely_causal,
            'time_lag_days': time_lag,
            'first_a': str(first_a) if first_a else None,
            'first_b': str(first_b) if first_b else None
        }

    # ===== VISUALIZATION =====

    def export_timeline_chart(self, df: pd.DataFrame, output_path: str,
                             metric: str = 'post_count'):
        """
        Export timeline chart.

        Args:
            df: Timeline DataFrame
            output_path: Path to save chart
            metric: Metric to plot
        """
        try:
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(14, 6))

            # Plot metric
            ax.plot(df.index, df[metric], label=metric, linewidth=2)

            # Plot moving average if available
            ma_col = f'{metric}_ma7'
            if ma_col in df.columns:
                ax.plot(df.index, df[ma_col], label='7-day MA',
                       linestyle='--', alpha=0.7)

            # Mark surges
            surges = self.detect_surges(df, metric)
            for surge in surges:
                surge_time = pd.to_datetime(surge['timestamp'])
                ax.axvline(surge_time, color='red', alpha=0.3, linestyle=':')
                ax.text(surge_time, surge['value'], f"{surge['magnitude']:.1f}x",
                       rotation=90, va='bottom', fontsize=8)

            ax.set_xlabel('Time')
            ax.set_ylabel(metric)
            ax.set_title(f'X Timeline: {metric}')
            ax.legend()
            ax.grid(True, alpha=0.3)

            plt.tight_layout()
            plt.savefig(output_path, dpi=150)
            plt.close()

            logger.info(f"Timeline chart saved to {output_path}")

        except ImportError:
            logger.warning("matplotlib not available for chart export")
        except Exception as e:
            logger.error(f"Error exporting chart: {e}")

    # ===== HIGH-LEVEL ANALYSIS =====

    def analyze_topic_evolution(self, topic: str, days: int = 30) -> Dict[str, Any]:
        """
        Complete analysis of topic evolution over time.

        Args:
            topic: Topic to analyze
            days: Number of days to analyze

        Returns:
            Comprehensive analysis
        """
        since = datetime.now() - timedelta(days=days)

        # Build timeline
        df = self.build_timeline(topic=topic, since=since)

        if df.empty:
            return {'error': 'No data found for topic'}

        # Aggregate
        agg_df = self.aggregate_timeline(df, freq='D')

        # Detect surges
        surges = self.detect_surges(agg_df, metric='post_count')

        # Detect trends
        trends = self.detect_trends(agg_df, metric='post_count')

        # Analyze surge contexts
        surge_contexts = []
        for surge in surges[:5]:  # Top 5 surges
            context = self.analyze_surge_context(surge, df)
            surge_contexts.append({
                'surge': surge,
                'context': context
            })

        return {
            'topic': topic,
            'period_days': days,
            'total_posts': len(df),
            'date_range': {
                'start': str(df.index.min()),
                'end': str(df.index.max())
            },
            'trends': trends,
            'surges': surges,
            'surge_contexts': surge_contexts,
            'peak_engagement': {
                'date': str(df['engagement'].idxmax()) if not df.empty else None,
                'value': float(df['engagement'].max()) if not df.empty else 0
            }
        }


if __name__ == "__main__":
    # Test X Timeline Analyzer
    import asyncio
    import sys
    sys.path.append('..')

    from deep_x_nexus import DeepXNexus
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
        await nexus.ingest_x_query("WordPress CVE", max_posts=20)

        analyzer = XTimelineAnalyzer(nexus)

        print("\n" + "="*60)
        print("X Timeline Analyzer Test")
        print("="*60)

        # Build timeline
        print("\n[Test] Building timeline...")
        df = analyzer.build_timeline(topic="WordPress")
        print(f"Timeline entries: {len(df)}")

        if not df.empty:
            # Aggregate
            print("\n[Test] Aggregating timeline...")
            agg_df = analyzer.aggregate_timeline(df, freq='D')
            print(f"Aggregated periods: {len(agg_df)}")

            # Detect surges
            print("\n[Test] Detecting surges...")
            surges = analyzer.detect_surges(agg_df)
            print(f"Surges detected: {len(surges)}")
            for surge in surges[:3]:
                print(f"  - {surge['timestamp']}: {surge['magnitude']:.1f}x ({surge['type']})")

            # Detect trends
            print("\n[Test] Detecting trends...")
            trends = analyzer.detect_trends(agg_df)
            print(f"Trend: {trends['trend']} (confidence: {trends['confidence']:.2f})")

            # Full analysis
            print("\n[Test] Full topic evolution analysis...")
            analysis = analyzer.analyze_topic_evolution("WordPress", days=30)
            print(f"Total posts: {analysis['total_posts']}")
            print(f"Surges: {len(analysis['surges'])}")
            print(f"Trend: {analysis['trends']['trend']}")

        print("\n" + "="*60)
        print("✅ X Timeline Analyzer operational!")
        print("="*60)

    asyncio.run(test())
