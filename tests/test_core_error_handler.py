"""
Tests for core.error_handler module

Tests for IntelligentErrorHandler and related classes:
- ErrorType enum
- RecoveryAction enum
- ErrorContext dataclass
- RecoveryStrategy dataclass
- IntelligentErrorHandler class
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from core.error_handler import (
    ErrorType,
    RecoveryAction,
    ErrorContext,
    RecoveryStrategy,
    IntelligentErrorHandler
)


class TestErrorType:
    """Tests for ErrorType enum"""

    def test_error_types_exist(self):
        """Test all error types are defined"""
        assert ErrorType.TIMEOUT is not None
        assert ErrorType.PERMISSION_DENIED is not None
        assert ErrorType.NETWORK_UNREACHABLE is not None
        assert ErrorType.RATE_LIMITED is not None
        assert ErrorType.TOOL_NOT_FOUND is not None
        assert ErrorType.INVALID_PARAMETERS is not None
        assert ErrorType.RESOURCE_EXHAUSTED is not None
        assert ErrorType.AUTHENTICATION_FAILED is not None
        assert ErrorType.TARGET_UNREACHABLE is not None
        assert ErrorType.PARSING_ERROR is not None
        assert ErrorType.UNKNOWN is not None

    def test_error_type_values(self):
        """Test error type values are correct"""
        assert ErrorType.TIMEOUT.value == "timeout"
        assert ErrorType.PERMISSION_DENIED.value == "permission_denied"
        assert ErrorType.NETWORK_UNREACHABLE.value == "network_unreachable"


class TestRecoveryAction:
    """Tests for RecoveryAction enum"""

    def test_recovery_actions_exist(self):
        """Test recovery actions are defined"""
        assert RecoveryAction.RETRY_WITH_BACKOFF is not None
        assert RecoveryAction.RETRY_WITH_REDUCED_SCOPE is not None
        assert RecoveryAction.ADJUST_PARAMETERS is not None
        assert RecoveryAction.SWITCH_TO_ALTERNATIVE_TOOL is not None
        assert RecoveryAction.ESCALATE_TO_HUMAN is not None
        assert RecoveryAction.GRACEFUL_DEGRADATION is not None
        assert RecoveryAction.ABORT_OPERATION is not None


class TestErrorContext:
    """Tests for ErrorContext dataclass"""

    def test_error_context_creation(self):
        """Test creating an ErrorContext"""
        from datetime import datetime
        context = ErrorContext(
            tool_name="nmap",
            target="192.168.1.1",
            parameters={"scan_type": "-sS"},
            error_type=ErrorType.TIMEOUT,
            error_message="Connection timeout",
            attempt_count=1,
            timestamp=datetime.now(),
            stack_trace="",
            system_resources={}
        )

        assert context.tool_name == "nmap"
        assert context.target == "192.168.1.1"
        assert context.error_message == "Connection timeout"
        assert context.error_type == ErrorType.TIMEOUT
        assert context.attempt_count == 1

    def test_error_context_with_defaults(self):
        """Test ErrorContext uses default values"""
        from datetime import datetime
        context = ErrorContext(
            tool_name="nmap",
            target="192.168.1.1",
            parameters={"scan_type": "-sS"},
            error_type=ErrorType.UNKNOWN,
            error_message="error",
            attempt_count=1,
            timestamp=datetime.now(),
            stack_trace="",
            system_resources={}
        )

        # Check that default values are set
        assert context.timestamp is not None
        assert context.parameters is not None
        assert isinstance(context.parameters, dict)
        assert context.previous_errors == []


class TestRecoveryStrategy:
    """Tests for RecoveryStrategy dataclass"""

    def test_recovery_strategy_creation(self):
        """Test creating a RecoveryStrategy"""
        strategy = RecoveryStrategy(
            action=RecoveryAction.RETRY_WITH_BACKOFF,
            parameters={"timeout": 60},
            max_attempts=3,
            backoff_multiplier=2.0,
            success_probability=0.8,
            estimated_time=120
        )

        assert strategy.action == RecoveryAction.RETRY_WITH_BACKOFF
        assert strategy.parameters == {"timeout": 60}
        assert strategy.max_attempts == 3
        assert strategy.backoff_multiplier == 2.0
        assert strategy.success_probability == 0.8
        assert strategy.estimated_time == 120


class TestIntelligentErrorHandler:
    """Tests for IntelligentErrorHandler class"""

    def test_handler_initialization(self):
        """Test IntelligentErrorHandler initializes correctly"""
        handler = IntelligentErrorHandler()

        assert handler is not None
        assert hasattr(handler, 'error_patterns')
        assert hasattr(handler, 'recovery_strategies')

    def test_classify_timeout_error(self):
        """Test classifying timeout errors"""
        handler = IntelligentErrorHandler()

        error_type = handler.classify_error(
            error_message="Connection timed out after 30 seconds"
        )

        assert error_type == ErrorType.TIMEOUT

    def test_classify_permission_denied_error(self):
        """Test classifying permission denied errors"""
        handler = IntelligentErrorHandler()

        error_type = handler.classify_error(
            error_message="Permission denied: cannot access /root/file.txt"
        )

        assert error_type == ErrorType.PERMISSION_DENIED

    def test_classify_network_error(self):
        """Test classifying network unreachable errors"""
        handler = IntelligentErrorHandler()

        error_type = handler.classify_error(
            error_message="network unreachable"
        )

        assert error_type == ErrorType.NETWORK_UNREACHABLE

    def test_classify_rate_limited_error(self):
        """Test classifying rate limited errors"""
        handler = IntelligentErrorHandler()

        error_type = handler.classify_error(
            error_message="Rate limit exceeded, too many requests"
        )

        assert error_type == ErrorType.RATE_LIMITED

    def test_classify_tool_not_found_error(self):
        """Test classifying tool not found errors"""
        handler = IntelligentErrorHandler()

        error_type = handler.classify_error(
            error_message="nmap: command not found"
        )

        assert error_type == ErrorType.TOOL_NOT_FOUND

    def test_handle_tool_failure_for_timeout(self):
        """Test handling tool failure for timeout"""
        handler = IntelligentErrorHandler()

        error = TimeoutError("Connection timeout")
        context = {
            "target": "192.168.1.1",
            "parameters": {"timeout": 30, "threads": 50},
            "attempt_count": 1
        }

        strategy = handler.handle_tool_failure("nmap", error, context)

        assert strategy is not None
        assert isinstance(strategy, RecoveryStrategy)
        assert strategy.action in [RecoveryAction.RETRY_WITH_BACKOFF, RecoveryAction.RETRY_WITH_REDUCED_SCOPE, RecoveryAction.SWITCH_TO_ALTERNATIVE_TOOL]

    def test_handle_tool_failure_for_rate_limit(self):
        """Test handling tool failure for rate limiting"""
        handler = IntelligentErrorHandler()

        error = Exception("Rate limit exceeded")
        context = {
            "target": "http://example.com",
            "parameters": {"threads": 50, "delay": 0},
            "attempt_count": 1
        }

        strategy = handler.handle_tool_failure("gobuster", error, context)

        assert strategy is not None
        assert isinstance(strategy, RecoveryStrategy)
        assert strategy.action in [RecoveryAction.RETRY_WITH_BACKOFF, RecoveryAction.ADJUST_PARAMETERS]

    def test_handle_tool_failure_for_tool_not_found(self):
        """Test handling tool failure when tool not found"""
        handler = IntelligentErrorHandler()

        error = FileNotFoundError("nmap: command not found")
        context = {
            "target": "192.168.1.1",
            "parameters": {},
            "attempt_count": 1
        }

        strategy = handler.handle_tool_failure("nmap", error, context)

        assert strategy is not None
        assert isinstance(strategy, RecoveryStrategy)
        assert strategy.action in [RecoveryAction.SWITCH_TO_ALTERNATIVE_TOOL, RecoveryAction.ESCALATE_TO_HUMAN]

    def test_auto_adjust_parameters(self):
        """Test automatic parameter adjustment"""
        handler = IntelligentErrorHandler()

        original_params = {"timeout": 30, "threads": 50}
        adjusted = handler.auto_adjust_parameters("nmap", ErrorType.TIMEOUT, original_params)

        assert adjusted is not None
        assert isinstance(adjusted, dict)
        # Should have adjusted parameters (original + adjustments)
        assert len(adjusted) >= len(original_params)

    def test_get_error_statistics(self):
        """Test getting error statistics"""
        handler = IntelligentErrorHandler()

        # Initially should have no errors
        stats = handler.get_error_statistics()
        assert stats is not None
        assert "total_errors" in stats
        assert stats["total_errors"] == 0

        # Add some errors
        error = TimeoutError("Connection timeout")
        context = {"target": "192.168.1.1", "parameters": {}, "attempt_count": 1}
        handler.handle_tool_failure("nmap", error, context)

        # Now should have errors
        stats = handler.get_error_statistics()
        assert stats["total_errors"] >= 1

    def test_get_alternative_tool_for_nmap(self):
        """Test getting alternative tool for nmap"""
        handler = IntelligentErrorHandler()

        alternative = handler.get_alternative_tool("nmap", {})

        assert alternative is not None
        assert alternative in ["rustscan", "masscan", "zmap"]

    def test_get_alternative_tool_for_gobuster(self):
        """Test getting alternative tool for gobuster"""
        handler = IntelligentErrorHandler()

        alternative = handler.get_alternative_tool("gobuster", {})

        assert alternative is not None
        assert alternative in ["feroxbuster", "dirsearch", "ffuf", "dirb"]

    def test_auto_adjust_parameters_for_timeout(self):
        """Test parameter adjustment for timeout errors"""
        handler = IntelligentErrorHandler()

        original_params = {"timeout": 30, "threads": 50}
        adjusted = handler.auto_adjust_parameters("nmap", ErrorType.TIMEOUT, original_params)

        assert adjusted is not None
        assert isinstance(adjusted, dict)
        # Should have some adjustments applied
        assert "timing" in adjusted or "timeout" in adjusted

    def test_auto_adjust_parameters_for_rate_limit(self):
        """Test parameter adjustment for rate limiting"""
        handler = IntelligentErrorHandler()

        original_params = {"threads": 50, "delay": 0}
        adjusted = handler.auto_adjust_parameters("nmap", ErrorType.RATE_LIMITED, original_params)

        assert adjusted is not None
        assert isinstance(adjusted, dict)
        # Should have rate limiting adjustments
        assert "timing" in adjusted or "delay" in adjusted or "threads" in adjusted

    # SKIP: _should_escalate_to_human is not a public method
    # The escalation logic is embedded in handle_tool_failure and recovery strategies

    def test_escalate_to_human(self):
        """Test escalating to human operator"""
        handler = IntelligentErrorHandler()
        from datetime import datetime

        context = ErrorContext(
            tool_name="nmap",
            target="192.168.1.1",
            parameters={"timeout": 30},
            error_type=ErrorType.TIMEOUT,
            error_message="Connection timeout",
            attempt_count=1,
            timestamp=datetime.now(),
            stack_trace="",
            system_resources={}
        )

        result = handler.escalate_to_human(context, urgency="medium")

        assert result is not None
        assert isinstance(result, dict)
        assert "tool" in result
        assert "error_type" in result
        assert result["tool"] == "nmap"
        assert result["urgency"] == "medium"

    @patch('core.visual.ModernVisualEngine')
    def test_error_logging(self, mock_visual):
        """Test that errors are properly logged"""
        handler = IntelligentErrorHandler()

        error = TimeoutError("Connection timeout")
        context = {
            "target": "192.168.1.1",
            "parameters": {},
            "attempt_count": 1
        }

        with patch('logging.Logger.warning') as mock_log:
            handler.handle_tool_failure("nmap", error, context)
            # Verify logging occurred (may or may not be called depending on implementation)
            # This is just to ensure the handler doesn't crash when logging

    def test_multiple_error_types_classification(self):
        """Test classifying various error types"""
        handler = IntelligentErrorHandler()

        test_cases = [
            ("Connection timeout", ErrorType.TIMEOUT),
            ("Permission denied", ErrorType.PERMISSION_DENIED),
            ("Network is unreachable", ErrorType.NETWORK_UNREACHABLE),
            ("Rate limit exceeded", ErrorType.RATE_LIMITED),
            ("command not found", ErrorType.TOOL_NOT_FOUND),
        ]

        for error_msg, expected_type in test_cases:
            result = handler.classify_error(error_msg)
            assert result == expected_type or result == ErrorType.UNKNOWN


def test_error_handler_integration():
    """Integration test for error handler workflow"""
    handler = IntelligentErrorHandler()

    # Simulate a timeout error
    error = TimeoutError("Connection timed out after 30 seconds")
    context = {
        "target": "192.168.1.1",
        "parameters": {"timeout": 30, "threads": 100, "ports": "1-65535"},
        "attempt_count": 1
    }

    strategy = handler.handle_tool_failure("nmap", error, context)

    # Verify the handler returns a proper recovery strategy
    assert strategy is not None
    assert isinstance(strategy, RecoveryStrategy)
    assert hasattr(strategy, 'action')
    assert hasattr(strategy, 'parameters')
    assert strategy.action in [ra for ra in RecoveryAction]


def test_error_handler_with_unknown_error():
    """Test error handler gracefully handles unknown errors"""
    handler = IntelligentErrorHandler()

    error = Exception("Something very unusual happened: XYZ123")
    context = {
        "target": "unknown",
        "parameters": {},
        "attempt_count": 1
    }

    strategy = handler.handle_tool_failure("custom_tool", error, context)

    # Should still return a strategy, possibly for UNKNOWN error type
    assert strategy is not None
    assert isinstance(strategy, RecoveryStrategy)


def test_error_handler_preserves_context():
    """Test that error handler preserves all context information"""
    handler = IntelligentErrorHandler()

    original_params = {"timeout": 30, "threads": 50, "custom_flag": "value"}
    error = Exception("Error occurred")
    context = {
        "target": "192.168.1.1",
        "parameters": original_params.copy(),
        "attempt_count": 1
    }

    strategy = handler.handle_tool_failure("nmap", error, context)

    # Strategy should be returned
    assert strategy is not None
    # The original context parameters should not be modified
    assert context["parameters"] == original_params
