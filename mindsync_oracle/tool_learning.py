#!/usr/bin/env python3
"""
MindSync Oracle - Tool Learning & Optimization

Tracks which security tools work best for which tasks and automatically
optimizes tool selection over time.

After 10+ pentests, the system knows:
- nmap is faster than masscan for small scans
- Feroxbuster finds more dirs than Gobuster for your targets
- nuclei templates X,Y,Z have highest hit rate

This turns "tool access" into "tool mastery".
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
import statistics

logger = logging.getLogger(__name__)


class ToolPerformanceTracker:
    """
    Tracks and analyzes security tool performance.

    Learns:
    - Which tools succeed vs fail
    - Execution times
    - Result quality
    - Best tool for each scenario
    """

    def __init__(self, memory_manager):
        """
        Initialize tool performance tracker.

        Args:
            memory_manager: MemoryManager for storing tool metrics
        """
        self.memory = memory_manager
        logger.info("Tool Performance Tracker initialized")

    def record_tool_execution(self, tool_name: str, execution_data: Dict[str, Any]):
        """
        Record tool execution for learning.

        Args:
            tool_name: Name of tool executed
            execution_data: Execution results and metrics
        """
        # Extract key metrics
        success = execution_data.get('success', False)
        duration = execution_data.get('duration', 0)
        results_count = execution_data.get('results_count', 0)
        error = execution_data.get('error')

        # Calculate quality score
        quality_score = self._calculate_quality_score(execution_data)

        # Store as pattern
        self.memory.store_pattern(
            "tool_execution",
            {
                "tool": tool_name,
                "success": success,
                "duration": duration,
                "results_count": results_count,
                "quality_score": quality_score,
                "error": error,
                "target_type": execution_data.get('target_type', 'unknown'),
                "timestamp": datetime.now().isoformat()
            },
            confidence=quality_score
        )

        # Update tool usage stats
        self.memory.store_pattern(
            "tool_usage_stat",
            {
                "tool": tool_name,
                "usage_count": 1,  # Will be aggregated
                "last_used": datetime.now().isoformat()
            },
            confidence=0.5
        )

        logger.info(f"Recorded {tool_name} execution (quality: {quality_score:.2f})")

    def _calculate_quality_score(self, execution_data: Dict[str, Any]) -> float:
        """
        Calculate quality score for tool execution.

        Args:
            execution_data: Execution data

        Returns:
            Quality score (0.0 to 1.0)
        """
        score = 0.0

        # Success is worth 40%
        if execution_data.get('success'):
            score += 0.4

        # Results found are worth 30%
        results_count = execution_data.get('results_count', 0)
        if results_count > 0:
            # Logarithmic scale for results
            score += min(0.3, 0.3 * (1 - (1 / (1 + results_count / 10))))

        # Speed is worth 20%
        duration = execution_data.get('duration', 999999)
        if duration < 60:  # Under 1 minute
            score += 0.2
        elif duration < 300:  # Under 5 minutes
            score += 0.1

        # No errors worth 10%
        if not execution_data.get('error'):
            score += 0.1

        return min(1.0, score)

    def get_tool_performance(self, tool_name: str) -> Dict[str, Any]:
        """
        Get performance statistics for a tool.

        Args:
            tool_name: Tool name

        Returns:
            Performance statistics
        """
        # Get all executions for this tool
        executions = self.memory.get_patterns(pattern_type="tool_execution")
        tool_executions = [
            e for e in executions
            if e['pattern_data']['tool'] == tool_name
        ]

        if not tool_executions:
            return {
                "tool": tool_name,
                "executions": 0,
                "avg_quality": 0.0,
                "success_rate": 0.0
            }

        # Calculate statistics
        qualities = [e['confidence'] for e in tool_executions]
        successes = [e['pattern_data']['success'] for e in tool_executions]
        durations = [e['pattern_data']['duration'] for e in tool_executions if e['pattern_data']['duration'] > 0]

        return {
            "tool": tool_name,
            "executions": len(tool_executions),
            "avg_quality": statistics.mean(qualities),
            "success_rate": sum(successes) / len(successes) if successes else 0.0,
            "avg_duration": statistics.mean(durations) if durations else 0.0,
            "median_duration": statistics.median(durations) if durations else 0.0,
            "last_used": tool_executions[-1]['pattern_data']['timestamp']
        }

    def compare_tools(self, tool1: str, tool2: str, scenario: str = "general") -> Dict[str, Any]:
        """
        Compare performance of two tools.

        Args:
            tool1: First tool
            tool2: Second tool
            scenario: Scenario context (e.g., "subdomain_enum", "port_scan")

        Returns:
            Comparison results
        """
        perf1 = self.get_tool_performance(tool1)
        perf2 = self.get_tool_performance(tool2)

        # Determine winner
        score1 = perf1['avg_quality'] * perf1['success_rate']
        score2 = perf2['avg_quality'] * perf2['success_rate']

        winner = tool1 if score1 > score2 else tool2
        confidence = abs(score1 - score2)

        return {
            "tool1": tool1,
            "tool2": tool2,
            "tool1_score": score1,
            "tool2_score": score2,
            "winner": winner,
            "confidence": min(1.0, confidence * 2),  # Scale confidence
            "recommendation": f"{winner} performs {confidence*100:.0f}% better for {scenario}"
        }

    def recommend_tool(self, task_type: str, target_type: str = "general") -> Tuple[str, float]:
        """
        Recommend best tool for a task based on learned performance.

        Args:
            task_type: Type of task (e.g., "port_scan", "dir_enum", "vuln_scan")
            target_type: Type of target

        Returns:
            (recommended_tool, confidence)
        """
        # Map task types to tool categories
        tool_categories = {
            "port_scan": ["nmap", "rustscan", "masscan"],
            "dir_enum": ["gobuster", "feroxbuster", "ffuf", "dirsearch"],
            "vuln_scan": ["nuclei", "nikto"],
            "subdomain_enum": ["amass", "subfinder", "dnsenum"],
            "web_scan": ["whatweb", "httpx", "katana"],
            "sql_injection": ["sqlmap"],
            "password_crack": ["hydra", "john", "hashcat"]
        }

        candidate_tools = tool_categories.get(task_type, [])

        if not candidate_tools:
            logger.warning(f"No candidate tools for task type: {task_type}")
            return ("unknown", 0.0)

        # Get performance for each candidate
        performances = {}
        for tool in candidate_tools:
            perf = self.get_tool_performance(tool)
            if perf['executions'] > 0:
                # Score = quality * success_rate * (1 / log(duration))
                score = perf['avg_quality'] * perf['success_rate']
                if perf['avg_duration'] > 0:
                    # Penalty for slow tools
                    import math
                    time_factor = 1 / (1 + math.log(perf['avg_duration'] + 1) / 10)
                    score *= time_factor
                performances[tool] = score

        if not performances:
            # No data, return first tool as default
            return (candidate_tools[0], 0.3)

        # Get best tool
        best_tool = max(performances.items(), key=lambda x: x[1])

        # Calculate confidence based on data
        tool_perf = self.get_tool_performance(best_tool[0])
        confidence = min(1.0, tool_perf['executions'] / 10)  # More executions = more confidence

        logger.info(f"Recommended {best_tool[0]} for {task_type} (confidence: {confidence:.2f})")

        return (best_tool[0], confidence)

    def get_tool_rankings(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get ranked list of all tools by performance.

        Args:
            limit: Maximum number of tools to return

        Returns:
            List of tool rankings
        """
        # Get all unique tools
        executions = self.memory.get_patterns(pattern_type="tool_execution")
        unique_tools = set(e['pattern_data']['tool'] for e in executions)

        # Get performance for each
        rankings = []
        for tool in unique_tools:
            perf = self.get_tool_performance(tool)
            if perf['executions'] > 0:
                # Overall score
                score = perf['avg_quality'] * perf['success_rate']
                rankings.append({
                    **perf,
                    "overall_score": score
                })

        # Sort by score
        rankings.sort(key=lambda x: x['overall_score'], reverse=True)

        return rankings[:limit]

    def generate_tool_report(self) -> str:
        """
        Generate comprehensive tool performance report.

        Returns:
            Markdown-formatted report
        """
        rankings = self.get_tool_rankings()

        report = f"""
# Tool Performance Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Top Performing Tools

"""

        for i, tool in enumerate(rankings, 1):
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
            report += f"{emoji} **{i}. {tool['tool']}**\n"
            report += f"   - Executions: {tool['executions']}\n"
            report += f"   - Success Rate: {tool['success_rate']*100:.1f}%\n"
            report += f"   - Avg Quality: {tool['avg_quality']*100:.1f}%\n"
            report += f"   - Avg Duration: {tool['avg_duration']:.1f}s\n"
            report += f"   - Overall Score: {tool['overall_score']:.3f}\n\n"

        report += """
## Tool Selection Guidelines

Based on learned performance, here are recommended tools for common tasks:

"""

        # Add recommendations for common tasks
        common_tasks = [
            "port_scan",
            "dir_enum",
            "vuln_scan",
            "subdomain_enum"
        ]

        for task in common_tasks:
            tool, confidence = self.recommend_tool(task)
            report += f"- **{task.replace('_', ' ').title()}**: {tool} (confidence: {confidence*100:.0f}%)\n"

        report += "\n---\n\n*This report generated automatically based on execution history*\n"

        return report


if __name__ == "__main__":
    # Test tool learning
    import sys
    sys.path.append('..')

    from storage.memory_manager import MemoryManager

    logging.basicConfig(level=logging.INFO)

    memory = MemoryManager("test_memory.db")
    tracker = ToolPerformanceTracker(memory)

    # Simulate tool executions
    print("\nSimulating tool executions...")

    # nmap - good performance
    for i in range(10):
        tracker.record_tool_execution("nmap", {
            "success": True,
            "duration": 45 + i * 5,
            "results_count": 15,
            "target_type": "network"
        })

    # rustscan - faster but fewer results
    for i in range(8):
        tracker.record_tool_execution("rustscan", {
            "success": True,
            "duration": 10 + i * 2,
            "results_count": 12,
            "target_type": "network"
        })

    # gobuster - mixed results
    for i in range(5):
        tracker.record_tool_execution("gobuster", {
            "success": i < 4,  # One failure
            "duration": 120 + i * 10,
            "results_count": 8 if i < 4 else 0,
            "target_type": "web"
        })

    # Get rankings
    print("\nTool Rankings:")
    rankings = tracker.get_tool_rankings()
    for i, tool in enumerate(rankings, 1):
        print(f"  {i}. {tool['tool']}: {tool['overall_score']:.3f}")

    # Get recommendation
    print("\nRecommendations:")
    tool, conf = tracker.recommend_tool("port_scan")
    print(f"  Port Scan: {tool} ({conf*100:.0f}% confidence)")

    # Generate report
    print("\nFull Report:")
    print(tracker.generate_tool_report())
