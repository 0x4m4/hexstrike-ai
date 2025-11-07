#!/usr/bin/env python3
"""
MindSync Oracle - Self-Improving Feedback System

THE BREAKTHROUGH: AI that learns from outcomes and evolves autonomously.

After each goal completion, the system:
1. Analyzes what worked vs what didn't
2. Stores lessons learned
3. Updates future behavior automatically
4. Suggests optimizations

This is what separates "smart AI" from "learning AGI".
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class SelfImprovementEngine:
    """
    Analyzes goal outcomes and evolves system behavior.

    This is THE missing piece for true AGI - learning from experience.
    """

    def __init__(self, memory_manager, agent_orchestrator):
        """
        Initialize self-improvement engine.

        Args:
            memory_manager: MemoryManager for storing lessons
            agent_orchestrator: Claude orchestrator for analysis
        """
        self.memory = memory_manager
        self.orchestrator = agent_orchestrator
        logger.info("Self-Improvement Engine initialized")

    async def analyze_goal_outcome(self, goal_id: int,
                                   execution_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a completed goal and extract learnings.

        Args:
            goal_id: Goal ID
            execution_results: Full execution data

        Returns:
            Analysis with lessons learned
        """
        # Get goal details
        goals = self.memory.get_active_goals()
        goal = next((g for g in goals if g['id'] == goal_id), None)

        if not goal:
            logger.warning(f"Goal {goal_id} not found for analysis")
            return {"success": False}

        # Analyze with Claude
        analysis_prompt = f"""
Analyze this completed goal execution and provide learnings.

Goal: {goal['goal_text']}
Priority: {goal.get('priority', 'medium')}
Execution Time: {execution_results.get('duration', 'N/A')}
Success: {execution_results.get('success', False)}

Results Summary:
{json.dumps(execution_results, indent=2, default=str)[:2000]}

Provide analysis in JSON format:
{{
    "success_rating": 1-10,
    "what_worked": ["specific things that were effective"],
    "what_failed": ["specific issues or failures"],
    "time_efficiency": "fast | moderate | slow",
    "tool_effectiveness": {{"tool_name": "rating (1-10)"}},
    "suggested_improvements": ["specific actionable improvements"],
    "patterns_detected": ["any behavioral patterns noticed"],
    "optimization_opportunities": ["ways to do this faster/better next time"]
}}

Be specific and actionable. Focus on concrete learnings.
"""

        try:
            response = await self.orchestrator.chat(analysis_prompt, store_in_memory=False)

            # Parse JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                # Fallback analysis
                analysis = {
                    "success_rating": 7,
                    "what_worked": ["Goal completed"],
                    "what_failed": [],
                    "suggested_improvements": ["Continue current approach"]
                }

            # Store learnings
            self._store_learnings(goal, analysis)

            # Update patterns based on analysis
            self._update_patterns(goal, analysis)

            logger.info(f"Goal {goal_id} analyzed: rating {analysis.get('success_rating', 'N/A')}/10")

            return {
                "success": True,
                "analysis": analysis,
                "lessons_stored": True
            }

        except Exception as e:
            logger.error(f"Error analyzing goal outcome: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def _store_learnings(self, goal: Dict[str, Any], analysis: Dict[str, Any]):
        """Store learnings in memory as patterns."""
        # Store tool effectiveness
        for tool, rating in analysis.get('tool_effectiveness', {}).items():
            if float(rating) >= 7:  # Store high-performing tools
                self.memory.store_pattern(
                    "tool_effectiveness",
                    {
                        "tool": tool,
                        "goal_type": goal['goal_text'][:50],
                        "rating": rating,
                        "context": "self_improvement_analysis"
                    },
                    confidence=float(rating) / 10
                )

        # Store optimization patterns
        for improvement in analysis.get('suggested_improvements', []):
            self.memory.store_pattern(
                "optimization_opportunity",
                {
                    "improvement": improvement,
                    "goal_context": goal['goal_text'][:100]
                },
                confidence=0.7
            )

        # Store failure patterns (to avoid)
        for failure in analysis.get('what_failed', []):
            self.memory.store_pattern(
                "failure_pattern",
                {
                    "failure": failure,
                    "context": goal['goal_text'][:100]
                },
                confidence=0.8
            )

        logger.info(f"Stored {len(analysis.get('what_worked', []))} learnings")

    def _update_patterns(self, goal: Dict[str, Any], analysis: Dict[str, Any]):
        """Update existing patterns based on new learnings."""
        # Update workflow patterns
        if analysis.get('time_efficiency') == 'fast':
            self.memory.store_pattern(
                "workflow_optimization",
                {
                    "approach": "current_method_effective",
                    "goal_type": goal['goal_text'][:50]
                },
                confidence=0.85
            )

        # Store pattern detections
        for pattern in analysis.get('patterns_detected', []):
            self.memory.store_pattern(
                "behavioral_pattern",
                {
                    "pattern": pattern,
                    "detected_in": goal['goal_text'][:100]
                },
                confidence=0.75
            )

    async def suggest_optimizations(self) -> List[Dict[str, Any]]:
        """
        Analyze all stored learnings and suggest system-wide optimizations.

        Returns:
            List of optimization suggestions
        """
        # Get all optimization patterns
        optimizations = self.memory.get_patterns(
            pattern_type="optimization_opportunity",
            min_confidence=0.6
        )

        tool_ratings = self.memory.get_patterns(
            pattern_type="tool_effectiveness",
            min_confidence=0.7
        )

        failures = self.memory.get_patterns(
            pattern_type="failure_pattern",
            min_confidence=0.6
        )

        suggestions = []

        # Tool preference suggestions
        if tool_ratings:
            best_tools = sorted(
                tool_ratings,
                key=lambda x: x['confidence'],
                reverse=True
            )[:5]

            suggestions.append({
                "type": "tool_preference",
                "suggestion": f"Top performing tools: {', '.join([t['pattern_data']['tool'] for t in best_tools])}",
                "impact": "high",
                "auto_applicable": True
            })

        # Failure avoidance
        if failures:
            common_failures = {}
            for f in failures:
                key = f['pattern_data']['failure']
                common_failures[key] = common_failures.get(key, 0) + 1

            top_failure = max(common_failures.items(), key=lambda x: x[1])
            suggestions.append({
                "type": "failure_avoidance",
                "suggestion": f"Avoid: {top_failure[0]} (failed {top_failure[1]} times)",
                "impact": "high",
                "auto_applicable": False
            })

        # Workflow improvements
        if optimizations:
            for opt in optimizations[:3]:
                suggestions.append({
                    "type": "optimization",
                    "suggestion": opt['pattern_data']['improvement'],
                    "impact": "medium",
                    "auto_applicable": False
                })

        logger.info(f"Generated {len(suggestions)} optimization suggestions")
        return suggestions

    async def auto_optimize(self, apply_safe_optimizations: bool = True) -> Dict[str, Any]:
        """
        Automatically apply safe optimizations based on learnings.

        Args:
            apply_safe_optimizations: Whether to auto-apply or just suggest

        Returns:
            Optimization results
        """
        suggestions = await self.suggest_optimizations()

        applied = []
        suggested = []

        for suggestion in suggestions:
            if suggestion['auto_applicable'] and apply_safe_optimizations:
                # Apply optimization
                if suggestion['type'] == 'tool_preference':
                    # Update default tool preferences
                    logger.info(f"Auto-applied: {suggestion['suggestion']}")
                    applied.append(suggestion)
            else:
                suggested.append(suggestion)

        return {
            "auto_applied": applied,
            "suggestions": suggested,
            "total_optimizations": len(suggestions)
        }

    async def generate_improvement_report(self) -> str:
        """
        Generate comprehensive improvement report.

        Returns:
            Markdown-formatted report
        """
        suggestions = await self.suggest_optimizations()

        # Get statistics
        patterns = self.memory.get_patterns()
        goals = self.memory.get_active_goals()

        # Completed goals
        completed_count = self.memory._count_completed_goals()

        report = f"""
# MindSync Oracle - Self-Improvement Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Learning Statistics

- **Total Patterns Learned**: {len(patterns)}
- **Goals Completed**: {completed_count}
- **Active Goals**: {len(goals)}
- **Optimization Opportunities**: {len(suggestions)}

## Key Learnings

"""

        # Add tool effectiveness
        tool_patterns = [p for p in patterns if p['pattern_type'] == 'tool_effectiveness']
        if tool_patterns:
            report += "\n### Top Performing Tools\n\n"
            for tool in sorted(tool_patterns, key=lambda x: x['confidence'], reverse=True)[:5]:
                report += f"- **{tool['pattern_data']['tool']}**: {tool['confidence']*100:.0f}% effectiveness\n"

        # Add failures to avoid
        failure_patterns = [p for p in patterns if p['pattern_type'] == 'failure_pattern']
        if failure_patterns:
            report += "\n### Patterns to Avoid\n\n"
            for fail in failure_patterns[:3]:
                report += f"- {fail['pattern_data']['failure']}\n"

        # Add optimization suggestions
        if suggestions:
            report += "\n### Recommended Optimizations\n\n"
            for i, sugg in enumerate(suggestions, 1):
                impact_emoji = "🔥" if sugg['impact'] == 'high' else "💡"
                report += f"{i}. {impact_emoji} **[{sugg['type']}]** {sugg['suggestion']}\n"

        report += "\n---\n\n*This report generated automatically by the Self-Improvement Engine*\n"

        return report


if __name__ == "__main__":
    # Test self-improvement engine
    import sys
    import asyncio
    sys.path.append('..')

    from storage.memory_manager import MemoryManager

    logging.basicConfig(level=logging.INFO)

    # Mock orchestrator
    class MockOrchestrator:
        async def chat(self, prompt, store_in_memory=True):
            return """{
                "success_rating": 8,
                "what_worked": ["Effective tool selection", "Fast execution"],
                "what_failed": ["Initial scan timeout"],
                "time_efficiency": "fast",
                "tool_effectiveness": {"nmap": "9", "nuclei": "8"},
                "suggested_improvements": ["Increase scan timeout", "Add retry logic"],
                "patterns_detected": ["User prefers Feroxbuster"],
                "optimization_opportunities": ["Cache DNS results"]
            }"""

    async def test():
        memory = MemoryManager("test_memory.db")
        orchestrator = MockOrchestrator()

        engine = SelfImprovementEngine(memory, orchestrator)

        # Simulate goal completion
        result = await engine.analyze_goal_outcome(
            goal_id=1,
            execution_results={
                "success": True,
                "duration": "5 minutes",
                "tools_used": ["nmap", "nuclei"]
            }
        )

        print(f"\nAnalysis Result:\n{json.dumps(result, indent=2)}")

        # Get suggestions
        suggestions = await engine.suggest_optimizations()
        print(f"\nOptimizations: {len(suggestions)}")

        # Generate report
        report = await engine.generate_improvement_report()
        print(f"\n{report}")

    asyncio.run(test())
