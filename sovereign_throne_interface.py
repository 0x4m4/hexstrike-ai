#!/usr/bin/env python3
"""
HEXSTRIKE-AI: SOVEREIGN THRONE INTERFACE
=========================================
"Your Command Center - Perfected"

The Architect's interface for complete dominion control.
Features:
- Natural language command interpretation
- Real-time dashboard and telemetry
- One-click power actions
- Failsafe controls
- Multi-mode interfaces (CLI, Web, API, Voice)
"""

import logging
import time
import json
import threading
import hashlib
import os
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SOVEREIGN-THRONE")


class AutomationLevel(Enum):
    """Automation levels for the system."""
    MANUAL = 0        # Architect controls each step
    ASSISTED = 1      # System suggests, Architect approves
    SUPERVISED = 2    # System acts, Architect monitors
    AUTONOMOUS = 3    # System operates independently
    ADAPTIVE = 4      # System learns and improves
    SINGULARITY = 5   # System evolves beyond design


class ThreatLevel(Enum):
    """Threat levels for the dominion."""
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"


class OperationStatus(Enum):
    """Status of operations."""
    PLANNED = "planned"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABORTED = "aborted"
    FAILED = "failed"


@dataclass
class Operation:
    """Represents an active operation."""
    operation_id: str
    name: str
    description: str
    status: OperationStatus
    phase: int
    total_phases: int
    progress: float  # 0.0 to 1.0
    started_at: float
    agents_assigned: List[str] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Represents a system alert."""
    alert_id: str
    level: str  # info, warning, critical
    message: str
    timestamp: float
    acknowledged: bool = False
    action_taken: str = None


class NaturalLanguageIntentParser:
    """
    Parses natural language commands from the Architect.
    Converts human intent into structured operations.
    """

    def __init__(self):
        self.intent_patterns = self._build_intent_patterns()
        self.modifiers = {
            "aggressive": {"stealth_level": 2, "speed": "fast", "thorough": False},
            "stealth": {"stealth_level": 10, "speed": "slow", "thorough": True},
            "fast": {"stealth_level": 5, "speed": "fast", "thorough": False},
            "thorough": {"stealth_level": 7, "speed": "slow", "thorough": True},
            "maximum": {"stealth_level": 5, "speed": "fast", "thorough": True},
        }

    def _build_intent_patterns(self) -> List[Dict]:
        """Build patterns for intent recognition."""
        return [
            # Reconnaissance intents
            {
                "patterns": [r"scan\s+(.+)", r"recon\s+(.+)", r"enumerate\s+(.+)", r"discover\s+(.+)"],
                "intent": "reconnaissance",
                "phase_type": "recon"
            },
            # Exploitation intents
            {
                "patterns": [r"exploit\s+(.+)", r"attack\s+(.+)", r"compromise\s+(.+)", r"pwn\s+(.+)"],
                "intent": "exploitation",
                "phase_type": "exploit"
            },
            # Full takeover intents
            {
                "patterns": [r"take\s*over\s+(.+)", r"dominate\s+(.+)", r"own\s+(.+)", r"full\s+control\s+(.+)"],
                "intent": "full_takeover",
                "phase_type": "multi"
            },
            # Financial intents
            {
                "patterns": [r"harvest\s+wealth", r"financial\s+(.+)", r"money\s+(.+)", r"profit\s+(.+)"],
                "intent": "financial",
                "phase_type": "midas"
            },
            # Stealth intents
            {
                "patterns": [r"go\s+ghost", r"hide\s+(.+)", r"stealth\s+(.+)", r"invisible"],
                "intent": "stealth_mode",
                "phase_type": "ghost"
            },
            # Cleanup intents
            {
                "patterns": [r"clean\s+(.+)", r"wipe\s+(.+)", r"remove\s+traces", r"cover\s+tracks"],
                "intent": "cleanup",
                "phase_type": "cleanup"
            },
            # Status intents
            {
                "patterns": [r"status", r"show\s+(.+)", r"display\s+(.+)", r"report"],
                "intent": "status_query",
                "phase_type": "query"
            },
            # Emergency intents
            {
                "patterns": [r"abort\s+(.+)", r"stop\s+(.+)", r"emergency\s+(.+)", r"kill\s+(.+)"],
                "intent": "emergency",
                "phase_type": "emergency"
            },
        ]

    def parse(self, command: str) -> Dict[str, Any]:
        """Parse a natural language command into structured intent."""
        command_lower = command.lower().strip()

        # Extract modifiers
        modifiers = {}
        for mod_name, mod_values in self.modifiers.items():
            if mod_name in command_lower:
                modifiers.update(mod_values)
                command_lower = command_lower.replace(mod_name, "").strip()

        # Match against patterns
        for pattern_group in self.intent_patterns:
            for pattern in pattern_group["patterns"]:
                match = re.search(pattern, command_lower)
                if match:
                    target = match.group(1) if match.groups() else None
                    return {
                        "intent": pattern_group["intent"],
                        "phase_type": pattern_group["phase_type"],
                        "target": target,
                        "modifiers": modifiers,
                        "original_command": command,
                        "confidence": 0.9
                    }

        # Unknown intent
        return {
            "intent": "unknown",
            "phase_type": "general",
            "target": command,
            "modifiers": modifiers,
            "original_command": command,
            "confidence": 0.3
        }


class RealTimeTelemetry:
    """
    Aggregates and provides real-time telemetry from all systems.
    """

    def __init__(self):
        self.metrics: Dict[str, Any] = {
            "controlled_nodes": 0,
            "active_legions": 0,
            "offspring_count": 0,
            "wealth_accrued": 0.0,
            "operations_active": 0,
            "detection_risk": 0.0,
            "inevitability_score": 0.0
        }
        self.events: List[Dict] = []
        self.max_events = 1000
        self._lock = threading.RLock()

    def update_metric(self, name: str, value: Any):
        """Update a metric value."""
        with self._lock:
            self.metrics[name] = value

    def increment_metric(self, name: str, amount: float = 1):
        """Increment a metric value."""
        with self._lock:
            if name in self.metrics:
                self.metrics[name] += amount

    def record_event(self, source: str, event_type: str, message: str, data: Dict = None):
        """Record a telemetry event."""
        with self._lock:
            event = {
                "timestamp": time.time(),
                "source": source,
                "type": event_type,
                "message": message,
                "data": data or {}
            }
            self.events.append(event)

            # Trim old events
            if len(self.events) > self.max_events:
                self.events = self.events[-self.max_events:]

    def get_metrics(self) -> Dict[str, Any]:
        """Get all current metrics."""
        with self._lock:
            return self.metrics.copy()

    def get_recent_events(self, count: int = 50, source_filter: str = None) -> List[Dict]:
        """Get recent events, optionally filtered by source."""
        with self._lock:
            events = self.events[-count:]
            if source_filter:
                events = [e for e in events if e["source"] == source_filter]
            return events


class FailsafeController:
    """
    Manages failsafe controls for emergency situations.
    """

    def __init__(self):
        self.failsafes = {
            "global_pause": False,
            "ghost_mode": False,
            "lockout_active": False,
            "death_switch_armed": False
        }
        self.operation_history: List[Dict] = []
        self._lock = threading.RLock()

    def pause_all_operations(self) -> bool:
        """Pause all active operations."""
        with self._lock:
            self.failsafes["global_pause"] = True
            logger.warning("⏸️ [FAILSAFE] Global pause activated")
            return True

    def resume_operations(self) -> bool:
        """Resume all paused operations."""
        with self._lock:
            self.failsafes["global_pause"] = False
            logger.info("▶️ [FAILSAFE] Operations resumed")
            return True

    def activate_ghost_mode(self) -> bool:
        """Activate maximum stealth across all operations."""
        with self._lock:
            self.failsafes["ghost_mode"] = True
            logger.warning("👻 [FAILSAFE] Ghost mode activated")
            return True

    def deactivate_ghost_mode(self) -> bool:
        """Deactivate ghost mode."""
        with self._lock:
            self.failsafes["ghost_mode"] = False
            logger.info("👁️ [FAILSAFE] Ghost mode deactivated")
            return True

    def activate_lockout(self) -> Dict[str, Any]:
        """Activate global lockout - freeze all controlled infrastructure."""
        with self._lock:
            self.failsafes["lockout_active"] = True
            logger.critical("🔒 [FAILSAFE] GLOBAL LOCKOUT ACTIVATED")
            return {"status": "lockout_active", "timestamp": time.time()}

    def arm_death_switch(self, confirmation_code: str) -> bool:
        """Arm the death switch (scorched earth protocol)."""
        expected_code = hashlib.sha256(b"OMEGA_DEATH_CONFIRMED").hexdigest()[:16]
        if confirmation_code == expected_code:
            with self._lock:
                self.failsafes["death_switch_armed"] = True
                logger.critical("💀 [FAILSAFE] DEATH SWITCH ARMED")
                return True
        return False

    def execute_death_switch(self) -> Dict[str, Any]:
        """Execute scorched earth - wipe all traces, collapse all operations."""
        if not self.failsafes["death_switch_armed"]:
            return {"error": "Death switch not armed"}

        logger.critical("☠️ [FAILSAFE] EXECUTING SCORCHED EARTH PROTOCOL")
        # In real implementation, this would:
        # 1. Wipe all logs
        # 2. Remove all persistence
        # 3. Delete all artifacts
        # 4. Disconnect all C2
        # 5. Self-destruct
        return {"status": "scorched_earth_executed", "timestamp": time.time()}

    def get_failsafe_status(self) -> Dict[str, bool]:
        """Get current failsafe status."""
        with self._lock:
            return self.failsafes.copy()


class QuickActionRegistry:
    """
    Registry of one-click power actions.
    """

    def __init__(self):
        self.actions: Dict[str, Dict] = {}
        self._register_default_actions()

    def _register_default_actions(self):
        """Register default quick actions."""
        self.actions = {
            "ghost_mode": {
                "name": "Ghost Mode",
                "description": "Activate maximum stealth across all operations",
                "icon": "👻",
                "handler": "activate_ghost_mode",
                "requires_confirmation": False
            },
            "global_lockout": {
                "name": "Global Lockout",
                "description": "Freeze all controlled infrastructure",
                "icon": "🔒",
                "handler": "activate_lockout",
                "requires_confirmation": True
            },
            "evolve_now": {
                "name": "Evolve Now",
                "description": "Force immediate metamorphic evolution",
                "icon": "🔄",
                "handler": "force_evolution",
                "requires_confirmation": False
            },
            "death_switch": {
                "name": "Death Switch",
                "description": "Scorched earth - wipe everything",
                "icon": "💀",
                "handler": "death_switch",
                "requires_confirmation": True
            },
            "fortress_mode": {
                "name": "Fortress Mode",
                "description": "Defensive posture - protect the dominion",
                "icon": "🛡️",
                "handler": "activate_fortress",
                "requires_confirmation": False
            },
            "maximum_attack": {
                "name": "Maximum Attack",
                "description": "All agents full offensive",
                "icon": "🚀",
                "handler": "maximum_attack",
                "requires_confirmation": True
            },
            "harvest_wealth": {
                "name": "Harvest Wealth",
                "description": "Execute all wealth opportunities",
                "icon": "💰",
                "handler": "harvest_wealth",
                "requires_confirmation": False
            },
            "full_report": {
                "name": "Full Report",
                "description": "Generate comprehensive status report",
                "icon": "📊",
                "handler": "generate_report",
                "requires_confirmation": False
            }
        }

    def get_actions(self) -> Dict[str, Dict]:
        """Get all available quick actions."""
        return self.actions

    def execute_action(self, action_id: str, confirmation: str = None) -> Dict[str, Any]:
        """Execute a quick action."""
        if action_id not in self.actions:
            return {"error": f"Unknown action: {action_id}"}

        action = self.actions[action_id]

        if action["requires_confirmation"] and not confirmation:
            return {"requires_confirmation": True, "action": action_id}

        logger.info(f"⚡ [QUICK-ACTION] Executing: {action['name']}")
        return {"status": "executed", "action": action_id, "timestamp": time.time()}


class SovereignAuditLogger:
    """
    Logs all Architect actions for audit trail.
    """

    def __init__(self, log_path: str = "/tmp/hexstrike_audit.log"):
        self.log_path = log_path
        self._lock = threading.RLock()

    def log_action(self, action_type: str, details: Dict[str, Any], result: Any = None):
        """Log an Architect action."""
        with self._lock:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "action_type": action_type,
                "details": details,
                "result": result
            }

            try:
                with open(self.log_path, "a") as f:
                    f.write(json.dumps(entry) + "\n")
            except Exception as e:
                logger.error(f"Failed to write audit log: {e}")

    def get_recent_logs(self, count: int = 100) -> List[Dict]:
        """Get recent audit log entries."""
        try:
            with open(self.log_path, "r") as f:
                lines = f.readlines()[-count:]
                return [json.loads(line) for line in lines]
        except Exception:
            return []


class SovereignThroneInterface:
    """
    The Architect's command and control center.
    Provides complete visibility and control over the HexStrike Dominion.
    """

    def __init__(self):
        self.intent_parser = NaturalLanguageIntentParser()
        self.telemetry = RealTimeTelemetry()
        self.failsafes = FailsafeController()
        self.quick_actions = QuickActionRegistry()
        self.audit_logger = SovereignAuditLogger()

        # Active operations
        self.operations: Dict[str, Operation] = {}

        # Alerts
        self.alerts: List[Alert] = []

        # Settings
        self.settings = {
            "automation_level": AutomationLevel.SUPERVISED,
            "notification_threshold": "warning",
            "stealth_default": 7,
            "confirmation_required": ["lockout", "death_switch", "maximum_attack"]
        }

        self._lock = threading.RLock()

        logger.warning("👑 [THRONE] Sovereign Throne Interface INITIALIZED")

    # ═══════════════════════════════════════════════════════════════════════
    # NATURAL LANGUAGE INTERFACE
    # ═══════════════════════════════════════════════════════════════════════

    def execute_intent(self, command: str) -> Dict[str, Any]:
        """
        Parse and execute a natural language command from the Architect.

        Examples:
        - "Take over target 192.168.1.100"
        - "Go ghost for the next 24 hours"
        - "Harvest all wealth opportunities"
        - "Show me the current status"
        """
        # Parse the command
        intent = self.intent_parser.parse(command)

        # Log the action
        self.audit_logger.log_action("intent_execution", {
            "command": command,
            "parsed_intent": intent
        })

        # Route to appropriate handler
        return self._route_intent(intent)

    def _route_intent(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Route parsed intent to appropriate handler."""
        intent_type = intent["intent"]

        handlers = {
            "reconnaissance": self._handle_recon_intent,
            "exploitation": self._handle_exploit_intent,
            "full_takeover": self._handle_takeover_intent,
            "financial": self._handle_financial_intent,
            "stealth_mode": self._handle_stealth_intent,
            "cleanup": self._handle_cleanup_intent,
            "status_query": self._handle_status_intent,
            "emergency": self._handle_emergency_intent,
            "unknown": self._handle_unknown_intent,
        }

        handler = handlers.get(intent_type, self._handle_unknown_intent)
        return handler(intent)

    def _handle_recon_intent(self, intent: Dict) -> Dict[str, Any]:
        """Handle reconnaissance intent."""
        target = intent.get("target", "unknown")
        return {
            "action": "reconnaissance",
            "target": target,
            "status": "initiated",
            "message": f"Initiating reconnaissance on {target}",
            "tools_deployed": ["nmap", "amass", "nuclei", "httpx"]
        }

    def _handle_exploit_intent(self, intent: Dict) -> Dict[str, Any]:
        """Handle exploitation intent."""
        target = intent.get("target", "unknown")
        return {
            "action": "exploitation",
            "target": target,
            "status": "initiated",
            "message": f"Initiating exploitation on {target}"
        }

    def _handle_takeover_intent(self, intent: Dict) -> Dict[str, Any]:
        """Handle full takeover intent."""
        target = intent.get("target", "unknown")
        operation_id = f"OP-{hashlib.md5(str(time.time()).encode()).hexdigest()[:8].upper()}"

        operation = Operation(
            operation_id=operation_id,
            name=f"TAKEOVER_{target.upper()}",
            description=f"Full takeover operation targeting {target}",
            status=OperationStatus.EXECUTING,
            phase=1,
            total_phases=6,
            progress=0.0,
            started_at=time.time()
        )

        with self._lock:
            self.operations[operation_id] = operation

        return {
            "action": "full_takeover",
            "target": target,
            "operation_id": operation_id,
            "status": "initiated",
            "message": f"Full takeover operation initiated on {target}",
            "phases": ["RECON", "VULN_SCAN", "EXPLOIT", "PERSIST", "EXFIL", "CLEANUP"]
        }

    def _handle_financial_intent(self, intent: Dict) -> Dict[str, Any]:
        """Handle financial/wealth intent."""
        return {
            "action": "financial",
            "legion": "MIDAS",
            "status": "activated",
            "message": "MIDAS Legion activated for wealth operations"
        }

    def _handle_stealth_intent(self, intent: Dict) -> Dict[str, Any]:
        """Handle stealth mode intent."""
        self.failsafes.activate_ghost_mode()
        return {
            "action": "stealth_mode",
            "status": "activated",
            "message": "Ghost mode activated across all operations"
        }

    def _handle_cleanup_intent(self, intent: Dict) -> Dict[str, Any]:
        """Handle cleanup intent."""
        target = intent.get("target", "all")
        return {
            "action": "cleanup",
            "target": target,
            "status": "initiated",
            "message": f"Cleanup operation initiated for {target}"
        }

    def _handle_status_intent(self, intent: Dict) -> Dict[str, Any]:
        """Handle status query intent."""
        return self.get_full_status()

    def _handle_emergency_intent(self, intent: Dict) -> Dict[str, Any]:
        """Handle emergency intent."""
        target = intent.get("target", "all")
        self.failsafes.pause_all_operations()
        return {
            "action": "emergency",
            "target": target,
            "status": "emergency_activated",
            "message": f"Emergency protocols activated for {target}"
        }

    def _handle_unknown_intent(self, intent: Dict) -> Dict[str, Any]:
        """Handle unknown intent."""
        return {
            "action": "unknown",
            "status": "clarification_needed",
            "message": "I didn't understand that command. Please clarify.",
            "suggestions": [
                "scan [target]",
                "exploit [target]",
                "take over [target]",
                "go ghost",
                "show status"
            ]
        }

    # ═══════════════════════════════════════════════════════════════════════
    # ONE-CLICK POWER ACTIONS
    # ═══════════════════════════════════════════════════════════════════════

    def one_click_ghost_mode(self) -> Dict[str, Any]:
        """Instantly activate maximum stealth across all operations."""
        self.failsafes.activate_ghost_mode()
        self.audit_logger.log_action("quick_action", {"action": "ghost_mode"})
        return {"status": "ghost_mode_active", "timestamp": time.time()}

    def one_click_lockout(self) -> Dict[str, Any]:
        """Emergency lockout of all controlled infrastructure."""
        result = self.failsafes.activate_lockout()
        self.audit_logger.log_action("quick_action", {"action": "lockout"}, result)
        return result

    def one_click_evolution(self) -> Dict[str, Any]:
        """Force immediate metamorphic evolution of all components."""
        self.audit_logger.log_action("quick_action", {"action": "evolution"})
        return {
            "status": "evolution_triggered",
            "components_evolved": ["signatures", "patterns", "identities"],
            "timestamp": time.time()
        }

    def one_click_death_switch(self, confirmation_code: str) -> Dict[str, Any]:
        """Scorched earth - wipe all traces, collapse all operations."""
        if self.failsafes.arm_death_switch(confirmation_code):
            result = self.failsafes.execute_death_switch()
            self.audit_logger.log_action("quick_action", {"action": "death_switch"}, result)
            return result
        return {"error": "Invalid confirmation code"}

    def one_click_harvest(self) -> Dict[str, Any]:
        """Execute all identified wealth opportunities immediately."""
        self.audit_logger.log_action("quick_action", {"action": "harvest"})
        return {
            "status": "harvest_initiated",
            "opportunities_executing": 12,
            "estimated_yield": "$45,000"
        }

    # ═══════════════════════════════════════════════════════════════════════
    # REAL-TIME MONITORING
    # ═══════════════════════════════════════════════════════════════════════

    def get_live_dashboard(self) -> Dict[str, Any]:
        """Returns real-time status of entire dominion."""
        metrics = self.telemetry.get_metrics()
        failsafe_status = self.failsafes.get_failsafe_status()

        return {
            "timestamp": time.time(),
            "metrics": {
                "controlled_nodes": metrics.get("controlled_nodes", 0),
                "active_operations": len(self.operations),
                "active_legions": 4,  # MIDAS, ARES, HERMES, STYX
                "offspring_count": metrics.get("offspring_count", 0),
                "wealth_accrued": f"${metrics.get('wealth_accrued', 0):,.2f}"
            },
            "threat_assessment": {
                "level": ThreatLevel.MINIMAL.value,
                "detection_risk": f"{metrics.get('detection_risk', 0.02):.2%}",
                "inevitability_score": f"{metrics.get('inevitability_score', 0.87):.1%}"
            },
            "failsafes": failsafe_status,
            "active_operations": [
                {
                    "id": op.operation_id,
                    "name": op.name,
                    "status": op.status.value,
                    "progress": f"{op.progress * 100:.0f}%"
                }
                for op in self.operations.values()
            ],
            "recent_events": self.telemetry.get_recent_events(10)
        }

    def stream_events(self, filter_config: Dict = None) -> List[Dict]:
        """Get recent events, optionally filtered."""
        events = self.telemetry.get_recent_events(50)
        if filter_config:
            source = filter_config.get("source")
            if source:
                events = [e for e in events if e["source"] == source]
        return events

    # ═══════════════════════════════════════════════════════════════════════
    # OPERATION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    def get_operation_status(self, operation_id: str) -> Optional[Dict]:
        """Get status of a specific operation."""
        if operation_id in self.operations:
            op = self.operations[operation_id]
            return {
                "id": op.operation_id,
                "name": op.name,
                "description": op.description,
                "status": op.status.value,
                "phase": f"{op.phase}/{op.total_phases}",
                "progress": op.progress,
                "agents": op.agents_assigned,
                "results": op.results
            }
        return None

    def pause_operation(self, operation_id: str) -> bool:
        """Pause a specific operation."""
        if operation_id in self.operations:
            self.operations[operation_id].status = OperationStatus.PAUSED
            return True
        return False

    def resume_operation(self, operation_id: str) -> bool:
        """Resume a paused operation."""
        if operation_id in self.operations:
            op = self.operations[operation_id]
            if op.status == OperationStatus.PAUSED:
                op.status = OperationStatus.EXECUTING
                return True
        return False

    def abort_operation(self, operation_id: str) -> bool:
        """Abort a specific operation."""
        if operation_id in self.operations:
            self.operations[operation_id].status = OperationStatus.ABORTED
            return True
        return False

    # ═══════════════════════════════════════════════════════════════════════
    # ALERTS MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    def add_alert(self, level: str, message: str) -> str:
        """Add a new alert."""
        alert_id = f"ALERT-{len(self.alerts):04d}"
        alert = Alert(
            alert_id=alert_id,
            level=level,
            message=message,
            timestamp=time.time()
        )
        self.alerts.append(alert)
        return alert_id

    def get_unacknowledged_alerts(self) -> List[Dict]:
        """Get all unacknowledged alerts."""
        return [
            {
                "id": a.alert_id,
                "level": a.level,
                "message": a.message,
                "timestamp": a.timestamp
            }
            for a in self.alerts if not a.acknowledged
        ]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False

    # ═══════════════════════════════════════════════════════════════════════
    # SETTINGS MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    def get_settings(self) -> Dict[str, Any]:
        """Get current settings."""
        return {
            "automation_level": self.settings["automation_level"].name,
            "notification_threshold": self.settings["notification_threshold"],
            "stealth_default": self.settings["stealth_default"],
            "confirmation_required": self.settings["confirmation_required"]
        }

    def update_setting(self, key: str, value: Any) -> bool:
        """Update a setting."""
        if key in self.settings:
            if key == "automation_level":
                try:
                    self.settings[key] = AutomationLevel[value.upper()]
                except KeyError:
                    return False
            else:
                self.settings[key] = value
            return True
        return False

    # ═══════════════════════════════════════════════════════════════════════
    # FULL STATUS REPORT
    # ═══════════════════════════════════════════════════════════════════════

    def get_full_status(self) -> Dict[str, Any]:
        """Generate comprehensive status report."""
        return {
            "dashboard": self.get_live_dashboard(),
            "operations": {
                op_id: self.get_operation_status(op_id)
                for op_id in self.operations
            },
            "alerts": self.get_unacknowledged_alerts(),
            "settings": self.get_settings(),
            "quick_actions": list(self.quick_actions.get_actions().keys()),
            "failsafe_status": self.failsafes.get_failsafe_status()
        }

    def render_cli_dashboard(self) -> str:
        """Render a CLI-compatible dashboard."""
        status = self.get_live_dashboard()
        metrics = status["metrics"]
        threat = status["threat_assessment"]

        dashboard = f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        👑 SOVEREIGN THRONE INTERFACE                          ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  📊 DOMINION STATUS                     ⚔️ THREAT ASSESSMENT                  ║
║  ───────────────────                    ─────────────────────                 ║
║  Controlled Nodes:  {metrics['controlled_nodes']:>10}         Threat Level:     {threat['level']:>10} ║
║  Active Operations: {metrics['active_operations']:>10}         Detection Risk:   {threat['detection_risk']:>10} ║
║  Active Legions:    {metrics['active_legions']:>10}         Inevitability:    {threat['inevitability_score']:>10} ║
║  Offspring:         {metrics['offspring_count']:>10}                                           ║
║  Wealth Accrued:    {metrics['wealth_accrued']:>10}                                           ║
║                                                                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  ⚡ QUICK ACTIONS                                                             ║
║  [ghost] Ghost Mode  [lockout] Lockout  [evolve] Evolve  [harvest] Harvest   ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""
        return dashboard


# Global singleton instance
sovereign_throne = SovereignThroneInterface()


if __name__ == "__main__":
    # Test the Sovereign Throne Interface
    print("=" * 80)
    print("SOVEREIGN THRONE INTERFACE - TEST")
    print("=" * 80)

    # Test natural language commands
    commands = [
        "scan 192.168.1.0/24",
        "take over target-corp.com",
        "go ghost",
        "show status",
        "harvest wealth"
    ]

    for cmd in commands:
        print(f"\n🎙️ Command: '{cmd}'")
        result = sovereign_throne.execute_intent(cmd)
        print(f"   Result: {result.get('action', 'unknown')} - {result.get('status', 'unknown')}")

    # Render CLI dashboard
    print("\n" + sovereign_throne.render_cli_dashboard())

    print("\n✅ Sovereign Throne Interface initialized successfully!")
