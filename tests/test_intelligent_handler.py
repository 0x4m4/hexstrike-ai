import pytest
from unittest.mock import Mock, patch, MagicMock
from hexstrike_server import IntelligentErrorHandler, ErrorType, RecoveryAction

class TestIntelligentErrorHandler:
    @pytest.fixture
    def handler(self):
        return IntelligentErrorHandler()

    @pytest.mark.parametrize("error_msg, expected_type", [
        ("operation timed out", ErrorType.TIMEOUT),
        ("permission denied for /root", ErrorType.PERMISSION_DENIED),
        ("connection refused", ErrorType.NETWORK_UNREACHABLE),
        ("rate limit exceeded (429)", ErrorType.RATE_LIMITED),
        ("command 'amass' not found", ErrorType.TOOL_NOT_FOUND),
        ("invalid option --help", ErrorType.INVALID_PARAMETERS),
        ("no space left on device", ErrorType.RESOURCE_EXHAUSTED),
        ("invalid credentials for api", ErrorType.AUTHENTICATION_FAILED),
        ("dns resolution failed", ErrorType.TARGET_UNREACHABLE),
        ("json decode error", ErrorType.PARSING_ERROR),
        ("totally unknown weird error", ErrorType.UNKNOWN),
    ])
    def test_classify_error_patterns(self, handler, error_msg, expected_type):
        assert handler.classify_error(error_msg) == expected_type

    def test_classify_error_exceptions(self, handler):
        assert handler.classify_error("msg", TimeoutError()) == ErrorType.TIMEOUT
        assert handler.classify_error("msg", PermissionError()) == ErrorType.PERMISSION_DENIED
        assert handler.classify_error("msg", ConnectionError()) == ErrorType.NETWORK_UNREACHABLE
        assert handler.classify_error("msg", FileNotFoundError()) == ErrorType.TOOL_NOT_FOUND

    def test_select_best_strategy_escalation(self, handler):
        # Mock ErrorContext
        from hexstrike_server import ErrorContext
        from datetime import datetime
        
        def create_context(attempts):
            return ErrorContext(
                tool_name="nmap",
                target="example.com",
                parameters={},
                error_type=ErrorType.TIMEOUT,
                error_message="timeout",
                attempt_count=attempts,
                timestamp=datetime.now(),
                stack_trace="",
                system_resources={}
            )

        # First attempt for TIMEOUT should NOT be ESCALATE_TO_HUMAN
        strategies = handler.recovery_strategies[ErrorType.TIMEOUT]
        strategy = handler._select_best_strategy(strategies, create_context(1))
        assert strategy.action != RecoveryAction.ESCALATE_TO_HUMAN

        # After max_attempts (TIMEOUT max_attempts is 3 for RETRY_WITH_BACKOFF)
        # It should escalate to human
        strategy = handler._select_best_strategy(strategies, create_context(10))
        assert strategy.action == RecoveryAction.ESCALATE_TO_HUMAN

    @patch('psutil.cpu_percent', return_value=95.0)
    @patch('psutil.virtual_memory')
    def test_get_system_resources(self, mock_mem, mock_cpu, handler):
        mock_mem.return_value.percent = 90.0
        resources = handler._get_system_resources()
        assert resources["cpu_percent"] == 95.0
        assert resources["memory_percent"] == 90.0
