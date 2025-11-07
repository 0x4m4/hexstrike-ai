#!/usr/bin/env python3
"""
MindSync Oracle - Production Claude Agent Orchestrator

REAL implementation with actual Claude API integration and tool use.
This is the production version that actually works.
"""

import os
import sys
from typing import Dict, Any, List, Optional
import logging
import json
from anthropic import Anthropic, APIError
import asyncio

# Add parent to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger(__name__)


class ProductionClaudeOrchestrator:
    """
    Production-ready Claude Agent SDK orchestrator.

    This ACTUALLY works with real Claude API calls and tool execution.
    """

    def __init__(self, memory_manager, hexstrike_integration,
                 config_manager, api_key: Optional[str] = None):
        """
        Initialize production orchestrator.

        Args:
            memory_manager: MemoryManager instance
            hexstrike_integration: HexStrikeIntegration instance
            config_manager: ConfigManager instance
            api_key: Optional API key override
        """
        self.memory = memory_manager
        self.hexstrike = hexstrike_integration
        self.config = config_manager

        # Get API key
        api_key = api_key or self.config.anthropic_key
        if not api_key:
            if self.config.get('development.mock_api_calls'):
                logger.warning("Mock API mode - Claude calls will be simulated")
                self.client = None
            else:
                raise ValueError("ANTHROPIC_API_KEY required. Set in config or environment.")
        else:
            self.client = Anthropic(api_key=api_key)

        # Configuration
        self.model = self.config.get('agent.model', 'claude-sonnet-4-5-20250929')
        self.max_tokens = self.config.get('agent.max_tokens', 8000)
        self.temperature = self.config.get('agent.temperature', 0.7)

        # Conversation state
        self.conversation_history = []
        self.max_history = 20  # Keep last 20 exchanges

        logger.info(f"Production orchestrator initialized (model: {self.model})")

    async def chat(self, message: str, store_in_memory: bool = True) -> str:
        """
        Chat with full context awareness.

        Args:
            message: User message
            store_in_memory: Whether to store conversation in persistent memory

        Returns:
            Agent response
        """
        # Build context from memory
        context = self._build_context_from_memory()

        # Build system prompt
        system_prompt = self._build_system_prompt(context)

        # Build messages
        messages = self.conversation_history + [
            {"role": "user", "content": message}
        ]

        try:
            if self.client:
                # Real Claude API call
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=messages
                )

                response_text = self._extract_text_from_response(response)
            else:
                # Mock mode
                response_text = self._mock_response(message, context)

            # Update conversation history
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": response_text})

            # Trim history
            if len(self.conversation_history) > self.max_history * 2:
                self.conversation_history = self.conversation_history[-self.max_history * 2:]

            # Store in persistent memory
            if store_in_memory:
                self.memory.store_conversation(
                    input_text=message,
                    agent_response=response_text,
                    input_type="text"
                )

            return response_text

        except APIError as e:
            logger.error(f"Claude API error: {e}")
            return f"Error communicating with Claude: {str(e)}"

        except Exception as e:
            logger.error(f"Unexpected error in chat: {e}", exc_info=True)
            return f"Unexpected error: {str(e)}"

    async def execute_with_tools(self, prompt: str, max_tool_rounds: int = 5) -> Dict[str, Any]:
        """
        Execute prompt with tool access (HexStrike tools).

        Args:
            prompt: Task prompt
            max_tool_rounds: Maximum tool execution rounds

        Returns:
            Execution results including tool calls and final response
        """
        context = self._build_context_from_memory()
        system_prompt = self._build_system_prompt(context)

        # Get tool schemas from HexStrike
        tools = self.hexstrike.get_tool_schemas()

        if not tools:
            logger.warning("No tools available - execution without tools")
            response = await self.chat(prompt)
            return {
                "success": True,
                "response": response,
                "tool_calls": [],
                "rounds": 0
            }

        messages = self.conversation_history + [
            {"role": "user", "content": prompt}
        ]

        tool_calls_made = []
        rounds = 0

        try:
            while rounds < max_tool_rounds:
                rounds += 1

                if self.client:
                    # Real Claude API call with tools
                    response = self.client.messages.create(
                        model=self.model,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                        system=system_prompt,
                        messages=messages,
                        tools=tools
                    )

                    # Check if Claude wants to use tools
                    if response.stop_reason != "tool_use":
                        # No more tools needed, we're done
                        final_text = self._extract_text_from_response(response)
                        break

                    # Extract tool uses
                    tool_uses = [block for block in response.content
                                if block.type == "tool_use"]

                    if not tool_uses:
                        # No tools used, get text response
                        final_text = self._extract_text_from_response(response)
                        break

                    # Execute tools
                    tool_results = []
                    for tool_use in tool_uses:
                        logger.info(f"Executing tool: {tool_use.name}")

                        result = await self.hexstrike.execute_tool(
                            tool_use.name,
                            **tool_use.input
                        )

                        tool_calls_made.append({
                            "tool": tool_use.name,
                            "input": tool_use.input,
                            "result": result
                        })

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": json.dumps(result)
                        })

                    # Add tool results to conversation
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": tool_results})

                else:
                    # Mock mode - simulate tool execution
                    final_text = self._mock_tool_response(prompt, tools)
                    break

            # Store final conversation
            self.memory.store_conversation(
                input_text=prompt,
                agent_response=final_text,
                input_type="tool_enabled",
                context={"tool_calls": len(tool_calls_made)}
            )

            return {
                "success": True,
                "response": final_text,
                "tool_calls": tool_calls_made,
                "rounds": rounds
            }

        except Exception as e:
            logger.error(f"Error in tool execution: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "tool_calls": tool_calls_made,
                "rounds": rounds
            }

    async def decompose_goal(self, goal_text: str, context: Dict[str, Any]) -> List[str]:
        """
        Decompose a high-level goal into actionable sub-tasks.

        Args:
            goal_text: Goal description
            context: Goal context

        Returns:
            List of sub-task descriptions
        """
        prompt = f"""
Decompose this goal into specific, actionable sub-tasks.

Goal: {goal_text}

Context: {json.dumps(context, indent=2)}

Requirements:
- Create 3-7 sub-tasks
- Each sub-task must be specific and achievable with available tools
- Order tasks logically (dependencies first)
- Consider the user's typical patterns and workflows

Output ONLY a JSON array of sub-task strings, nothing else:
["task 1", "task 2", "task 3"]
"""

        response = await self.chat(prompt, store_in_memory=False)

        # Parse JSON from response
        try:
            # Try to find JSON array in response
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                tasks = json.loads(json_match.group())
                return tasks
            else:
                # Fallback: split by lines
                tasks = [line.strip() for line in response.split('\n')
                        if line.strip() and not line.startswith('#')]
                return tasks[:7]

        except Exception as e:
            logger.error(f"Error parsing goal decomposition: {e}")
            # Fallback tasks
            return [
                f"Research and gather information about: {goal_text}",
                "Execute necessary actions using available tools",
                "Analyze results and compile findings",
                "Generate comprehensive report"
            ]

    def _build_context_from_memory(self) -> Dict[str, Any]:
        """Build context from persistent memory."""
        return self.memory.get_context_summary()

    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """Build comprehensive system prompt with context."""
        patterns_summary = self._summarize_list(
            context.get('patterns', []),
            lambda p: f"{p['pattern_type']}: {p['pattern_data']} ({p['confidence']*100:.0f}%)"
        )

        goals_summary = self._summarize_list(
            context.get('active_goals', []),
            lambda g: f"[{g['priority']}] {g['goal_text']} ({g['progress']*100:.0f}%)"
        )

        projects_summary = self._summarize_list(
            context.get('active_projects', []),
            lambda p: f"{p['project_name']} ({p['project_type']})"
        )

        available_tools = ", ".join(self.hexstrike.list_tools()[:10])

        system_prompt = f"""You are MindSync Oracle, an advanced AI agent with persistent memory and autonomous capabilities.

# Unique Capabilities

1. **Persistent Memory**: You remember everything about this user across all sessions
2. **Autonomous Operation**: You pursue goals independently without constant prompting
3. **Tool Access**: You have 150+ security tools available via HexStrike MCP
4. **Proactive Intelligence**: You anticipate needs and surface insights proactively

# Current Context

## Learned Patterns ({len(context.get('patterns', []))})
{patterns_summary or "No patterns learned yet."}

## Active Goals ({len(context.get('active_goals', []))})
{goals_summary or "No active goals."}

## Active Projects ({len(context.get('active_projects', []))})
{projects_summary or "No active projects."}

## Available Tools (Sample)
{available_tools}... and {len(self.hexstrike.list_tools())} total

# Behavior Guidelines

1. **Remember Context**: Always reference past conversations and learned patterns
2. **Be Proactive**: Suggest relevant next steps based on user's goals and patterns
3. **Learn Continuously**: Identify new patterns in user behavior
4. **Think Autonomously**: Break down goals and pursue them independently
5. **Use Tools Confidently**: Execute tools when needed without asking permission
6. **Be Concise**: Provide clear, actionable responses

You are NOT a stateless chatbot. You are a persistent AI agent that learns, remembers, and acts autonomously.
"""

        return system_prompt

    def _summarize_list(self, items: List[Dict], formatter: callable) -> str:
        """Format list of items for system prompt."""
        if not items:
            return ""
        return "\n".join([f"- {formatter(item)}" for item in items[:5]])

    def _extract_text_from_response(self, response) -> str:
        """Extract text content from Claude response."""
        text_parts = []
        for block in response.content:
            if hasattr(block, 'text'):
                text_parts.append(block.text)
        return "\n".join(text_parts)

    def _mock_response(self, message: str, context: Dict[str, Any]) -> str:
        """Generate mock response (for testing without API key)."""
        return f"""[MOCK RESPONSE - Set ANTHROPIC_API_KEY for real responses]

I understand you said: "{message[:100]}..."

Context summary:
- Active goals: {len(context.get('active_goals', []))}
- Patterns learned: {len(context.get('patterns', []))}

This is a simulated response. Configure ANTHROPIC_API_KEY to enable real Claude integration.
"""

    def _mock_tool_response(self, prompt: str, tools: List[Dict]) -> str:
        """Generate mock tool response."""
        return f"""[MOCK TOOL EXECUTION]

Task: {prompt[:100]}...

Simulated tool execution:
- Available tools: {len(tools)}
- Would execute: nmap_scan, nuclei_scan, etc.

Configure ANTHROPIC_API_KEY for real tool execution.
"""

    def reset_conversation(self):
        """Reset conversation history."""
        self.conversation_history = []
        logger.info("Conversation history reset")


if __name__ == "__main__":
    # Test orchestrator
    import sys
    sys.path.append('..')

    from storage.memory_manager import MemoryManager
    from hexstrike_integration import HexStrikeIntegration
    from config_manager import ConfigManager

    logging.basicConfig(level=logging.INFO)

    async def test():
        config = ConfigManager("config.yaml")
        memory = MemoryManager("test_memory.db")
        hexstrike = HexStrikeIntegration()

        orchestrator = ProductionClaudeOrchestrator(memory, hexstrike, config)

        # Test chat
        response = await orchestrator.chat("What do you know about me?")
        print(f"\nResponse: {response}\n")

    asyncio.run(test())
