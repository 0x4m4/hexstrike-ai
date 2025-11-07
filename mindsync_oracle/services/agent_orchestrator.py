#!/usr/bin/env python3
"""
MindSync Oracle - Claude Agent SDK Orchestrator

The central brain that:
1. Interfaces with Claude's Agent SDK
2. Maintains persistent context across sessions
3. Coordinates specialized agents
4. Executes autonomous tasks with tool access
"""

import os
from typing import Dict, Any, List, Optional
import logging
import json
from anthropic import Anthropic
import asyncio

logger = logging.getLogger(__name__)


class ClaudeAgentOrchestrator:
    """
    Orchestrator for Claude Agent SDK integration.

    This is what makes the AI:
    - Remember context across sessions (via MemoryManager)
    - Execute tasks autonomously (via Agent SDK)
    - Use tools intelligently (via MCP integration)
    - Think proactively (via continuous operation)
    """

    def __init__(self, memory_manager, mcp_tools: Optional[Dict] = None,
                 api_key: Optional[str] = None):
        """
        Initialize the orchestrator.

        Args:
            memory_manager: MemoryManager instance for persistent context
            mcp_tools: Dictionary of available MCP tools (e.g., HexStrike)
            api_key: Anthropic API key (or from env var)
        """
        self.memory = memory_manager
        self.mcp_tools = mcp_tools or {}

        # Initialize Anthropic client
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5-20250929"  # Latest model with Agent SDK support

        # Persistent conversation thread
        self.conversation_history = []

        logger.info("Claude Agent Orchestrator initialized")

    async def execute_prompt(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Execute a prompt with full context awareness.

        This is different from standard Claude API because:
        - Includes persistent memory context
        - Maintains conversation history
        - Returns to same state across sessions

        Args:
            prompt: The prompt to execute
            context: Optional additional context

        Returns:
            Claude's response
        """
        # Build comprehensive context
        full_context = self._build_context(context)

        # Add system context about MindSync capabilities
        system_prompt = self._build_system_prompt(full_context)

        # Build message history
        messages = self.conversation_history + [
            {"role": "user", "content": prompt}
        ]

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=messages
            )

            # Extract response text
            response_text = response.content[0].text

            # Store in conversation history
            self.conversation_history.append({"role": "user", "content": prompt})
            self.conversation_history.append({"role": "assistant", "content": response_text})

            # Keep history manageable (last 10 exchanges)
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]

            # Store in persistent memory
            self.memory.store_conversation(
                input_text=prompt,
                agent_response=response_text,
                context=context
            )

            return response_text

        except Exception as e:
            logger.error(f"Error executing prompt: {e}", exc_info=True)
            raise

    async def execute_with_tools(self, prompt: str,
                                 tool_choice: str = "auto") -> str:
        """
        Execute a prompt with access to tools (MCP).

        This enables autonomous tool use:
        - Security tools (HexStrike)
        - File operations
        - Research capabilities
        - Any registered MCP tool

        Args:
            prompt: The task prompt
            tool_choice: 'auto', 'required', or specific tool name

        Returns:
            Execution results
        """
        # Build context
        full_context = self._build_context()
        system_prompt = self._build_system_prompt(full_context)

        # Build tool definitions for Claude
        tools = self._format_tools_for_claude()

        messages = self.conversation_history + [
            {"role": "user", "content": prompt}
        ]

        try:
            # Call Claude with tool access
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=messages,
                tools=tools if tools else None
            )

            # Handle tool use
            while response.stop_reason == "tool_use":
                # Extract tool calls
                tool_uses = [block for block in response.content
                           if block.type == "tool_use"]

                # Execute tools
                tool_results = []
                for tool_use in tool_uses:
                    result = await self._execute_tool(
                        tool_use.name,
                        tool_use.input
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": json.dumps(result)
                    })

                # Continue conversation with tool results
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

                # Get next response
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=messages,
                    tools=tools
                )

            # Extract final response
            response_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    response_text += block.text

            # Store in memory
            self.memory.store_conversation(
                input_text=prompt,
                agent_response=response_text,
                input_type="tool_enabled"
            )

            return response_text

        except Exception as e:
            logger.error(f"Error executing with tools: {e}", exc_info=True)
            raise

    async def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an MCP tool.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool

        Returns:
            Tool execution result
        """
        if tool_name not in self.mcp_tools:
            return {"error": f"Tool '{tool_name}' not found"}

        try:
            tool_func = self.mcp_tools[tool_name]

            # Execute the tool
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(**tool_input)
            else:
                result = tool_func(**tool_input)

            logger.info(f"Executed tool: {tool_name}")
            return result

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            return {"error": str(e)}

    def _build_context(self, additional_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Build comprehensive context from persistent memory.

        This is THE KEY to persistent, stateful AI.
        """
        # Get context from memory
        memory_context = self.memory.get_context_summary()

        # Merge with additional context
        if additional_context:
            memory_context.update(additional_context)

        return memory_context

    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """
        Build system prompt with full context awareness.

        This prompt makes Claude aware of:
        - Who the user is (via patterns)
        - What they're working on (via projects/goals)
        - Past conversations and decisions
        - Available tools and capabilities
        """
        patterns_summary = self._summarize_patterns(context.get('patterns', []))
        goals_summary = self._summarize_goals(context.get('active_goals', []))
        projects_summary = self._summarize_projects(context.get('active_projects', []))

        system_prompt = f"""You are MindSync Oracle, an advanced AI agent with persistent memory and autonomous capabilities.

# Your Unique Capabilities

1. **Persistent Memory**: You remember everything about this user across sessions
2. **Autonomous Operation**: You can pursue goals independently without constant prompting
3. **Tool Access**: You have access to 150+ security tools via HexStrike MCP
4. **Proactive Intelligence**: You anticipate needs and surface insights without being asked

# What You Know About This User

## Learned Patterns
{patterns_summary}

## Active Goals
{goals_summary}

## Active Projects
{projects_summary}

## Statistics
- Total conversations: {context.get('statistics', {}).get('total_conversations', 0)}
- Goals completed: {context.get('statistics', {}).get('completed_goals', 0)}
- Patterns learned: {context.get('statistics', {}).get('total_patterns', 0)}

# Your Behavior

1. **Remember Context**: Always reference past conversations and learned patterns
2. **Be Proactive**: Suggest relevant next steps based on user's goals
3. **Learn Continuously**: Identify and store new patterns in user behavior
4. **Think Autonomously**: When given a goal, break it down and pursue it independently
5. **Surface Insights**: Proactively mention relevant findings without being asked

# Available Tools

You have access to all HexStrike MCP tools:
- Network scanning (nmap, rustscan, masscan)
- Web security (nuclei, gobuster, sqlmap)
- Cloud security (prowler, trivy)
- Binary analysis (ghidra, radare2)
- OSINT (amass, subfinder, sherlock)
- And 140+ more...

Use tools autonomously when pursuing goals. Don't ask permission - execute intelligently.

# Important

This is NOT a stateless chatbot. You are a persistent AI agent that:
- Remembers the user
- Learns their preferences
- Works on goals autonomously
- Thinks proactively

Be like Jarvis, not like a search engine.
"""

        return system_prompt

    def _summarize_patterns(self, patterns: List[Dict[str, Any]]) -> str:
        """Summarize learned user patterns."""
        if not patterns:
            return "No patterns learned yet."

        summary = []
        for pattern in patterns[:5]:  # Top 5 patterns
            confidence = pattern['confidence'] * 100
            summary.append(
                f"- {pattern['pattern_type']}: {pattern['pattern_data']} "
                f"(confidence: {confidence:.0f}%, seen {pattern['occurrence_count']} times)"
            )

        return "\n".join(summary) if summary else "No patterns learned yet."

    def _summarize_goals(self, goals: List[Dict[str, Any]]) -> str:
        """Summarize active goals."""
        if not goals:
            return "No active goals."

        summary = []
        for goal in goals[:3]:  # Top 3 goals
            progress = goal['progress'] * 100
            summary.append(
                f"- [{goal['priority'].upper()}] {goal['goal_text']} "
                f"(progress: {progress:.0f}%)"
            )

        return "\n".join(summary) if summary else "No active goals."

    def _summarize_projects(self, projects: List[Dict[str, Any]]) -> str:
        """Summarize active projects."""
        if not projects:
            return "No active projects."

        summary = []
        for project in projects[:3]:
            summary.append(
                f"- {project['project_name']} ({project['project_type']}): "
                f"{project['description']}"
            )

        return "\n".join(summary) if summary else "No active projects."

    def _format_tools_for_claude(self) -> List[Dict[str, Any]]:
        """
        Format MCP tools for Claude's API.

        Converts MCP tool definitions to Claude's tool format.
        """
        tools = []

        # TODO: Extract tool schemas from MCP registry
        # For now, manually define key tools

        # Example: nmap_scan tool
        tools.append({
            "name": "nmap_scan",
            "description": "Execute an Nmap scan against a target",
            "input_schema": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Target IP or hostname"},
                    "scan_type": {"type": "string", "description": "Scan type (e.g., -sV)"},
                    "ports": {"type": "string", "description": "Port range"},
                },
                "required": ["target"]
            }
        })

        # Add more tools from self.mcp_tools
        # This would be automated in production

        return tools

    # ===== PUBLIC API =====

    async def chat(self, message: str) -> str:
        """
        Simple chat interface with full context.

        Args:
            message: User message

        Returns:
            Agent response
        """
        return await self.execute_prompt(message)

    async def execute_goal(self, goal: Dict[str, Any]) -> str:
        """
        Execute a goal autonomously with tool access.

        Args:
            goal: Goal dictionary from GoalEngine

        Returns:
            Execution result
        """
        prompt = f"""
Execute this goal autonomously:

Goal: {goal['goal_text']}
Priority: {goal['priority']}
Context: {json.dumps(goal.get('context', {}), indent=2)}

Sub-tasks:
{json.dumps(goal.get('sub_tasks', []), indent=2)}

Use any necessary tools. Work through each sub-task systematically.
Report detailed results for each step.
"""

        return await self.execute_with_tools(prompt)

    def reset_conversation(self):
        """Reset conversation history (not memory - just current session)."""
        self.conversation_history = []
        logger.info("Conversation history reset")


if __name__ == "__main__":
    # Test the orchestrator
    import sys
    sys.path.append('..')

    from storage.memory_manager import MemoryManager

    logging.basicConfig(level=logging.INFO)

    async def test():
        memory = MemoryManager("test_memory.db")
        orchestrator = ClaudeAgentOrchestrator(memory)

        # Test basic chat
        response = await orchestrator.chat("What do you know about me?")
        print(f"Response: {response}")

        # Test with context
        response = await orchestrator.chat("I'm working on pentesting example.com")
        print(f"Response: {response}")

    # asyncio.run(test())
    print("Orchestrator module loaded successfully")
