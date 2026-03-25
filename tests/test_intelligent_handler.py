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
