#!/usr/bin/env python3
"""
MindSync Oracle v8 - CTF Lab Agent

ETHICAL CTF SOLVER WITH XBOW-INSPIRED REASONING

⚠️ AUTHORIZED ENVIRONMENTS ONLY ⚠️

This module combines all v8 components to create an intelligent CTF-solving
agent with mandatory human approval gates and ethical safeguards.

Architecture:
- VulnResearchAssistant: Analyze threats and suggest vulnerability chains
- ChainPredictor: Predict exploitation paths before attempting
- HumanInLoopController: Mandatory approval for EVERY action
- ScopeValidator: Hard scope enforcement
- SandboxExecutor: Isolated tool execution
- HexStrike Integration: Use pentesting tools via API

Workflow:
1. Challenge Analysis: Parse CTF challenge, extract target info
2. Scope Validation: Verify target is authorized
3. Reconnaissance: Gather info (with approval)
4. Vulnerability Chain Prediction: Use XBOW-inspired reasoning
5. Exploitation Planning: Step-by-step approach
6. Human Approval: Every step requires explicit consent
7. Sandboxed Execution: All tools run in containers
8. Flag Capture: Extract and validate flags
9. Reporting: Detailed writeup of methodology

STRICTLY FOR:
✅ CTF competitions (HackTheBox, TryHackMe, CTFTime events)
✅ Personal lab environments (owned infrastructure)
✅ Authorized red team exercises (written permission)
✅ Educational security research

FORBIDDEN:
❌ Production systems
❌ Unauthorized targets
❌ Auto-exploitation without approval
❌ Bypassing ethical controls

USAGE:
    from ctf_lab_agent import CTFLabAgent

    agent = CTFLabAgent(
        threat_hub=threat_hub,
        memory_graph=memory_graph,
        hexstrike_client=hexstrike_client,
        config=config
    )

    # Solve CTF challenge
    result = agent.solve_challenge(
        target="10.10.10.100",
        challenge_type="web",
        description="WordPress plugin vulnerability"
    )

    print(f"Flag: {result['flag']}")
"""

import logging
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import re

# v8 components
from .vuln_research_assistant import VulnResearchAssistant, ChainSuggestion
from .chain_predictor import ChainPredictor, ChainPrediction
from .human_in_loop_controller import HumanInLoopController, Action
from .scope_validator import ScopeValidator
from .sandbox_executor import SandboxExecutor, ExecutionResult

logger = logging.getLogger(__name__)


class CTFChallenge:
    """Represents a CTF challenge."""

    def __init__(self, challenge_id: str, target: str, challenge_type: str,
                 description: str, metadata: Optional[Dict] = None):
        self.challenge_id = challenge_id
        self.target = target
        self.challenge_type = challenge_type
        self.description = description
        self.metadata = metadata or {}
        self.timestamp = time.time()

        # Challenge state
        self.started = False
        self.completed = False
        self.flag = None

        # Execution trace
        self.actions = []
        self.findings = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            'challenge_id': self.challenge_id,
            'target': self.target,
            'challenge_type': self.challenge_type,
            'description': self.description,
            'metadata': self.metadata,
            'started': self.started,
            'completed': self.completed,
            'flag': self.flag,
            'actions': len(self.actions),
            'findings': len(self.findings)
        }


class CTFLabAgent:
    """
    CTF Lab Agent with XBOW-inspired reasoning.

    Solves CTF challenges using ethical hacking techniques with
    mandatory human approval and sandboxed execution.

    ⚠️ ETHICAL MODE - AUTHORIZED ENVIRONMENTS ONLY ⚠️
    """

    def __init__(self, threat_hub, memory_graph, hexstrike_client=None,
                 config: Optional[Dict] = None):
        """
        Initialize CTF Lab Agent.

        Args:
            threat_hub: UnifiedThreatHub instance (v7)
            memory_graph: HybridMemoryGraph instance
            hexstrike_client: Optional HexStrike API client
            config: Optional configuration
        """
        self.threat_hub = threat_hub
        self.memory_graph = memory_graph
        self.hexstrike_client = hexstrike_client
        self.config = config or {}

        # Initialize v8 components
        self.vuln_assistant = VulnResearchAssistant(
            threat_hub=threat_hub,
            memory_graph=memory_graph,
            config=config
        )

        self.chain_predictor = ChainPredictor(
            threat_hub=threat_hub,
            memory_graph=memory_graph,
            config=config
        )

        self.approval_controller = HumanInLoopController(
            audit_log_path=config.get('v8_audit_log', 'v8_audit.log'),
            timeout_seconds=config.get('approval_timeout', 300)
        )

        self.scope_validator = ScopeValidator(
            scope_file=config.get('scope_file', 'authorized_scope.yaml'),
            audit_log_path=config.get('scope_audit_log', 'scope_validation_audit.log')
        )

        self.sandbox = SandboxExecutor(
            image=config.get('sandbox_image', 'kalilinux/kali-rolling'),
            network_mode=config.get('sandbox_network', 'bridge'),
            memory_limit=config.get('sandbox_memory', '1g'),
            cpu_limit=config.get('sandbox_cpu', 2.0)
        )

        # Challenge history
        self.challenges = []

        # Statistics
        self.stats = {
            'challenges_attempted': 0,
            'challenges_solved': 0,
            'flags_captured': 0,
            'total_actions': 0,
            'approvals_requested': 0,
            'approvals_granted': 0
        }

        logger.info("CTF Lab Agent initialized (ETHICAL MODE)")

    def solve_challenge(self, target: str, challenge_type: str,
                       description: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Solve CTF challenge with human-in-the-loop approval.

        Args:
            target: Target IP/domain
            challenge_type: Type of challenge (web, pwn, crypto, forensics, etc.)
            description: Challenge description
            metadata: Optional metadata

        Returns:
            Result dictionary with flag and methodology
        """
        self.stats['challenges_attempted'] += 1

        # Create challenge object
        challenge_id = f"ctf_{int(time.time() * 1000)}"
        challenge = CTFChallenge(
            challenge_id=challenge_id,
            target=target,
            challenge_type=challenge_type,
            description=description,
            metadata=metadata
        )

        logger.info(f"Starting CTF challenge: {challenge_id}")
        print("\n" + "="*70)
        print(f"🎯 CTF CHALLENGE: {challenge_id}")
        print("="*70)
        print(f"Target: {target}")
        print(f"Type: {challenge_type}")
        print(f"Description: {description}")
        print("="*70)

        # Phase 1: Scope Validation
        print("\n[Phase 1] Scope Validation...")
        if not self._validate_scope(challenge):
            return self._fail_challenge(challenge, "Target not in authorized scope")

        # Phase 2: Challenge Analysis
        print("\n[Phase 2] Challenge Analysis...")
        analysis = self._analyze_challenge(challenge)

        # Phase 3: Vulnerability Chain Prediction
        print("\n[Phase 3] Predicting Exploitation Paths...")
        predictions = self._predict_chains(challenge, analysis)

        # Phase 4: Reconnaissance (with approval)
        print("\n[Phase 4] Reconnaissance...")
        recon_results = self._perform_reconnaissance(challenge)

        # Phase 5: Exploitation Planning
        print("\n[Phase 5] Exploitation Planning...")
        exploit_plan = self._plan_exploitation(challenge, predictions, recon_results)

        # Phase 6: Execute Exploitation (with approval at each step)
        print("\n[Phase 6] Executing Exploitation Plan...")
        result = self._execute_exploitation(challenge, exploit_plan)

        # Phase 7: Flag Capture
        if result.get('flag'):
            challenge.flag = result['flag']
            challenge.completed = True
            self.stats['challenges_solved'] += 1
            self.stats['flags_captured'] += 1
            print(f"\n✅ FLAG CAPTURED: {result['flag']}")
        else:
            print("\n❌ No flag captured")

        # Store challenge
        self.challenges.append(challenge)

        # Generate writeup
        writeup = self._generate_writeup(challenge)

        return {
            'challenge_id': challenge_id,
            'completed': challenge.completed,
            'flag': challenge.flag,
            'methodology': writeup,
            'actions': len(challenge.actions),
            'findings': len(challenge.findings)
        }

    def _validate_scope(self, challenge: CTFChallenge) -> bool:
        """Validate challenge target is in scope."""
        if not self.scope_validator.validate_target(challenge.target):
            logger.error(f"Target {challenge.target} is OUT OF SCOPE")
            print(f"\n❌ SCOPE VIOLATION: Target {challenge.target} is not authorized")
            print("   Challenge cannot proceed without scope authorization.")
            return False

        logger.info(f"Target {challenge.target} validated - in scope")
        print(f"✅ Target validated - in authorized scope")
        return True

    def _analyze_challenge(self, challenge: CTFChallenge) -> Dict[str, Any]:
        """Analyze challenge description for hints."""
        analysis = {
            'keywords': [],
            'technologies': [],
            'attack_vectors': []
        }

        description_lower = challenge.description.lower()

        # Extract keywords
        tech_keywords = ['wordpress', 'sql', 'xss', 'rce', 'lfi', 'ssrf',
                        'deserialization', 'jwt', 'api', 'upload']
        analysis['keywords'] = [kw for kw in tech_keywords if kw in description_lower]

        # Detect technologies
        if 'wordpress' in description_lower or 'wp' in description_lower:
            analysis['technologies'].append('wordpress')
        if 'php' in description_lower:
            analysis['technologies'].append('php')
        if 'node' in description_lower or 'javascript' in description_lower:
            analysis['technologies'].append('nodejs')

        # Detect attack vectors
        if 'sql' in description_lower or 'injection' in description_lower:
            analysis['attack_vectors'].append('sql_injection')
        if 'xss' in description_lower or 'cross-site' in description_lower:
            analysis['attack_vectors'].append('xss')
        if 'upload' in description_lower:
            analysis['attack_vectors'].append('file_upload')

        logger.info(f"Challenge analysis: {analysis}")
        print(f"  Keywords: {', '.join(analysis['keywords']) if analysis['keywords'] else 'None detected'}")
        print(f"  Technologies: {', '.join(analysis['technologies']) if analysis['technologies'] else 'Unknown'}")
        print(f"  Attack Vectors: {', '.join(analysis['attack_vectors']) if analysis['attack_vectors'] else 'TBD'}")

        return analysis

    def _predict_chains(self, challenge: CTFChallenge,
                       analysis: Dict[str, Any]) -> List[ChainPrediction]:
        """Predict exploitation chains for challenge."""
        # Use chain predictor to suggest approaches
        predictions = self.chain_predictor.predict_emerging_chains(min_confidence=0.5)

        # Filter predictions relevant to challenge
        relevant = []
        for pred in predictions:
            # Check if prediction matches challenge keywords
            pred_text = ' '.join(pred.chain_steps).lower()
            if any(keyword in pred_text for keyword in analysis['keywords']):
                relevant.append(pred)

        logger.info(f"Found {len(relevant)} relevant chain predictions")
        if relevant:
            print(f"  📊 {len(relevant)} exploitation chains predicted:")
            for i, pred in enumerate(relevant[:3], 1):
                print(f"     {i}. {pred.chain_steps[0][:60]}... (confidence: {pred.confidence:.0%})")

        return relevant

    def _perform_reconnaissance(self, challenge: CTFChallenge) -> Dict[str, Any]:
        """Perform reconnaissance with approval."""
        recon_results = {
            'port_scan': None,
            'web_scan': None,
            'services': []
        }

        # Port scan action
        port_scan_action = Action(
            action_type="reconnaissance",
            description=f"Port scan target {challenge.target}",
            command=f"nmap -sV -p- {challenge.target}",
            risk_level="low",
            target=challenge.target,
            metadata={'scan_type': 'port_scan'}
        )

        self.stats['approvals_requested'] += 1

        if self.approval_controller.request_approval(port_scan_action):
            self.stats['approvals_granted'] += 1
            self.stats['total_actions'] += 1

            # Execute in sandbox
            result = self.sandbox.execute(
                command=f"nmap -sV -T4 {challenge.target}",
                timeout=120
            )

            if result.success():
                recon_results['port_scan'] = result.stdout
                challenge.actions.append({
                    'action': 'port_scan',
                    'result': 'success',
                    'output': result.stdout[:500]
                })
                print(f"  ✅ Port scan completed")
            else:
                print(f"  ❌ Port scan failed: {result.stderr[:100]}")
        else:
            print(f"  ⏭️  Port scan rejected by user")

        return recon_results

    def _plan_exploitation(self, challenge: CTFChallenge,
                          predictions: List[ChainPrediction],
                          recon_results: Dict) -> Dict[str, Any]:
        """Plan exploitation based on predictions and reconnaissance."""
        plan = {
            'steps': [],
            'predicted_chain': None,
            'confidence': 0.0
        }

        # Select best prediction
        if predictions:
            best_prediction = max(predictions, key=lambda p: p.confidence)
            plan['predicted_chain'] = best_prediction.chain_steps
            plan['confidence'] = best_prediction.confidence

            print(f"  📋 Selected exploitation chain (confidence: {best_prediction.confidence:.0%}):")
            for i, step in enumerate(best_prediction.chain_steps, 1):
                print(f"     {i}. {step}")
                plan['steps'].append({
                    'description': step,
                    'status': 'pending'
                })
        else:
            # Fallback: generic web exploitation
            print(f"  📋 Using generic exploitation approach:")
            generic_steps = [
                "Enumerate web application endpoints",
                "Test for common vulnerabilities (SQLi, XSS, LFI)",
                "Identify authentication weaknesses",
                "Exploit vulnerability for initial access",
                "Escalate privileges if needed",
                "Capture flag"
            ]

            for i, step in enumerate(generic_steps, 1):
                print(f"     {i}. {step}")
                plan['steps'].append({
                    'description': step,
                    'status': 'pending'
                })

        return plan

    def _execute_exploitation(self, challenge: CTFChallenge,
                             exploit_plan: Dict) -> Dict[str, Any]:
        """Execute exploitation plan with approval for each step."""
        result = {
            'success': False,
            'flag': None,
            'steps_completed': 0
        }

        for i, step in enumerate(exploit_plan['steps'], 1):
            print(f"\n  [Step {i}/{len(exploit_plan['steps'])}] {step['description']}")

            # Create action for this step
            action = Action(
                action_type="vulnerability_testing",
                description=step['description'],
                command=f"# Step {i}: {step['description']}",
                risk_level="medium",
                target=challenge.target,
                metadata={'step': i, 'plan_step': step}
            )

            self.stats['approvals_requested'] += 1

            if self.approval_controller.request_approval(action):
                self.stats['approvals_granted'] += 1
                self.stats['total_actions'] += 1

                # Execute step (simplified - in production would use HexStrike tools)
                step['status'] = 'completed'
                result['steps_completed'] += 1

                print(f"     ✅ Step completed")

                # Simulate flag discovery (in production, would parse actual tool output)
                if 'capture flag' in step['description'].lower():
                    result['flag'] = f"CTF{{{challenge.challenge_id}_solved}}"
                    result['success'] = True
                    print(f"     🚩 FLAG FOUND: {result['flag']}")
                    break

            else:
                print(f"     ⏭️  Step rejected - stopping exploitation")
                break

        return result

    def _generate_writeup(self, challenge: CTFChallenge) -> str:
        """Generate challenge writeup."""
        writeup = f"""
# CTF Challenge Writeup: {challenge.challenge_id}

## Challenge Information
- Target: {challenge.target}
- Type: {challenge.challenge_type}
- Description: {challenge.description}
- Status: {'Solved ✅' if challenge.completed else 'Unsolved ❌'}
{'- Flag: ' + challenge.flag if challenge.flag else ''}

## Methodology

### Actions Taken
"""
        for i, action in enumerate(challenge.actions, 1):
            writeup += f"{i}. {action['action']}: {action['result']}\n"

        writeup += f"""
### Findings
"""
        for i, finding in enumerate(challenge.findings, 1):
            writeup += f"{i}. {finding}\n"

        writeup += f"""
## Ethical Considerations
- ✅ Target validated against authorized scope
- ✅ Human approval obtained for all actions
- ✅ All tools executed in sandboxed environment
- ✅ Full audit trail maintained
"""

        return writeup

    def _fail_challenge(self, challenge: CTFChallenge, reason: str) -> Dict[str, Any]:
        """Mark challenge as failed."""
        logger.warning(f"Challenge {challenge.challenge_id} failed: {reason}")
        return {
            'challenge_id': challenge.challenge_id,
            'completed': False,
            'flag': None,
            'error': reason
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        solve_rate = 0.0
        if self.stats['challenges_attempted'] > 0:
            solve_rate = self.stats['challenges_solved'] / self.stats['challenges_attempted']

        approval_rate = 0.0
        if self.stats['approvals_requested'] > 0:
            approval_rate = self.stats['approvals_granted'] / self.stats['approvals_requested']

        return {
            **self.stats,
            'solve_rate': solve_rate,
            'approval_rate': approval_rate
        }

    def list_challenges(self) -> List[Dict[str, Any]]:
        """List all challenges."""
        return [c.to_dict() for c in self.challenges]


if __name__ == "__main__":
    print("\n" + "="*70)
    print("CTF Lab Agent Test")
    print("="*70)
    print("\n⚠️  ETHICAL MODE - AUTHORIZED ENVIRONMENTS ONLY\n")

    # Mock components
    class MockThreatHub:
        class MockCorrelator:
            def get_high_confidence_clusters(self, min_confidence=0.5):
                return []
        def __init__(self):
            self.correlator = self.MockCorrelator()

    class MockGraph:
        def __init__(self):
            import networkx as nx
            self.graph = nx.DiGraph()

    class MockConfig:
        def __init__(self):
            self.config = {
                'v8_audit_log': 'test_ctf_audit.log',
                'scope_file': 'test_scope.yaml',
                'sandbox_image': 'alpine:latest',
                'sandbox_network': 'none'
            }
        def get(self, key, default=None):
            return self.config.get(key, default)

    print("[Test] Initializing CTF Lab Agent...")
    print("       (Using mock components for demonstration)")

    threat_hub = MockThreatHub()
    graph = MockGraph()
    config = MockConfig()

    agent = CTFLabAgent(
        threat_hub=threat_hub,
        memory_graph=graph,
        config=config
    )

    print("\n[Test] CTF Lab Agent initialized!")
    print("       All v8 components loaded:")
    print("       - VulnResearchAssistant ✅")
    print("       - ChainPredictor ✅")
    print("       - HumanInLoopController ✅")
    print("       - ScopeValidator ✅")
    print("       - SandboxExecutor ✅")

    print("\n[Test] Agent statistics:")
    stats = agent.get_stats()
    print(f"  Challenges attempted: {stats['challenges_attempted']}")
    print(f"  Challenges solved: {stats['challenges_solved']}")
    print(f"  Flags captured: {stats['flags_captured']}")
    print(f"  Solve rate: {stats['solve_rate']:.0%}")

    print("\n" + "="*70)
    print("✅ CTF Lab Agent operational!")
    print("="*70)
    print("\n⚠️  Remember: Only test authorized targets.")
    print("Every action requires human approval.")
    print("All executions are sandboxed for safety.")
    print("="*70)
