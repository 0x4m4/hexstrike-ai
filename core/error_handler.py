"""
Intelligent Error Handler - Advanced Error Recovery System

This module provides sophisticated error handling and automatic recovery
strategies for HexStrike, including:
- Error classification and pattern matching
- Intelligent recovery strategy selection
- Tool alternative suggestions
- Parameter auto-adjustment
- Human escalation with full context

Part of the HexStrike modular refactoring (Phase 3).
"""

import re
import os
import json
import logging
import traceback
import psutil
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

# Import visual engine for formatted output
from core.visual import ModernVisualEngine

logger = logging.getLogger(__name__)


# ============================================================================
# ERROR TYPES AND RECOVERY ACTIONS
# ============================================================================

class ErrorType(Enum):
    """Enumeration of different error types for intelligent handling"""
    TIMEOUT = "timeout"
    PERMISSION_DENIED = "permission_denied"
    NETWORK_UNREACHABLE = "network_unreachable"
    RATE_LIMITED = "rate_limited"
    TOOL_NOT_FOUND = "tool_not_found"
    INVALID_PARAMETERS = "invalid_parameters"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    AUTHENTICATION_FAILED = "authentication_failed"
    TARGET_UNREACHABLE = "target_unreachable"
    PARSING_ERROR = "parsing_error"
    UNKNOWN = "unknown"


class RecoveryAction(Enum):
    """Types of recovery actions that can be taken"""
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    RETRY_WITH_REDUCED_SCOPE = "retry_with_reduced_scope"
    SWITCH_TO_ALTERNATIVE_TOOL = "switch_to_alternative_tool"
    ADJUST_PARAMETERS = "adjust_parameters"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    ABORT_OPERATION = "abort_operation"


@dataclass
class ErrorContext:
    """Context information for error handling decisions"""
    tool_name: str
    target: str
    parameters: Dict[str, Any]
    error_type: ErrorType
    error_message: str
    attempt_count: int
    timestamp: datetime
    stack_trace: str
    system_resources: Dict[str, Any]
    previous_errors: List['ErrorContext'] = field(default_factory=list)


@dataclass
class RecoveryStrategy:
    """Recovery strategy with configuration"""
    action: RecoveryAction
    parameters: Dict[str, Any]
    max_attempts: int
    backoff_multiplier: float
    success_probability: float
    estimated_time: int  # seconds


# ============================================================================
# INTELLIGENT ERROR HANDLER
# ============================================================================

class IntelligentErrorHandler:
    """Advanced error handling with automatic recovery strategies"""

    def __init__(self):
        self.error_patterns = self._initialize_error_patterns()
        self.recovery_strategies = self._initialize_recovery_strategies()
        self.tool_alternatives = self._initialize_tool_alternatives()
        self.parameter_adjustments = self._initialize_parameter_adjustments()
        self.error_history = []
        self.max_history_size = 1000

    def _initialize_error_patterns(self) -> Dict[str, ErrorType]:
        """Initialize error pattern recognition"""
        return {
            # Timeout patterns
            r"timeout|timed out|connection timeout|read timeout": ErrorType.TIMEOUT,
            r"operation timed out|command timeout": ErrorType.TIMEOUT,

            # Permission patterns
            r"permission denied|access denied|forbidden|not authorized": ErrorType.PERMISSION_DENIED,
            r"sudo required|root required|insufficient privileges": ErrorType.PERMISSION_DENIED,

            # Network patterns
            r"network unreachable|host unreachable|no route to host": ErrorType.NETWORK_UNREACHABLE,
            r"connection refused|connection reset|network error": ErrorType.NETWORK_UNREACHABLE,

            # Rate limiting patterns
            r"rate limit|too many requests|throttled|429": ErrorType.RATE_LIMITED,
            r"request limit exceeded|quota exceeded": ErrorType.RATE_LIMITED,

            # Tool not found patterns
            r"command not found|no such file or directory|not found": ErrorType.TOOL_NOT_FOUND,
            r"executable not found|binary not found": ErrorType.TOOL_NOT_FOUND,

            # Parameter patterns
            r"invalid argument|invalid option|unknown option": ErrorType.INVALID_PARAMETERS,
            r"bad parameter|invalid parameter|syntax error": ErrorType.INVALID_PARAMETERS,

            # Resource patterns
            r"out of memory|memory error|disk full|no space left": ErrorType.RESOURCE_EXHAUSTED,
            r"resource temporarily unavailable|too many open files": ErrorType.RESOURCE_EXHAUSTED,

            # Authentication patterns
            r"authentication failed|login failed|invalid credentials": ErrorType.AUTHENTICATION_FAILED,
            r"unauthorized|invalid token|expired token": ErrorType.AUTHENTICATION_FAILED,

            # Target patterns
            r"target unreachable|target not responding|target down": ErrorType.TARGET_UNREACHABLE,
            r"host not found|dns resolution failed": ErrorType.TARGET_UNREACHABLE,

            # Parsing patterns
            r"parse error|parsing failed|invalid format|malformed": ErrorType.PARSING_ERROR,
            r"json decode error|xml parse error|invalid json": ErrorType.PARSING_ERROR
        }

    def _initialize_recovery_strategies(self) -> Dict[ErrorType, List[RecoveryStrategy]]:
        """Initialize recovery strategies for different error types"""
        return {
            ErrorType.TIMEOUT: [
                RecoveryStrategy(
                    action=RecoveryAction.RETRY_WITH_BACKOFF,
                    parameters={"initial_delay": 5, "max_delay": 60},
                    max_attempts=3,
                    backoff_multiplier=2.0,
                    success_probability=0.7,
                    estimated_time=30
                ),
                RecoveryStrategy(
                    action=RecoveryAction.RETRY_WITH_REDUCED_SCOPE,
                    parameters={"reduce_threads": True, "reduce_timeout": True},
                    max_attempts=2,
                    backoff_multiplier=1.0,
                    success_probability=0.8,
                    estimated_time=45
                ),
                RecoveryStrategy(
                    action=RecoveryAction.SWITCH_TO_ALTERNATIVE_TOOL,
                    parameters={"prefer_faster_tools": True},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=0.6,
                    estimated_time=60
                )
            ],
            ErrorType.PERMISSION_DENIED: [
                RecoveryStrategy(
                    action=RecoveryAction.ESCALATE_TO_HUMAN,
                    parameters={"message": "Privilege escalation required", "urgency": "medium"},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=0.9,
                    estimated_time=300
                ),
                RecoveryStrategy(
                    action=RecoveryAction.SWITCH_TO_ALTERNATIVE_TOOL,
                    parameters={"require_no_privileges": True},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=0.5,
                    estimated_time=30
                )
            ],
            ErrorType.NETWORK_UNREACHABLE: [
                RecoveryStrategy(
                    action=RecoveryAction.RETRY_WITH_BACKOFF,
                    parameters={"initial_delay": 10, "max_delay": 120},
                    max_attempts=3,
                    backoff_multiplier=2.0,
                    success_probability=0.6,
                    estimated_time=60
                ),
                RecoveryStrategy(
                    action=RecoveryAction.SWITCH_TO_ALTERNATIVE_TOOL,
                    parameters={"prefer_offline_tools": True},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=0.4,
                    estimated_time=30
                )
            ],
            ErrorType.RATE_LIMITED: [
                RecoveryStrategy(
                    action=RecoveryAction.RETRY_WITH_BACKOFF,
                    parameters={"initial_delay": 30, "max_delay": 300},
                    max_attempts=5,
                    backoff_multiplier=1.5,
                    success_probability=0.9,
                    estimated_time=180
                ),
                RecoveryStrategy(
                    action=RecoveryAction.ADJUST_PARAMETERS,
                    parameters={"reduce_rate": True, "increase_delays": True},
                    max_attempts=2,
                    backoff_multiplier=1.0,
                    success_probability=0.8,
                    estimated_time=120
                )
            ],
            ErrorType.TOOL_NOT_FOUND: [
                RecoveryStrategy(
                    action=RecoveryAction.SWITCH_TO_ALTERNATIVE_TOOL,
                    parameters={"find_equivalent": True},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=0.7,
                    estimated_time=15
                ),
                RecoveryStrategy(
                    action=RecoveryAction.ESCALATE_TO_HUMAN,
                    parameters={"message": "Tool installation required", "urgency": "low"},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=0.9,
                    estimated_time=600
                )
            ],
            ErrorType.INVALID_PARAMETERS: [
                RecoveryStrategy(
                    action=RecoveryAction.ADJUST_PARAMETERS,
                    parameters={"use_defaults": True, "remove_invalid": True},
                    max_attempts=3,
                    backoff_multiplier=1.0,
                    success_probability=0.8,
                    estimated_time=10
                ),
                RecoveryStrategy(
                    action=RecoveryAction.SWITCH_TO_ALTERNATIVE_TOOL,
                    parameters={"simpler_interface": True},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=0.6,
                    estimated_time=30
                )
            ],
            ErrorType.RESOURCE_EXHAUSTED: [
                RecoveryStrategy(
                    action=RecoveryAction.RETRY_WITH_REDUCED_SCOPE,
                    parameters={"reduce_memory": True, "reduce_threads": True},
                    max_attempts=2,
                    backoff_multiplier=1.0,
                    success_probability=0.7,
                    estimated_time=60
                ),
                RecoveryStrategy(
                    action=RecoveryAction.RETRY_WITH_BACKOFF,
                    parameters={"initial_delay": 60, "max_delay": 300},
                    max_attempts=2,
                    backoff_multiplier=2.0,
                    success_probability=0.5,
                    estimated_time=180
                )
            ],
            ErrorType.AUTHENTICATION_FAILED: [
                RecoveryStrategy(
                    action=RecoveryAction.ESCALATE_TO_HUMAN,
                    parameters={"message": "Authentication credentials required", "urgency": "high"},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=0.9,
                    estimated_time=300
                ),
                RecoveryStrategy(
                    action=RecoveryAction.SWITCH_TO_ALTERNATIVE_TOOL,
                    parameters={"no_auth_required": True},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=0.4,
                    estimated_time=30
                )
            ],
            ErrorType.TARGET_UNREACHABLE: [
                RecoveryStrategy(
                    action=RecoveryAction.RETRY_WITH_BACKOFF,
                    parameters={"initial_delay": 15, "max_delay": 180},
                    max_attempts=3,
                    backoff_multiplier=2.0,
                    success_probability=0.6,
                    estimated_time=90
                ),
                RecoveryStrategy(
                    action=RecoveryAction.GRACEFUL_DEGRADATION,
                    parameters={"skip_target": True, "continue_with_others": True},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=1.0,
                    estimated_time=5
                )
            ],
            ErrorType.PARSING_ERROR: [
                RecoveryStrategy(
                    action=RecoveryAction.ADJUST_PARAMETERS,
                    parameters={"change_output_format": True, "add_parsing_flags": True},
                    max_attempts=2,
                    backoff_multiplier=1.0,
                    success_probability=0.7,
                    estimated_time=20
                ),
                RecoveryStrategy(
                    action=RecoveryAction.SWITCH_TO_ALTERNATIVE_TOOL,
                    parameters={"better_output_format": True},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=0.6,
                    estimated_time=30
                )
            ],
            ErrorType.UNKNOWN: [
                RecoveryStrategy(
                    action=RecoveryAction.RETRY_WITH_BACKOFF,
                    parameters={"initial_delay": 5, "max_delay": 30},
                    max_attempts=2,
                    backoff_multiplier=2.0,
                    success_probability=0.3,
                    estimated_time=45
                ),
                RecoveryStrategy(
                    action=RecoveryAction.ESCALATE_TO_HUMAN,
                    parameters={"message": "Unknown error encountered", "urgency": "medium"},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=0.9,
                    estimated_time=300
                )
            ]
        }

    def _initialize_tool_alternatives(self) -> Dict[str, List[str]]:
        """Initialize alternative tools for fallback scenarios"""
        return {
            # Network scanning alternatives
            "nmap": ["rustscan", "masscan", "zmap"],
            "rustscan": ["nmap", "masscan"],
            "masscan": ["nmap", "rustscan", "zmap"],

            # Directory/file discovery alternatives
            "gobuster": ["feroxbuster", "dirsearch", "ffuf", "dirb"],
            "feroxbuster": ["gobuster", "dirsearch", "ffuf"],
            "dirsearch": ["gobuster", "feroxbuster", "ffuf"],
            "ffuf": ["gobuster", "feroxbuster", "dirsearch"],

            # Vulnerability scanning alternatives
            "nuclei": ["jaeles", "nikto", "w3af"],
            "jaeles": ["nuclei", "nikto"],
            "nikto": ["nuclei", "jaeles", "w3af"],

            # Web crawling alternatives
            "katana": ["gau", "waybackurls", "hakrawler"],
            "gau": ["katana", "waybackurls", "hakrawler"],
            "waybackurls": ["gau", "katana", "hakrawler"],

            # Parameter discovery alternatives
            "arjun": ["paramspider", "x8", "ffuf"],
            "paramspider": ["arjun", "x8"],
            "x8": ["arjun", "paramspider"],

            # SQL injection alternatives
            "sqlmap": ["sqlninja", "jsql-injection"],

            # XSS testing alternatives
            "dalfox": ["xsser", "xsstrike"],

            # Subdomain enumeration alternatives
            "subfinder": ["amass", "assetfinder", "findomain"],
            "amass": ["subfinder", "assetfinder", "findomain"],
            "assetfinder": ["subfinder", "amass", "findomain"],

            # Cloud security alternatives
            "prowler": ["scout-suite", "cloudmapper"],
            "scout-suite": ["prowler", "cloudmapper"],

            # Container security alternatives
            "trivy": ["clair", "docker-bench-security"],
            "clair": ["trivy", "docker-bench-security"],

            # Binary analysis alternatives
            "ghidra": ["radare2", "ida", "binary-ninja"],
            "radare2": ["ghidra", "objdump", "gdb"],
            "gdb": ["radare2", "lldb"],

            # Exploitation alternatives
            "pwntools": ["ropper", "ropgadget"],
            "ropper": ["ropgadget", "pwntools"],
            "ropgadget": ["ropper", "pwntools"]
        }

    def _initialize_parameter_adjustments(self) -> Dict[str, Dict[ErrorType, Dict[str, Any]]]:
        """Initialize parameter adjustments for different error types and tools"""
        return {
            "nmap": {
                ErrorType.TIMEOUT: {"timing": "-T2", "reduce_ports": True},
                ErrorType.RATE_LIMITED: {"timing": "-T1", "delay": "1000ms"},
                ErrorType.RESOURCE_EXHAUSTED: {"max_parallelism": "10"}
            },
            "gobuster": {
                ErrorType.TIMEOUT: {"threads": "10", "timeout": "30s"},
                ErrorType.RATE_LIMITED: {"threads": "5", "delay": "1s"},
                ErrorType.RESOURCE_EXHAUSTED: {"threads": "5"}
            },
            "nuclei": {
                ErrorType.TIMEOUT: {"concurrency": "10", "timeout": "30"},
                ErrorType.RATE_LIMITED: {"rate-limit": "10", "concurrency": "5"},
                ErrorType.RESOURCE_EXHAUSTED: {"concurrency": "5"}
            },
            "feroxbuster": {
                ErrorType.TIMEOUT: {"threads": "10", "timeout": "30"},
                ErrorType.RATE_LIMITED: {"threads": "5", "rate-limit": "10"},
                ErrorType.RESOURCE_EXHAUSTED: {"threads": "5"}
            },
            "ffuf": {
                ErrorType.TIMEOUT: {"threads": "10", "timeout": "30"},
                ErrorType.RATE_LIMITED: {"threads": "5", "rate": "10"},
                ErrorType.RESOURCE_EXHAUSTED: {"threads": "5"}
            }
        }

    def classify_error(self, error_message: str, exception: Exception = None) -> ErrorType:
        """Classify error based on message and exception type"""
        error_text = error_message.lower()

        # Check exception type first
        if exception:
            if isinstance(exception, TimeoutError):
                return ErrorType.TIMEOUT
            elif isinstance(exception, PermissionError):
                return ErrorType.PERMISSION_DENIED
            elif isinstance(exception, ConnectionError):
                return ErrorType.NETWORK_UNREACHABLE
            elif isinstance(exception, FileNotFoundError):
                return ErrorType.TOOL_NOT_FOUND

        # Check error patterns
        for pattern, error_type in self.error_patterns.items():
            if re.search(pattern, error_text, re.IGNORECASE):
                return error_type

        return ErrorType.UNKNOWN

    def handle_tool_failure(self, tool: str, error: Exception, context: Dict[str, Any]) -> RecoveryStrategy:
        """Determine best recovery action for tool failures"""
        error_message = str(error)
        error_type = self.classify_error(error_message, error)

        # Create error context
        error_context = ErrorContext(
            tool_name=tool,
            target=context.get('target', 'unknown'),
            parameters=context.get('parameters', {}),
            error_type=error_type,
            error_message=error_message,
            attempt_count=context.get('attempt_count', 1),
            timestamp=datetime.now(),
            stack_trace=traceback.format_exc(),
            system_resources=self._get_system_resources()
        )

        # Add to error history
        self._add_to_history(error_context)

        # Get recovery strategies for this error type
        strategies = self.recovery_strategies.get(error_type, self.recovery_strategies[ErrorType.UNKNOWN])

        # Select best strategy based on context
        best_strategy = self._select_best_strategy(strategies, error_context)

        error_message = f'{error_type.value} - Applying {best_strategy.action.value}'
        logger.warning(f"{ModernVisualEngine.format_error_card('RECOVERY', tool, error_message)}")

        return best_strategy

    def _select_best_strategy(self, strategies: List[RecoveryStrategy], context: ErrorContext) -> RecoveryStrategy:
        """Select the best recovery strategy based on context"""
        # Filter strategies based on attempt count
        viable_strategies = [s for s in strategies if context.attempt_count <= s.max_attempts]

        if not viable_strategies:
            # If all strategies exhausted, escalate to human
            return RecoveryStrategy(
                action=RecoveryAction.ESCALATE_TO_HUMAN,
                parameters={"message": f"All recovery strategies exhausted for {context.tool_name}", "urgency": "high"},
                max_attempts=1,
                backoff_multiplier=1.0,
                success_probability=0.9,
                estimated_time=300
            )

        # Score strategies based on success probability and estimated time
        scored_strategies = []
        for strategy in viable_strategies:
            # Adjust success probability based on previous failures
            adjusted_probability = strategy.success_probability * (0.9 ** (context.attempt_count - 1))

            # Prefer strategies with higher success probability and lower time
            score = adjusted_probability - (strategy.estimated_time / 1000.0)
            scored_strategies.append((score, strategy))

        # Return strategy with highest score
        scored_strategies.sort(key=lambda x: x[0], reverse=True)
        return scored_strategies[0][1]

    def auto_adjust_parameters(self, tool: str, error_type: ErrorType, original_params: Dict[str, Any]) -> Dict[str, Any]:
        """Automatically adjust tool parameters based on error patterns"""
        adjustments = self.parameter_adjustments.get(tool, {}).get(error_type, {})

        if not adjustments:
            # Generic adjustments based on error type
            if error_type == ErrorType.TIMEOUT:
                adjustments = {"timeout": "60", "threads": "5"}
            elif error_type == ErrorType.RATE_LIMITED:
                adjustments = {"delay": "2s", "threads": "3"}
            elif error_type == ErrorType.RESOURCE_EXHAUSTED:
                adjustments = {"threads": "3", "memory_limit": "1G"}

        # Apply adjustments to original parameters
        adjusted_params = original_params.copy()
        adjusted_params.update(adjustments)

        adjustment_info = f'Parameters adjusted: {adjustments}'
        logger.info(f"{ModernVisualEngine.format_tool_status(tool, 'RECOVERY', adjustment_info)}")

        return adjusted_params

    def get_alternative_tool(self, failed_tool: str, context: Dict[str, Any]) -> Optional[str]:
        """Get alternative tool for failed tool"""
        alternatives = self.tool_alternatives.get(failed_tool, [])

        if not alternatives:
            return None

        # Filter alternatives based on context requirements
        filtered_alternatives = []
        for alt in alternatives:
            if context.get('require_no_privileges') and alt in ['nmap', 'masscan']:
                continue  # Skip tools that typically require privileges
            if context.get('prefer_faster_tools') and alt in ['amass', 'w3af']:
                continue  # Skip slower tools
            filtered_alternatives.append(alt)

        if not filtered_alternatives:
            filtered_alternatives = alternatives

        # Return first available alternative
        return filtered_alternatives[0] if filtered_alternatives else None

    def escalate_to_human(self, context: ErrorContext, urgency: str = "medium") -> Dict[str, Any]:
        """Escalate complex errors to human operator with full context"""
        escalation_data = {
            "timestamp": context.timestamp.isoformat(),
            "tool": context.tool_name,
            "target": context.target,
            "error_type": context.error_type.value,
            "error_message": context.error_message,
            "attempt_count": context.attempt_count,
            "urgency": urgency,
            "suggested_actions": self._get_human_suggestions(context),
            "context": {
                "parameters": context.parameters,
                "system_resources": context.system_resources,
                "recent_errors": [e.error_message for e in context.previous_errors[-5:]]
            }
        }

        # Log escalation with enhanced formatting
        logger.error(f"{ModernVisualEngine.format_error_card('CRITICAL', context.tool_name, context.error_message, 'HUMAN ESCALATION REQUIRED')}")
        logger.error(f"{ModernVisualEngine.format_highlighted_text('ESCALATION DETAILS', 'RED')}")
        logger.error(f"{json.dumps(escalation_data, indent=2)}")

        return escalation_data

    def _get_human_suggestions(self, context: ErrorContext) -> List[str]:
        """Get human-readable suggestions for error resolution"""
        suggestions = []

        if context.error_type == ErrorType.PERMISSION_DENIED:
            suggestions.extend([
                "Run the command with sudo privileges",
                "Check file/directory permissions",
                "Verify user is in required groups"
            ])
        elif context.error_type == ErrorType.TOOL_NOT_FOUND:
            suggestions.extend([
                f"Install {context.tool_name} using package manager",
                "Check if tool is in PATH",
                "Verify tool installation"
            ])
        elif context.error_type == ErrorType.NETWORK_UNREACHABLE:
            suggestions.extend([
                "Check network connectivity",
                "Verify target is accessible",
                "Check firewall rules"
            ])
        elif context.error_type == ErrorType.RATE_LIMITED:
            suggestions.extend([
                "Wait before retrying",
                "Use slower scan rates",
                "Check API rate limits"
            ])
        else:
            suggestions.append("Review error details and logs")

        return suggestions

    def _get_system_resources(self) -> Dict[str, Any]:
        """Get current system resource information"""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None,
                "active_processes": len(psutil.pids())
            }
        except Exception:
            return {"error": "Unable to get system resources"}

    def _add_to_history(self, error_context: ErrorContext):
        """Add error context to history"""
        self.error_history.append(error_context)

        # Maintain history size limit
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size:]

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring"""
        if not self.error_history:
            return {"total_errors": 0}

        error_counts = {}
        tool_errors = {}
        recent_errors = []

        # Count errors by type and tool
        for error in self.error_history:
            error_type = error.error_type.value
            tool = error.tool_name

            error_counts[error_type] = error_counts.get(error_type, 0) + 1
            tool_errors[tool] = tool_errors.get(tool, 0) + 1

            # Recent errors (last hour)
            if (datetime.now() - error.timestamp).total_seconds() < 3600:
                recent_errors.append({
                    "tool": tool,
                    "error_type": error_type,
                    "timestamp": error.timestamp.isoformat()
                })

        return {
            "total_errors": len(self.error_history),
            "error_counts_by_type": error_counts,
            "error_counts_by_tool": tool_errors,
            "recent_errors_count": len(recent_errors),
            "recent_errors": recent_errors[-10:]  # Last 10 recent errors
        }


# ============================================================================
# GLOBAL ERROR HANDLER INSTANCE
# ============================================================================

error_handler = IntelligentErrorHandler()
