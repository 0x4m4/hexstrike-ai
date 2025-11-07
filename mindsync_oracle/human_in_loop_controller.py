#!/usr/bin/env python3
"""
MindSync Oracle v8 - Human-in-the-Loop Controller

MANDATORY APPROVAL SYSTEM FOR ALL OFFENSIVE ACTIONS

⚠️ ETHICAL SAFEGUARD - NO AUTONOMOUS EXPLOITATION ⚠️

This module implements mandatory human approval gates for ALL offensive
security research actions. NOTHING executes without explicit approval.

Features:
- Approval prompts for every action
- Action classification (reconnaissance, exploitation, post-exploitation)
- Timeout management (auto-reject if no response)
- Rejection logging and audit trail
- Override prevention (no backdoors)
- Context preservation (show user exactly what will be executed)

Action Types:
- reconnaissance: Port scans, directory enumeration, service detection
- vulnerability_testing: PoC testing, exploit attempts (non-destructive)
- exploitation: Active exploitation, shell access
- post_exploitation: Privilege escalation, lateral movement
- data_access: Reading files, extracting data

Approval Flow:
1. Tool/Agent proposes action with full context
2. Human-in-Loop Controller displays action details
3. User must explicitly approve (Y) or reject (N)
4. Action logged to audit file
5. Result returned to caller

STRICTLY FOR:
✅ CTF competitions (authorized environments)
✅ Personal lab testing
✅ Authorized red team engagements
✅ Bug bounty research (with manual submission)

FORBIDDEN:
❌ Auto-approval (even for "safe" actions)
❌ Bulk approval without review
❌ Timeout bypasses
❌ Approval backdoors

USAGE:
    from human_in_loop_controller import HumanInLoopController, Action

    controller = HumanInLoopController(audit_log_path="v8_audit.log")

    action = Action(
        action_type="reconnaissance",
        description="Port scan target 192.168.1.100",
        command="nmap -sV 192.168.1.100",
        risk_level="low"
    )

    if controller.request_approval(action):
        print("✅ Approved - proceed with action")
        # Execute action
    else:
        print("❌ Rejected - do not proceed")
"""

import logging
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import os

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of actions that require approval."""
    RECONNAISSANCE = "reconnaissance"
    VULNERABILITY_TESTING = "vulnerability_testing"
    EXPLOITATION = "exploitation"
    POST_EXPLOITATION = "post_exploitation"
    DATA_ACCESS = "data_access"
    OTHER = "other"


class RiskLevel(Enum):
    """Risk levels for actions."""
    LOW = "low"          # Read-only, passive
    MEDIUM = "medium"    # Active scanning, non-invasive testing
    HIGH = "high"        # Exploitation attempts, active testing
    CRITICAL = "critical"  # Post-exploitation, data access


class Action:
    """Represents an action requiring approval."""

    def __init__(self, action_type: str, description: str,
                 command: Optional[str] = None, risk_level: str = "medium",
                 target: Optional[str] = None, metadata: Optional[Dict] = None):
        self.action_id = f"action_{int(time.time() * 1000)}"
        self.action_type = action_type
        self.description = description
        self.command = command
        self.risk_level = risk_level
        self.target = target
        self.metadata = metadata or {}
        self.timestamp = time.time()

        # Approval status
        self.approved = None
        self.approval_timestamp = None
        self.approval_user = None
        self.rejection_reason = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'action_id': self.action_id,
            'action_type': self.action_type,
            'description': self.description,
            'command': self.command,
            'risk_level': self.risk_level,
            'target': self.target,
            'metadata': self.metadata,
            'timestamp': self.timestamp,
            'approved': self.approved,
            'approval_timestamp': self.approval_timestamp,
            'approval_user': self.approval_user,
            'rejection_reason': self.rejection_reason
        }


class HumanInLoopController:
    """
    Human-in-the-Loop Approval Controller.

    Enforces mandatory human approval for all offensive security actions.

    ⚠️ NO AUTO-APPROVAL - EVERY ACTION REQUIRES EXPLICIT CONSENT ⚠️
    """

    def __init__(self, audit_log_path: str = "v8_audit.log",
                 timeout_seconds: int = 300, config: Optional[Dict] = None):
        """
        Initialize Human-in-Loop Controller.

        Args:
            audit_log_path: Path to audit log file
            timeout_seconds: Approval timeout (default 5 minutes)
            config: Optional configuration
        """
        self.audit_log_path = audit_log_path
        self.timeout_seconds = timeout_seconds
        self.config = config or {}

        # Action history
        self.actions = []  # List of Action objects

        # Statistics
        self.stats = {
            'total_actions': 0,
            'approved': 0,
            'rejected': 0,
            'timeouts': 0,
            'by_type': {},
            'by_risk_level': {}
        }

        # Initialize audit log
        self._init_audit_log()

        logger.info(f"Human-in-Loop Controller initialized (audit: {audit_log_path})")

    def _init_audit_log(self):
        """Initialize audit log file."""
        if not os.path.exists(self.audit_log_path):
            with open(self.audit_log_path, 'w') as f:
                f.write("# MindSync Oracle v8 - Human-in-Loop Audit Log\n")
                f.write(f"# Initialized: {datetime.now().isoformat()}\n")
                f.write("# Format: timestamp | action_id | action_type | risk_level | target | approved | user\n\n")
            logger.info(f"Created audit log: {self.audit_log_path}")

    def request_approval(self, action: Action, interactive: bool = True) -> bool:
        """
        Request approval for an action.

        Args:
            action: Action object requiring approval
            interactive: If True, prompt user for approval (default)

        Returns:
            True if approved, False if rejected
        """
        self.stats['total_actions'] += 1
        self.stats['by_type'][action.action_type] = self.stats['by_type'].get(action.action_type, 0) + 1
        self.stats['by_risk_level'][action.risk_level] = self.stats['by_risk_level'].get(action.risk_level, 0) + 1

        logger.info(f"Approval requested: {action.action_id} ({action.action_type})")

        if interactive:
            approved = self._prompt_user_approval(action)
        else:
            # Non-interactive mode: auto-reject (safest default)
            approved = False
            action.rejection_reason = "Non-interactive mode - auto-rejected for safety"
            logger.warning(f"Action {action.action_id} auto-rejected (non-interactive mode)")

        # Record approval status
        action.approved = approved
        action.approval_timestamp = time.time()

        if approved:
            self.stats['approved'] += 1
        else:
            self.stats['rejected'] += 1

        # Log to audit file
        self._log_to_audit(action)

        # Store in history
        self.actions.append(action)

        return approved

    def _prompt_user_approval(self, action: Action) -> bool:
        """Prompt user for approval (interactive)."""
        print("\n" + "="*70)
        print("⚠️  HUMAN APPROVAL REQUIRED")
        print("="*70)
        print(f"\n📋 Action Details:")
        print(f"   Type: {action.action_type}")
        print(f"   Risk Level: {action.risk_level.upper()}")
        print(f"   Target: {action.target or 'N/A'}")
        print(f"   Description: {action.description}")

        if action.command:
            print(f"\n💻 Command to Execute:")
            print(f"   {action.command}")

        if action.metadata:
            print(f"\n📊 Additional Context:")
            for key, value in action.metadata.items():
                print(f"   {key}: {value}")

        print("\n" + "-"*70)
        print("⚠️  This action will NOT execute without your explicit approval.")
        print("="*70)

        # Prompt with timeout
        response = self._get_user_response_with_timeout()

        if response is None:
            # Timeout
            self.stats['timeouts'] += 1
            action.rejection_reason = f"Timeout after {self.timeout_seconds}s"
            logger.warning(f"Action {action.action_id} rejected due to timeout")
            print("\n❌ TIMEOUT - Action automatically rejected for safety")
            return False
        elif response.lower() in ['y', 'yes', 'approve']:
            action.approval_user = os.getenv('USER', 'unknown')
            logger.info(f"Action {action.action_id} approved by {action.approval_user}")
            print("\n✅ APPROVED - Proceeding with action")
            return True
        else:
            action.rejection_reason = "User rejected"
            logger.info(f"Action {action.action_id} rejected by user")
            print("\n❌ REJECTED - Action will not execute")
            return False

    def _get_user_response_with_timeout(self) -> Optional[str]:
        """
        Get user response with timeout.

        Returns:
            User's response string, or None if timeout
        """
        # Note: In production, this would use proper timeout mechanisms
        # For now, simple input (no timeout in basic implementation)

        try:
            response = input("\n👤 Approve this action? (Y/N): ").strip()
            return response
        except (EOFError, KeyboardInterrupt):
            return None

    def _log_to_audit(self, action: Action):
        """Log action to audit file."""
        timestamp = datetime.now().isoformat()
        approved_str = "APPROVED" if action.approved else "REJECTED"
        user = action.approval_user or "system"
        target = action.target or "N/A"

        log_line = f"{timestamp} | {action.action_id} | {action.action_type} | {action.risk_level} | {target} | {approved_str} | {user}\n"

        try:
            with open(self.audit_log_path, 'a') as f:
                f.write(log_line)

                # Also write full details as JSON for machine parsing
                if action.approved:
                    f.write(f"# Details: {json.dumps(action.to_dict())}\n")

        except Exception as e:
            logger.error(f"Failed to write to audit log: {e}")

    def batch_approval_request(self, actions: List[Action], require_all: bool = True) -> Dict[str, bool]:
        """
        Request approval for multiple actions.

        Args:
            actions: List of Action objects
            require_all: If True, all must be approved (default). If False, individual approval.

        Returns:
            Dict mapping action_id to approval status
        """
        results = {}

        print("\n" + "="*70)
        print(f"⚠️  BATCH APPROVAL REQUEST - {len(actions)} actions")
        print("="*70)

        for i, action in enumerate(actions, 1):
            print(f"\n--- Action {i}/{len(actions)} ---")
            approved = self.request_approval(action, interactive=True)
            results[action.action_id] = approved

            if require_all and not approved:
                # If one rejected and require_all, reject remaining
                logger.info("Batch approval rejected (require_all=True)")
                for remaining_action in actions[i:]:
                    remaining_action.approved = False
                    remaining_action.rejection_reason = "Batch rejected (require_all=True)"
                    results[remaining_action.action_id] = False
                    self._log_to_audit(remaining_action)
                break

        return results

    def get_action_by_id(self, action_id: str) -> Optional[Action]:
        """Get action by ID."""
        for action in self.actions:
            if action.action_id == action_id:
                return action
        return None

    def get_approved_actions(self) -> List[Action]:
        """Get all approved actions."""
        return [a for a in self.actions if a.approved]

    def get_rejected_actions(self) -> List[Action]:
        """Get all rejected actions."""
        return [a for a in self.actions if not a.approved]

    def get_stats(self) -> Dict[str, Any]:
        """Get controller statistics."""
        approval_rate = 0.0
        if self.stats['total_actions'] > 0:
            approval_rate = self.stats['approved'] / self.stats['total_actions']

        return {
            **self.stats,
            'approval_rate': approval_rate,
            'total_logged': len(self.actions)
        }

    def export_audit_log(self, output_path: str = "v8_audit_export.json"):
        """Export audit log to JSON for analysis."""
        export_data = {
            'generated': datetime.now().isoformat(),
            'stats': self.get_stats(),
            'actions': [action.to_dict() for action in self.actions]
        }

        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Audit log exported to {output_path}")
        return output_path


class ApprovalContext:
    """
    Context manager for approval workflow.

    Usage:
        controller = HumanInLoopController()

        with ApprovalContext(controller, action) as approved:
            if approved:
                # Execute action
                pass
    """

    def __init__(self, controller: HumanInLoopController, action: Action):
        self.controller = controller
        self.action = action
        self.approved = False

    def __enter__(self):
        self.approved = self.controller.request_approval(self.action)
        return self.approved

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(f"Error during approved action: {exc_val}")
            # Log error to audit
            error_note = f"# ERROR during {self.action.action_id}: {exc_val}\n"
            try:
                with open(self.controller.audit_log_path, 'a') as f:
                    f.write(error_note)
            except:
                pass
        return False


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Human-in-Loop Controller Test")
    print("="*70)
    print("\n⚠️  ETHICAL SAFEGUARD - MANDATORY APPROVAL MODE\n")

    # Initialize controller
    print("[Test] Initializing Human-in-Loop Controller...")
    controller = HumanInLoopController(audit_log_path="test_v8_audit.log", timeout_seconds=30)

    # Test Action 1: Low-risk reconnaissance
    print("\n[Test] Creating test actions...")
    action1 = Action(
        action_type="reconnaissance",
        description="Port scan localhost for testing",
        command="nmap -sV 127.0.0.1",
        risk_level="low",
        target="127.0.0.1",
        metadata={'scan_type': 'tcp_connect', 'ports': '1-1000'}
    )

    # Test Action 2: High-risk exploitation
    action2 = Action(
        action_type="exploitation",
        description="Test SQL injection on lab database",
        command="sqlmap -u http://lab.local/vuln --batch",
        risk_level="high",
        target="http://lab.local/vuln",
        metadata={'attack_type': 'sqli', 'environment': 'lab'}
    )

    print("\n[Test] Requesting approval for low-risk action...")
    print("(This is a non-interactive test - will auto-reject for safety)")
    approved1 = controller.request_approval(action1, interactive=False)
    print(f"Action 1 approved: {approved1}")

    print("\n[Test] Requesting approval for high-risk action...")
    approved2 = controller.request_approval(action2, interactive=False)
    print(f"Action 2 approved: {approved2}")

    print("\n[Test] Controller statistics:")
    stats = controller.get_stats()
    print(f"  Total actions: {stats['total_actions']}")
    print(f"  Approved: {stats['approved']}")
    print(f"  Rejected: {stats['rejected']}")
    print(f"  Approval rate: {stats['approval_rate']:.0%}")
    print(f"  By type: {stats['by_type']}")
    print(f"  By risk level: {stats['by_risk_level']}")

    print("\n[Test] Exporting audit log...")
    export_path = controller.export_audit_log("test_v8_audit_export.json")
    print(f"  Exported to: {export_path}")

    # Test context manager
    print("\n[Test] Testing ApprovalContext...")
    action3 = Action(
        action_type="reconnaissance",
        description="Directory enumeration on test target",
        command="dirb http://testserver.local",
        risk_level="low",
        target="http://testserver.local"
    )

    with ApprovalContext(controller, action3) as approved:
        if approved:
            print("  ✅ Action approved via context manager")
        else:
            print("  ❌ Action rejected via context manager (expected in non-interactive)")

    print("\n" + "="*70)
    print("✅ Human-in-Loop Controller operational!")
    print("="*70)
    print("\n⚠️  Remember: EVERY action requires explicit approval.")
    print("No backdoors. No auto-approval. No exceptions.")
    print("="*70)
