#!/usr/bin/env python3
"""
MindSync Oracle - Goal-Directed Autonomy Engine

THE MISSING PIECE for AGI-like behavior:
- Autonomous goal pursuit (not just reactive responses)
- Background task execution
- Proactive progress reporting

This is what separates "smart chatbot" from "Jarvis".
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class GoalDirectedEngine:
    """
    Autonomous goal pursuit engine.

    Instead of:
        User: "Do X"
        AI: <does X>
        [conversation ends]

    This enables:
        User: "I need to accomplish X"
        AI: <breaks into tasks>
            <works on tasks autonomously>
            <reports progress proactively>
            <surfaces results when ready>
    """

    def __init__(self, memory_manager, agent_orchestrator):
        """
        Initialize the goal engine.

        Args:
            memory_manager: MemoryManager instance for persistence
            agent_orchestrator: Claude Agent SDK orchestrator for execution
        """
        self.memory = memory_manager
        self.orchestrator = agent_orchestrator
        self.active_tasks = {}  # task_id -> asyncio.Task
        self.is_running = False
        logger.info("Goal-Directed Engine initialized")

    async def start(self):
        """Start the autonomous goal processing loop."""
        self.is_running = True
        logger.info("🚀 Goal engine started - entering autonomous mode")

        # Start the main processing loop
        await self._autonomous_loop()

    async def stop(self):
        """Stop the autonomous processing loop."""
        self.is_running = False
        # Cancel all active tasks
        for task_id, task in self.active_tasks.items():
            task.cancel()
            logger.info(f"Cancelled task: {task_id}")
        logger.info("Goal engine stopped")

    async def _autonomous_loop(self):
        """
        Main autonomous processing loop.

        This runs continuously in the background, checking for:
        - New goals to pursue
        - Progress updates needed
        - Completed tasks to report
        """
        while self.is_running:
            try:
                # Get all active goals from memory
                active_goals = self.memory.get_active_goals()

                for goal in active_goals:
                    goal_id = goal['id']

                    # Check if we're already working on this goal
                    if goal_id not in self.active_tasks:
                        # Start autonomous pursuit
                        task = asyncio.create_task(
                            self._pursue_goal(goal)
                        )
                        self.active_tasks[goal_id] = task
                        logger.info(f"Started autonomous pursuit of goal {goal_id}: {goal['goal_text']}")

                # Clean up completed tasks
                completed = [gid for gid, task in self.active_tasks.items() if task.done()]
                for goal_id in completed:
                    del self.active_tasks[goal_id]

                # Sleep before next check (configurable - could be 1min, 5min, etc.)
                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Error in autonomous loop: {e}", exc_info=True)
                await asyncio.sleep(60)

    async def _pursue_goal(self, goal: Dict[str, Any]):
        """
        Autonomously pursue a single goal.

        This is where the magic happens - the AI works on goals WITHOUT user prompting.

        Args:
            goal: Goal dictionary from memory
        """
        goal_id = goal['id']
        goal_text = goal['goal_text']

        logger.info(f"🎯 Pursuing goal: {goal_text}")

        try:
            # Step 1: Decompose goal into actionable sub-tasks if not already done
            if not goal['sub_tasks']:
                sub_tasks = await self._decompose_goal(goal_text, goal.get('context', {}))
                self.memory.update_goal_progress(goal_id, 0.1, status='active')
                logger.info(f"Decomposed goal into {len(sub_tasks)} sub-tasks")
            else:
                sub_tasks = goal['sub_tasks']

            # Step 2: Execute sub-tasks autonomously
            total_tasks = len(sub_tasks)
            completed_tasks = 0

            for i, task in enumerate(sub_tasks):
                logger.info(f"Executing sub-task {i+1}/{total_tasks}: {task}")

                # Execute the sub-task using the orchestrator
                result = await self._execute_subtask(task, goal.get('context', {}))

                # Update progress
                completed_tasks += 1
                progress = completed_tasks / total_tasks
                self.memory.update_goal_progress(goal_id, progress)

                logger.info(f"Completed sub-task {i+1}/{total_tasks} - Progress: {progress*100:.0f}%")

                # Store results in context
                if not isinstance(goal.get('context'), dict):
                    goal['context'] = {}
                if 'subtask_results' not in goal['context']:
                    goal['context']['subtask_results'] = []
                goal['context']['subtask_results'].append({
                    'task': task,
                    'result': result,
                    'timestamp': datetime.now().isoformat()
                })

            # Step 3: Mark goal as completed
            self.memory.update_goal_progress(goal_id, 1.0, status='completed')

            # Step 4: Prepare proactive report
            report = await self._generate_goal_report(goal, goal['context']['subtask_results'])

            logger.info(f"✅ Goal completed: {goal_text}")
            logger.info(f"📊 Report: {report[:200]}...")

            # TODO: Surface this report proactively to user via notification
            # For now, it's stored in memory and can be retrieved

        except Exception as e:
            logger.error(f"Error pursuing goal {goal_id}: {e}", exc_info=True)
            self.memory.update_goal_progress(goal_id, goal['progress'], status='failed')

    async def _decompose_goal(self, goal_text: str, context: Dict[str, Any]) -> List[str]:
        """
        Decompose a high-level goal into actionable sub-tasks.

        This uses the Claude Agent SDK to intelligently break down goals.

        Args:
            goal_text: Natural language goal description
            context: Additional context about the goal

        Returns:
            List of sub-task descriptions
        """
        prompt = f"""
You are a goal decomposition expert. Break down this goal into specific, actionable sub-tasks.

Goal: {goal_text}

Context: {json.dumps(context, indent=2)}

Requirements:
- Create 3-7 sub-tasks
- Each sub-task should be specific and measurable
- Order tasks logically (dependencies first)
- Make tasks achievable with available tools

Output format (JSON):
{{
    "sub_tasks": [
        "Task 1 description",
        "Task 2 description",
        ...
    ]
}}
"""

        # Use orchestrator to get decomposition from Claude
        response = await self.orchestrator.execute_prompt(prompt)

        try:
            # Parse JSON response
            result = json.loads(response)
            return result.get('sub_tasks', [])
        except json.JSONDecodeError:
            # Fallback: extract tasks from text
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            return [line for line in lines if line and not line.startswith('#')][:7]

    async def _execute_subtask(self, task: str, context: Dict[str, Any]) -> str:
        """
        Execute a single sub-task autonomously.

        Args:
            task: Task description
            context: Goal context

        Returns:
            Task execution result
        """
        prompt = f"""
Execute this sub-task autonomously. Use any available tools as needed.

Task: {task}

Context: {json.dumps(context, indent=2)}

Available tools:
- Security tools (via HexStrike MCP)
- Research capabilities
- Data analysis
- File operations

Execute the task and report results in detail.
"""

        # Use orchestrator to execute with tool access
        result = await self.orchestrator.execute_with_tools(prompt)

        return result

    async def _generate_goal_report(self, goal: Dict[str, Any],
                                   subtask_results: List[Dict[str, Any]]) -> str:
        """
        Generate a comprehensive report for a completed goal.

        Args:
            goal: Goal dictionary
            subtask_results: Results from all sub-tasks

        Returns:
            Formatted report text
        """
        prompt = f"""
Generate a comprehensive report for this completed goal.

Goal: {goal['goal_text']}
Priority: {goal['priority']}
Duration: {goal['created_at']} to {datetime.now().isoformat()}

Sub-task Results:
{json.dumps(subtask_results, indent=2)}

Create a clear, actionable report with:
1. Executive summary
2. Key findings
3. Detailed results from each sub-task
4. Recommendations
5. Next steps (if any)

Format: Markdown
"""

        report = await self.orchestrator.execute_prompt(prompt)
        return report

    # ===== PUBLIC API =====

    def add_goal(self, goal_text: str, priority: str = "medium",
                context: Optional[Dict[str, Any]] = None) -> int:
        """
        Add a new goal for autonomous pursuit.

        Args:
            goal_text: Natural language goal description
            priority: 'low', 'medium', 'high', 'critical'
            context: Optional additional context

        Returns:
            Goal ID
        """
        goal_id = self.memory.create_goal(goal_text, priority=priority, context=context)
        logger.info(f"Added goal for autonomous pursuit: {goal_text} (ID: {goal_id})")
        return goal_id

    def get_goal_status(self, goal_id: int) -> Dict[str, Any]:
        """Get current status of a goal."""
        goals = self.memory.get_active_goals()
        for goal in goals:
            if goal['id'] == goal_id:
                return {
                    'goal_id': goal_id,
                    'status': goal.get('status', 'active'),
                    'progress': goal['progress'],
                    'is_running': goal_id in self.active_tasks
                }
        return {'goal_id': goal_id, 'status': 'not_found'}

    def pause_goal(self, goal_id: int):
        """Pause autonomous pursuit of a goal."""
        # Cancel the task if running
        if goal_id in self.active_tasks:
            self.active_tasks[goal_id].cancel()
            del self.active_tasks[goal_id]

        # Update memory
        goals = self.memory.get_active_goals()
        for goal in goals:
            if goal['id'] == goal_id:
                self.memory.update_goal_progress(goal_id, goal['progress'], status='paused')
                logger.info(f"Paused goal {goal_id}")
                break

    def resume_goal(self, goal_id: int):
        """Resume a paused goal."""
        # Just update status - the autonomous loop will pick it up
        goals = self.memory.get_active_goals()
        for goal in goals:
            if goal['id'] == goal_id:
                self.memory.update_goal_progress(goal_id, goal['progress'], status='active')
                logger.info(f"Resumed goal {goal_id}")
                break


class GoalDecompositionAgent:
    """
    Specialized agent for breaking down complex goals.

    This agent understands:
    - Dependencies between tasks
    - Available tools and capabilities
    - User's typical workflows (from memory)
    """

    def __init__(self, memory_manager):
        self.memory = memory_manager

    async def decompose(self, goal_text: str, context: Dict[str, Any]) -> List[str]:
        """
        Intelligently decompose a goal into sub-tasks.

        Uses:
        - User's past patterns
        - Available tools
        - Domain knowledge
        """
        # Get user's patterns to inform decomposition
        patterns = self.memory.get_patterns(min_confidence=0.6)

        # TODO: Use Claude to generate context-aware decomposition
        # For now, return a simple breakdown
        return [
            f"Research and gather information about: {goal_text}",
            f"Analyze findings and identify key issues",
            f"Execute necessary tools/actions",
            f"Compile results and generate report"
        ]


class ProactiveReportingAgent:
    """
    Agent that surfaces completed work proactively.

    Instead of waiting for user to ask "what's done?",
    this agent pushes results when ready.
    """

    def __init__(self, memory_manager, notification_callback: Optional[Callable] = None):
        self.memory = memory_manager
        self.notify = notification_callback or self._default_notify

    async def check_and_report(self):
        """Check for completed goals and report them."""
        # Get recently completed goals that haven't been reported
        # TODO: Track which goals have been reported

        logger.info("Checking for completed goals to report...")

    def _default_notify(self, message: str):
        """Default notification (just log)."""
        logger.info(f"📣 NOTIFICATION: {message}")


if __name__ == "__main__":
    # Test the goal engine
    import sys
    sys.path.append('..')

    from storage.memory_manager import MemoryManager

    logging.basicConfig(level=logging.INFO)

    # Mock orchestrator for testing
    class MockOrchestrator:
        async def execute_prompt(self, prompt):
            return '{"sub_tasks": ["Task 1", "Task 2", "Task 3"]}'

        async def execute_with_tools(self, prompt):
            await asyncio.sleep(1)  # Simulate work
            return "Task completed successfully"

    async def test():
        memory = MemoryManager("test_memory.db")
        orchestrator = MockOrchestrator()
        engine = GoalDirectedEngine(memory, orchestrator)

        # Add a goal
        goal_id = engine.add_goal(
            "Research CVE-2024-1234 and prepare exploit analysis",
            priority="high",
            context={"target": "example.com"}
        )

        print(f"Created goal: {goal_id}")

        # Start autonomous processing (run for 10 seconds for demo)
        task = asyncio.create_task(engine.start())
        await asyncio.sleep(10)
        await engine.stop()

        # Check status
        status = engine.get_goal_status(goal_id)
        print(f"Final status: {status}")

    asyncio.run(test())
