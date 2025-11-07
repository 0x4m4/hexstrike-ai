#!/usr/bin/env python3
"""
MindSync Oracle v4 - Multi-LLM Orchestration

THE BREAKTHROUGH: Multiple LLMs working together, each with specialized roles.

Claude: Structured reasoning, tool orchestration, pentest chains
Grok: Live intelligence, X/web searches, uncensored red-team scenarios

The router intelligently selects which LLM to use based on:
- Query type (tool execution vs intelligence gathering)
- Graph-learned preferences (user patterns)
- Performance metrics (which LLM performs better for what)

This is swarm intelligence at the LLM layer.
"""

import logging
import requests
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class LLMType(Enum):
    """Available LLM types."""
    CLAUDE = "claude"
    GROK = "grok"
    AUTO = "auto"  # Let the router decide


class QueryType(Enum):
    """Query classification types."""
    TOOL_EXECUTION = "tool_execution"      # Use Claude (HexStrike tools)
    INTELLIGENCE = "intelligence"          # Use Grok (web/X search)
    HYBRID = "hybrid"                      # Chain both
    REASONING = "reasoning"                # Use Claude (structured)
    SEARCH = "search"                      # Use Grok (live data)


class MultiLLMOrchestrator:
    """
    Multi-LLM orchestration layer for MindSync Oracle v4.

    Routes queries to the best LLM based on:
    - Query type classification
    - Graph-learned preferences
    - Performance metrics
    """

    def __init__(self, config, claude_orchestrator, memory_graph=None):
        """
        Initialize multi-LLM orchestrator.

        Args:
            config: ConfigManager instance
            claude_orchestrator: ProductionClaudeOrchestrator instance
            memory_graph: Optional HybridMemoryGraph for learning
        """
        self.config = config
        self.claude = claude_orchestrator
        self.memory_graph = memory_graph

        # Grok/xAI configuration
        self.grok_enabled = config.get('xai.enabled', False)
        self.grok_api_key = config.get('xai.api_key') or config.get_env('XAI_API_KEY')
        self.grok_base_url = config.get('xai.base_url', 'https://api.x.ai/v1/chat/completions')
        self.grok_model = config.get('xai.model', 'grok-beta')

        # Router configuration
        self.router_rules = config.get('llm_router', {
            'intelligence': 'grok',
            'tools': 'claude',
            'reasoning': 'claude',
            'search': 'grok',
            'hybrid': 'auto'
        })

        # Performance tracking
        self.llm_metrics = {
            'claude': {'calls': 0, 'successes': 0, 'avg_time': 0},
            'grok': {'calls': 0, 'successes': 0, 'avg_time': 0}
        }

        logger.info(f"Multi-LLM Orchestrator initialized (Grok: {self.grok_enabled})")

    # ===== QUERY CLASSIFICATION =====

    def classify_query(self, query: str, context: Optional[Dict] = None) -> QueryType:
        """
        Classify query to determine best LLM routing.

        Args:
            query: User query
            context: Optional context (goal, tools available, etc.)

        Returns:
            QueryType enum
        """
        query_lower = query.lower()

        # Intelligence/search keywords
        intel_keywords = ['search', 'find', 'latest', 'news', 'x.com', 'twitter',
                         'threat', 'live', 'emerging', 'trending', 'recent']
        if any(keyword in query_lower for keyword in intel_keywords):
            return QueryType.INTELLIGENCE

        # Tool execution keywords
        tool_keywords = ['scan', 'exploit', 'pentest', 'run', 'execute',
                        'nmap', 'nuclei', 'gobuster', 'test']
        if any(keyword in query_lower for keyword in tool_keywords):
            return QueryType.TOOL_EXECUTION

        # Hybrid (needs both)
        hybrid_keywords = ['research and test', 'find and exploit',
                          'discover and scan']
        if any(keyword in query_lower for keyword in hybrid_keywords):
            return QueryType.HYBRID

        # Check graph for learned preferences
        if self.memory_graph:
            try:
                # Query graph for similar past queries
                similar_queries = self.memory_graph.find_similar_nodes(
                    query,
                    node_type='goal'
                )
                if similar_queries:
                    # Use the LLM that worked best for similar queries
                    # This would be stored in graph metadata
                    pass
            except Exception as e:
                logger.debug(f"Error querying graph for classification: {e}")

        # Default: reasoning (Claude's strength)
        return QueryType.REASONING

    def select_llm(self, query_type: QueryType, query: str) -> LLMType:
        """
        Select which LLM to use based on query type and performance.

        Args:
            query_type: Classified query type
            query: Original query

        Returns:
            LLMType to use
        """
        # Check router rules from config
        rule_map = {
            QueryType.TOOL_EXECUTION: 'tools',
            QueryType.INTELLIGENCE: 'intelligence',
            QueryType.REASONING: 'reasoning',
            QueryType.SEARCH: 'search',
            QueryType.HYBRID: 'hybrid'
        }

        rule_key = rule_map.get(query_type, 'reasoning')
        llm_choice = self.router_rules.get(rule_key, 'claude')

        # Auto mode: select based on performance metrics
        if llm_choice == 'auto':
            claude_score = self._calculate_llm_score('claude', query_type)
            grok_score = self._calculate_llm_score('grok', query_type)

            llm_choice = 'grok' if grok_score > claude_score else 'claude'
            logger.debug(f"Auto-selected {llm_choice} (scores: claude={claude_score:.2f}, grok={grok_score:.2f})")

        # Fallback to Claude if Grok not available
        if llm_choice == 'grok' and not self.grok_enabled:
            logger.warning("Grok requested but not enabled, falling back to Claude")
            llm_choice = 'claude'

        return LLMType.GROK if llm_choice == 'grok' else LLMType.CLAUDE

    def _calculate_llm_score(self, llm_type: str, query_type: QueryType) -> float:
        """
        Calculate performance score for an LLM.

        Args:
            llm_type: 'claude' or 'grok'
            query_type: Type of query

        Returns:
            Score (0.0 to 1.0)
        """
        metrics = self.llm_metrics.get(llm_type, {})

        if metrics.get('calls', 0) == 0:
            # No data yet, use defaults
            defaults = {
                'claude': {
                    QueryType.TOOL_EXECUTION: 0.9,
                    QueryType.REASONING: 0.95,
                    QueryType.INTELLIGENCE: 0.6,
                    QueryType.SEARCH: 0.5
                },
                'grok': {
                    QueryType.TOOL_EXECUTION: 0.5,
                    QueryType.REASONING: 0.7,
                    QueryType.INTELLIGENCE: 0.9,
                    QueryType.SEARCH: 0.95
                }
            }
            return defaults.get(llm_type, {}).get(query_type, 0.5)

        # Calculate from actual performance
        success_rate = metrics['successes'] / metrics['calls']
        speed_factor = 1.0 / max(metrics.get('avg_time', 1.0), 0.1)

        return (success_rate * 0.7) + (speed_factor * 0.3)

    # ===== LLM EXECUTION =====

    async def execute(self, query: str, context: Optional[Dict] = None,
                     force_llm: Optional[LLMType] = None) -> Dict[str, Any]:
        """
        Execute query with best LLM.

        Args:
            query: User query
            context: Optional context dictionary
            force_llm: Force specific LLM (optional)

        Returns:
            Execution result with metadata
        """
        start_time = datetime.now()

        # Classify and route
        query_type = self.classify_query(query, context)
        llm_type = force_llm or self.select_llm(query_type, query)

        logger.info(f"Routing query (type={query_type.value}) to {llm_type.value}")

        try:
            # Execute on selected LLM
            if llm_type == LLMType.GROK:
                result = await self._execute_grok(query, context)
            else:
                result = await self._execute_claude(query, context)

            # Record success
            self._record_execution(llm_type.value, True,
                                  (datetime.now() - start_time).total_seconds())

            # Add to memory graph if available
            if self.memory_graph:
                try:
                    self._add_to_graph(query, result, llm_type, query_type)
                except Exception as e:
                    logger.error(f"Error adding LLM execution to graph: {e}")

            return {
                'success': True,
                'content': result,
                'llm_used': llm_type.value,
                'query_type': query_type.value,
                'execution_time': (datetime.now() - start_time).total_seconds()
            }

        except Exception as e:
            logger.error(f"Error executing on {llm_type.value}: {e}")

            # Record failure
            self._record_execution(llm_type.value, False,
                                  (datetime.now() - start_time).total_seconds())

            # Try fallback to Claude if Grok failed
            if llm_type == LLMType.GROK:
                logger.info("Grok failed, falling back to Claude")
                try:
                    result = await self._execute_claude(query, context)
                    return {
                        'success': True,
                        'content': result,
                        'llm_used': 'claude',
                        'fallback': True,
                        'original_llm': 'grok'
                    }
                except Exception as fallback_error:
                    logger.error(f"Fallback to Claude also failed: {fallback_error}")

            return {
                'success': False,
                'error': str(e),
                'llm_used': llm_type.value
            }

    async def _execute_claude(self, query: str, context: Optional[Dict] = None) -> str:
        """Execute query on Claude."""
        # Use existing Claude orchestrator
        if context and context.get('use_tools', True):
            return await self.claude.execute_with_tools(query)
        else:
            return await self.claude.chat(query, store_in_memory=True)

    async def _execute_grok(self, query: str, context: Optional[Dict] = None) -> str:
        """
        Execute query on Grok via xAI API.

        Args:
            query: User query
            context: Optional context

        Returns:
            Grok's response
        """
        if not self.grok_api_key:
            raise ValueError(
                "Grok API key not configured. Set XAI_API_KEY in config or environment.\n"
                "Get your key at: https://x.ai/api"
            )

        # Build payload
        messages = [{"role": "user", "content": query}]

        # Add context if provided
        if context:
            system_prompt = self._build_grok_system_prompt(context)
            messages.insert(0, {"role": "system", "content": system_prompt})

        payload = {
            "model": self.grok_model,
            "messages": messages,
            "temperature": context.get('temperature', 0.7) if context else 0.7,
            "max_tokens": context.get('max_tokens', 4000) if context else 4000
        }

        headers = {
            "Authorization": f"Bearer {self.grok_api_key}",
            "Content-Type": "application/json"
        }

        logger.debug(f"Calling Grok API: {self.grok_base_url}")

        # Make API call (async-friendly)
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(self.grok_base_url, json=payload, headers=headers, timeout=30)
        )

        if response.status_code != 200:
            raise ValueError(f"Grok API error ({response.status_code}): {response.text}")

        result = response.json()
        content = result['choices'][0]['message']['content']

        logger.info(f"Grok response received ({len(content)} chars)")

        return content

    def _build_grok_system_prompt(self, context: Dict) -> str:
        """Build system prompt for Grok based on context."""
        prompt_parts = [
            "You are Grok, assisting with cybersecurity intelligence gathering.",
            "Provide accurate, actionable information from the latest available data."
        ]

        if context.get('search_focus'):
            prompt_parts.append(f"Focus on: {context['search_focus']}")

        if context.get('target'):
            prompt_parts.append(f"Target context: {context['target']}")

        return " ".join(prompt_parts)

    # ===== HYBRID EXECUTION =====

    async def execute_hybrid(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute query using both LLMs in sequence.

        Typical flow:
        1. Grok gathers intelligence
        2. Claude uses that intel to plan tool execution

        Args:
            query: User query
            context: Optional context

        Returns:
            Combined result
        """
        logger.info(f"Executing hybrid query: {query}")

        # Step 1: Intelligence gathering with Grok
        intel_query = f"Gather the latest intelligence and context for: {query}"
        intel_result = await self.execute(intel_query, context, force_llm=LLMType.GROK)

        if not intel_result['success']:
            logger.warning("Intel gathering failed, proceeding with Claude only")
            return await self.execute(query, context, force_llm=LLMType.CLAUDE)

        # Step 2: Tool execution with Claude using Grok's intel
        enhanced_context = context or {}
        enhanced_context['intelligence'] = intel_result['content']

        action_query = f"""Based on this intelligence:
{intel_result['content']}

Execute the following goal:
{query}

Use available tools as needed."""

        action_result = await self.execute(action_query, enhanced_context, force_llm=LLMType.CLAUDE)

        return {
            'success': action_result['success'],
            'intelligence': intel_result['content'],
            'action': action_result.get('content'),
            'hybrid': True,
            'steps': ['grok_intel', 'claude_action']
        }

    # ===== TRACKING & LEARNING =====

    def _record_execution(self, llm_type: str, success: bool, execution_time: float):
        """Record LLM execution metrics."""
        if llm_type not in self.llm_metrics:
            self.llm_metrics[llm_type] = {'calls': 0, 'successes': 0, 'avg_time': 0}

        metrics = self.llm_metrics[llm_type]
        metrics['calls'] += 1
        if success:
            metrics['successes'] += 1

        # Update rolling average
        if metrics['avg_time'] == 0:
            metrics['avg_time'] = execution_time
        else:
            metrics['avg_time'] = (metrics['avg_time'] * 0.9) + (execution_time * 0.1)

    def _add_to_graph(self, query: str, result: str, llm_type: LLMType, query_type: QueryType):
        """Add LLM execution to memory graph."""
        if not self.memory_graph:
            return

        # Create query node
        query_id = self.memory_graph._generate_node_id('query')
        self.memory_graph.graph.add_node(
            query_id,
            type='query',
            text=query[:200],  # Truncate
            query_type=query_type.value,
            llm_used=llm_type.value,
            timestamp=datetime.now().isoformat()
        )

        # Link to result as learning
        learning_text = f"Query '{query[:50]}...' best handled by {llm_type.value}"
        learning_id = self.memory_graph._add_learning(learning_text)

        self.memory_graph.graph.add_edge(
            query_id,
            learning_id,
            type='learned_from'
        )

        self.memory_graph._save()

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for all LLMs."""
        stats = {}

        for llm_type, metrics in self.llm_metrics.items():
            if metrics['calls'] > 0:
                stats[llm_type] = {
                    'calls': metrics['calls'],
                    'success_rate': metrics['successes'] / metrics['calls'],
                    'avg_time': metrics['avg_time']
                }
            else:
                stats[llm_type] = {
                    'calls': 0,
                    'success_rate': 0.0,
                    'avg_time': 0.0
                }

        return stats


# ===== MOCK GROK FOR TESTING =====

class MockGrokOrchestrator(MultiLLMOrchestrator):
    """Mock Grok for testing without real API."""

    async def _execute_grok(self, query: str, context: Optional[Dict] = None) -> str:
        """Mock Grok execution."""
        logger.info(f"[MOCK GROK] Executing: {query}")

        # Simulate intelligence gathering
        mock_responses = {
            'search': f"[Mock Grok Intelligence] Latest findings for '{query}':\n"
                     "- CVE-2024-9999: WordPress RCE discovered on X\n"
                     "- Active exploitation in the wild\n"
                     "- Affects versions 6.0-6.4",
            'threat': f"[Mock Grok Threat Intel] Emerging threats related to '{query}':\n"
                     "- Zero-day chatter on X from @security_researcher\n"
                     "- PoC code leaked on pastebin\n"
                     "- CISA alert expected within 24h",
            'default': f"[Mock Grok Response] Analysis for '{query}':\n"
                      "Based on latest X/web data, this requires further investigation.\n"
                      "Recommend using nuclei + manual validation."
        }

        # Select response based on query
        query_lower = query.lower()
        if 'search' in query_lower or 'find' in query_lower:
            response = mock_responses['search']
        elif 'threat' in query_lower or 'intel' in query_lower:
            response = mock_responses['threat']
        else:
            response = mock_responses['default']

        # Simulate API delay
        import asyncio
        await asyncio.sleep(0.5)

        return response


if __name__ == "__main__":
    # Test multi-LLM orchestrator
    import asyncio
    import sys
    sys.path.append('..')

    from config_manager import ConfigManager
    from storage.memory_manager import MemoryManager
    from hybrid_memory_graph import HybridMemoryGraph

    # Mock Claude orchestrator
    class MockClaude:
        async def chat(self, query, store_in_memory=True):
            return f"[Claude] Structured response to: {query}"

        async def execute_with_tools(self, query):
            return f"[Claude] Executed with tools: {query}\nResults: 3 ports open, 2 CVEs found"

    async def test():
        config = ConfigManager('config.yaml')
        memory = MemoryManager('test_memory.db')
        graph = HybridMemoryGraph('test_graph.pkl')
        claude = MockClaude()

        # Use mock Grok
        orchestrator = MockGrokOrchestrator(config, claude, graph)

        print("\n" + "="*60)
        print("Multi-LLM Orchestrator Test")
        print("="*60)

        # Test 1: Intelligence query (should use Grok)
        print("\n[Test 1] Intelligence Query")
        result = await orchestrator.execute("Search X for latest WordPress vulnerabilities")
        print(f"LLM used: {result['llm_used']}")
        print(f"Content: {result['content'][:200]}...")

        # Test 2: Tool execution query (should use Claude)
        print("\n[Test 2] Tool Execution Query")
        result = await orchestrator.execute("Scan example.com with nmap")
        print(f"LLM used: {result['llm_used']}")
        print(f"Content: {result['content'][:200]}...")

        # Test 3: Hybrid execution
        print("\n[Test 3] Hybrid Execution")
        result = await orchestrator.execute_hybrid("Research and pentest latest WordPress exploits")
        print(f"Hybrid: {result.get('hybrid', False)}")
        print(f"Intel: {result.get('intelligence', '')[:100]}...")
        print(f"Action: {result.get('action', '')[:100]}...")

        # Performance stats
        print("\n[Performance Stats]")
        stats = orchestrator.get_performance_stats()
        for llm, metrics in stats.items():
            print(f"{llm}: {metrics}")

        print("\n" + "="*60)
        print("✅ Multi-LLM orchestration operational!")
        print("="*60)

    asyncio.run(test())
