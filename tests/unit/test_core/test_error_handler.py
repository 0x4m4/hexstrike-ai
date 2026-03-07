"""
Unit tests for IntelligentErrorHandler

Tests cover:
- Error classification and pattern matching
- Recovery strategy selection
- Tool alternatives
- Parameter adjustments
- Retry logic with backoff
- Human escalation
- Error history tracking
- System resource monitoring
- Edge cases and error handling

Target: 95%+ code coverage with 30+ comprehensive tests
"""

import pytest
import sys
import os
import psutil
import traceback
from unittest.mock import patch, MagicMock
from datetime import datetime
from typing import Dict, List, Any

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from core.error_handler import (
    IntelligentErrorHandler,
    ErrorType,
    RecoveryAction,
    ErrorContext,
    RecoveryStrategy
)


class TestErrorHandlerInitialization:
    """Test IntelligentErrorHandler initialization"""

    def test_handler_initializes_successfully(self):
        """Test error handler initializes with all required components"""
        handler = IntelligentErrorHandler()
        assert handler.error_patterns is not None
        assert handler.recovery_strategies is not None
        assert handler.tool_alternatives is not None
        assert handler.parameter_adjustments is not None
        assert handler.error_history == []
        assert handler.max_history_size == 1000

    def test_error_patterns_initialized(self):
        """Test error patterns are properly initialized"""
        handler = IntelligentErrorHandler()
        assert len(handler.error_patterns) > 0
        assert isinstance(handler.error_patterns, dict)
        # Verify some key patterns exist
        assert any("timeout" in pattern.lower() for pattern in handler.error_patterns.keys())
        assert any("permission" in pattern.lower() for pattern in handler.error_patterns.keys())

    def test_recovery_strategies_initialized(self):
        """Test recovery strategies for all error types"""
        handler = IntelligentErrorHandler()
        # All error types should have recovery strategies
        for error_type in ErrorType:
            assert error_type in handler.recovery_strategies
            strategies = handler.recovery_strategies[error_type]
            assert isinstance(strategies, list)
            assert len(strategies) > 0

    def test_tool_alternatives_initialized(self):
        """Test tool alternatives are initialized"""
        handler = IntelligentErrorHandler()
        assert len(handler.tool_alternatives) > 0
        # Verify some common tools have alternatives
        assert "nmap" in handler.tool_alternatives
        assert "gobuster" in handler.tool_alternatives
        assert "nuclei" in handler.tool_alternatives

    def test_parameter_adjustments_initialized(self):
        """Test parameter adjustments are initialized"""
        handler = IntelligentErrorHandler()
        assert len(handler.parameter_adjustments) > 0
        assert isinstance(handler.parameter_adjustments, dict)


class TestErrorClassification:
    """Test error classification logic"""

    def test_classify_timeout_error(self):
        """Test classification of timeout errors"""
        handler = IntelligentErrorHandler()
        error_type = handler.classify_error("Connection timed out")
        assert error_type == ErrorType.TIMEOUT

    def test_classify_timeout_error_variant(self):
        """Test classification of timeout error variants"""
        handler = IntelligentErrorHandler()
        error_type = handler.classify_error("Operation timed out")
        assert error_type == ErrorType.TIMEOUT

    def test_classify_permission_denied(self):
        """Test classification of permission denied errors"""
        handler = IntelligentErrorHandler()
        error_type = handler.classify_error("Permission denied")
        assert error_type == ErrorType.PERMISSION_DENIED

    def test_classify_network_unreachable(self):
        """Test classification of network unreachable errors"""
        handler = IntelligentErrorHandler()
        error_type = handler.classify_error("Network unreachable")
        assert error_type == ErrorType.NETWORK_UNREACHABLE

    def test_classify_rate_limited(self):
        """Test classification of rate limit errors"""
        handler = IntelligentErrorHandler()
        error_type = handler.classify_error("Rate limit exceeded")
        assert error_type == ErrorType.RATE_LIMITED

    def test_classify_tool_not_found(self):
        """Test classification of tool not found errors"""
        handler = IntelligentErrorHandler()
        error_type = handler.classify_error("command not found: nmap")
        assert error_type == ErrorType.TOOL_NOT_FOUND

    def test_classify_invalid_parameters(self):
        """Test classification of invalid parameter errors"""
        handler = IntelligentErrorHandler()
        error_type = handler.classify_error("invalid argument: --unknown")
        assert error_type == ErrorType.INVALID_PARAMETERS

    def test_classify_resource_exhausted(self):
        """Test classification of resource exhaustion errors"""
        handler = IntelligentErrorHandler()
        error_type = handler.classify_error("out of memory")
        assert error_type == ErrorType.RESOURCE_EXHAUSTED

    def test_classify_authentication_failed(self):
        """Test classification of authentication failures"""
        handler = IntelligentErrorHandler()
        error_type = handler.classify_error("authentication failed")
        assert error_type == ErrorType.AUTHENTICATION_FAILED

    def test_classify_target_unreachable(self):
        """Test classification of target unreachable errors"""
        handler = IntelligentErrorHandler()
        error_type = handler.classify_error("target unreachable")
        assert error_type == ErrorType.TARGET_UNREACHABLE

    def test_classify_parsing_error(self):
        """Test classification of parsing errors"""
        handler = IntelligentErrorHandler()
        error_type = handler.classify_error("parse error: invalid JSON")
        assert error_type == ErrorType.PARSING_ERROR

    def test_classify_unknown_error(self):
        """Test classification of unknown errors"""
        handler = IntelligentErrorHandler()
        error_type = handler.classify_error("something went completely wrong")
        assert error_type == ErrorType.UNKNOWN

    def test_classify_error_by_exception_type(self):
        """Test classification by exception type"""
        handler = IntelligentErrorHandler()
        error_type = handler.classify_error("error", TimeoutError())
        assert error_type == ErrorType.TIMEOUT

    def test_classify_permission_error_exception(self):
        """Test classification of PermissionError exception"""
        handler = IntelligentErrorHandler()
        error_type = handler.classify_error("error", PermissionError())
        assert error_type == ErrorType.PERMISSION_DENIED

    def test_classify_connection_error_exception(self):
        """Test classification of ConnectionError exception"""
        handler = IntelligentErrorHandler()
        error_type = handler.classify_error("error", ConnectionError())
        assert error_type == ErrorType.NETWORK_UNREACHABLE

    def test_classify_file_not_found_exception(self):
        """Test classification of FileNotFoundError exception"""
        handler = IntelligentErrorHandler()
        error_type = handler.classify_error("error", FileNotFoundError())
        assert error_type == ErrorType.TOOL_NOT_FOUND

    def test_classify_case_insensitive(self):
        """Test error classification is case insensitive"""
        handler = IntelligentErrorHandler()
        error_type1 = handler.classify_error("TIMEOUT ERROR")
        error_type2 = handler.classify_error("timeout error")
        assert error_type1 == error_type2 == ErrorType.TIMEOUT


class TestRecoveryStrategySelection:
    """Test recovery strategy selection logic"""

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.pids')
    def test_handle_tool_failure_timeout(self, mock_pids, mock_disk, mock_mem, mock_cpu):
        """Test handling of timeout failure"""
        # Mock system resources
        mock_cpu.return_value = 50.0
        mock_mem.return_value = MagicMock(percent=60.0)
        mock_disk.return_value = MagicMock(percent=70.0)
        mock_pids.return_value = [1, 2, 3]

        handler = IntelligentErrorHandler()
        error = Exception("Connection timed out")
        context = {
            'target': 'example.com',
            'parameters': {'timeout': 30},
            'attempt_count': 1
        }

        strategy = handler.handle_tool_failure("nmap", error, context)
        assert isinstance(strategy, RecoveryStrategy)
        assert strategy.action in [RecoveryAction.RETRY_WITH_BACKOFF, RecoveryAction.RETRY_WITH_REDUCED_SCOPE]

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.pids')
    def test_handle_tool_failure_tool_not_found(self, mock_pids, mock_disk, mock_mem, mock_cpu):
        """Test handling of tool not found failure"""
        mock_cpu.return_value = 50.0
        mock_mem.return_value = MagicMock(percent=60.0)
        mock_disk.return_value = MagicMock(percent=70.0)
        mock_pids.return_value = [1, 2, 3]

        handler = IntelligentErrorHandler()
        error = Exception("command not found: gobuster")
        context = {
            'target': 'example.com',
            'parameters': {},
            'attempt_count': 1
        }

        strategy = handler.handle_tool_failure("gobuster", error, context)
        assert isinstance(strategy, RecoveryStrategy)
        assert strategy.action in [RecoveryAction.SWITCH_TO_ALTERNATIVE_TOOL, RecoveryAction.ESCALATE_TO_HUMAN]

    def test_select_best_strategy_first_attempt(self):
        """Test strategy selection on first attempt"""
        handler = IntelligentErrorHandler()
        strategies = handler.recovery_strategies[ErrorType.TIMEOUT]

        context = ErrorContext(
            tool_name="nmap",
            target="example.com",
            parameters={},
            error_type=ErrorType.TIMEOUT,
            error_message="timeout",
            attempt_count=1,
            timestamp=datetime.now(),
            stack_trace="",
            system_resources={}
        )

        best = handler._select_best_strategy(strategies, context)
        assert isinstance(best, RecoveryStrategy)
        assert best.max_attempts >= 1

    def test_select_best_strategy_exhausted(self):
        """Test strategy selection when all attempts exhausted"""
        handler = IntelligentErrorHandler()
        strategies = handler.recovery_strategies[ErrorType.TIMEOUT]

        context = ErrorContext(
            tool_name="nmap",
            target="example.com",
            parameters={},
            error_type=ErrorType.TIMEOUT,
            error_message="timeout",
            attempt_count=100,  # Exceeds max attempts
            timestamp=datetime.now(),
            stack_trace="",
            system_resources={}
        )

        best = handler._select_best_strategy(strategies, context)
        assert best.action == RecoveryAction.ESCALATE_TO_HUMAN


class TestParameterAdjustment:
    """Test parameter adjustment logic"""

    def test_auto_adjust_nmap_parameters_timeout(self):
        """Test nmap parameter adjustment for timeout"""
        handler = IntelligentErrorHandler()
        original_params = {"scan_type": "-sS", "ports": "1-65535"}
        adjusted = handler.auto_adjust_parameters("nmap", ErrorType.TIMEOUT, original_params)

        assert isinstance(adjusted, dict)
        assert "timing" in adjusted or "timeout" in adjusted

    def test_auto_adjust_gobuster_parameters_rate_limited(self):
        """Test gobuster parameter adjustment for rate limiting"""
        handler = IntelligentErrorHandler()
        original_params = {"threads": "50"}
        adjusted = handler.auto_adjust_parameters("gobuster", ErrorType.RATE_LIMITED, original_params)

        assert isinstance(adjusted, dict)
        # Should reduce threads or add delay
        assert "threads" in adjusted or "delay" in adjusted

    def test_auto_adjust_generic_timeout(self):
        """Test generic timeout adjustment for unknown tool"""
        handler = IntelligentErrorHandler()
        original_params = {}
        adjusted = handler.auto_adjust_parameters("unknown_tool", ErrorType.TIMEOUT, original_params)

        assert "timeout" in adjusted
        assert "threads" in adjusted

    def test_auto_adjust_generic_rate_limited(self):
        """Test generic rate limit adjustment"""
        handler = IntelligentErrorHandler()
        original_params = {}
        adjusted = handler.auto_adjust_parameters("unknown_tool", ErrorType.RATE_LIMITED, original_params)

        assert "delay" in adjusted
        assert "threads" in adjusted

    def test_auto_adjust_generic_resource_exhausted(self):
        """Test generic resource exhaustion adjustment"""
        handler = IntelligentErrorHandler()
        original_params = {}
        adjusted = handler.auto_adjust_parameters("unknown_tool", ErrorType.RESOURCE_EXHAUSTED, original_params)

        assert "threads" in adjusted or "memory_limit" in adjusted

    def test_auto_adjust_preserves_original_params(self):
        """Test that adjustment preserves original parameters"""
        handler = IntelligentErrorHandler()
        original_params = {"custom_param": "value", "threads": "10"}
        adjusted = handler.auto_adjust_parameters("nmap", ErrorType.TIMEOUT, original_params)

        assert "custom_param" in adjusted
        assert adjusted["custom_param"] == "value"


class TestToolAlternatives:
    """Test tool alternative selection"""

    def test_get_alternative_for_nmap(self):
        """Test getting alternative for nmap"""
        handler = IntelligentErrorHandler()
        alternative = handler.get_alternative_tool("nmap", {})

        assert alternative is not None
        assert alternative in ["rustscan", "masscan", "zmap"]

    def test_get_alternative_for_gobuster(self):
        """Test getting alternative for gobuster"""
        handler = IntelligentErrorHandler()
        alternative = handler.get_alternative_tool("gobuster", {})

        assert alternative is not None
        assert alternative in ["feroxbuster", "dirsearch", "ffuf", "dirb"]

    def test_get_alternative_for_nuclei(self):
        """Test getting alternative for nuclei"""
        handler = IntelligentErrorHandler()
        alternative = handler.get_alternative_tool("nuclei", {})

        assert alternative is not None
        assert alternative in ["jaeles", "nikto", "w3af"]

    def test_get_alternative_with_no_privileges(self):
        """Test alternative selection requiring no privileges"""
        handler = IntelligentErrorHandler()
        context = {"require_no_privileges": True}
        alternative = handler.get_alternative_tool("nmap", context)

        # Should not return tools requiring privileges
        assert alternative not in ["nmap", "masscan"] if alternative else True

    def test_get_alternative_prefer_faster(self):
        """Test alternative selection preferring faster tools"""
        handler = IntelligentErrorHandler()
        context = {"prefer_faster_tools": True}
        alternative = handler.get_alternative_tool("subfinder", context)

        # Should not return slow tools
        assert alternative not in ["amass", "w3af"] if alternative else True

    def test_get_alternative_for_unknown_tool(self):
        """Test getting alternative for unknown tool"""
        handler = IntelligentErrorHandler()
        alternative = handler.get_alternative_tool("unknown_tool_xyz", {})

        assert alternative is None


class TestHumanEscalation:
    """Test human escalation logic"""

    def test_escalate_to_human_basic(self):
        """Test basic human escalation"""
        handler = IntelligentErrorHandler()
        context = ErrorContext(
            tool_name="nmap",
            target="example.com",
            parameters={"scan_type": "-sS"},
            error_type=ErrorType.PERMISSION_DENIED,
            error_message="Permission denied",
            attempt_count=3,
            timestamp=datetime.now(),
            stack_trace="traceback...",
            system_resources={"cpu_percent": 50.0}
        )

        escalation = handler.escalate_to_human(context)
        assert isinstance(escalation, dict)
        assert "timestamp" in escalation
        assert "tool" in escalation
        assert "error_type" in escalation
        assert "suggested_actions" in escalation

    def test_get_human_suggestions_permission_denied(self):
        """Test suggestions for permission denied"""
        handler = IntelligentErrorHandler()
        context = ErrorContext(
            tool_name="nmap",
            target="example.com",
            parameters={},
            error_type=ErrorType.PERMISSION_DENIED,
            error_message="Permission denied",
            attempt_count=1,
            timestamp=datetime.now(),
            stack_trace="",
            system_resources={}
        )

        suggestions = handler._get_human_suggestions(context)
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert any("sudo" in s.lower() for s in suggestions)

    def test_get_human_suggestions_tool_not_found(self):
        """Test suggestions for tool not found"""
        handler = IntelligentErrorHandler()
        context = ErrorContext(
            tool_name="gobuster",
            target="example.com",
            parameters={},
            error_type=ErrorType.TOOL_NOT_FOUND,
            error_message="command not found",
            attempt_count=1,
            timestamp=datetime.now(),
            stack_trace="",
            system_resources={}
        )

        suggestions = handler._get_human_suggestions(context)
        assert isinstance(suggestions, list)
        assert any("install" in s.lower() for s in suggestions)

    def test_get_human_suggestions_network_unreachable(self):
        """Test suggestions for network unreachable"""
        handler = IntelligentErrorHandler()
        context = ErrorContext(
            tool_name="nmap",
            target="example.com",
            parameters={},
            error_type=ErrorType.NETWORK_UNREACHABLE,
            error_message="network unreachable",
            attempt_count=1,
            timestamp=datetime.now(),
            stack_trace="",
            system_resources={}
        )

        suggestions = handler._get_human_suggestions(context)
        assert isinstance(suggestions, list)
        assert any("network" in s.lower() or "firewall" in s.lower() for s in suggestions)


class TestErrorHistory:
    """Test error history tracking"""

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.pids')
    def test_error_history_tracking(self, mock_pids, mock_disk, mock_mem, mock_cpu):
        """Test that errors are added to history"""
        mock_cpu.return_value = 50.0
        mock_mem.return_value = MagicMock(percent=60.0)
        mock_disk.return_value = MagicMock(percent=70.0)
        mock_pids.return_value = [1, 2, 3]

        handler = IntelligentErrorHandler()
        initial_count = len(handler.error_history)

        error = Exception("Test error")
        context = {'target': 'example.com', 'parameters': {}, 'attempt_count': 1}
        handler.handle_tool_failure("nmap", error, context)

        assert len(handler.error_history) == initial_count + 1

    def test_error_history_size_limit(self):
        """Test error history size limit"""
        handler = IntelligentErrorHandler()
        handler.max_history_size = 10

        # Add more errors than the limit
        for i in range(20):
            context = ErrorContext(
                tool_name="test",
                target="test",
                parameters={},
                error_type=ErrorType.UNKNOWN,
                error_message=f"error {i}",
                attempt_count=1,
                timestamp=datetime.now(),
                stack_trace="",
                system_resources={}
            )
            handler._add_to_history(context)

        assert len(handler.error_history) == 10

    def test_get_error_statistics_empty(self):
        """Test error statistics with empty history"""
        handler = IntelligentErrorHandler()
        stats = handler.get_error_statistics()

        assert isinstance(stats, dict)
        assert stats["total_errors"] == 0


class TestSystemResources:
    """Test system resource monitoring"""

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.pids')
    @patch('os.getloadavg')
    def test_get_system_resources_success(self, mock_loadavg, mock_pids, mock_disk, mock_mem, mock_cpu):
        """Test successful system resource retrieval"""
        mock_cpu.return_value = 45.5
        mock_mem.return_value = MagicMock(percent=60.2)
        mock_disk.return_value = MagicMock(percent=75.8)
        mock_pids.return_value = list(range(100))
        mock_loadavg.return_value = (1.5, 2.0, 2.5)

        handler = IntelligentErrorHandler()
        resources = handler._get_system_resources()

        assert isinstance(resources, dict)
        assert "cpu_percent" in resources
        assert "memory_percent" in resources
        assert "disk_percent" in resources
        assert "active_processes" in resources
        assert resources["cpu_percent"] == 45.5
        assert resources["memory_percent"] == 60.2
        assert resources["active_processes"] == 100

    @patch('psutil.cpu_percent')
    def test_get_system_resources_failure(self, mock_cpu):
        """Test system resource retrieval failure handling"""
        mock_cpu.side_effect = Exception("psutil error")

        handler = IntelligentErrorHandler()
        resources = handler._get_system_resources()

        assert isinstance(resources, dict)
        assert "error" in resources


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_classify_empty_error_message(self):
        """Test classification of empty error message"""
        handler = IntelligentErrorHandler()
        error_type = handler.classify_error("")
        assert error_type == ErrorType.UNKNOWN

    def test_classify_none_error_message(self):
        """Test handling of None error message"""
        handler = IntelligentErrorHandler()
        # Should not crash
        try:
            error_type = handler.classify_error(None)
        except AttributeError:
            # Expected behavior for None
            pass

    def test_auto_adjust_parameters_empty_params(self):
        """Test parameter adjustment with empty original params"""
        handler = IntelligentErrorHandler()
        adjusted = handler.auto_adjust_parameters("nmap", ErrorType.TIMEOUT, {})
        assert isinstance(adjusted, dict)

    def test_auto_adjust_parameters_unknown_error_type(self):
        """Test parameter adjustment with unknown error type"""
        handler = IntelligentErrorHandler()
        original_params = {"key": "value"}
        adjusted = handler.auto_adjust_parameters("nmap", ErrorType.UNKNOWN, original_params)
        # Should preserve original params
        assert "key" in adjusted

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.pids')
    def test_handle_tool_failure_with_empty_context(self, mock_pids, mock_disk, mock_mem, mock_cpu):
        """Test handling failure with minimal context"""
        mock_cpu.return_value = 50.0
        mock_mem.return_value = MagicMock(percent=60.0)
        mock_disk.return_value = MagicMock(percent=70.0)
        mock_pids.return_value = [1, 2, 3]

        handler = IntelligentErrorHandler()
        error = Exception("Test error")
        strategy = handler.handle_tool_failure("nmap", error, {})

        assert isinstance(strategy, RecoveryStrategy)


class TestRecoveryStrategy:
    """Test RecoveryStrategy dataclass"""

    def test_recovery_strategy_creation(self):
        """Test creating a recovery strategy"""
        strategy = RecoveryStrategy(
            action=RecoveryAction.RETRY_WITH_BACKOFF,
            parameters={"delay": 5},
            max_attempts=3,
            backoff_multiplier=2.0,
            success_probability=0.7,
            estimated_time=30
        )

        assert strategy.action == RecoveryAction.RETRY_WITH_BACKOFF
        assert strategy.max_attempts == 3
        assert strategy.backoff_multiplier == 2.0
        assert strategy.success_probability == 0.7


class TestErrorContext:
    """Test ErrorContext dataclass"""

    def test_error_context_creation(self):
        """Test creating an error context"""
        context = ErrorContext(
            tool_name="nmap",
            target="example.com",
            parameters={"scan_type": "-sS"},
            error_type=ErrorType.TIMEOUT,
            error_message="Connection timed out",
            attempt_count=2,
            timestamp=datetime.now(),
            stack_trace="traceback...",
            system_resources={"cpu_percent": 50.0}
        )

        assert context.tool_name == "nmap"
        assert context.error_type == ErrorType.TIMEOUT
        assert context.attempt_count == 2
        assert context.previous_errors == []

    def test_error_context_with_previous_errors(self):
        """Test error context with previous errors"""
        previous = ErrorContext(
            tool_name="gobuster",
            target="example.com",
            parameters={},
            error_type=ErrorType.TIMEOUT,
            error_message="timeout",
            attempt_count=1,
            timestamp=datetime.now(),
            stack_trace="",
            system_resources={}
        )

        context = ErrorContext(
            tool_name="nmap",
            target="example.com",
            parameters={},
            error_type=ErrorType.NETWORK_UNREACHABLE,
            error_message="unreachable",
            attempt_count=1,
            timestamp=datetime.now(),
            stack_trace="",
            system_resources={},
            previous_errors=[previous]
        )

        assert len(context.previous_errors) == 1
        assert context.previous_errors[0].tool_name == "gobuster"
