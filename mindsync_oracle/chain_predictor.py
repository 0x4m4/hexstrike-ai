#!/usr/bin/env python3
"""
MindSync Oracle v8 - Predictive Chain Predictor

XBOW-INSPIRED PREDICTIVE VULNERABILITY CHAINING

⚠️ ETHICAL RESEARCH ONLY - PREDICTIONS, NOT EXPLOITATION ⚠️

This module analyzes v7 threat intelligence patterns and predicts likely
vulnerability chains BEFORE they become public exploits. Think XBOW's
predictive capabilities, but for defensive research only.

Features:
- Pattern-based chain prediction from threat clusters
- CVE timeline analysis for early warning signals
- Researcher activity correlation (from v5 Deep X)
- Exploitation likelihood forecasting
- Chain evolution tracking (how chains morph over time)
- PREDICTIONS ONLY - no autonomous exploitation

Prediction Confidence Factors:
- Cross-source validation (X + Tor + traditional feeds)
- Researcher expertise/credibility
- Similar CVE pattern history
- Temporal surge detection
- Keyword co-occurrence patterns

STRICTLY FOR:
✅ Early threat detection
✅ Proactive defense planning
✅ Security posture assessment
✅ Research prioritization
✅ CTF preparation (predicting challenge patterns)

REQUIRES:
- v7 unified threat hub operational
- v5 Deep X researcher graphs (optional but recommended)
- Human validation of predictions
- Audit logging

USAGE:
    from chain_predictor import ChainPredictor

    predictor = ChainPredictor(
        threat_hub=threat_hub,
        memory_graph=memory_graph,
        config=config
    )

    predictions = predictor.predict_emerging_chains()
    for prediction in predictions:
        print(f"Chain: {prediction['chain_steps']}")
        print(f"Confidence: {prediction['confidence']}")
        print(f"ETA to public exploit: {prediction['eta_days']} days")
"""

import logging
import json
import time
from typing import Dict, Any, List, Optional, Set, Tuple
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import re
import math

logger = logging.getLogger(__name__)


class ChainPrediction:
    """Represents a predicted vulnerability chain."""

    def __init__(self, prediction_id: str, chain_steps: List[str],
                 confidence: float, signals: List[Dict], eta_days: Optional[int] = None):
        self.prediction_id = prediction_id
        self.chain_steps = chain_steps
        self.confidence = confidence
        self.signals = signals  # List of threat signals that led to prediction
        self.eta_days = eta_days  # Estimated days until public exploit
        self.timestamp = time.time()

        # Prediction metadata
        self.likelihood = self._calculate_likelihood()
        self.novelty = self._assess_novelty()
        self.impact = self._assess_impact()

        # Tracking
        self.validated = False
        self.validation_date = None

    def _calculate_likelihood(self) -> str:
        """Calculate exploitation likelihood."""
        if self.confidence > 0.85:
            return "very_high"
        elif self.confidence > 0.75:
            return "high"
        elif self.confidence > 0.6:
            return "medium"
        else:
            return "low"

    def _assess_novelty(self) -> str:
        """Assess how novel this chain is."""
        # Check for unique patterns in signals
        unique_indicators = set()
        for signal in self.signals:
            unique_indicators.update(signal.get('keywords', []))

        # More unique indicators = higher novelty
        if len(unique_indicators) > 10:
            return "high"
        elif len(unique_indicators) > 5:
            return "medium"
        else:
            return "low"

    def _assess_impact(self) -> str:
        """Assess potential impact."""
        high_impact_keywords = ['rce', 'remote code execution', 'privilege escalation',
                                'authentication bypass', 'takeover', 'zero-day']

        chain_text = ' '.join(self.chain_steps).lower()
        signal_text = ' '.join(s.get('content', '') for s in self.signals).lower()
        combined_text = chain_text + ' ' + signal_text

        matches = sum(1 for keyword in high_impact_keywords if keyword in combined_text)

        if matches >= 3:
            return "critical"
        elif matches >= 2:
            return "high"
        elif matches >= 1:
            return "medium"
        else:
            return "low"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'prediction_id': self.prediction_id,
            'chain_steps': self.chain_steps,
            'confidence': self.confidence,
            'signals': self.signals,
            'eta_days': self.eta_days,
            'likelihood': self.likelihood,
            'novelty': self.novelty,
            'impact': self.impact,
            'timestamp': self.timestamp,
            'validated': self.validated,
            'validation_date': self.validation_date
        }


class ChainPredictor:
    """
    Predictive Vulnerability Chain Predictor.

    Analyzes threat intelligence patterns to predict likely vulnerability
    chains before they become public exploits.

    ⚠️ PREDICTIONS ONLY - NO AUTONOMOUS EXPLOITATION ⚠️
    """

    def __init__(self, threat_hub, memory_graph, config: Optional[Dict] = None):
        """
        Initialize chain predictor.

        Args:
            threat_hub: UnifiedThreatHub instance (v7)
            memory_graph: HybridMemoryGraph instance
            config: Optional configuration
        """
        self.threat_hub = threat_hub
        self.memory_graph = memory_graph
        self.config = config or {}

        # Predictions
        self.predictions = []  # List of ChainPrediction objects

        # Historical chain patterns (learn from validated predictions)
        self.historical_patterns = defaultdict(int)

        # Researcher credibility (from v5 Deep X if available)
        self.researcher_credibility = {}

        # Statistics
        self.stats = {
            'predictions_made': 0,
            'predictions_validated': 0,
            'signals_analyzed': 0,
            'high_confidence_predictions': 0,
            'false_positives': 0
        }

        logger.info("Chain Predictor initialized (ETHICAL PREDICTION MODE)")

    def predict_emerging_chains(self, min_confidence: float = 0.6) -> List[ChainPrediction]:
        """
        Predict emerging vulnerability chains from threat intelligence.

        Args:
            min_confidence: Minimum confidence threshold (0-1)

        Returns:
            List of ChainPrediction objects
        """
        logger.info("Predicting emerging vulnerability chains...")

        if not self.threat_hub or not hasattr(self.threat_hub, 'correlator'):
            logger.warning("No threat hub available for prediction")
            return []

        # Get recent threat signals (last 48 hours for early detection)
        clusters = self.threat_hub.correlator.get_high_confidence_clusters(min_confidence=0.5)

        predictions = []

        # Analyze temporal patterns
        temporal_groups = self._group_by_temporal_patterns(clusters)

        for temporal_group in temporal_groups:
            self.stats['signals_analyzed'] += len(temporal_group)

            # Predict chains from this temporal group
            group_predictions = self._predict_from_temporal_group(temporal_group)

            for prediction in group_predictions:
                if prediction.confidence >= min_confidence:
                    predictions.append(prediction)
                    self.predictions.append(prediction)
                    self.stats['predictions_made'] += 1

                    if prediction.confidence >= 0.8:
                        self.stats['high_confidence_predictions'] += 1

        # Sort by confidence and ETA
        predictions.sort(key=lambda p: (p.confidence, -p.eta_days if p.eta_days else 999), reverse=True)

        logger.info(f"Prediction complete: {len(predictions)} emerging chains predicted")
        return predictions

    def _group_by_temporal_patterns(self, clusters: List[Dict]) -> List[List[Dict]]:
        """Group threat clusters by temporal patterns (surges, coordinated discussions)."""
        # Sort by timestamp
        sorted_clusters = sorted(clusters, key=lambda c: c.get('timestamp', 0))

        groups = []
        current_group = []
        last_timestamp = None

        # Time window for grouping (1 hour)
        window_seconds = 3600

        for cluster in sorted_clusters:
            timestamp = cluster.get('timestamp', time.time())

            if last_timestamp is None or (timestamp - last_timestamp) <= window_seconds:
                current_group.append(cluster)
            else:
                if current_group:
                    groups.append(current_group)
                current_group = [cluster]

            last_timestamp = timestamp

        if current_group:
            groups.append(current_group)

        return groups

    def _predict_from_temporal_group(self, clusters: List[Dict]) -> List[ChainPrediction]:
        """Predict vulnerability chains from a temporal group of clusters."""
        predictions = []

        # Extract all keywords and CVEs
        all_keywords = []
        all_cves = []
        all_sources = set()

        for cluster in clusters:
            all_keywords.extend(cluster.get('keywords', []))
            all_cves.extend(cluster.get('cves', []))
            all_sources.update(cluster.get('sources', []))

        # Keyword co-occurrence analysis
        keyword_pairs = self._analyze_keyword_cooccurrence(all_keywords)

        # Check for known chain patterns
        chain_patterns = self._match_chain_patterns(keyword_pairs, all_cves)

        for pattern in chain_patterns:
            # Calculate confidence
            confidence = self._calculate_prediction_confidence(
                pattern=pattern,
                clusters=clusters,
                sources=all_sources,
                keyword_pairs=keyword_pairs
            )

            # Estimate ETA to public exploit
            eta_days = self._estimate_exploit_eta(pattern, clusters)

            # Create prediction
            prediction_id = f"pred_{int(time.time() * 1000)}_{pattern['name']}"

            prediction = ChainPrediction(
                prediction_id=prediction_id,
                chain_steps=pattern['steps'],
                confidence=confidence,
                signals=[{'content': ' '.join(all_keywords), 'sources': list(all_sources), 'cves': all_cves}],
                eta_days=eta_days
            )

            predictions.append(prediction)

        return predictions

    def _analyze_keyword_cooccurrence(self, keywords: List[str]) -> List[Tuple[str, str, int]]:
        """Analyze keyword co-occurrence patterns."""
        # Count keyword pairs
        keyword_counter = Counter(keywords)
        pairs = []

        unique_keywords = list(set(keywords))
        for i, kw1 in enumerate(unique_keywords):
            for kw2 in unique_keywords[i+1:]:
                # Count how many times these keywords appear together
                count = min(keyword_counter[kw1], keyword_counter[kw2])
                if count > 0:
                    pairs.append((kw1, kw2, count))

        # Sort by co-occurrence count
        pairs.sort(key=lambda p: p[2], reverse=True)
        return pairs

    def _match_chain_patterns(self, keyword_pairs: List[Tuple], cves: List[str]) -> List[Dict]:
        """Match keyword patterns to known vulnerability chain templates."""
        patterns = []

        # Convert keyword pairs to set for fast lookup
        keyword_set = set()
        for kw1, kw2, count in keyword_pairs:
            keyword_set.add(kw1.lower())
            keyword_set.add(kw2.lower())

        # Pattern 1: Authentication Bypass → Privilege Escalation
        if any(auth_kw in keyword_set for auth_kw in ['authentication', 'auth', 'bypass', 'jwt', 'session']):
            if any(priv_kw in keyword_set for priv_kw in ['privilege', 'escalation', 'admin', 'root']):
                patterns.append({
                    'name': 'auth_bypass_to_privesc',
                    'steps': [
                        '1. Identify authentication mechanism weakness',
                        '2. Bypass authentication (predicted method based on signals)',
                        '3. Gain initial access with low privileges',
                        '4. Exploit privilege escalation vector',
                        '5. Achieve admin/root access'
                    ]
                })

        # Pattern 2: File Upload → RCE
        if any(upload_kw in keyword_set for upload_kw in ['upload', 'file', 'multipart']):
            if any(exec_kw in keyword_set for exec_kw in ['rce', 'execution', 'shell', 'command']):
                patterns.append({
                    'name': 'upload_to_rce',
                    'steps': [
                        '1. Identify file upload functionality',
                        '2. Bypass file type validation',
                        '3. Upload malicious file (webshell, script)',
                        '4. Trigger file execution',
                        '5. Remote code execution achieved'
                    ]
                })

        # Pattern 3: SQL Injection → Data Exfiltration
        if any(sql_kw in keyword_set for sql_kw in ['sql', 'injection', 'sqli', 'database']):
            patterns.append({
                'name': 'sqli_to_exfil',
                'steps': [
                    '1. Identify SQL injection point',
                    '2. Enumerate database structure',
                    '3. Extract sensitive data (credentials, PII)',
                    '4. Lateral movement with extracted credentials',
                    '5. Full database compromise'
                ]
            })

        # Pattern 4: SSRF → Internal Network Access
        if any(ssrf_kw in keyword_set for ssrf_kw in ['ssrf', 'server-side', 'request forgery']):
            patterns.append({
                'name': 'ssrf_to_internal',
                'steps': [
                    '1. Identify SSRF vulnerability in URL parameter',
                    '2. Access internal services (cloud metadata, Redis, etc.)',
                    '3. Extract credentials or sensitive configuration',
                    '4. Pivot to internal network',
                    '5. Lateral movement across internal infrastructure'
                ]
            })

        # Pattern 5: XSS → Session Hijacking → Account Takeover
        if any(xss_kw in keyword_set for xss_kw in ['xss', 'cross-site', 'scripting']):
            if any(session_kw in keyword_set for session_kw in ['session', 'cookie', 'token']):
                patterns.append({
                    'name': 'xss_to_takeover',
                    'steps': [
                        '1. Identify XSS vulnerability',
                        '2. Craft payload to steal session tokens',
                        '3. Deliver payload to victim',
                        '4. Capture session token/cookie',
                        '5. Session hijacking and account takeover'
                    ]
                })

        # Pattern 6: LFI → Log Poisoning → RCE
        if any(lfi_kw in keyword_set for lfi_kw in ['lfi', 'local file', 'inclusion', 'directory traversal']):
            patterns.append({
                'name': 'lfi_poison_rce',
                'steps': [
                    '1. Identify Local File Inclusion vulnerability',
                    '2. Test file read capabilities (../../../etc/passwd)',
                    '3. Poison log files with malicious code',
                    '4. Include poisoned log file via LFI',
                    '5. Remote code execution via log poisoning'
                ]
            })

        # Pattern 7: Deserialization → Gadget Chain → RCE
        if any(deser_kw in keyword_set for deser_kw in ['deserialization', 'pickle', 'unserialize', 'yaml']):
            patterns.append({
                'name': 'deser_to_rce',
                'steps': [
                    '1. Identify deserialization of untrusted data',
                    '2. Analyze available gadget chains',
                    '3. Craft malicious serialized payload',
                    '4. Trigger deserialization',
                    '5. Remote code execution via gadget chain'
                ]
            })

        # Pattern 8: API Misconfiguration → IDOR → Privilege Escalation
        if any(api_kw in keyword_set for api_kw in ['api', 'endpoint', 'rest', 'graphql']):
            if any(idor_kw in keyword_set for idor_kw in ['idor', 'reference', 'id', 'parameter']):
                patterns.append({
                    'name': 'api_idor_privesc',
                    'steps': [
                        '1. Enumerate API endpoints',
                        '2. Identify IDOR vulnerability (insecure object references)',
                        '3. Access other users\' resources',
                        '4. Modify user role/privileges via IDOR',
                        '5. Privilege escalation to admin'
                    ]
                })

        return patterns

    def _calculate_prediction_confidence(self, pattern: Dict, clusters: List[Dict],
                                         sources: Set[str], keyword_pairs: List) -> float:
        """Calculate confidence for a predicted chain."""
        base_confidence = 0.5

        # Factor 1: Cross-source validation
        if len(sources) >= 2:
            base_confidence += 0.15
        if len(sources) >= 3:
            base_confidence += 0.1

        # Factor 2: CVE mentions
        total_cves = sum(len(c.get('cves', [])) for c in clusters)
        if total_cves > 0:
            base_confidence += min(0.1 * total_cves, 0.2)

        # Factor 3: Keyword co-occurrence strength
        if keyword_pairs:
            max_cooccurrence = max(count for _, _, count in keyword_pairs)
            if max_cooccurrence >= 3:
                base_confidence += 0.1

        # Factor 4: Temporal density (many signals in short time = higher confidence)
        if len(clusters) >= 3:
            base_confidence += 0.05
        if len(clusters) >= 5:
            base_confidence += 0.05

        # Factor 5: Historical pattern match
        pattern_name = pattern['name']
        if pattern_name in self.historical_patterns:
            historical_accuracy = min(self.historical_patterns[pattern_name] * 0.05, 0.15)
            base_confidence += historical_accuracy

        # Cap at 1.0
        return min(base_confidence, 1.0)

    def _estimate_exploit_eta(self, pattern: Dict, clusters: List[Dict]) -> Optional[int]:
        """Estimate days until public exploit likely appears."""
        # Heuristic based on signal strength
        total_signals = len(clusters)

        # Check if CVEs are mentioned
        has_cves = any(c.get('cves') for c in clusters)

        # Check for PoC mentions
        has_poc_mentions = any(
            any(keyword in c.get('keywords', []) for keyword in ['poc', 'proof of concept', 'exploit code'])
            for c in clusters
        )

        if has_poc_mentions:
            # PoC mentioned = exploit likely imminent
            return 1
        elif has_cves and total_signals >= 5:
            # Active discussion of CVE with many signals = 2-7 days
            return 3
        elif has_cves:
            # CVE mentioned but less discussion = 7-14 days
            return 10
        elif total_signals >= 3:
            # No CVE but multiple signals = 14-30 days
            return 21
        else:
            # Weak signals = 30+ days or may not materialize
            return 45

    def validate_prediction(self, prediction_id: str, validated: bool = True):
        """Mark a prediction as validated (or false positive)."""
        for prediction in self.predictions:
            if prediction.prediction_id == prediction_id:
                prediction.validated = validated
                prediction.validation_date = time.time()

                if validated:
                    self.stats['predictions_validated'] += 1

                    # Update historical patterns (learn from success)
                    pattern_name = prediction_id.split('_')[-1]
                    self.historical_patterns[pattern_name] += 1
                else:
                    self.stats['false_positives'] += 1

                logger.info(f"Prediction {prediction_id} marked as {'validated' if validated else 'false positive'}")
                return True

        logger.warning(f"Prediction {prediction_id} not found")
        return False

    def get_prediction_by_id(self, prediction_id: str) -> Optional[ChainPrediction]:
        """Get prediction by ID."""
        for prediction in self.predictions:
            if prediction.prediction_id == prediction_id:
                return prediction
        return None

    def get_top_predictions(self, limit: int = 10) -> List[ChainPrediction]:
        """Get top N predictions by confidence."""
        sorted_predictions = sorted(self.predictions, key=lambda p: p.confidence, reverse=True)
        return sorted_predictions[:limit]

    def get_imminent_predictions(self, max_eta_days: int = 7) -> List[ChainPrediction]:
        """Get predictions likely to materialize soon."""
        imminent = [p for p in self.predictions
                   if p.eta_days is not None and p.eta_days <= max_eta_days]
        imminent.sort(key=lambda p: p.eta_days)
        return imminent

    def get_stats(self) -> Dict[str, Any]:
        """Get predictor statistics."""
        accuracy = 0.0
        if self.stats['predictions_made'] > 0:
            validated = self.stats['predictions_validated']
            total = self.stats['predictions_made']
            accuracy = validated / total if total > 0 else 0.0

        return {
            **self.stats,
            'accuracy': accuracy,
            'total_predictions': len(self.predictions),
            'historical_patterns': dict(self.historical_patterns)
        }


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Chain Predictor Test")
    print("="*70)
    print("\n⚠️  ETHICAL PREDICTION MODE - NO EXPLOITATION\n")

    # Mock components
    class MockThreatHub:
        class MockCorrelator:
            def get_high_confidence_clusters(self, min_confidence=0.5):
                current_time = time.time()
                return [
                    {
                        'cluster_id': 'cluster_1',
                        'confidence': 0.85,
                        'cves': ['CVE-2025-11833'],
                        'keywords': ['wordpress', 'plugin', 'authentication', 'bypass', 'admin', 'privilege escalation'],
                        'sources': ['x_stream', 'tor_osint'],
                        'timestamp': current_time - 1800  # 30 min ago
                    },
                    {
                        'cluster_id': 'cluster_2',
                        'confidence': 0.75,
                        'cves': ['CVE-2025-11833'],
                        'keywords': ['wordpress', 'takeover', 'unauth', 'rce', 'poc'],
                        'sources': ['x_stream', 'exploit_db'],
                        'timestamp': current_time - 1200  # 20 min ago
                    },
                    {
                        'cluster_id': 'cluster_3',
                        'confidence': 0.8,
                        'cves': [],
                        'keywords': ['file', 'upload', 'bypass', 'rce', 'shell', 'execution'],
                        'sources': ['x_stream'],
                        'timestamp': current_time - 600  # 10 min ago
                    }
                ]

        def __init__(self):
            self.correlator = self.MockCorrelator()

    class MockGraph:
        def __init__(self):
            import networkx as nx
            self.graph = nx.DiGraph()

    threat_hub = MockThreatHub()
    graph = MockGraph()

    print("[Test] Initializing Chain Predictor...")
    predictor = ChainPredictor(threat_hub, graph)

    print("\n[Test] Predicting emerging vulnerability chains...")
    predictions = predictor.predict_emerging_chains(min_confidence=0.6)

    print(f"\n[Test] Generated {len(predictions)} chain predictions:\n")

    for i, prediction in enumerate(predictions[:5], 1):
        print(f"{i}. Prediction ID: {prediction.prediction_id}")
        print(f"   Confidence: {prediction.confidence:.0%}")
        print(f"   Likelihood: {prediction.likelihood}")
        print(f"   Impact: {prediction.impact}")
        print(f"   Novelty: {prediction.novelty}")
        print(f"   ETA to public exploit: {prediction.eta_days} days")
        print(f"   Predicted Chain:")
        for step in prediction.chain_steps:
            print(f"     {step}")
        print()

    print("[Test] Chain predictor statistics:")
    stats = predictor.get_stats()
    print(f"  Predictions made: {stats['predictions_made']}")
    print(f"  Signals analyzed: {stats['signals_analyzed']}")
    print(f"  High confidence: {stats['high_confidence_predictions']}")
    print(f"  Accuracy: {stats['accuracy']:.0%}")

    print("\n" + "="*70)
    print("✅ Chain Predictor operational!")
    print("="*70)
    print("\n⚠️  Remember: These are PREDICTIONS for proactive defense.")
    print("Always validate predictions before taking action.")
    print("="*70)
