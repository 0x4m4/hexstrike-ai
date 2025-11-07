#!/usr/bin/env python3
"""
MindSync Oracle - Production Goal-Directed Autonomy Engine

REAL autonomous goal pursuit that actually works.
This runs in background and executes goals without user intervention.
"""

import asyncio
import sys
import os
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import json

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger(__name__)

# Import notification level enum
try:
    from notification_system import NotificationLevel
except ImportError:
    from enum import Enum
    class NotificationLevel(Enum):
        INFO = "info"
        SUCCESS = "success"
        WARNING = "warning"
        CRITICAL = "critical"


class ProductionGoalEngine:
    """
    Production goal engine with REAL autonomous execution.

    This actually works - pursues goals in background without prompting.
    """

    def __init__(self, memory_manager, agent_orchestrator, notification_system,
                 tool_tracker=None, self_improvement=None, adaptive_notifier=None,
                 memory_graph=None):
        """
        Initialize production goal engine.

        Args:
            memory_manager: MemoryManager instance
            agent_orchestrator: Claude orchestrator for execution
            notification_system: NotificationSystem for proactive alerts
            tool_tracker: Optional ToolPerformanceTracker (v2)
            self_improvement: Optional SelfImprovementEngine (v2)
            adaptive_notifier: Optional AdaptiveNotificationEngine (v2)
            memory_graph: Optional HybridMemoryGraph (v3)
        """
        self.memory = memory_manager
        self.orchestrator = agent_orchestrator
        self.notifier = notification_system

        # v2/v3 enhancements (optional)
        self.tool_tracker = tool_tracker
        self.self_improvement = self_improvement
        self.adaptive_notifier = adaptive_notifier
        self.memory_graph = memory_graph

        self.active_executions = {}  # goal_id -> asyncio.Task
        self.is_running = False

        logger.info("Production Goal Engine initialized (v2/v3 enhancements: {})".format(
            "enabled" if tool_tracker else "disabled"
        ))

    async def start_autonomous_loop(self):
        """
        Start the main autonomous goal processing loop.

        This runs continuously in background, checking for and executing goals.
        """
        self.is_running = True
        logger.info("🚀 Autonomous goal engine started")

        while self.is_running:
            try:
                await self._process_active_goals()
                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Error in autonomous loop: {e}", exc_info=True)
                await asyncio.sleep(60)

    async def stop(self):
        """Stop autonomous processing."""
        self.is_running = False

        # Cancel all active executions
        for goal_id, task in self.active_executions.items():
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled goal {goal_id}")

        self.active_executions.clear()
        logger.info("Goal engine stopped")

    async def _process_active_goals(self):
        """Process all active goals autonomously."""
        active_goals = self.memory.get_active_goals()

        for goal in active_goals:
            goal_id = goal['id']

            # Skip if already being worked on
            if goal_id in self.active_executions:
                task = self.active_executions[goal_id]
                if not task.done():
                    continue
                else:
                    # Task completed, remove it
                    del self.active_executions[goal_id]

            # Start working on this goal
            task = asyncio.create_task(self._execute_goal_autonomous(goal))
            self.active_executions[goal_id] = task

            logger.info(f"Started autonomous execution of goal {goal_id}: {goal['goal_text']}")

    async def _execute_goal_autonomous(self, goal: Dict[str, Any]):
        """
        Execute a single goal autonomously from start to finish.

        This is the CORE autonomous behavior - works without user input.

        Args:
            goal: Goal dictionary from memory
        """
        goal_id = goal['id']
        goal_text = goal['goal_text']

        logger.info(f"🎯 Executing goal: {goal_text}")

        try:
            # Step 1: Decompose goal if needed
            if not goal.get('sub_tasks'):
                logger.info(f"Decomposing goal {goal_id}...")
                sub_tasks = await self.orchestrator.decompose_goal(
                    goal_text,
                    goal.get('context', {})
                )

                # Update goal with sub-tasks
                # Note: We'd need to add this method to memory_manager
                logger.info(f"Created {len(sub_tasks)} sub-tasks")
            else:
                sub_tasks = goal['sub_tasks']

            if not sub_tasks:
                sub_tasks = [goal_text]  # Fallback

            # Step 2: Execute each sub-task
            total_tasks = len(sub_tasks)
            results = []

            for i, task in enumerate(sub_tasks):
                logger.info(f"[{i+1}/{total_tasks}] Executing: {task}")

                # Execute sub-task using orchestrator with tool access
                result = await self.orchestrator.execute_with_tools(
                    f"""Execute this sub-task as part of the goal: "{goal_text}"

Sub-task: {task}

Use any available tools as needed. Provide detailed results."""
                )

                results.append({
                    "task": task,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })

                # Update progress
                progress = (i + 1) / total_tasks
                self.memory.update_goal_progress(goal_id, progress)

                logger.info(f"Progress: {progress*100:.0f}%")

            # Step 3: Generate final report
            report = await self._generate_report(goal, results)

            # Step 4: Mark goal as completed
            self.memory.update_goal_progress(goal_id, 1.0, status='completed')

            # Step 5: v2/v3 Integration - Self-Improvement & Learning
            execution_data = {
                "success": True,
                "goal_id": goal_id,
                "results": results,
                "report": report,
                "duration": (datetime.now() - datetime.fromisoformat(goal.get('created_at', datetime.now().isoformat()))).total_seconds(),
                "tools_used": self._extract_tools_from_results(results)
            }

            # v2: Self-improvement analysis
            if self.self_improvement:
                try:
                    analysis = await self.self_improvement.analyze_goal_outcome(goal_id, execution_data)
                    logger.info(f"Self-improvement analysis: {analysis.get('analysis', {}).get('success_rating', 'N/A')}/10")
                except Exception as e:
                    logger.error(f"Error in self-improvement: {e}")

            # v3: Add to memory graph
            if self.memory_graph:
                try:
                    tools_used = execution_data['tools_used']
                    learnings = self._extract_learnings_from_results(results, analysis if self.self_improvement else {})
                    self.memory_graph.add_goal_execution(
                        goal_text,
                        tools_used=tools_used,
                        outcome={'success': True, 'duration': execution_data['duration']},
                        learnings=learnings
                    )
                    logger.info(f"Added goal execution to memory graph")
                except Exception as e:
                    logger.error(f"Error adding to memory graph: {e}")

            # Step 6: Notify user proactively (using adaptive notifier if available)
            if self.adaptive_notifier:
                await self.adaptive_notifier.send_adaptive(
                    "Goal Completed",
                    f"{goal_text}\n\nCompleted {len(sub_tasks)} tasks. {report[:200]}...",
                    notification_type="goal_completed"
                )
            else:
                self.notifier.goal_completed(
                    goal_text,
                    f"Completed {len(sub_tasks)} tasks. {report[:200]}..."
                )

            logger.info(f"✅ Goal {goal_id} completed successfully")

            return {
                "success": True,
                "goal_id": goal_id,
                "results": results,
                "report": report
            }

        except Exception as e:
            logger.error(f"Error executing goal {goal_id}: {e}", exc_info=True)

            # Mark goal as failed
            self.memory.update_goal_progress(goal_id, goal.get('progress', 0), status='failed')

            # Notify user
            self.notifier.goal_failed(goal_text, str(e))

            return {
                "success": False,
                "goal_id": goal_id,
                "error": str(e)
            }

    async def _generate_report(self, goal: Dict[str, Any],
                               results: List[Dict[str, Any]]) -> str:
        """
        Generate comprehensive report for completed goal.

        Args:
            goal: Goal dictionary
            results: List of sub-task results

        Returns:
            Formatted report
        """
        prompt = f"""Generate a concise report for this completed goal.

Goal: {goal['goal_text']}
Priority: {goal.get('priority', 'medium')}
Sub-tasks completed: {len(results)}

Results:
{json.dumps(results, indent=2, default=str)}

Create a brief report (3-5 bullet points) highlighting key findings and results.
"""

        try:
            report = await self.orchestrator.chat(prompt, store_in_memory=False)
            return report
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return f"Goal completed with {len(results)} tasks executed."

    # Public API

    def add_goal(self, goal_text: str, priority: str = "medium",
                context: Optional[Dict[str, Any]] = None) -> int:
        """
        Add a new goal for autonomous pursuit.

        Args:
            goal_text: Goal description
            priority: Priority level (low, medium, high, critical)
            context: Optional additional context

        Returns:
            Goal ID
        """
        goal_id = self.memory.create_goal(
            goal_text,
            priority=priority,
            context=context
        )

        logger.info(f"Added goal for autonomous execution: {goal_text} (ID: {goal_id})")

        # Notify user
        self.notifier.notify(
            "New Goal Added",
            f"Goal '{goal_text}' will be executed autonomously (Priority: {priority})",
            level=NotificationLevel.INFO
        )

        return goal_id

    def get_goal_status(self, goal_id: int) -> Dict[str, Any]:
        """Get current status of a goal."""
        goals = self.memory.get_active_goals()

        for goal in goals:
            if goal['id'] == goal_id:
                return {
                    "goal_id": goal_id,
                    "goal_text": goal['goal_text'],
                    "status": "in_progress" if goal_id in self.active_executions else "queued",
                    "progress": goal['progress'],
                    "priority": goal.get('priority', 'medium')
                }

        # Check if completed
        return {
            "goal_id": goal_id,
            "status": "not_found"
        }

    def list_active_goals(self) -> List[Dict[str, Any]]:
        """List all active goals with status."""
        goals = self.memory.get_active_goals()

        return [{
            "goal_id": g['id'],
            "goal_text": g['goal_text'],
            "progress": g['progress'],
            "priority": g.get('priority', 'medium'),
            "status": "in_progress" if g['id'] in self.active_executions else "queued"
        } for g in goals]

    # v2/v3 Integration Helper Methods

    def _extract_tools_from_results(self, results: List[Dict[str, Any]]) -> List[str]:
        """
        Extract tool names from execution results.

        Args:
            results: List of execution results

        Returns:
            List of tool names used
        """
        tools = []
        for result in results:
            # Extract tools from result data
            if isinstance(result, dict):
                result_text = str(result.get('result', ''))
                # Common security tools
                common_tools = [
                    'nmap', 'rustscan', 'masscan', 'nuclei', 'nikto',
                    'gobuster', 'feroxbuster', 'ffuf', 'dirsearch',
                    'amass', 'subfinder', 'sqlmap', 'hydra', 'john',
                    'hashcat', 'metasploit', 'burpsuite', 'whatweb',
                    'httpx', 'katana'
                ]
                for tool in common_tools:
                    if tool in result_text.lower():
                        if tool not in tools:
                            tools.append(tool)

        return tools if tools else ['claude']  # Default to claude if no specific tools detected

    def _extract_learnings_from_results(self, results: List[Dict[str, Any]],
                                       analysis: Dict[str, Any]) -> List[str]:
        """
        Extract learnings from execution results and self-improvement analysis.

        Args:
            results: List of execution results
            analysis: Self-improvement analysis (if available)

        Returns:
            List of learning strings
        """
        learnings = []

        # Extract from self-improvement analysis
        if analysis and 'analysis' in analysis:
            what_worked = analysis['analysis'].get('what_worked', [])
            learnings.extend(what_worked[:3])  # Top 3 learnings

            suggested = analysis['analysis'].get('suggested_improvements', [])
            learnings.extend(suggested[:2])  # Top 2 improvements

        # Extract from results
        for result in results[:3]:  # First 3 results
            if isinstance(result, dict):
                result_text = str(result.get('result', ''))
                # Extract key findings (simplified)
                if 'found' in result_text.lower() or 'discovered' in result_text.lower():
                    learnings.append(result_text[:100])  # First 100 chars

        return learnings[:5] if learnings else ['Goal completed successfully']


if __name__ == "__main__":
    # Test goal engine
    import sys
    sys.path.append('..')

    from storage.memory_manager import MemoryManager
    from notification_system import NotificationSystem

    logging.basicConfig(level=logging.INFO)

    # Mock orchestrator for testing
    class MockOrchestrator:
        async def decompose_goal(self, goal_text, context):
            return [
                "Step 1: Research the topic",
                "Step 2: Execute analysis",
                "Step 3: Compile results"
            ]

        async def execute_with_tools(self, prompt):
            await asyncio.sleep(1)
            return {
                "success": True,
                "response": "Task completed successfully",
                "tool_calls": []
            }

        async def chat(self, prompt, store_in_memory=True):
            return "Summary: All tasks completed successfully."

    async def test():
        memory = MemoryManager("test_memory.db")
        notifier = NotificationSystem(enabled_methods=['terminal'])
        orchestrator = MockOrchestrator()

        engine = ProductionGoalEngine(memory, orchestrator, notifier)

        # Add a goal
        goal_id = engine.add_goal(
            "Research CVE-2024-1234 and test exploit",
            priority="high"
        )

        print(f"Created goal: {goal_id}")

        # Start autonomous execution (run for 10 seconds)
        task = asyncio.create_task(engine.start_autonomous_loop())

        await asyncio.sleep(10)

        await engine.stop()

        # Check status
        status = engine.get_goal_status(goal_id)
        print(f"\nFinal status: {json.dumps(status, indent=2)}")

    asyncio.run(test())
