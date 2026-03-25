import pytest
from unittest.mock import Mock, patch, MagicMock
from hexstrike_server import IntelligentErrorHandler, ErrorType, RecoveryAction

class TestIntelligentErrorHandler:
    @pytest.fixture
    def handler(self):
        return IntelligentErrorHandler()
