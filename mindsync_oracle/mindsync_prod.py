#!/usr/bin/env python3
"""
MindSync Oracle - Production Main Entry Point

The complete, working AGI-like AI agent system.
This is the REAL production version that actually works.

Usage:
    python mindsync_prod.py                    # Interactive CLI
    python mindsync_prod.py --daemon           # Background daemon
    python mindsync_prod.py --goal "..."       # Add goal and exit
"""

import os
import sys
import asyncio
import argparse
import logging
from pathlib import Path
from typing import Optional
import signal

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import all components
from config_manager import ConfigManager
from storage.memory_manager import MemoryManager
from hexstrike_integration import HexStrikeIntegration
from notification_system import NotificationSystem
from scheduler import MindSyncScheduler
from services.agent_orchestrator_prod import ProductionClaudeOrchestrator
from agents.goal_engine_prod import ProductionGoalEngine
from interfaces.input_processor import MultiModalInputProcessor

# Import v2 and v3 enhancements
from self_improvement import SelfImprovementEngine
from adaptive_notifications import AdaptiveNotificationEngine
from tool_learning import ToolPerformanceTracker
from hybrid_memory_graph import HybridMemoryGraph

# Import v4 enhancements
from multi_llm_orchestrator import MultiLLMOrchestrator
from live_threat_feed import LiveThreatFeed

# Import v5 enhancements
from deep_x_nexus import DeepXNexus
from x_timeline_analyzer import XTimelineAnalyzer
from x_researcher_dossier import XResearcherDossier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mindsync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MindSyncOracleProduction:
    """
    Production MindSync Oracle system.

    The complete, working AGI-like agent with:
    - Persistent memory
    - Autonomous goal pursuit
    - Multi-modal input
    - Proactive intelligence
    - Background scheduling
    """

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the complete system."""
        logger.info("="*60)
        logger.info("MindSync Oracle - Production System")
        logger.info("="*60)

        # Load configuration
        self.config = ConfigManager(config_path)
        logger.info(f"✅ Configuration loaded")

        # Initialize persistent memory
        db_path = self.config.get('database.path', 'mindsync_memory.db')
        self.memory = MemoryManager(db_path)
        logger.info(f"✅ Memory system initialized ({db_path})")

        # Initialize HexStrike integration
        if self.config.hexstrike_enabled:
            self.hexstrike = HexStrikeIntegration(
                server_url=self.config.get('hexstrike.server_url')
            )
            logger.info(f"✅ HexStrike integration ({len(self.hexstrike.list_tools())} tools)")
        else:
            self.hexstrike = HexStrikeIntegration()  # No tools
            logger.info(f"⚠️  HexStrike disabled in config")

        # Initialize notification system
        notification_methods = self.config.get('notifications.methods', ['terminal'])
        self.notifier = NotificationSystem(enabled_methods=notification_methods)
        logger.info(f"✅ Notification system ({', '.join(notification_methods)})")

        # Initialize input processor
        self.input_processor = MultiModalInputProcessor(
            whisper_api_key=self.config.openai_key
        )
        logger.info(f"✅ Multi-modal input processor")

        # Initialize Claude orchestrator
        try:
            self.orchestrator = ProductionClaudeOrchestrator(
                self.memory,
                self.hexstrike,
                self.config
            )
            logger.info(f"✅ Claude orchestrator (model: {self.orchestrator.model})")
        except Exception as e:
            logger.error(f"Error initializing Claude orchestrator: {e}")
            logger.info("Running in limited mode without Claude integration")
            self.orchestrator = None

        # Note: Goal engine initialization moved after v2/v3 enhancements
        self.goal_engine = None  # Will be initialized after v2/v3 systems
        self.scheduler = None  # Will be initialized after goal engine

        # Initialize v2 and v3 enhancements
        logger.info("Initializing v2/v3 enhancements...")

        # v3: Hybrid Memory Graph
        graph_path = self.config.get('database.graph_path', 'mindsync_graph.pkl')
        self.memory_graph = HybridMemoryGraph(graph_path)
        logger.info(f"✅ Hybrid Memory Graph (v3) - {self.memory_graph.get_graph_stats()['total_nodes']} nodes")

        # v2: Tool Performance Tracker
        self.tool_tracker = ToolPerformanceTracker(self.memory)
        logger.info(f"✅ Tool Performance Tracker (v2)")

        # v2: Self-Improvement Engine
        if self.orchestrator:
            self.self_improvement = SelfImprovementEngine(self.memory, self.orchestrator)
            logger.info(f"✅ Self-Improvement Engine (v2)")
        else:
            self.self_improvement = None
            logger.warning("Self-improvement disabled (no Claude orchestrator)")

        # v2: Adaptive Notification Engine
        self.adaptive_notifier = AdaptiveNotificationEngine(
            self.notifier,
            self.memory,
            self.config
        )
        logger.info(f"✅ Adaptive Notification Engine (v2)")

        # Initialize goal engine with v2/v3 enhancements
        if self.orchestrator:
            self.goal_engine = ProductionGoalEngine(
                self.memory,
                self.orchestrator,
                self.notifier,
                tool_tracker=self.tool_tracker,
                self_improvement=self.self_improvement,
                adaptive_notifier=self.adaptive_notifier,
                memory_graph=self.memory_graph
            )
            logger.info(f"✅ Goal engine initialized (v2/v3 integrated)")
        else:
            logger.warning("Goal engine disabled (no Claude orchestrator)")

        # Re-initialize scheduler with goal engine now available
        if self.config.scheduler_enabled and self.goal_engine:
            self.scheduler = MindSyncScheduler(
                self.goal_engine,
                self.memory,
                self.notifier
            )
            logger.info(f"✅ Background scheduler (re-initialized)")

        # Initialize v4 enhancements
        logger.info("Initializing v4 multi-LLM orchestration...")

        # v4: Multi-LLM Orchestrator (Claude + Grok)
        if self.orchestrator:
            self.multi_llm = MultiLLMOrchestrator(
                self.config,
                self.orchestrator,
                self.memory_graph
            )
            logger.info(f"✅ Multi-LLM Orchestrator (v4) - Grok: {self.multi_llm.grok_enabled}")
        else:
            self.multi_llm = None
            logger.warning("Multi-LLM orchestrator disabled (no Claude orchestrator)")

        # v4: Live Threat Feed
        if self.multi_llm and self.config.get('threat_feed.enabled', False):
            self.threat_feed = LiveThreatFeed(
                self.multi_llm,
                self.memory_graph,
                self.goal_engine,
                self.config
            )
            logger.info(f"✅ Live Threat Feed (v4) - Sources: {len(self.threat_feed.sources)}")
        else:
            self.threat_feed = None
            if not self.config.get('threat_feed.enabled', False):
                logger.info("⚠️  Threat feed disabled in config")

        # Initialize v5 enhancements
        if self.multi_llm and self.config.get('deep_x.enabled', False):
            logger.info("Initializing v5 Deep X Intelligence Nexus...")

            # v5: Deep X Nexus (researcher graphs)
            self.deep_x = DeepXNexus(
                self.multi_llm,
                self.memory_graph,
                self.config
            )
            logger.info(f"✅ Deep X Nexus (v5) - X graph intelligence")

            # v5: Timeline Analyzer (temporal patterns)
            self.x_timeline = XTimelineAnalyzer(
                self.deep_x,
                self.config
            )
            logger.info(f"✅ X Timeline Analyzer (v5) - Surge detection")

            # v5: Researcher Dossier (influence profiling)
            self.x_dossier = XResearcherDossier(
                self.deep_x,
                self.x_timeline,
                self.config
            )
            logger.info(f"✅ X Researcher Dossier (v5) - Community profiling")
        else:
            self.deep_x = None
            self.x_timeline = None
            self.x_dossier = None
            if not self.config.get('deep_x.enabled', False):
                logger.info("⚠️  Deep X intelligence disabled in config")

        self.is_running = False
        logger.info("="*60)
        logger.info("🚀 MindSync Oracle v5 ready! (Omniscient X-Augmented AGI)")
        logger.info("="*60)

    async def start(self, daemon_mode: bool = False):
        """
        Start MindSync Oracle.

        Args:
            daemon_mode: Run in background with autonomous goal processing
        """
        self.is_running = True

        if daemon_mode and self.goal_engine:
            # Start autonomous goal processing
            self.goal_task = asyncio.create_task(
                self.goal_engine.start_autonomous_loop()
            )
            logger.info("🔄 Daemon mode: Autonomous goal processing active")

        if self.scheduler:
            self.scheduler.start()
            logger.info("📅 Background scheduler started")

        # Start threat feed if enabled
        if self.threat_feed:
            asyncio.create_task(self.threat_feed.start())
            logger.info("🔴 Live threat feed started")

    async def stop(self):
        """Stop MindSync Oracle."""
        logger.info("Stopping MindSync Oracle...")
        self.is_running = False

        if hasattr(self, 'goal_task'):
            await self.goal_engine.stop()

        if self.scheduler:
            self.scheduler.stop()

        if self.threat_feed:
            await self.threat_feed.stop()

        logger.info("MindSync Oracle stopped")

    # Core interaction methods

    async def chat(self, message: str) -> str:
        """
        Chat with the AI agent.

        Args:
            message: User message

        Returns:
            Agent response
        """
        if not self.orchestrator:
            return "Claude orchestrator not available. Please configure ANTHROPIC_API_KEY."

        # Process input
        event = self.input_processor.process_text(message)

        # Check if this looks like a goal statement
        if self._is_goal_statement(message) and self.goal_engine:
            # Extract priority
            priority = self._infer_priority(message)

            # Create goal
            goal_id = self.goal_engine.add_goal(message, priority=priority)

            return f"""Goal created (ID: {goal_id})

I'll work on this autonomously and notify you when complete.

Priority: {priority}
Status: Queued for execution

You can check progress anytime with: /goals
"""

        # Regular chat
        response = await self.orchestrator.chat(message)
        return response

    async def add_goal(self, goal_text: str, priority: str = "medium") -> int:
        """Add a goal for autonomous pursuit."""
        if not self.goal_engine:
            raise RuntimeError("Goal engine not available")

        return self.goal_engine.add_goal(goal_text, priority)

    def list_goals(self) -> list:
        """List all active goals."""
        if not self.goal_engine:
            return []

        return self.goal_engine.list_active_goals()

    def get_context(self) -> dict:
        """Get current context summary."""
        return self.memory.get_context_summary()

    def _is_goal_statement(self, text: str) -> bool:
        """Detect if input is a goal statement."""
        indicators = [
            "i need to", "i want to", "help me", "can you",
            "i'm working on", "my goal is", "i have to",
            "research", "analyze", "pentest", "scan", "test"
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in indicators)

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


# CLI Interface

class MindSyncCLI:
    """Interactive CLI for MindSync Oracle."""

    def __init__(self, oracle: MindSyncOracleProduction):
        self.oracle = oracle

    async def run(self):
        """Run interactive CLI."""
        print("\n" + "="*60)
        print("MindSync Oracle - Interactive Mode")
        print("="*60)
        print("\nCommands:")
        print("  /goals      - Show active goals")
        print("  /context    - Show current context summary")
        print("  /status     - Show system status")
        print("  /add-goal   - Add a new goal")
        print("  /help       - Show this help")
        print("  /quit       - Exit")
        print("="*60)
        print()

        while self.oracle.is_running:
            try:
                user_input = input("\n You: ").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input == "/quit":
                    break

                elif user_input == "/help":
                    self._show_help()

                elif user_input == "/goals":
                    self._show_goals()

                elif user_input == "/context":
                    self._show_context()

                elif user_input == "/status":
                    self._show_status()

                elif user_input == "/add-goal":
                    await self._add_goal_interactive()

                elif user_input.startswith("/"):
                    print(f"Unknown command: {user_input}. Type /help for commands.")

                else:
                    # Regular chat
                    response = await self.oracle.chat(user_input)
                    print(f"\n MindSync: {response}")

            except KeyboardInterrupt:
                print("\n\nExiting...")
                break

            except Exception as e:
                logger.error(f"Error in CLI: {e}", exc_info=True)
                print(f"\n Error: {e}")

    def _show_help(self):
        """Show help message."""
        print("""
MindSync Oracle Commands:

  /goals      - List all active goals with progress
  /context    - Show what I know about you (patterns, projects)
  /status     - Show system status
  /add-goal   - Interactively add a new goal
  /help       - Show this help
  /quit       - Exit MindSync

You can also just chat naturally, and I'll:
- Remember our conversations
- Learn your patterns
- Create goals automatically when appropriate
- Work on goals autonomously in the background
""")

    def _show_goals(self):
        """Show active goals."""
        goals = self.oracle.list_goals()

        if not goals:
            print("\n No active goals.")
            print(" Tip: Add a goal with /add-goal or just tell me what you need!")
            return

        print(f"\n Active Goals ({len(goals)}):\n")
        for goal in goals:
            status_emoji = "🔄" if goal['status'] == "in_progress" else "⏳"
            print(f"  {status_emoji} [{goal['priority'].upper()}] {goal['goal_text']}")
            print(f"     Progress: {goal['progress']*100:.0f}% | Status: {goal['status']}")
            print()

    def _show_context(self):
        """Show context summary."""
        context = self.oracle.get_context()

        print("\n Context Summary:\n")
        print(f"  Patterns Learned: {len(context.get('patterns', []))}")
        print(f"  Active Goals: {len(context.get('active_goals', []))}")
        print(f"  Active Projects: {len(context.get('active_projects', []))}")
        print(f"  Total Conversations: {context.get('statistics', {}).get('total_conversations', 0)}")
        print(f"  Goals Completed: {context.get('statistics', {}).get('completed_goals', 0)}")

        # Show top patterns
        patterns = context.get('patterns', [])
        if patterns:
            print(f"\n  Top Patterns:")
            for p in patterns[:3]:
                print(f"    - {p['pattern_type']}: {p['pattern_data']} ({p['confidence']*100:.0f}%)")

    def _show_status(self):
        """Show system status."""
        print("\n System Status:\n")
        print(f"  Claude Orchestrator: {'✅ Active' if self.oracle.orchestrator else '❌ Inactive'}")
        print(f"  Goal Engine: {'✅ Active' if self.oracle.goal_engine else '❌ Inactive'}")
        print(f"  HexStrike Tools: {'✅ ' + str(len(self.oracle.hexstrike.list_tools())) + ' tools' if self.oracle.hexstrike else '❌ Inactive'}")
        print(f"  Scheduler: {'✅ Active' if self.oracle.scheduler else '❌ Inactive'}")
        print(f"  Memory DB: {self.oracle.config.get('database.path')}")

    async def _add_goal_interactive(self):
        """Add goal interactively."""
        print("\n Add New Goal:\n")
        goal_text = input(" Goal: ").strip()

        if not goal_text:
            print(" Cancelled.")
            return

        print("\n Priority (low/medium/high/critical) [medium]: ", end="")
        priority = input().strip() or "medium"

        if priority not in ["low", "medium", "high", "critical"]:
            priority = "medium"

        try:
            goal_id = await self.oracle.add_goal(goal_text, priority)
            print(f"\n ✅ Goal {goal_id} created and queued for autonomous execution!")
        except Exception as e:
            print(f"\n ❌ Error creating goal: {e}")


# Main entry point

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="MindSync Oracle - AGI-like AI Agent with Persistent Memory"
    )

    parser.add_argument("--daemon", action="store_true",
                       help="Run in daemon mode (background goal processing)")

    parser.add_argument("--goal", type=str,
                       help="Add a goal and exit")

    parser.add_argument("--priority", type=str, default="medium",
                       choices=["low", "medium", "high", "critical"],
                       help="Priority for --goal")

    parser.add_argument("--config", type=str, default="config.yaml",
                       help="Path to config file")

    parser.add_argument("--debug", action="store_true",
                       help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize MindSync Oracle
    oracle = MindSyncOracleProduction(config_path=args.config)

    # Handle --goal flag (add goal and exit)
    if args.goal:
        await oracle.start(daemon_mode=False)
        goal_id = await oracle.add_goal(args.goal, priority=args.priority)
        print(f"Goal {goal_id} created: {args.goal}")
        await oracle.stop()
        return

    # Start oracle
    await oracle.start(daemon_mode=args.daemon)

    # Handle signals for graceful shutdown
    def signal_handler(sig, frame):
        print("\n\nShutting down...")
        asyncio.create_task(oracle.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run CLI
    cli = MindSyncCLI(oracle)

    try:
        if args.daemon:
            print("Daemon mode: Press Ctrl+C to stop")
            while oracle.is_running:
                await asyncio.sleep(1)
        else:
            await cli.run()

    finally:
        await oracle.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
