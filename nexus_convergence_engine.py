#!/usr/bin/env python3
"""
HEXSTRIKE-AI: NEXUS CONVERGENCE ENGINE
========================================
"Where All Powers Converge"

The meta-orchestrator that unifies all HexStrike systems.
Features:
- Intent parsing and routing
- Phase synthesis across all systems
- Unified execution bus
- Cross-system coordination
- Natural language operation translation
"""

import logging
import time
import json
import hashlib
import threading
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("NEXUS-CONVERGENCE")


class OperationDomain(Enum):
    """Domains of operation."""
    OFFENSIVE = "offensive"
    DEFENSIVE = "defensive"
    STEALTH = "stealth"
    INTELLIGENCE = "intelligence"
    FINANCIAL = "financial"
    INFRASTRUCTURE = "infrastructure"
    PSYCHOLOGICAL = "psychological"
    EVOLUTION = "evolution"


class ExecutionPriority(Enum):
    """Execution priority levels."""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


class SystemType(Enum):
    """Types of HexStrike systems."""
    MCP_PROTOCOL = "mcp_protocol"
    THRONE_INTERFACE = "throne_interface"
    AGENT_TEAMS = "agent_teams"
    TOOL_SYNTHESIS = "tool_synthesis"
    AUTOMATION = "automation"
    BAEL_CORE = "bael_core"
    SINGULARITY = "singularity"
    LEGION = "legion"
    ORACLE = "oracle"
    OFFENSIVE = "offensive"
    METAMORPHIC = "metamorphic"
    HARDWARE = "hardware"


@dataclass
class OperationIntent:
    """Represents a parsed operation intent."""
    intent_id: str
    raw_input: str
    domain: OperationDomain
    action: str
    targets: List[str]
    parameters: Dict[str, Any]
    priority: ExecutionPriority
    constraints: Dict[str, Any] = field(default_factory=dict)
    parsed_at: float = field(default_factory=time.time)


@dataclass
class ExecutionPlan:
    """A plan for executing an operation across multiple systems."""
    plan_id: str
    intent: OperationIntent
    phases: List[Dict]
    systems_involved: List[SystemType]
    estimated_duration: float
    risk_level: float
    success_probability: float
    created_at: float = field(default_factory=time.time)


@dataclass
class ExecutionResult:
    """Result of an execution."""
    execution_id: str
    plan_id: str
    status: str  # success, partial, failed
    phase_results: List[Dict]
    duration: float
    systems_engaged: List[str]
    artifacts: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class IntentParser:
    """
    Parses natural language and structured intents into operation specifications.
    """

    def __init__(self):
        self.domain_keywords = self._build_domain_keywords()
        self.action_patterns = self._build_action_patterns()

    def _build_domain_keywords(self) -> Dict[OperationDomain, List[str]]:
        """Build keyword mapping for domains."""
        return {
            OperationDomain.OFFENSIVE: [
                "attack", "exploit", "penetrate", "compromise", "breach",
                "pwn", "hack", "takeover"
            ],
            OperationDomain.DEFENSIVE: [
                "defend", "protect", "secure", "harden", "monitor",
                "detect", "respond", "investigate"
            ],
            OperationDomain.STEALTH: [
                "stealth", "ghost", "hidden", "covert", "invisible",
                "undetected", "silent"
            ],
            OperationDomain.INTELLIGENCE: [
                "recon", "scan", "enumerate", "discover", "gather",
                "intelligence", "osint", "survey"
            ],
            OperationDomain.FINANCIAL: [
                "wealth", "money", "profit", "harvest", "financial",
                "cryptocurrency", "transaction"
            ],
            OperationDomain.INFRASTRUCTURE: [
                "deploy", "build", "infrastructure", "c2", "server",
                "network", "provision"
            ],
            OperationDomain.PSYCHOLOGICAL: [
                "influence", "narrative", "disinformation", "social",
                "psychological", "perception"
            ],
            OperationDomain.EVOLUTION: [
                "evolve", "mutate", "adapt", "upgrade", "metamorphic",
                "transform"
            ]
        }

    def _build_action_patterns(self) -> Dict[str, Dict]:
        """Build action patterns for intent matching."""
        return {
            "full_takeover": {
                "keywords": ["takeover", "own", "dominate", "control"],
                "phases": ["recon", "exploit", "persist", "lateral", "exfil"],
                "domain": OperationDomain.OFFENSIVE
            },
            "reconnaissance": {
                "keywords": ["scan", "recon", "enumerate", "discover"],
                "phases": ["passive_recon", "active_recon", "vuln_scan"],
                "domain": OperationDomain.INTELLIGENCE
            },
            "exfiltration": {
                "keywords": ["exfil", "extract", "steal", "copy"],
                "phases": ["identify", "stage", "transfer", "cleanup"],
                "domain": OperationDomain.OFFENSIVE
            },
            "persistence": {
                "keywords": ["persist", "maintain", "implant", "backdoor"],
                "phases": ["access", "implant", "fortify", "redundancy"],
                "domain": OperationDomain.STEALTH
            },
            "defense": {
                "keywords": ["defend", "protect", "secure", "harden"],
                "phases": ["assess", "implement", "verify", "monitor"],
                "domain": OperationDomain.DEFENSIVE
            }
        }

    def parse(self, input_text: str, context: Dict = None) -> OperationIntent:
        """Parse input into an operation intent."""
        input_lower = input_text.lower()

        # Determine domain
        domain = self._detect_domain(input_lower)

        # Determine action
        action = self._detect_action(input_lower)

        # Extract targets
        targets = self._extract_targets(input_text)

        # Extract parameters
        parameters = self._extract_parameters(input_text, context or {})

        # Determine priority
        priority = self._assess_priority(input_lower)

        intent_id = f"INT-{hashlib.md5(input_text.encode()).hexdigest()[:8].upper()}"

        return OperationIntent(
            intent_id=intent_id,
            raw_input=input_text,
            domain=domain,
            action=action,
            targets=targets,
            parameters=parameters,
            priority=priority
        )

    def _detect_domain(self, text: str) -> OperationDomain:
        """Detect the operation domain from text."""
        for domain, keywords in self.domain_keywords.items():
            if any(kw in text for kw in keywords):
                return domain
        return OperationDomain.OFFENSIVE  # Default

    def _detect_action(self, text: str) -> str:
        """Detect the specific action from text."""
        for action, config in self.action_patterns.items():
            if any(kw in text for kw in config["keywords"]):
                return action
        return "general"

    def _extract_targets(self, text: str) -> List[str]:
        """Extract targets from text."""
        import re
        targets = []

        # IP addresses
        ips = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:/\d{1,2})?', text)
        targets.extend(ips)

        # Domain names
        domains = re.findall(r'[\w\-]+(?:\.[\w\-]+)+', text)
        targets.extend(domains)

        return targets

    def _extract_parameters(self, text: str, context: Dict) -> Dict[str, Any]:
        """Extract parameters from text and context."""
        params = {}

        # Check for stealth level
        if "stealth" in text.lower() or "ghost" in text.lower():
            params["stealth_level"] = 10
        elif "fast" in text.lower() or "quick" in text.lower():
            params["stealth_level"] = 3
        else:
            params["stealth_level"] = 7

        # Merge with context
        params.update(context)

        return params

    def _assess_priority(self, text: str) -> ExecutionPriority:
        """Assess priority from text."""
        if any(word in text for word in ["urgent", "critical", "emergency", "now"]):
            return ExecutionPriority.CRITICAL
        elif any(word in text for word in ["high", "important", "priority"]):
            return ExecutionPriority.HIGH
        elif any(word in text for word in ["low", "background", "when possible"]):
            return ExecutionPriority.LOW
        return ExecutionPriority.NORMAL


class PhaseSynthesizer:
    """
    Synthesizes execution phases from intents.
    Creates optimized multi-phase operation plans.
    """

    def __init__(self):
        self.phase_templates = self._build_phase_templates()

    def _build_phase_templates(self) -> Dict[str, List[Dict]]:
        """Build phase templates for different operations."""
        return {
            "full_takeover": [
                {"phase": 1, "name": "RECONNAISSANCE", "systems": [SystemType.ORACLE, SystemType.OFFENSIVE], "duration": 30},
                {"phase": 2, "name": "VULNERABILITY_SCAN", "systems": [SystemType.OFFENSIVE, SystemType.TOOL_SYNTHESIS], "duration": 60},
                {"phase": 3, "name": "EXPLOITATION", "systems": [SystemType.OFFENSIVE, SystemType.AGENT_TEAMS], "duration": 120},
                {"phase": 4, "name": "PERSISTENCE", "systems": [SystemType.METAMORPHIC, SystemType.HARDWARE], "duration": 60},
                {"phase": 5, "name": "LATERAL_MOVEMENT", "systems": [SystemType.AGENT_TEAMS, SystemType.LEGION], "duration": 180},
                {"phase": 6, "name": "EXFILTRATION", "systems": [SystemType.STEALTH, SystemType.OFFENSIVE], "duration": 120},
                {"phase": 7, "name": "CLEANUP", "systems": [SystemType.METAMORPHIC], "duration": 30}
            ],
            "reconnaissance": [
                {"phase": 1, "name": "PASSIVE_RECON", "systems": [SystemType.ORACLE], "duration": 60},
                {"phase": 2, "name": "ACTIVE_RECON", "systems": [SystemType.OFFENSIVE, SystemType.TOOL_SYNTHESIS], "duration": 120},
                {"phase": 3, "name": "ANALYSIS", "systems": [SystemType.ORACLE, SystemType.SINGULARITY], "duration": 30}
            ],
            "persistence": [
                {"phase": 1, "name": "ACCESS_VERIFICATION", "systems": [SystemType.OFFENSIVE], "duration": 10},
                {"phase": 2, "name": "IMPLANT_DEPLOYMENT", "systems": [SystemType.METAMORPHIC, SystemType.HARDWARE], "duration": 60},
                {"phase": 3, "name": "FORTIFICATION", "systems": [SystemType.METAMORPHIC], "duration": 30},
                {"phase": 4, "name": "REDUNDANCY", "systems": [SystemType.HARDWARE], "duration": 30}
            ],
            "exfiltration": [
                {"phase": 1, "name": "DATA_IDENTIFICATION", "systems": [SystemType.ORACLE], "duration": 30},
                {"phase": 2, "name": "STAGING", "systems": [SystemType.OFFENSIVE], "duration": 60},
                {"phase": 3, "name": "COVERT_TRANSFER", "systems": [SystemType.STEALTH], "duration": 120},
                {"phase": 4, "name": "CLEANUP", "systems": [SystemType.METAMORPHIC], "duration": 15}
            ],
            "defense": [
                {"phase": 1, "name": "ASSESSMENT", "systems": [SystemType.ORACLE], "duration": 30},
                {"phase": 2, "name": "HARDENING", "systems": [SystemType.DEFENSIVE], "duration": 60},
                {"phase": 3, "name": "MONITORING_SETUP", "systems": [SystemType.AUTOMATION], "duration": 30},
                {"phase": 4, "name": "VALIDATION", "systems": [SystemType.AGENT_TEAMS], "duration": 30}
            ]
        }

    def synthesize(self, intent: OperationIntent) -> ExecutionPlan:
        """Synthesize an execution plan from an intent."""
        phases = self.phase_templates.get(intent.action, self.phase_templates["reconnaissance"])

        # Customize phases based on parameters
        customized_phases = self._customize_phases(phases, intent)

        # Calculate systems involved
        systems = set()
        for phase in customized_phases:
            systems.update(phase.get("systems", []))

        # Estimate duration
        total_duration = sum(p.get("duration", 60) for p in customized_phases)

        # Assess risk and success probability
        risk_level = self._assess_risk(intent, customized_phases)
        success_prob = self._estimate_success(intent, customized_phases)

        plan_id = f"PLAN-{hashlib.md5(intent.intent_id.encode()).hexdigest()[:8].upper()}"

        return ExecutionPlan(
            plan_id=plan_id,
            intent=intent,
            phases=customized_phases,
            systems_involved=list(systems),
            estimated_duration=total_duration,
            risk_level=risk_level,
            success_probability=success_prob
        )

    def _customize_phases(self, phases: List[Dict], intent: OperationIntent) -> List[Dict]:
        """Customize phases based on intent parameters."""
        customized = []

        stealth_level = intent.parameters.get("stealth_level", 7)

        for phase in phases:
            custom_phase = phase.copy()

            # Adjust duration based on stealth level
            if stealth_level >= 8:
                custom_phase["duration"] = int(phase["duration"] * 1.5)  # Slower for stealth
                custom_phase["stealth_mode"] = True
            elif stealth_level <= 3:
                custom_phase["duration"] = int(phase["duration"] * 0.7)  # Faster but louder
                custom_phase["stealth_mode"] = False

            customized.append(custom_phase)

        return customized

    def _assess_risk(self, intent: OperationIntent, phases: List[Dict]) -> float:
        """Assess risk level of the operation."""
        base_risk = 0.3

        # Higher risk for offensive operations
        if intent.domain == OperationDomain.OFFENSIVE:
            base_risk += 0.2

        # More phases = more risk
        base_risk += len(phases) * 0.05

        # Stealth reduces risk
        if intent.parameters.get("stealth_level", 7) >= 8:
            base_risk *= 0.7

        return min(base_risk, 1.0)

    def _estimate_success(self, intent: OperationIntent, phases: List[Dict]) -> float:
        """Estimate probability of success."""
        base_success = 0.85

        # Complex operations have lower base success
        base_success -= len(phases) * 0.02

        # Stealth operations are more reliable
        if intent.parameters.get("stealth_level", 7) >= 8:
            base_success += 0.05

        return max(min(base_success, 1.0), 0.1)


class UnifiedExecutionBus:
    """
    The unified execution bus for coordinating all systems.
    Routes operations to appropriate systems and manages execution flow.
    """

    def __init__(self):
        self.system_handlers: Dict[SystemType, Callable] = {}
        self.execution_history: List[ExecutionResult] = []
        self.active_executions: Dict[str, Dict] = {}
        self._lock = threading.RLock()

    def register_handler(self, system_type: SystemType, handler: Callable):
        """Register a handler for a system type."""
        self.system_handlers[system_type] = handler
        logger.info(f"📍 Registered handler for: {system_type.value}")

    def execute_plan(self, plan: ExecutionPlan) -> ExecutionResult:
        """Execute an operation plan."""
        execution_id = f"EXEC-{hashlib.md5(plan.plan_id.encode()).hexdigest()[:8].upper()}"

        logger.warning(f"🚀 [NEXUS] Executing plan: {plan.plan_id}")

        with self._lock:
            self.active_executions[execution_id] = {
                "plan": plan,
                "status": "executing",
                "started_at": time.time()
            }

        phase_results = []
        errors = []
        systems_engaged = set()

        start_time = time.time()

        for phase in plan.phases:
            phase_result = self._execute_phase(phase, plan.intent)
            phase_results.append(phase_result)

            systems_engaged.update([s.value for s in phase.get("systems", [])])

            if phase_result.get("status") == "failed":
                errors.append(f"Phase {phase['name']} failed: {phase_result.get('error', 'Unknown')}")
                # Continue or abort based on phase criticality
                if phase.get("critical", False):
                    break

        duration = time.time() - start_time

        # Determine overall status
        if errors:
            status = "partial" if any(r.get("status") == "success" for r in phase_results) else "failed"
        else:
            status = "success"

        result = ExecutionResult(
            execution_id=execution_id,
            plan_id=plan.plan_id,
            status=status,
            phase_results=phase_results,
            duration=duration,
            systems_engaged=list(systems_engaged),
            errors=errors
        )

        with self._lock:
            self.execution_history.append(result)
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]

        logger.info(f"✅ [NEXUS] Execution complete: {status}")
        return result

    def _execute_phase(self, phase: Dict, intent: OperationIntent) -> Dict:
        """Execute a single phase."""
        phase_name = phase.get("name", "UNKNOWN")
        logger.info(f"⚡ [NEXUS] Phase: {phase_name}")

        results = []

        for system_type in phase.get("systems", []):
            if system_type in self.system_handlers:
                try:
                    handler = self.system_handlers[system_type]
                    result = handler(phase, intent)
                    results.append({"system": system_type.value, "result": result})
                except Exception as e:
                    results.append({"system": system_type.value, "error": str(e)})
            else:
                # No handler - simulate
                results.append({"system": system_type.value, "result": "simulated"})

        return {
            "phase": phase_name,
            "status": "success" if all(r.get("result") for r in results) else "partial",
            "system_results": results
        }


class NexusConvergenceEngine:
    """
    The Nexus Convergence Engine - Meta-orchestrator for all HexStrike systems.
    """

    def __init__(self):
        self.intent_parser = IntentParser()
        self.synthesizer = PhaseSynthesizer()
        self.execution_bus = UnifiedExecutionBus()

        # System references (will be connected at integration)
        self.connected_systems: Dict[SystemType, Any] = {}

        # Operation history
        self.operation_history: List[Dict] = []

        # Convergence state
        self.convergence_active = True

        self._lock = threading.RLock()

        # Register default handlers
        self._register_default_handlers()

        logger.warning("🌀 [NEXUS] Convergence Engine INITIALIZED")

    def _register_default_handlers(self):
        """Register default system handlers."""

        # Generic handler for simulation
        def generic_handler(phase: Dict, intent: OperationIntent) -> Dict:
            return {
                "status": "executed",
                "phase": phase.get("name"),
                "simulated": True
            }

        for system_type in SystemType:
            self.execution_bus.register_handler(system_type, generic_handler)

    def connect_system(self, system_type: SystemType, system_instance: Any):
        """Connect a live system instance."""
        self.connected_systems[system_type] = system_instance
        logger.info(f"🔗 Connected system: {system_type.value}")

    # ═══════════════════════════════════════════════════════════════════════
    # NATURAL LANGUAGE OPERATION
    # ═══════════════════════════════════════════════════════════════════════

    def execute_intent(self, intent_text: str, context: Dict = None) -> ExecutionResult:
        """
        Execute an operation from natural language intent.

        Examples:
        - "Take over target-corp.com with maximum stealth"
        - "Scan the 10.0.0.0/8 network for vulnerabilities"
        - "Establish persistent presence on the compromised systems"
        """
        # Parse intent
        intent = self.intent_parser.parse(intent_text, context)
        logger.info(f"📝 Parsed intent: {intent.action} on {intent.targets}")

        # Synthesize plan
        plan = self.synthesizer.synthesize(intent)
        logger.info(f"📋 Synthesized plan: {len(plan.phases)} phases, {plan.estimated_duration}s estimated")

        # Execute plan
        result = self.execution_bus.execute_plan(plan)

        # Record in history
        with self._lock:
            self.operation_history.append({
                "timestamp": time.time(),
                "intent_text": intent_text,
                "intent": intent.__dict__,
                "plan_id": plan.plan_id,
                "result": result.__dict__
            })

        return result

    def analyze_intent(self, intent_text: str, context: Dict = None) -> Dict[str, Any]:
        """Analyze an intent without executing, for preview/approval."""
        intent = self.intent_parser.parse(intent_text, context)
        plan = self.synthesizer.synthesize(intent)

        return {
            "intent": {
                "id": intent.intent_id,
                "domain": intent.domain.value,
                "action": intent.action,
                "targets": intent.targets,
                "priority": intent.priority.value
            },
            "plan": {
                "id": plan.plan_id,
                "phases": [{"name": p["name"], "duration": p["duration"]} for p in plan.phases],
                "systems": [s.value for s in plan.systems_involved],
                "estimated_duration": f"{plan.estimated_duration}s",
                "risk_level": f"{plan.risk_level:.1%}",
                "success_probability": f"{plan.success_probability:.1%}"
            }
        }

    # ═══════════════════════════════════════════════════════════════════════
    # DIRECT OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════

    def execute_full_spectrum_attack(self, target: str,
                                      stealth_level: int = 7) -> ExecutionResult:
        """Execute a full spectrum attack on a target."""
        return self.execute_intent(
            f"Take over {target} with stealth level {stealth_level}",
            {"stealth_level": stealth_level}
        )

    def execute_reconnaissance(self, target: str) -> ExecutionResult:
        """Execute reconnaissance on a target."""
        return self.execute_intent(f"Scan and enumerate {target}")

    def execute_persistence(self, targets: List[str]) -> ExecutionResult:
        """Establish persistence on targets."""
        return self.execute_intent(
            f"Establish persistent presence on {', '.join(targets)}"
        )

    def execute_exfiltration(self, target: str, data_type: str = "all") -> ExecutionResult:
        """Execute data exfiltration."""
        return self.execute_intent(
            f"Exfiltrate {data_type} data from {target}"
        )

    # ═══════════════════════════════════════════════════════════════════════
    # CROSS-SYSTEM COORDINATION
    # ═══════════════════════════════════════════════════════════════════════

    def coordinate_multi_target(self, targets: List[str],
                                 operation: str) -> List[ExecutionResult]:
        """Coordinate operations across multiple targets."""
        results = []

        for target in targets:
            result = self.execute_intent(f"{operation} {target}")
            results.append(result)

        return results

    def synchronize_operations(self, operations: List[Dict]) -> Dict[str, Any]:
        """Synchronize multiple operations for simultaneous execution."""
        sync_id = f"SYNC-{hashlib.md5(json.dumps(operations).encode()).hexdigest()[:8].upper()}"

        plans = []
        for op in operations:
            intent = self.intent_parser.parse(op["intent"], op.get("context", {}))
            plan = self.synthesizer.synthesize(intent)
            plans.append(plan)

        logger.warning(f"🔄 [NEXUS] Synchronized {len(plans)} operations")

        return {
            "sync_id": sync_id,
            "operations": len(plans),
            "total_phases": sum(len(p.phases) for p in plans),
            "plans": [p.plan_id for p in plans]
        }

    # ═══════════════════════════════════════════════════════════════════════
    # STATUS AND REPORTING
    # ═══════════════════════════════════════════════════════════════════════

    def get_status(self) -> Dict[str, Any]:
        """Get Nexus status."""
        return {
            "convergence_active": self.convergence_active,
            "connected_systems": len(self.connected_systems),
            "active_executions": len(self.execution_bus.active_executions),
            "total_operations": len(self.operation_history),
            "execution_history": len(self.execution_bus.execution_history)
        }

    def get_recent_operations(self, count: int = 10) -> List[Dict]:
        """Get recent operations."""
        return self.operation_history[-count:]

    def get_operation_summary(self, execution_id: str) -> Optional[Dict]:
        """Get summary of a specific operation."""
        for result in self.execution_bus.execution_history:
            if result.execution_id == execution_id:
                return {
                    "id": result.execution_id,
                    "plan": result.plan_id,
                    "status": result.status,
                    "duration": f"{result.duration:.2f}s",
                    "phases": len(result.phase_results),
                    "systems": result.systems_engaged,
                    "errors": result.errors
                }
        return None

    def render_convergence_status(self) -> str:
        """Render convergence status as text."""
        status = self.get_status()

        output = f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                       🌀 NEXUS CONVERGENCE ENGINE                             ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  Status:           {"ACTIVE" if status["convergence_active"] else "INACTIVE":>10}                                      ║
║  Connected Systems: {status["connected_systems"]:>10}                                      ║
║  Active Executions: {status["active_executions"]:>10}                                      ║
║  Total Operations:  {status["total_operations"]:>10}                                      ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""
        return output


# Global singleton instance
nexus_convergence = NexusConvergenceEngine()


if __name__ == "__main__":
    # Test the Nexus Convergence Engine
    print("=" * 80)
    print("NEXUS CONVERGENCE ENGINE - TEST")
    print("=" * 80)

    # Test intent analysis
    analysis = nexus_convergence.analyze_intent(
        "Take over target-corp.com with maximum stealth"
    )
    print(f"\n📋 Analysis: {json.dumps(analysis, indent=2)}")

    # Test execution
    result = nexus_convergence.execute_intent(
        "Scan the 192.168.1.0/24 network for vulnerabilities"
    )
    print(f"\n🚀 Execution result: {result.status}")
    print(f"   Duration: {result.duration:.2f}s")
    print(f"   Phases: {len(result.phase_results)}")

    # Test full spectrum attack
    result2 = nexus_convergence.execute_full_spectrum_attack("megacorp.com", stealth_level=9)
    print(f"\n⚔️ Full spectrum: {result2.status}")

    # Show status
    print(nexus_convergence.render_convergence_status())

    print("\n✅ Nexus Convergence Engine initialized successfully!")
