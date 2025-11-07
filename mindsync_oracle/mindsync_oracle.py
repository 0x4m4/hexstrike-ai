#!/usr/bin/env python3
"""
MindSync Oracle - Main Orchestrator

The complete AGI-like system:
- Persistent memory across sessions
- Goal-directed autonomy
- Multi-modal input
- Proactive intelligence

This is what bridges the gap from "smart chatbot" to "Jarvis".
"""

import os
import sys
import asyncio
import argparse
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from mindsync_oracle.storage.memory_manager import MemoryManager
from mindsync_oracle.services.agent_orchestrator import ClaudeAgentOrchestrator
from mindsync_oracle.agents.goal_engine import GoalDirectedEngine
from mindsync_oracle.interfaces.input_processor import MultiModalInputProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MindSyncOracle:
    """
    Main MindSync Oracle system.

    Combines:
    - Persistent memory (MemoryManager)
    - Claude Agent SDK (AgentOrchestrator)
    - Goal-directed autonomy (GoalEngine)
    - Multi-modal input (InputProcessor)

    The result: An AI that remembers you, learns your patterns,
    pursues goals autonomously, and thinks proactively.
    """

    def __init__(self,
                 db_path: str = "mindsync_memory.db",
                 anthropic_api_key: Optional[str] = None,
                 openai_api_key: Optional[str] = None):
        """
        Initialize MindSync Oracle.

        Args:
            db_path: Path to SQLite database for persistent memory
            anthropic_api_key: Anthropic API key for Claude
            openai_api_key: OpenAI API key for Whisper (optional)
        """
        logger.info("🧠 Initializing MindSync Oracle...")

        # Initialize components
        self.memory = MemoryManager(db_path)
        logger.info("✅ Memory system initialized")

        self.input_processor = MultiModalInputProcessor(whisper_api_key=openai_api_key)
        logger.info("✅ Input processor initialized")

        # TODO: Load MCP tools (e.g., from HexStrike)
        mcp_tools = self._load_mcp_tools()

        self.orchestrator = ClaudeAgentOrchestrator(
            self.memory,
            mcp_tools=mcp_tools,
            api_key=anthropic_api_key
        )
        logger.info("✅ Claude orchestrator initialized")

        self.goal_engine = GoalDirectedEngine(self.memory, self.orchestrator)
        logger.info("✅ Goal engine initialized")

        self.is_running = False

        logger.info("🚀 MindSync Oracle fully initialized")

    def _load_mcp_tools(self) -> Dict[str, Any]:
        """
        Load MCP tools for agent use.

        In production, this would connect to HexStrike MCP server
        and register all available tools.
        """
        # TODO: Integrate with HexStrike MCP
        # For now, return empty dict
        logger.info("MCP tools loading... (TODO: integrate HexStrike)")
        return {}

    # ===== CORE METHODS =====

    async def start(self, daemon_mode: bool = False):
        """
        Start MindSync Oracle.

        Args:
            daemon_mode: If True, run goal engine in background
        """
        self.is_running = True
        logger.info("🎯 MindSync Oracle started")

        if daemon_mode:
            # Start goal engine in background
            self.goal_task = asyncio.create_task(self.goal_engine.start())
            logger.info("🔄 Daemon mode: Goal engine running in background")

    async def stop(self):
        """Stop MindSync Oracle."""
        self.is_running = False

        if hasattr(self, 'goal_task'):
            await self.goal_engine.stop()
            await self.goal_task

        logger.info("🛑 MindSync Oracle stopped")

    async def process_input(self, input_text: str,
                           input_type: str = "text",
                           metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Process an input and generate response.

        Args:
            input_text: Input content
            input_type: Type of input ('text', 'voice', 'file', etc.)
            metadata: Optional metadata

        Returns:
            Agent response
        """
        # Create input event
        if input_type == "text":
            event = self.input_processor.process_text(input_text, metadata)
        elif input_type == "voice":
            event = self.input_processor.process_voice(input_text, metadata)
        elif input_type == "file":
            event = self.input_processor.process_file(input_text, metadata)
        else:
            event = self.input_processor.process_text(input_text, metadata)

        # Format for agent
        formatted_input = self.input_processor.format_for_agent(event)

        # Process with orchestrator
        response = await self.orchestrator.chat(formatted_input)

        # Check if response indicates a new goal
        if self._is_goal_statement(input_text):
            # Extract and create goal
            goal_id = self.goal_engine.add_goal(
                input_text,
                priority=self._infer_priority(input_text),
                context=metadata
            )
            logger.info(f"Created goal {goal_id} from input")

        return response

    def _is_goal_statement(self, text: str) -> bool:
        """Detect if input is a goal statement."""
        goal_indicators = [
            "i need to", "i want to", "help me", "can you",
            "i'm working on", "my goal is", "i have to"
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in goal_indicators)

    def _infer_priority(self, text: str) -> str:
        """Infer goal priority from text."""
        text_lower = text.lower()
        if any(word in text_lower for word in ["urgent", "asap", "critical", "immediately"]):
            return "critical"
        elif any(word in text_lower for word in ["important", "high priority", "soon"]):
            return "high"
        elif any(word in text_lower for word in ["later", "eventually", "sometime"]):
            return "low"
        else:
            return "medium"

    # ===== PUBLIC API =====

    async def chat(self, message: str) -> str:
        """
        Simple chat interface.

        Args:
            message: User message

        Returns:
            Agent response
        """
        return await self.process_input(message, input_type="text")

    async def voice_input(self, audio_file: str) -> str:
        """
        Process voice input.

        Args:
            audio_file: Path to audio file

        Returns:
            Agent response
        """
        return await self.process_input(audio_file, input_type="voice")

    async def file_input(self, file_path: str) -> str:
        """
        Process file input.

        Args:
            file_path: Path to file

        Returns:
            Agent response
        """
        return await self.process_input(file_path, input_type="file")

    def add_goal(self, goal_text: str, priority: str = "medium") -> int:
        """
        Add a goal for autonomous pursuit.

        Args:
            goal_text: Goal description
            priority: Priority level

        Returns:
            Goal ID
        """
        return self.goal_engine.add_goal(goal_text, priority)

    def get_context(self) -> Dict[str, Any]:
        """Get current context summary."""
        return self.memory.get_context_summary()

    def get_active_goals(self) -> list:
        """Get all active goals."""
        return self.memory.get_active_goals()


# ===== CLI INTERFACE =====

async def cli_mode(oracle: MindSyncOracle):
    """Interactive CLI mode."""
    print("=" * 60)
    print("MindSync Oracle - CLI Mode")
    print("=" * 60)
    print("Commands:")
    print("  /goals     - Show active goals")
    print("  /context   - Show current context")
    print("  /quit      - Exit")
    print("=" * 60)
    print()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input == "/quit":
                break

            if user_input == "/goals":
                goals = oracle.get_active_goals()
                if goals:
                    print("\nActive Goals:")
                    for goal in goals:
                        print(f"  [{goal['priority']}] {goal['goal_text']} - {goal['progress']*100:.0f}%")
                else:
                    print("No active goals")
                print()
                continue

            if user_input == "/context":
                context = oracle.get_context()
                print(f"\nContext Summary:")
                print(f"  Patterns: {len(context.get('patterns', []))}")
                print(f"  Active Goals: {len(context.get('active_goals', []))}")
                print(f"  Conversations: {context.get('statistics', {}).get('total_conversations', 0)}")
                print()
                continue

            # Process input
            response = await oracle.chat(user_input)
            print(f"\nMindSync: {response}\n")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            print(f"Error: {e}\n")


async def daemon_mode(oracle: MindSyncOracle):
    """Daemon mode - background goal processing."""
    print("🔄 Daemon mode activated - goal engine running in background")
    print("Press Ctrl+C to stop")

    try:
        await oracle.start(daemon_mode=True)

        # Keep running until interrupted
        while oracle.is_running:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping daemon...")
        await oracle.stop()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="MindSync Oracle - AGI-like AI Agent")

    parser.add_argument("--mode", choices=["cli", "daemon", "hybrid"],
                       default="cli", help="Operation mode")

    parser.add_argument("--db", default="mindsync_memory.db",
                       help="Path to memory database")

    parser.add_argument("--debug", action="store_true",
                       help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize oracle
    oracle = MindSyncOracle(db_path=args.db)

    # Run in selected mode
    if args.mode == "cli":
        await oracle.start(daemon_mode=False)
        await cli_mode(oracle)
        await oracle.stop()

    elif args.mode == "daemon":
        await daemon_mode(oracle)

    elif args.mode == "hybrid":
        # Start daemon in background
        await oracle.start(daemon_mode=True)
        # Run CLI in foreground
        await cli_mode(oracle)
        await oracle.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
