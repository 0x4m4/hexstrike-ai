import pytest
from unittest.mock import Mock, patch, MagicMock
from hexstrike_server import ParameterOptimizer, ErrorType

class TestParameterOptimizer:
    @pytest.fixture
    def optimizer(self):
        return ParameterOptimizer()
