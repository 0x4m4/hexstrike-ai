#!/usr/bin/env python3
"""
MindSync Oracle v9 - Confidence Scoring System

RELIABILITY ASSESSMENT FOR PREDICTIONS AND CHAINS

This module assesses confidence in predictions, vulnerability chains, and
tool outputs to determine if human approval is needed.

Key Features:
- Multi-factor confidence scoring (0-1)
- Graph consistency validation
- Output quality assessment
- Hedging language detection
- Integration with v8 human-in-loop controller

Confidence Factors:
1. Output quality (length, detail, structure)
2. Hedging language (uncertainty indicators)
3. Graph consistency (alignment with stored facts)
4. Source validation (cross-source confirmation)
5. Historical accuracy (learn from past predictions)

Low Confidence Actions:
- <0.7: Route to human approval (v8 controller)
- <0.5: Swarm consensus vote (v6)
- <0.3: Reject with warning

Integration Points:
- v8: Post-execution confidence checks
- v6: Swarm fallback for low-confidence decisions
- v3: Graph validation against memory
- v7: Cross-source threat validation

Usage:
    from confidence_scorer import ConfidenceScorer

    scorer = ConfidenceScorer(memory_graph, config)

    # Score a prediction
    confidence = scorer.score_prediction(output, context)

    if confidence < 0.7:
        # Route to human approval
        approved = human_in_loop_controller.request_approval(action)
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
import time

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """
    Confidence Scoring System for predictions and chains.

    Assesses confidence to determine if human review is needed.
    """

    def __init__(self, memory_graph=None, config: Optional[Dict] = None):
        """
        Initialize confidence scorer.

        Args:
            memory_graph: HybridMemoryGraph instance for validation
            config: Configuration dict
        """
        self.memory_graph = memory_graph
        self.config = config or {}

        # Confidence thresholds from config
        self.thresholds = {
            'high': self.config.get('confidence_thresholds', {}).get('high', 0.8),
            'medium': self.config.get('confidence_thresholds', {}).get('medium', 0.7),
            'low': self.config.get('confidence_thresholds', {}).get('low', 0.5),
            'reject': self.config.get('confidence_thresholds', {}).get('reject', 0.3)
        }

        # Hedging language patterns
        self.hedging_patterns = [
            r'\b(might|may|could|possibly|perhaps|maybe)\b',
            r'\b(uncertain|unclear|unknown|unsure)\b',
            r'\b(likely|unlikely|probably|probably not)\b',
            r'\b(appears to|seems to|looks like)\b',
            r'\b(not sure|not certain|not clear)\b',
            r'\b(I think|I believe|I guess)\b'
        ]

        # Historical accuracy tracking
        self.history = {
            'total_predictions': 0,
            'validated_correct': 0,
            'validated_incorrect': 0,
            'pending_validation': 0
        }

        # Statistics
        self.stats = {
            'total_scored': 0,
            'high_confidence': 0,
            'medium_confidence': 0,
            'low_confidence': 0,
            'rejected': 0,
            'human_routed': 0,
            'swarm_routed': 0
        }

        logger.info("Confidence Scorer initialized")

    def score_prediction(self, output: str, context: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        Score confidence in a prediction or chain.

        Args:
            output: Output text to score
            context: Context dict with request details, graph data, etc.

        Returns:
            Tuple of (confidence_score, details_dict)
        """
        self.stats['total_scored'] += 1

        # Multi-factor scoring
        scores = {}

        # Factor 1: Output quality (0-1)
        scores['quality'] = self._score_output_quality(output)

        # Factor 2: Hedging language (0-1, inverse of hedging)
        scores['certainty'] = self._score_certainty(output)

        # Factor 3: Graph consistency (0-1)
        scores['graph_consistency'] = self._score_graph_consistency(output, context)

        # Factor 4: Source validation (0-1)
        scores['source_validation'] = self._score_source_validation(context)

        # Factor 5: Historical accuracy (0-1)
        scores['historical_accuracy'] = self._score_historical_accuracy(context)

        # Weighted average (customize weights based on use case)
        weights = {
            'quality': 0.20,
            'certainty': 0.25,
            'graph_consistency': 0.25,
            'source_validation': 0.20,
            'historical_accuracy': 0.10
        }

        # Calculate final confidence
        confidence = sum(scores[k] * weights[k] for k in scores)
        confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]

        # Classify confidence level
        if confidence >= self.thresholds['high']:
            level = 'high'
            self.stats['high_confidence'] += 1
        elif confidence >= self.thresholds['medium']:
            level = 'medium'
            self.stats['medium_confidence'] += 1
        elif confidence >= self.thresholds['low']:
            level = 'low'
            self.stats['low_confidence'] += 1
        else:
            level = 'reject'
            self.stats['rejected'] += 1

        details = {
            'confidence': confidence,
            'level': level,
            'scores': scores,
            'weights': weights,
            'threshold_met': confidence >= self.thresholds['medium'],
            'requires_human': confidence < self.thresholds['medium'],
            'requires_swarm': confidence < self.thresholds['low'],
            'should_reject': confidence < self.thresholds['reject']
        }

        logger.info(f"Confidence scored: {confidence:.2f} ({level})")
        return confidence, details

    def _score_output_quality(self, output: str) -> float:
        """
        Score output quality based on length, structure, detail.

        Args:
            output: Output text

        Returns:
            Quality score (0-1)
        """
        if not output or len(output) < 10:
            return 0.0

        score = 0.5  # Base score

        # Length: Prefer substantial outputs (100-2000 chars optimal)
        length = len(output)
        if 100 <= length <= 2000:
            score += 0.2
        elif length > 2000:
            score += 0.1
        elif length < 50:
            score -= 0.2

        # Structure: Check for numbered steps, bullet points
        if re.search(r'^\d+\.', output, re.MULTILINE) or '- ' in output:
            score += 0.15

        # Detail: Check for specific terms (CVE, technical terms)
        if re.search(r'CVE-\d{4}-\d+', output):
            score += 0.1

        # Code/commands present
        if '```' in output or re.search(r'`[^`]+`', output):
            score += 0.05

        return max(0.0, min(1.0, score))

    def _score_certainty(self, output: str) -> float:
        """
        Score certainty (inverse of hedging language).

        Args:
            output: Output text

        Returns:
            Certainty score (0-1)
        """
        if not output:
            return 0.5

        # Count hedging patterns
        hedging_count = 0
        output_lower = output.lower()

        for pattern in self.hedging_patterns:
            matches = re.findall(pattern, output_lower)
            hedging_count += len(matches)

        # Normalize by output length (words)
        word_count = len(output.split())
        if word_count == 0:
            return 0.5

        hedging_ratio = hedging_count / word_count

        # Convert to certainty score (less hedging = more certain)
        # Typical hedging ratio: 0-0.05 (5% hedging is high)
        if hedging_ratio == 0:
            certainty = 1.0
        elif hedging_ratio < 0.01:
            certainty = 0.9
        elif hedging_ratio < 0.03:
            certainty = 0.7
        elif hedging_ratio < 0.05:
            certainty = 0.5
        else:
            certainty = 0.3

        return certainty

    def _score_graph_consistency(self, output: str, context: Dict[str, Any]) -> float:
        """
        Score consistency with memory graph facts.

        Args:
            output: Output text
            context: Context with graph data

        Returns:
            Consistency score (0-1)
        """
        if not self.memory_graph:
            return 0.7  # Neutral if no graph available

        # Extract key entities from output (CVEs, vulnerabilities, tools)
        cves = re.findall(r'CVE-\d{4}-\d+', output)

        if not cves and not context.get('graph_context'):
            return 0.7  # Neutral if no entities to validate

        score = 0.5  # Base score

        # Check if mentioned CVEs exist in graph
        if cves and hasattr(self.memory_graph, 'graph'):
            known_cves = [node for node in self.memory_graph.graph.nodes
                         if node.startswith('CVE-')]
            matching_cves = [cve for cve in cves if cve in known_cves]

            if cves:
                match_ratio = len(matching_cves) / len(cves)
                score += match_ratio * 0.3

        # Check if context aligns with graph
        if context.get('graph_context'):
            # Simplified consistency check
            # In production, would do semantic matching
            score += 0.2

        return max(0.0, min(1.0, score))

    def _score_source_validation(self, context: Dict[str, Any]) -> float:
        """
        Score based on source validation (cross-source confirmation).

        Args:
            context: Context with source information

        Returns:
            Source validation score (0-1)
        """
        sources = context.get('sources', [])

        if not sources:
            return 0.5  # Neutral if no source info

        # More sources = higher confidence
        num_sources = len(sources)

        if num_sources >= 3:
            score = 1.0
        elif num_sources == 2:
            score = 0.8
        elif num_sources == 1:
            score = 0.6
        else:
            score = 0.5

        # Boost for cross-source validation flag
        if context.get('cross_source_validated'):
            score = min(1.0, score + 0.2)

        return score

    def _score_historical_accuracy(self, context: Dict[str, Any]) -> float:
        """
        Score based on historical prediction accuracy.

        Args:
            context: Context with prediction type

        Returns:
            Historical accuracy score (0-1)
        """
        if self.history['total_predictions'] == 0:
            return 0.7  # Neutral for new system

        # Calculate historical accuracy
        validated = self.history['validated_correct'] + self.history['validated_incorrect']
        if validated == 0:
            return 0.7  # No validation data yet

        accuracy = self.history['validated_correct'] / validated

        # Confidence increases with more data
        data_confidence = min(1.0, validated / 50)  # 50+ validated predictions = full confidence

        return accuracy * 0.7 + data_confidence * 0.3

    def validate_prediction(self, prediction_id: str, correct: bool):
        """
        Validate a past prediction (for learning).

        Args:
            prediction_id: Prediction identifier
            correct: Whether prediction was correct
        """
        self.history['total_predictions'] += 1

        if correct:
            self.history['validated_correct'] += 1
        else:
            self.history['validated_incorrect'] += 1

        logger.info(f"Prediction {prediction_id} validated: {'correct' if correct else 'incorrect'}")

    def route_by_confidence(self, confidence: float, output: str,
                           context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route action based on confidence level.

        Args:
            confidence: Confidence score (0-1)
            output: Output to route
            context: Context information

        Returns:
            Routing decision dict
        """
        routing = {
            'confidence': confidence,
            'action': None,
            'reason': None
        }

        if confidence >= self.thresholds['medium']:
            # High/medium confidence: Approve
            routing['action'] = 'approve'
            routing['reason'] = f'High confidence ({confidence:.2f})'

        elif confidence >= self.thresholds['low']:
            # Low confidence: Route to human approval
            routing['action'] = 'human_approval'
            routing['reason'] = f'Low confidence ({confidence:.2f}) - human review required'
            self.stats['human_routed'] += 1

        elif confidence >= self.thresholds['reject']:
            # Very low: Route to swarm consensus
            routing['action'] = 'swarm_consensus'
            routing['reason'] = f'Very low confidence ({confidence:.2f}) - swarm vote required'
            self.stats['swarm_routed'] += 1

        else:
            # Extremely low: Reject
            routing['action'] = 'reject'
            routing['reason'] = f'Confidence too low ({confidence:.2f}) - rejected for safety'

        logger.info(f"Routing decision: {routing['action']} ({routing['reason']})")
        return routing

    def get_stats(self) -> Dict[str, Any]:
        """Get scorer statistics."""
        accuracy = 0.0
        if self.history['validated_correct'] + self.history['validated_incorrect'] > 0:
            accuracy = self.history['validated_correct'] / (
                self.history['validated_correct'] + self.history['validated_incorrect']
            )

        return {
            **self.stats,
            'history': self.history,
            'historical_accuracy': accuracy,
            'thresholds': self.thresholds
        }


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Confidence Scorer Test")
    print("="*70)

    print("\n[Test] Initializing Confidence Scorer...")
    scorer = ConfidenceScorer()

    # Test 1: High confidence output
    print("\n[Test 1] Scoring high-confidence output...")
    output1 = """
1. Identify SQL injection vulnerability in login form
2. Enumerate database structure using UNION-based injection
3. Extract admin credentials from users table
4. Escalate privileges via admin panel

CVE-2025-1234 confirmed exploitation path. Cross-validated via 3 sources.
"""
    context1 = {
        'sources': ['x_stream', 'tor_osint', 'exploit_db'],
        'cross_source_validated': True,
        'graph_context': {'cve': 'CVE-2025-1234'}
    }
    confidence1, details1 = scorer.score_prediction(output1, context1)
    print(f"  Confidence: {confidence1:.2%}")
    print(f"  Level: {details1['level']}")
    print(f"  Requires human: {details1['requires_human']}")

    # Test 2: Low confidence output (hedging)
    print("\n[Test 2] Scoring low-confidence output...")
    output2 = "Maybe there's a vulnerability. Not sure. Possibly SQL injection."
    context2 = {'sources': []}
    confidence2, details2 = scorer.score_prediction(output2, context2)
    print(f"  Confidence: {confidence2:.2%}")
    print(f"  Level: {details2['level']}")
    print(f"  Requires human: {details2['requires_human']}")

    # Test 3: Routing decisions
    print("\n[Test 3] Testing routing decisions...")
    for conf in [0.85, 0.65, 0.45, 0.25]:
        routing = scorer.route_by_confidence(conf, "", {})
        print(f"  Confidence {conf:.2f} → {routing['action']}")

    # Test 4: Validation learning
    print("\n[Test 4] Testing validation learning...")
    scorer.validate_prediction("pred_1", correct=True)
    scorer.validate_prediction("pred_2", correct=True)
    scorer.validate_prediction("pred_3", correct=False)
    print(f"  Historical accuracy: {scorer.get_stats()['historical_accuracy']:.0%}")

    # Statistics
    print("\n[Test] Scorer statistics:")
    stats = scorer.get_stats()
    print(f"  Total scored: {stats['total_scored']}")
    print(f"  High confidence: {stats['high_confidence']}")
    print(f"  Medium confidence: {stats['medium_confidence']}")
    print(f"  Low confidence: {stats['low_confidence']}")
    print(f"  Rejected: {stats['rejected']}")
    print(f"  Human routed: {stats['human_routed']}")
    print(f"  Swarm routed: {stats['swarm_routed']}")

    print("\n" + "="*70)
    print("✅ Confidence Scorer operational!")
    print("="*70)
    print("\nIntegrate with v8 human-in-loop controller for ethical safeguards.")
    print("="*70)
